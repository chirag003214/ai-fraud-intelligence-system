"""
Sentinel configuration via pydantic-settings.

Every environment variable the application needs is declared here with types,
defaults, and documentation. Values are loaded from a .env file or from the
system environment, with env vars taking precedence.
"""

from __future__ import annotations

import structlog
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed, validated application settings loaded from environment."""

    # ── Database ──────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/sentinel"
    """PostgreSQL async connection URL (asyncpg driver)."""

    # ── Redis ─────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379"
    """Redis URL for velocity tracking and Celery broker."""

    # ── Secrets ───────────────────────────────────────────────────────
    HF_TOKEN: str = ""
    """HuggingFace API token for LLM inference."""

    SECRET_KEY: str = "change-me-in-production-min-32-chars!!"
    """JWT signing key — must be at least 32 characters in production."""

    API_KEY: str = "sentinel-dev-key"
    """Static API key fallback for simple auth."""

    # ── MLflow / Model ────────────────────────────────────────────────
    MLFLOW_TRACKING_URI: str = "sqlite:///mlflow.db"
    """MLflow tracking server URI."""

    MODEL_PATH: str = "fraud_model"
    """Path to the exported MLflow model directory."""

    # ── Cost Matrix ───────────────────────────────────────────────────
    FRAUD_FP_COST: float = 5.0
    """False-positive cost in dollars (analyst investigation time)."""

    FRAUD_FN_COST: float = 850.0
    """False-negative cost in dollars (average fraud loss)."""

    # ── A/B Testing ───────────────────────────────────────────────────
    AB_CHALLENGER_PCT: int = 10
    """Percentage of traffic routed to the challenger model."""

    # ── Drift ─────────────────────────────────────────────────────────
    DRIFT_THRESHOLD: float = 0.2
    """PSI threshold that triggers a retrain alert."""

    # ── Logging ───────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    """Python log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)."""

    # ── Runtime ───────────────────────────────────────────────────────
    ENVIRONMENT: str = "development"
    """Runtime environment: development, staging, production."""

    CORS_ORIGINS: list[str] = ["http://localhost:8501"]
    """Allowed CORS origins for the API."""

    RATE_LIMIT_PER_MINUTE: int = 60
    """Maximum requests per minute for rate-limited endpoints."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


# ── Module-level singleton ────────────────────────────────────────────
settings = Settings()


def configure_logging() -> None:
    """Configure structlog with JSON rendering and context variables."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(),
    )
