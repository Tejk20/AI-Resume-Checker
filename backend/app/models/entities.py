import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, Integer, DateTime, ForeignKey, UniqueConstraint, CheckConstraint, JSON, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

J = JSON().with_variant(JSONB(), 'postgresql')


def now():
    return datetime.now(timezone.utc)


class Identity:
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Job(Identity, Base):
    __tablename__ = 'jobs'
    title: Mapped[str] = mapped_column(String(200))
    raw_text: Mapped[str] = mapped_column(Text)
    required_skills: Mapped[list] = mapped_column(J, default=list)
    preferred_skills: Mapped[list] = mapped_column(J, default=list)
    min_experience: Mapped[float | None] = mapped_column(Float)
    qualifications: Mapped[list] = mapped_column(J, default=list)
    responsibilities: Mapped[list] = mapped_column(J, default=list)
    extraction_warnings: Mapped[list] = mapped_column(J, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    match_status: Mapped[str] = mapped_column(String(30), default='idle')
    match_error: Mapped[str | None] = mapped_column(Text)
    batches: Mapped[list['UploadBatch']] = relationship(back_populates='job')


class UploadBatch(Identity, Base):
    __tablename__ = 'upload_batches'
    __table_args__ = (CheckConstraint("status IN ('pending','processing','completed','partially_completed','failed')"),)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('jobs.id'), index=True)
    status: Mapped[str] = mapped_column(String(30), default='pending')
    total_files: Mapped[int] = mapped_column(Integer)
    processed_files: Mapped[int] = mapped_column(Integer, default=0)
    failed_files: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list] = mapped_column(J, default=list)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    job: Mapped[Job] = relationship(back_populates='batches')
    candidates: Mapped[list['Candidate']] = relationship(back_populates='batch')


class Candidate(Identity, Base):
    __tablename__ = 'candidates'
    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('upload_batches.id'), index=True)
    name: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(254))
    phone: Mapped[str | None] = mapped_column(String(80))
    skills: Mapped[list] = mapped_column(J, default=list)
    skill_evidence: Mapped[dict] = mapped_column(J, default=dict)
    experience_years: Mapped[float | None] = mapped_column(Float)
    experience_details: Mapped[list] = mapped_column(J, default=list)
    education: Mapped[list] = mapped_column(J, default=list)
    projects: Mapped[list] = mapped_column(J, default=list)
    certifications: Mapped[list] = mapped_column(J, default=list)
    raw_text: Mapped[str] = mapped_column(Text)
    parsing_warnings: Mapped[list] = mapped_column(J, default=list)
    batch: Mapped[UploadBatch] = relationship(back_populates='candidates')
    resume_file: Mapped['ResumeFile'] = relationship(back_populates='candidate', uselist=False)


class ResumeFile(Identity, Base):
    __tablename__ = 'resume_files'
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('candidates.id'), unique=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(Text)
    mime_type: Mapped[str] = mapped_column(String(100))
    sha256_hash: Mapped[str] = mapped_column(String(64), index=True)
    extraction_status: Mapped[str] = mapped_column(String(30))
    extraction_error: Mapped[str | None] = mapped_column(Text)
    candidate: Mapped[Candidate] = relationship(back_populates='resume_file')


class MatchResult(Identity, Base):
    __tablename__ = 'match_results'
    __table_args__ = (UniqueConstraint('job_id', 'candidate_id'), CheckConstraint('overall_score >= 0 AND overall_score <= 100'))
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('jobs.id'), index=True)
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('candidates.id'), index=True)
    overall_score: Mapped[float] = mapped_column(Float, index=True)
    semantic_score: Mapped[float] = mapped_column(Float)
    skill_score: Mapped[float | None] = mapped_column(Float)
    experience_score: Mapped[float | None] = mapped_column(Float)
    education_score: Mapped[float | None] = mapped_column(Float)
    matched_skills: Mapped[list] = mapped_column(J)
    missing_skills: Mapped[list] = mapped_column(J)
    explanation: Mapped[dict] = mapped_column(J)
    algorithm_version: Mapped[str] = mapped_column(String(80))
    embedding_model: Mapped[str] = mapped_column(String(255), default='legacy/unknown', server_default='legacy/unknown')
    scoring_config: Mapped[dict] = mapped_column(J, default=dict, server_default='{}')
    run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('matching_runs.id', name='fk_match_results_run_id'), index=True)
    candidate: Mapped[Candidate] = relationship()


class MatchingRun(Identity, Base):
    __tablename__ = 'matching_runs'
    __table_args__ = (CheckConstraint("status IN ('processing','completed','failed')"),)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('jobs.id'), index=True)
    embedding_model: Mapped[str] = mapped_column(String(255))
    scoring_config: Mapped[dict] = mapped_column(J)
    algorithm_version: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30), default='processing')
    candidate_count: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)


class MatchResultHistory(Identity, Base):
    __tablename__ = 'match_result_history'
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('jobs.id'), index=True)
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('candidates.id'), index=True)
    previous_result_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('matching_runs.id'))
    embedding_model: Mapped[str] = mapped_column(String(255))
    scoring_config: Mapped[dict] = mapped_column(J)
    payload: Mapped[dict] = mapped_column(J)
