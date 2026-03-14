"""
Pydantic schemas for API responses.

Defines the shape of all outgoing data. Every response field is typed
so FastAPI auto-generates accurate OpenAPI documentation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PredictionResponse(BaseModel):
    """Response from POST /v1/predict."""

    transaction_id: str
    action: str = Field(..., description="ALLOW, CHALLENGE, or BLOCK")
    risk_score: str = Field(..., description="LOW, MEDIUM, HIGH, or CRITICAL")
    confidence: float = Field(..., ge=0, le=1)
    decision_threshold: float
    reasons: list[str]
    velocity_1h: int
    model_version: str
    ab_variant: str


class ExplainResponse(BaseModel):
    """Response from GET /v1/explain/{txn_id}."""

    transaction_id: str
    shap_values: list[dict[str, Any]] | None = None
    llm_explanation: str | None = None
    explanation_ready: bool = False


class HealthResponse(BaseModel):
    """Response from GET /v1/health."""

    status: str
    environment: str
    model_loaded: bool
    database_connected: bool
    redis_connected: bool
    uptime_seconds: float
    version: str = "2.0.0"


class DriftResponse(BaseModel):
    """Response from GET /v1/drift."""

    status: str
    max_psi: float = 0.0
    features: dict[str, float] = {}
    sample_size: int = 0
    computed_at: str = ""


class TokenResponse(BaseModel):
    """Response from POST /v1/auth/token."""

    access_token: str
    token_type: str = "bearer"


class BatchStatusResponse(BaseModel):
    """Response from a batch prediction request."""

    task_id: str
    status: str = "queued"
    total: int
    message: str = "Batch processing started"
