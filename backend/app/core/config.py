from pathlib import Path
from typing import Literal
import math
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore', protected_namespaces=('settings_',))
    database_url: str = 'postgresql+psycopg://resume:resume_local@127.0.0.1:5433/resume_matcher'
    cors_origins: list[str] = ['http://localhost:5173', 'http://127.0.0.1:5173']
    upload_dir: Path = Path('storage/uploads')
    max_file_mb: int = 10
    max_batch_files: int = 50
    embedding_model: str = Field(default='sentence-transformers/all-mpnet-base-v2', validation_alias=AliasChoices('EMBEDDING_MODEL', 'MODEL_NAME'))
    embedding_cache_mb: int = Field(default=128, ge=0, le=2048)
    embedding_batch_size: int = Field(default=32, ge=1, le=128)
    embedding_backend: Literal['pytorch', 'onnx-int8'] = 'pytorch'
    onnx_model_dir: Path = Path('../.model-cache/onnx-mpnet')
    scoring_weights: dict[str, float] = Field(default_factory=lambda: {'semantic': .25, 'skill': .40, 'experience': .25, 'education': .10})
    model_cache: str = '../.model-cache'
    frontend_dist: Path | None = None

    @field_validator('scoring_weights')
    @classmethod
    def valid_weights(cls, values):
        if set(values) != {'semantic', 'skill', 'experience', 'education'}:
            raise ValueError('Weights must contain semantic, skill, experience and education.')
        if any(not math.isfinite(v) or v < 0 or v > 1 for v in values.values()) or not math.isclose(sum(values.values()), 1.0, abs_tol=1e-9):
            raise ValueError('Scoring weights must be finite, nonnegative, and sum to 1.0.')
        return values

    @field_validator('database_url', mode='before')
    @classmethod
    def use_psycopg_driver(cls, value):
        # Hosting providers commonly supply a plain PostgreSQL URL.
        if isinstance(value, str):
            if value.startswith('postgres://'):
                return value.replace('postgres://', 'postgresql+psycopg://', 1)
            if value.startswith('postgresql://'):
                return value.replace('postgresql://', 'postgresql+psycopg://', 1)
        return value

    @property
    def model_name(self):
        """Compatibility alias for older integrations; EMBEDDING_MODEL takes priority."""
        return self.embedding_model


settings = Settings()
WEIGHTS = settings.scoring_weights
ALGORITHM_VERSION = '2.0.0-section-aware'
