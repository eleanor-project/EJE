"""Configuration settings for ELEANOR Moral Ops Center utilities."""
from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Runtime settings for the Ops Center services."""

    config_path: str = Field(
        "config/global.yaml",
        description="Path to the shared EJE global configuration file.",
    )
    db_path: str = Field(
        "eje_ops.db",
        description="SQLite database path for storing escalation logs and precedents.",
    )
    allowed_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost", "http://127.0.0.1"],
        description="CORS origins permitted to access the FastAPI layer.",
    )
    api_token: Optional[str] = Field(
        default=None,
        description="Optional bearer token to secure API endpoints.",
    )
    dynamic_weights: bool = Field(
        default=True,
        description="Enable adaptive critic weighting driven by dissent-aware learning.",
    )
    escalation_threshold: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="Confidence threshold below which cases are escalated.",
    )

    class Config:
        env_prefix = "EJE_"
        case_sensitive = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance sourced from env vars where available."""

    return Settings()
