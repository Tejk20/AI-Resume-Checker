import hashlib
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore
from uuid import UUID
from sqlalchemy import select
from app.core.database import SessionLocal
from app.core.config import settings, WEIGHTS, ALGORITHM_VERSION
from app.models import Job, UploadBatch, Candidate, ResumeFile, MatchResult, MatchingRun
from app.models.entities import now
from app.services.documents import extract_document, DocumentError
from app.services.extraction import parse_resume
from app.services.semantic import SemanticEvaluation, SemanticError
from app.services.scoring import score_candidate
from app.services.history import archive_result

logger = logging.getLogger(__name__)
EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix='resume-worker')
SLOTS = BoundedSemaphore(5)


def submit_reserved(fn, *args):
    def run():
        try:
            fn(*args)
        finally:
            SLOTS.release()
    try:
        return EXECUTOR.submit(run)
    except Exception:
        SLOTS.release()
        raise


def process_batch(batch_id: UUID, manifest: list[dict]):
    with SessionLocal() as db:
        batch = db.get(UploadBatch,batch_id)
        batch.status = 'processing'; db.commit()
        for item in manifest:
            path = Path(item['path'])
            try:
                content = path.read_bytes()
                text, mime = extract_document(item['name'],content,settings.max_file_mb)
                digest = hashlib.sha256(content).hexdigest()
                duplicate = db.scalar(select(ResumeFile.id).join(Candidate).join(UploadBatch).where(UploadBatch.job_id==batch.job_id, ResumeFile.sha256_hash==digest))
                if duplicate: raise DocumentError('Duplicate resume already processed for this job.')
                candidate = Candidate(batch_id=batch_id,**parse_resume(text))
                db.add(candidate); db.flush()
                db.add(ResumeFile(candidate_id=candidate.id,original_filename=item['name'],file_path=str(path),mime_type=mime,
                                  sha256_hash=digest,extraction_status='completed'))
                batch.processed_files += 1
                db.commit()
            except Exception as exc:
                db.rollback()
                batch = db.get(UploadBatch,batch_id)
                message = str(exc) if isinstance(exc,DocumentError) else 'Processing failed; retry with a readable document.'
                if not isinstance(exc,DocumentError): logger.error('Resume processing failed (%s)', type(exc).__name__)
                batch.failed_files += 1
                batch.errors = [*batch.errors,dict(filename=item['name'],error=message)]
                db.commit()
                path.unlink(missing_ok=True)
        batch.status = 'completed' if not batch.failed_files else 'partially_completed' if batch.processed_files else 'failed'
        batch.completed_at = now(); db.commit()


def process_matches(job_id: UUID, run_id: UUID | None = None):
    with SessionLocal() as db:
        job = db.get(Job,job_id)
        run = db.get(MatchingRun, run_id) if run_id else None
        if run is None:
            run = MatchingRun(job_id=job_id, embedding_model=settings.embedding_model,
                scoring_config={'default_weights': dict(WEIGHTS)}, algorithm_version=ALGORITHM_VERSION)
            db.add(run); db.commit()
        run_id = run.id
        try:
            evaluation = SemanticEvaluation(job)
            candidates = db.scalars(select(Candidate).join(UploadBatch).where(UploadBatch.job_id==job_id)).all()
            config = {'default_weights': dict(WEIGHTS), 'unknown_evidence_score': 50,
                      'semantic': evaluation.metadata}
            run.scoring_config = config
            run.candidate_count = len(candidates)
            prepared = evaluation.prepare_many(candidates)
            # Atomic evaluation: old results remain consistent until all new results succeed.
            for candidate, passages in zip(candidates, prepared):
                semantic, evidence = evaluation.compare_prepared(passages)
                values = score_candidate(job,candidate,semantic,evidence)
                values.update(embedding_model=evaluation.model_id, scoring_config=config, run_id=run_id)
                result = db.scalar(select(MatchResult).where(MatchResult.job_id==job_id,MatchResult.candidate_id==candidate.id))
                if result:
                    archive_result(db, result)
                    for key,value in values.items(): setattr(result,key,value)
                    result.created_at = now()
                else: db.add(MatchResult(job_id=job_id,candidate_id=candidate.id,**values))
            run.status = 'completed'; run.completed_at = now()
            job.match_status = 'completed'; job.match_error = None; db.commit()
        except Exception as exc:
            db.rollback()
            logger.error('Matching failed (%s)',type(exc).__name__)
            job = db.get(Job,job_id)
            run = db.get(MatchingRun, run_id)
            run.status = 'failed'; run.completed_at = now()
            run.error = str(exc) if isinstance(exc, SemanticError) else 'Matching failed; verify model and database configuration, then retry.'
            job.match_status = 'failed'
            job.match_error = run.error
            db.commit()


def recover_interrupted():
    # One API process only. No worker can still be running when lifespan starts.
    with SessionLocal() as db:
        for batch in db.scalars(select(UploadBatch).where(UploadBatch.status.in_(['pending','processing']))):
            remaining = batch.total_files-batch.processed_files-batch.failed_files
            batch.failed_files += remaining
            batch.errors = [*batch.errors,dict(filename='batch',error='Server restarted; unprocessed files must be uploaded again.')]
            batch.status = 'partially_completed' if batch.processed_files else 'failed'
            batch.completed_at = now()
        for job in db.scalars(select(Job).where(Job.match_status=='processing')):
            job.match_status='failed'; job.match_error='Server restarted during matching; run matching again.'
        for run in db.scalars(select(MatchingRun).where(MatchingRun.status=='processing')):
            run.status='failed'; run.error='Server restarted during matching; run matching again.'; run.completed_at=now()
        db.commit()
