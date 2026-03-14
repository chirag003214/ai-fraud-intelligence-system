"""
Explanation route: GET /v1/explain/{txn_id}.

Returns whatever explanation data is ready (SHAP, LLM, or both).
Frontend can poll until explanation_ready=True.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from sentinel.src.api.deps import get_current_user, get_db
from sentinel.src.core.database import get_transaction
from sentinel.src.schemas.response import ExplainResponse

router = APIRouter()


@router.get("/explain/{txn_id}", response_model=ExplainResponse)
async def explain(
    txn_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExplainResponse:
    """Retrieve SHAP and LLM explanation for a transaction."""
    txn = await get_transaction(db, txn_id)
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    assert txn is not None  # type narrowing for static analysis

    shap_values = None
    if txn.shap_values:
        try:
            shap_values = json.loads(txn.shap_values)
        except json.JSONDecodeError:
            shap_values = None

    return ExplainResponse(
        transaction_id=txn.transaction_id,
        shap_values=shap_values,
        llm_explanation=txn.llm_explanation,
        explanation_ready=txn.explanation_ready,
    )
