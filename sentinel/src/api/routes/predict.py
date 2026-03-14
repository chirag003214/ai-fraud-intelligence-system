"""
Prediction routes: POST /v1/predict and POST /v1/predict/batch.

Route handlers only: validate input → call service → return response.
No business logic here.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel.ml.ab_test import log_ab_outcome
from sentinel.ml.loader import model_registry
from sentinel.src.api.deps import get_current_user, get_db, get_redis
from sentinel.src.api.middleware import (
    MODEL_CONFIDENCE,
    PREDICTION_LATENCY,
    PREDICTIONS_TOTAL,
)
from sentinel.src.schemas.response import BatchStatusResponse, PredictionResponse
from sentinel.src.schemas.transaction import BatchRequest, TransactionRequest
from sentinel.src.services.detection import DetectionService
from sentinel.src.services.explainer import ExplainerService
from sentinel.src.services.velocity import increment_velocity
from sentinel.src.services.websocket_manager import manager
from sentinel.src.core.config import settings
from sentinel.src.core.database import create_transaction

logger = structlog.get_logger()

router = APIRouter()


@router.post("/predict", response_model=PredictionResponse)
async def predict(
    txn: TransactionRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> PredictionResponse:
    """Evaluate a single transaction for fraud risk."""
    start = time.monotonic()

    # Velocity check (Redis, O(1))
    velocity = await increment_velocity(redis, txn.customer_id)

    # Run detection pipeline
    service = DetectionService(model=model_registry, config=settings)
    result = service.evaluate_sync(
        customer_id=txn.customer_id,
        ip_address=txn.ip_address,
        txn_type=txn.transaction_type,
        amount=txn.amount,
        old_balance=txn.old_balance,
        new_balance=txn.new_balance,
        velocity=velocity,
    )

    # Persist to database
    await create_transaction(db, {
        "transaction_id": result.transaction_id,
        "customer_id": txn.customer_id,
        "ip_address": txn.ip_address,
        "txn_type": txn.transaction_type,
        "amount": txn.amount,
        "old_balance": txn.old_balance,
        "new_balance": txn.new_balance,
        "action": result.action,
        "risk_score": result.risk_score,
        "confidence": result.confidence,
        "velocity_1h": result.velocity_1h,
        "velocity_flag": velocity >= 5,
        "model_version": result.model_version,
        "ab_variant": result.ab_variant,
    })

    # Queue async explanation
    explainer = ExplainerService()
    explainer.trigger_async_explanation(
        txn_id=result.transaction_id,
        features={
            "type": txn.transaction_type,
            "amount": txn.amount,
            "oldbalanceOrg": txn.old_balance,
            "newbalanceOrig": txn.new_balance,
        },
        model_variant=result.ab_variant,
    )

    # WebSocket broadcast for BLOCK decisions
    if result.action == "BLOCK":
        await manager.broadcast_fraud_alert({
            "transaction_id": result.transaction_id,
            "customer_id": txn.customer_id,
            "amount": txn.amount,
            "risk_score": result.risk_score,
            "reasons": result.reasons,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # Prometheus metrics
    latency = time.monotonic() - start
    PREDICTION_LATENCY.observe(latency)
    PREDICTIONS_TOTAL.labels(
        action=result.action,
        risk_score=result.risk_score,
        ab_variant=result.ab_variant,
    ).inc()
    MODEL_CONFIDENCE.labels(ab_variant=result.ab_variant).observe(result.confidence)

    # A/B outcome logging
    log_ab_outcome(result.transaction_id, result.ab_variant, result.confidence, result.action)

    logger.info(
        "prediction_complete",
        transaction_id=result.transaction_id,
        action=result.action,
        confidence=result.confidence,
        latency_ms=round(latency * 1000, 2),  # type: ignore[call-overload]
    )

    return PredictionResponse(
        transaction_id=result.transaction_id,
        action=result.action,
        risk_score=result.risk_score,
        confidence=result.confidence,
        decision_threshold=result.decision_threshold,
        reasons=result.reasons,
        velocity_1h=result.velocity_1h,
        model_version=result.model_version,
        ab_variant=result.ab_variant,
    )


@router.post("/predict/batch", response_model=BatchStatusResponse)
async def predict_batch(
    batch: BatchRequest,
    user: dict = Depends(get_current_user),
) -> BatchStatusResponse:
    """Queue a batch of transactions for processing."""
    # In production this would delegate to Celery
    from uuid import uuid4

    task_id = str(uuid4())
    logger.info("batch_queued", task_id=task_id, total=len(batch.transactions))

    return BatchStatusResponse(
        task_id=task_id,
        status="queued",
        total=len(batch.transactions),
        message=f"Batch of {len(batch.transactions)} transactions queued",
    )
