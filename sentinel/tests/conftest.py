"""
Pytest fixtures for the Sentinel test suite.

Provides: mock model, test database (SQLite), mock Redis (fakeredis),
and an async HTTP test client.
"""

from __future__ import annotations

from typing import AsyncGenerator
from unittest.mock import MagicMock

import numpy as np
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sentinel.src.core.database import Base


# ── Mock model ───────────────────────────────────────────────────────

class MockModel:
    """Mock ML model that always returns configurable probability."""

    def __init__(self, proba: float = 0.9) -> None:
        self._proba = proba
        self.version = "mock-1.0.0"

    def predict(self, X):
        """Return 1 if proba >= 0.5 else 0."""
        return np.array([1 if self._proba >= 0.5 else 0] * len(X))

    def predict_proba(self, X):
        """Return fixed probability."""
        return np.array([[1 - self._proba, self._proba]] * len(X))

    @property
    def is_loaded(self) -> bool:
        return True

    def get_variant(self, variant: str):
        return self

    def load(self, *args, **kwargs):
        pass


@pytest.fixture
def mock_model() -> MockModel:
    """Return a mock model with 0.9 confidence."""
    return MockModel(proba=0.9)


@pytest.fixture
def clean_model() -> MockModel:
    """Return a mock model with low confidence (clean transaction)."""
    return MockModel(proba=0.05)


# ── Test database (SQLite async) ─────────────────────────────────────

@pytest_asyncio.fixture
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """In-memory SQLite async session for unit tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session

    await engine.dispose()


# ── Mock Redis (fakeredis) ───────────────────────────────────────────

@pytest.fixture
def mock_redis():
    """Return a fakeredis async client."""
    try:
        import fakeredis.aioredis

        return fakeredis.aioredis.FakeRedis(decode_responses=True)
    except ImportError:
        pytest.skip("fakeredis not installed")


# ── Test HTTP client ─────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_client(mock_model, mock_redis) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client with mocked dependencies."""
    from sentinel.src.api.main import create_app
    from sentinel.src.api import deps
    from sentinel.src.core import database, redis_client
    from sentinel.ml import loader

    # Patch model registry
    loader.model_registry = mock_model

    # Patch dependencies
    async def _get_db():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            yield session
        await engine.dispose()

    async def _get_redis():
        return mock_redis

    async def _mock_auth(api_key=None, bearer=None):
        return {"sub": "test_user", "role": "admin"}

    app = create_app()
    app.dependency_overrides[deps.get_db] = _get_db
    app.dependency_overrides[deps.get_redis] = _get_redis
    app.dependency_overrides[deps.get_current_user] = _mock_auth

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
