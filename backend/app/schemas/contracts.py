from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class JobCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    raw_text: str = Field(min_length=30, max_length=100000)

    @field_validator('title', 'raw_text')
    @classmethod
    def trim(cls, value):
        if not value.strip(): raise ValueError('Must not be blank')
        return value.strip()


class JobPatch(BaseModel):
    required_skills: list[str] | None = None
    preferred_skills: list[str] | None = None
    min_experience: float | None = Field(default=None, ge=0, le=60)
    qualifications: list[str] | None = None
    responsibilities: list[str] | None = None

    @field_validator('required_skills','preferred_skills','qualifications','responsibilities')
    @classmethod
    def clean_list(cls, values):
        if values is None: raise ValueError('Use an empty list to remove requirements')
        if len(values) > 100 or any(len(v)>2000 for v in values): raise ValueError('Too many or oversized requirements')
        return list(dict.fromkeys(v.strip() for v in values if v.strip()))

    @model_validator(mode='after')
    def disjoint(self):
        if set(self.required_skills or []) & set(self.preferred_skills or []):
            raise ValueError('Required and preferred skills must be distinct')
        return self


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class JobOut(ORM):
    id: UUID
    title: str
    is_demo: bool = False
    is_published: bool = False
    raw_text: str
    required_skills: list[str]
    preferred_skills: list[str]
    min_experience: float | None
    qualifications: list[str]
    responsibilities: list[str]
    extraction_warnings: list[str]
    match_status: str
    match_error: str | None
    created_at: datetime
    updated_at: datetime


class PublicJobOut(ORM):
    id: UUID
    title: str
    raw_text: str


class JobPublication(BaseModel):
    is_published: bool


class BatchOut(ORM):
    id: UUID
    job_id: UUID
    status: str
    total_files: int
    processed_files: int
    failed_files: int
    errors: list[dict]
    created_at: datetime
    completed_at: datetime | None


class CandidateSummary(ORM):
    id: UUID
    name: str | None
    skills: list[str]
    experience_years: float | None
    parsing_warnings: list[str]


class CandidateOut(CandidateSummary):
    batch_id: UUID
    email: str | None
    phone: str | None
    experience_details: list[dict]
    education: list[str]
    projects: list[str]
    certifications: list[str]
    skill_evidence: dict
    original_filename: str | None = None


class MatchOut(ORM):
    candidate_id: UUID
    job_id: UUID
    overall_score: float
    semantic_score: float
    skill_score: float | None
    experience_score: float | None
    education_score: float | None
    matched_skills: list[str]
    missing_skills: list[str]
    explanation: dict
    algorithm_version: str
    embedding_model: str
    scoring_config: dict
    run_id: UUID | None
    candidate: CandidateSummary


class JobsPage(BaseModel):
    items: list[JobOut]
    total: int


class CandidatesPage(BaseModel):
    items: list[CandidateSummary]
    total: int


class RankingsPage(BaseModel):
    items: list[MatchOut]
    total: int


class MatchingRunOut(ORM):
    id: UUID
    job_id: UUID
    embedding_model: str
    scoring_config: dict
    algorithm_version: str
    status: str
    candidate_count: int
    created_at: datetime
    completed_at: datetime | None
    error: str | None


class HistoryOut(ORM):
    id: UUID
    created_at: datetime
    previous_result_id: UUID
    run_id: UUID | None
    embedding_model: str
    scoring_config: dict
    payload: dict
