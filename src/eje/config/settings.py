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
        description="Bearer token to secure API endpoints.",
    )
    require_api_token: bool = Field(
        default=True,
        description="Whether to enforce non-empty API tokens on startup.",
    )
    reject_wildcard_origins: bool = Field(
        default=True,
        description="Disallow '*' CORS origins to enforce explicit allowlists.",
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
    
    # Rate limiting configuration (Task 10.5)
    rate_limit_requests: int = Field(
        default=100,
        description="Maximum number of requests per IP within the time window.",
    )
    
    rate_limit_window: int = Field(
        default=60,
        description="Time window in seconds for rate limiting.",
    )
    
    rate_limit_backoff_base: float = Field(
        default=2.0,
        description="Base duration in seconds for exponential backoff on rate limit violations.",
    )

    class Config:
        env_prefix = "EJE_"
        case_sensitive = False

    def validate_security(self) -> None:
        """Fail fast when security-sensitive settings are unsafe."""

        if self.require_api_token and not self.api_token:
            raise ValueError("API token is required; set EJE_API_TOKEN to a non-empty value")

        if not self.allowed_origins:
            raise ValueError("allowed_origins cannot be empty")

        if self.reject_wildcard_origins and any(origin == "*" for origin in self.allowed_origins):
            raise ValueError("Wildcard CORS origins are rejected; specify explicit domains instead")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance sourced from env vars where available."""

    return Settings()
