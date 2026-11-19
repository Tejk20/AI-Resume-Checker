"""Idempotent fictional demo workspace; all scores come from real inference."""
import hashlib
import logging
from pathlib import Path
from uuid import UUID, uuid5
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models import Job, UploadBatch, Candidate, ResumeFile, MatchResult
from app.models.entities import now
from app.services.documents import extract_document
from app.services.extraction import parse_job, parse_resume
from app.services.workers import process_matches

NAMESPACE = UUID('81923993-2cb1-45e3-b107-ec523068681e')
ROOT = Path(__file__).resolve().parents[3]/'sample_data'
ROLES = {'python_backend':'Python Backend Developer',
         'react_fullstack':'React Full Stack Developer', 'ai_ml':'AI/ML Engineer'}


def seed_demo():
    try:
        for slug, title in ROLES.items():
            seed_job(slug, title)
    except Exception as exc:
        logging.error('Demo data initialization failed (%s); will retry on next startup.', type(exc).__name__)


def seed_job(slug, title):
    jid = uuid5(NAMESPACE, 'job:'+slug)
    with SessionLocal() as db:
        job = db.get(Job, jid)
        if job and db.scalar(select(MatchResult.id).where(MatchResult.job_id==jid).limit(1)):
            return
        if not job:
            raw = (ROOT/'job_descriptions'/f'{slug}.txt').read_text()
            job = Job(id=jid, title=title, raw_text=raw, is_demo=True, **parse_job(raw))
            db.add(job); db.flush()
            paths = sorted(p for p in (ROOT/'synthetic_resumes').iterdir() if p.suffix in {'.pdf','.docx'})
            batch = UploadBatch(job_id=jid, total_files=len(paths), processed_files=len(paths),
                                failed_files=0, status='completed', completed_at=now())
            db.add(batch); db.flush()
            for path in paths:
                content = path.read_bytes()
                text, mime = extract_document(path.name, content)
                candidate = Candidate(batch_id=batch.id, **parse_resume(text))
                db.add(candidate); db.flush()
                db.add(ResumeFile(candidate_id=candidate.id, original_filename=path.name,
                    file_path=str(path), mime_type=mime, sha256_hash=hashlib.sha256(content).hexdigest(),
                    extraction_status='completed'))
            db.commit()
        job.match_status='processing'; job.match_error=None
        db.commit()
    process_matches(jid)
