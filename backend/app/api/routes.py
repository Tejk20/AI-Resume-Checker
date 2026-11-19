from pathlib import Path
from uuid import UUID, uuid4
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy import select, func, delete
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.config import settings, WEIGHTS, ALGORITHM_VERSION
from app.models import Job, UploadBatch, Candidate, MatchResult, MatchingRun, MatchResultHistory
from app.schemas.contracts import JobCreate, JobPatch, JobOut, BatchOut, CandidateOut, MatchOut, JobsPage, CandidatesPage, RankingsPage
from app.schemas.contracts import MatchingRunOut, HistoryOut
from app.services.history import archive_result
from app.services.extraction import parse_job
from app.services.documents import extract_document, DocumentError, safe_filename
from app.services.workers import SLOTS, submit_reserved, process_batch, process_matches
from app.services.auth import current_user, visible_jobs, check_origin

router = APIRouter(prefix='/api/v1', dependencies=[Depends(check_origin)])
DB = Annotated[Session, Depends(get_db)]


def job_or_404(db, job_id, user=None, write=False):
    if write and settings.auth_required and not user:
        raise HTTPException(401, 'Sign in to use your recruiter workspace.')
    job = db.scalar(select(Job).where(Job.id==job_id, visible_jobs(user)))
    if not job: raise HTTPException(404,'Job not found')
    if write and job.is_demo:
        raise HTTPException(403, 'Sample jobs are read-only. Create your own job to upload resumes and run matching.')
    return job


def active_upload(db, job_id):
    return db.scalar(select(UploadBatch.id).where(UploadBatch.job_id==job_id,UploadBatch.status.in_(['pending','processing'])))


@router.post('/jobs', response_model=JobOut, status_code=201)
def create_job(payload: JobCreate, db: DB, user=Depends(current_user)):
    if settings.auth_required and not user:
        raise HTTPException(401, 'Sign in to create a job.')
    job = Job(**payload.model_dump(), **parse_job(payload.raw_text), owner_id=user.id if user else None)
    db.add(job); db.commit(); db.refresh(job)
    return job


@router.post('/jobs/upload', response_model=JobOut, status_code=201)
def upload_job(db: DB, title: str = Form(min_length=2,max_length=200), file: UploadFile = File(), user=Depends(current_user)):
    if settings.auth_required and not user:
        raise HTTPException(401, 'Sign in to create a job.')
    content = file.file.read(settings.max_file_mb*1024*1024+1)
    try: text,_ = extract_document(file.filename or '',content,settings.max_file_mb)
    except DocumentError as exc: raise HTTPException(422,str(exc))
    return create_job(JobCreate(title=title,raw_text=text),db,user)


@router.get('/jobs',response_model=JobsPage)
def jobs(db: DB, offset: int=Query(0,ge=0), limit: int=Query(50,ge=1,le=100), user=Depends(current_user)):
    query=select(Job).where(visible_jobs(user))
    return dict(items=db.scalars(query.order_by(Job.is_demo,Job.created_at.desc()).offset(offset).limit(limit)).all(),total=db.scalar(select(func.count()).select_from(query.subquery())))


@router.get('/jobs/{job_id}',response_model=JobOut)
def get_job(job_id: UUID,db: DB,user=Depends(current_user)): return job_or_404(db,job_id,user)


@router.patch('/jobs/{job_id}',response_model=JobOut)
def patch_job(job_id: UUID,payload: JobPatch,db: DB,user=Depends(current_user)):
    job = job_or_404(db,job_id,user,write=True)
    if job.match_status=='processing' or active_upload(db,job_id): raise HTTPException(409,'Wait for current processing to finish.')
    values = payload.model_dump(exclude_unset=True)
    required = values.get('required_skills',job.required_skills)
    preferred = values.get('preferred_skills',job.preferred_skills)
    if set(required)&set(preferred): raise HTTPException(422,'Required and preferred skills must be distinct')
    for key,value in values.items(): setattr(job,key,value)
    for result in db.scalars(select(MatchResult).where(MatchResult.job_id==job_id)):
        archive_result(db, result)
    db.flush()
    db.execute(delete(MatchResult).where(MatchResult.job_id==job_id))
    job.match_status='idle'; job.match_error=None
    db.commit(); db.refresh(job)
    return job


@router.post('/jobs/{job_id}/resumes',response_model=BatchOut,status_code=202)
def upload_resumes(job_id: UUID,db: DB,files: list[UploadFile] = File(),user=Depends(current_user)):
    job = job_or_404(db,job_id,user,write=True)
    if not 1<=len(files)<=settings.max_batch_files: raise HTTPException(422,'Upload between 1 and 50 files.')
    if job.match_status=='processing' or active_upload(db,job_id): raise HTTPException(409,'Wait for current job processing to finish.')
    if not SLOTS.acquire(blocking=False): raise HTTPException(503,'Processing queue is full; retry shortly.')
    paths, manifest, errors = [], [], []
    try:
        batch = UploadBatch(job_id=job_id,total_files=len(files))
        db.add(batch); db.flush()
        settings.upload_dir.mkdir(parents=True,exist_ok=True)
        for file in files:
            name = safe_filename(file.filename or 'document')
            suffix = Path(name).suffix.lower()
            data = file.file.read(settings.max_file_mb*1024*1024+1)
            if suffix not in ['.pdf','.docx'] or len(data)>settings.max_file_mb*1024*1024:
                errors.append(dict(filename=name,error='Only PDF/DOCX files up to the configured size limit are supported.')); continue
            path = settings.upload_dir.resolve() / f'{uuid4()}{suffix}'
            path.write_bytes(data); paths.append(path)
            manifest.append(dict(name=name,path=str(path)))
        batch.errors=errors; batch.failed_files=len(errors)
        job.match_status='idle'; job.match_error=None
        db.commit(); db.refresh(batch)
    except Exception:
        db.rollback(); SLOTS.release()
        for path in paths: path.unlink(missing_ok=True)
        raise
    submit_reserved(process_batch,batch.id,manifest)
    return batch


@router.get('/batches/{batch_id}',response_model=BatchOut)
def get_batch(batch_id: UUID,db: DB,user=Depends(current_user)):
    batch = db.get(UploadBatch,batch_id)
    if not batch: raise HTTPException(404,'Batch not found')
    job_or_404(db,batch.job_id,user)
    return batch


@router.get('/jobs/{job_id}/candidates',response_model=CandidatesPage)
def candidates(job_id: UUID,db: DB,offset: int=Query(0,ge=0),limit: int=Query(50,ge=1,le=100),user=Depends(current_user)):
    job_or_404(db,job_id,user)
    query = select(Candidate).join(UploadBatch).where(UploadBatch.job_id==job_id)
    return dict(items=db.scalars(query.order_by(Candidate.created_at).offset(offset).limit(limit)).all(),total=db.scalar(select(func.count()).select_from(query.subquery())))


@router.get('/candidates/{candidate_id}',response_model=CandidateOut)
def candidate_detail(candidate_id: UUID,db: DB,user=Depends(current_user)):
    candidate = db.get(Candidate,candidate_id)
    if not candidate: raise HTTPException(404,'Candidate not found')
    job_or_404(db,candidate.batch.job_id,user)
    result = CandidateOut.model_validate(candidate)
    result.original_filename = candidate.resume_file.original_filename if candidate.resume_file else None
    return result


@router.post('/jobs/{job_id}/match',status_code=202)
def match(job_id: UUID,db: DB,user=Depends(current_user)):
    job=job_or_404(db,job_id,user,write=True)
    if job.match_status=='processing' or active_upload(db,job_id): raise HTTPException(409,'Wait for current job processing to finish.')
    count=db.scalar(select(func.count()).select_from(Candidate).join(UploadBatch).where(UploadBatch.job_id==job_id))
    if not count: raise HTTPException(422,'Upload readable resumes before matching.')
    if not SLOTS.acquire(blocking=False): raise HTTPException(503,'Processing queue is full; retry shortly.')
    try:
        run=MatchingRun(job_id=job_id,embedding_model=settings.embedding_model,
            scoring_config={'default_weights':dict(WEIGHTS)},algorithm_version=ALGORITHM_VERSION,
            candidate_count=count)
        db.add(run); db.flush()
        job.match_status='processing'; job.match_error=None; db.commit()
    except Exception:
        SLOTS.release(); raise
    submit_reserved(process_matches,job_id,run.id)
    return dict(job_id=str(job_id),run_id=str(run.id),status='processing')


@router.get('/jobs/{job_id}/rankings',response_model=RankingsPage)
def rankings(job_id: UUID,db: DB,search: str=Query('',max_length=100),min_score: float=Query(0,ge=0,le=100),
             sort: str=Query('score',pattern='^(score|experience)$'),offset: int=Query(0,ge=0),limit: int=Query(20,ge=1,le=100),user=Depends(current_user)):
    job_or_404(db,job_id,user)
    query=select(MatchResult).join(Candidate).where(MatchResult.job_id==job_id,MatchResult.overall_score>=min_score)
    if search: query=query.where(Candidate.name.ilike('%'+search.replace('%','\\%').replace('_','\\_')+'%',escape='\\'))
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    if sort=='experience':
        # JSON evidence contains the JD-specific years; total years are never substituted.
        query=query.order_by(MatchResult.explanation['relevant_years'].as_float().desc().nulls_last())
    query=query.order_by(MatchResult.overall_score.desc(),MatchResult.candidate_id).options(joinedload(MatchResult.candidate))
    return dict(items=db.scalars(query.offset(offset).limit(limit)).all(),total=total)


@router.get('/jobs/{job_id}/matches/{candidate_id}',response_model=MatchOut)
def match_detail(job_id: UUID,candidate_id: UUID,db: DB,user=Depends(current_user)):
    job_or_404(db,job_id,user)
    result=db.scalar(select(MatchResult).where(MatchResult.job_id==job_id,MatchResult.candidate_id==candidate_id))
    if not result: raise HTTPException(404,'Match not found; run matching first.')
    return result


@router.get('/dashboard')
def dashboard(db: DB,user=Depends(current_user)):
    visible=select(Job.id).where(visible_jobs(user))
    scores=db.scalars(select(MatchResult.overall_score).where(MatchResult.job_id.in_(visible))).all()
    buckets=[dict(name=label,count=sum(a<=s<b for s in scores)) for label,a,b in [('0–39',0,40),('40–59',40,60),('60–79',60,80),('80–100',80,101)]]
    batches=db.scalars(select(UploadBatch).where(UploadBatch.job_id.in_(visible)).order_by(UploadBatch.created_at.desc()).limit(5)).all()
    return dict(total_jobs=db.scalar(select(func.count()).select_from(Job).where(visible_jobs(user))),total_resumes=db.scalar(select(func.count()).select_from(Candidate).join(UploadBatch).where(UploadBatch.job_id.in_(visible))),
        demo_jobs=db.scalar(select(func.count()).select_from(Job).where(Job.is_demo.is_(True))),
        demo_loading=settings.seed_demo_data and db.scalar(select(func.count()).select_from(MatchResult).join(Job).where(Job.is_demo.is_(True))) < 36,
        total_evaluated=len(scores),average_score=round(sum(scores)/len(scores),2) if scores else None,distribution=buckets,
        recent_batches=[BatchOut.model_validate(b).model_dump() for b in batches])


@router.get('/jobs/{job_id}/runs', response_model=list[MatchingRunOut])
def matching_runs(job_id: UUID, db: DB, offset: int=Query(0, ge=0), limit: int=Query(50, ge=1, le=100),user=Depends(current_user)):
    job_or_404(db, job_id,user)
    return db.scalars(select(MatchingRun).where(MatchingRun.job_id==job_id)
        .order_by(MatchingRun.created_at.desc()).offset(offset).limit(limit)).all()


@router.get('/jobs/{job_id}/matches/{candidate_id}/history', response_model=list[HistoryOut])
def matching_history(job_id: UUID, candidate_id: UUID, db: DB,
                     offset: int=Query(0, ge=0), limit: int=Query(20, ge=1, le=100),user=Depends(current_user)):
    job_or_404(db, job_id,user)
    candidate=db.get(Candidate, candidate_id)
    if not candidate or candidate.batch.job_id != job_id:
        raise HTTPException(404, 'Candidate not found for this job')
    return db.scalars(select(MatchResultHistory).where(MatchResultHistory.job_id==job_id,
        MatchResultHistory.candidate_id==candidate_id).order_by(MatchResultHistory.created_at.desc())
        .offset(offset).limit(limit)).all()
