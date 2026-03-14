"""
History route: GET /v1/history.

Returns recent transactions from the database for the audit log dashboard.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel.src.api.deps import get_current_user, get_db
from sentinel.src.core.database import get_recent_transactions

router = APIRouter()


@router.get("/history")
async def history(
    limit: int = Query(default=50, ge=1, le=500),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Fetch recent transactions for the audit log."""
    txns = await get_recent_transactions(db, limit=limit)
    return [
        {
            "id": txn.id,
            "transaction_id": txn.transaction_id,
            "timestamp": txn.timestamp.isoformat() if txn.timestamp else None,
            "customer_id": txn.customer_id,
            "ip_address": txn.ip_address,
            "txn_type": txn.txn_type,
            "amount": txn.amount,
            "action": txn.action,
            "risk_score": txn.risk_score,
            "confidence": txn.confidence,
            "velocity_1h": txn.velocity_1h,
            "model_version": txn.model_version,
            "ab_variant": txn.ab_variant,
            "explanation_ready": txn.explanation_ready,
        }
        for txn in txns
    ]
