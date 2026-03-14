"""
Health, metrics, drift, and auth routes.

  GET  /v1/health     → system health check
  GET  /metrics       → Prometheus metrics (text format)
  GET  /v1/drift      → real PSI drift report
  POST /v1/auth/token → exchange API key for JWT
"""

from __future__ import annotations

import time

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel.ml.loader import model_registry
from sentinel.src.api.deps import get_db, get_redis
from sentinel.src.api.middleware import get_metrics_response
from sentinel.src.core.config import settings
from sentinel.src.core.database import get_transactions_for_drift_analysis
from sentinel.src.core.security import create_access_token
from sentinel.src.schemas.response import DriftResponse, HealthResponse, TokenResponse
from sentinel.src.services.drift import compute_drift_report

logger = structlog.get_logger()

router = APIRouter()

# Track startup time for uptime calculation
_startup_time: float = time.monotonic()


def set_startup_time() -> None:
    """Record startup time — called once from lifespan."""
    global _startup_time  # noqa: PLW0603
    _startup_time = time.monotonic()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> HealthResponse:
    """System health check for monitoring and load balancers."""
    # Check database
    db_ok = True
    try:
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    # Check Redis
    redis_ok = True
    try:
        await redis.ping()
    except Exception:
        redis_ok = False

    return HealthResponse(
        status="ok" if db_ok and redis_ok else "degraded",
        environment=settings.ENVIRONMENT,
        model_loaded=model_registry.is_loaded,
        database_connected=db_ok,
        redis_connected=redis_ok,
        uptime_seconds=round(time.monotonic() - _startup_time, 1),  # type: ignore[call-overload]
    )


@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics() -> PlainTextResponse:
    """Prometheus-compatible metrics endpoint."""
    return PlainTextResponse(
        content=get_metrics_response(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get("/drift", response_model=DriftResponse)
async def drift_report(
    db: AsyncSession = Depends(get_db),
) -> DriftResponse:
    """Compute and return real PSI drift report."""
    txns = await get_transactions_for_drift_analysis(db, limit=1000)

    # Convert ORM objects to dicts for drift computation
    txn_dicts = [
        {
            "type": txn.txn_type,
            "amount": txn.amount,
            "oldbalanceOrg": txn.old_balance,
            "newbalanceOrig": txn.new_balance,
        }
        for txn in txns
    ]

    result = await compute_drift_report(txn_dicts)

    return DriftResponse(
        status=result.get("status", "unknown"),
        max_psi=result.get("max_psi", 0.0),
        features=result.get("features", {}),
        sample_size=result.get("sample_size", 0),
        computed_at=result.get("computed_at", ""),
    )


@router.post("/auth/token", response_model=TokenResponse)
async def get_token(body: dict) -> TokenResponse:
    """Exchange a static API key for a JWT token."""
    api_key = body.get("api_key")
    if api_key != settings.API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")

    token = create_access_token({"sub": "api_key_user", "role": "service"})
    return TokenResponse(access_token=token)
