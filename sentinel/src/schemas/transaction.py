"""
Pydantic schemas for API request and response validation.

TransactionRequest and BatchRequest define the shape of incoming data.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TransactionRequest(BaseModel):
    """Single transaction to evaluate."""

    customer_id: str = Field(..., description="Unique customer identifier")
    ip_address: str = Field(..., description="Source IP address")
    transaction_type: str = Field(
        ..., alias="type", description="CASH_OUT, TRANSFER, PAYMENT, etc."
    )
    amount: float = Field(..., gt=0, description="Transaction amount in dollars")
    old_balance: float = Field(
        ..., alias="oldbalanceOrg", description="Sender balance before transaction"
    )
    new_balance: float = Field(
        ..., alias="newbalanceOrig", description="Sender balance after transaction"
    )

    model_config = {"populate_by_name": True}


class BatchRequest(BaseModel):
    """Batch of transactions for bulk evaluation."""

    transactions: list[TransactionRequest] = Field(
        ..., min_length=1, max_length=1000
    )
    webhook_url: str | None = Field(
        None, description="URL to call when batch processing completes"
    )
