from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://pmknowledge:localdev@localhost:5432/pmknowledge"
    embeddings_enabled: bool = False
    embedding_cache_dir: str = ".cache/embeddings"
    semantic_min_score: float = Field(default=0.6, ge=0.0, le=1.0)
    web_dist_dir: Path | None = None
