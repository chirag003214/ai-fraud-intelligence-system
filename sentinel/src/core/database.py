"""
Async SQLAlchemy database engine, session factory, ORM models, and CRUD.

Replaces the original synchronous SQLite-based backend/database.py with
fully async PostgreSQL (asyncpg) operations.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import DateTime, String, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from sentinel.src.core.config import settings

# ── Engine & session factory ──────────────────────────────────────────

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=(settings.ENVIRONMENT == "development"),
    pool_size=20,
    max_overflow=10,
)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


# ── ORM base ─────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


# ── Transaction model ────────────────────────────────────────────────

class Transaction(Base):
    """Persisted record of every evaluated transaction."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)
    customer_id: Mapped[str] = mapped_column(String(100), index=True)
    ip_address: Mapped[str] = mapped_column(String(45))
    txn_type: Mapped[str] = mapped_column(String(20))
    amount: Mapped[float]
    old_balance: Mapped[float]
    new_balance: Mapped[float]
    action: Mapped[str] = mapped_column(String(20))
    risk_score: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float]
    velocity_1h: Mapped[int]
    velocity_flag: Mapped[bool]
    model_version: Mapped[str] = mapped_column(String(50))
    ab_variant: Mapped[str] = mapped_column(String(20))
    shap_values: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    llm_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    explanation_ready: Mapped[bool] = mapped_column(default=False)


# ── Lifecycle ────────────────────────────────────────────────────────

async def init_db() -> None:
    """Create all tables (idempotent)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose the connection pool."""
    await engine.dispose()


# ── CRUD ─────────────────────────────────────────────────────────────

async def create_transaction(session: AsyncSession, data: dict) -> Transaction:
    """Insert a new transaction record."""
    txn = Transaction(**data)
    session.add(txn)
    await session.commit()
    await session.refresh(txn)
    return txn


async def get_transaction(session: AsyncSession, txn_id: str) -> Transaction | None:
    """Fetch a single transaction by its UUID."""
    stmt = select(Transaction).where(Transaction.transaction_id == txn_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_recent_transactions(
    session: AsyncSession, limit: int = 50
) -> Sequence[Transaction]:
    """Return the most recent transactions ordered by timestamp descending."""
    stmt = select(Transaction).order_by(Transaction.timestamp.desc()).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()


async def update_explanation(
    session: AsyncSession,
    txn_id: str,
    *,
    shap_values: str | None = None,
    llm_explanation: str | None = None,
) -> None:
    """Update SHAP and/or LLM explanation for a transaction."""
    txn = await get_transaction(session, txn_id)  # type: ignore[misc]
    if txn is None:
        return
    if shap_values is not None:
        txn.shap_values = shap_values
    if llm_explanation is not None:
        txn.llm_explanation = llm_explanation
    if shap_values is not None and llm_explanation is not None:
        txn.explanation_ready = True
    elif shap_values is not None and txn.llm_explanation is not None:
        txn.explanation_ready = True
    elif llm_explanation is not None and txn.shap_values is not None:
        txn.explanation_ready = True
    await session.commit()


async def get_transactions_for_drift_analysis(
    session: AsyncSession, limit: int = 1000
) -> Sequence[Transaction]:
    """Return recent transactions for drift analysis."""
    stmt = select(Transaction).order_by(Transaction.timestamp.desc()).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()
