"""
FastAPI dependency injection: database sessions, Redis, model, auth.

All dependencies are defined as async generators or callables so they
integrate cleanly with FastAPI's Depends() system.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBearer

from sentinel.src.core.config import settings
from sentinel.src.core.database import async_session_factory
from sentinel.src.core.redis_client import get_redis as _get_redis
from sentinel.src.core.security import verify_token

logger = structlog.get_logger()

# ── Security schemes ─────────────────────────────────────────────────

api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


# ── Database session ─────────────────────────────────────────────────

async def get_db():
    """Yield an async SQLAlchemy session, auto-closed after use."""
    async with async_session_factory() as session:
        yield session


# ── Redis ────────────────────────────────────────────────────────────

async def get_redis():
    """Return the active Redis client."""
    return _get_redis()


# ── Auth: dual JWT / API-key ─────────────────────────────────────────

async def get_current_user(
    api_key: str | None = Security(api_key_header),
    bearer: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> dict[str, Any]:
    """
    Accept either a Bearer JWT *or* an x-api-key header.

    Priority: JWT first, then API key. Returns a user-info dict.
    Raises HTTP 401/403 on failure.
    """
    # Try JWT first
    if bearer is not None:
        try:
            payload = verify_token(bearer.credentials)
            return payload
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired JWT token",
            )

    # Fall back to static API key
    if api_key is not None and api_key == settings.API_KEY:
        return {"sub": "api_key_user", "role": "service"}

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Missing or invalid authentication credentials",
    )


async def get_api_key(
    api_key: str | None = Security(api_key_header),
) -> str:
    """Accept only x-api-key header (backward compatibility)."""
    if api_key is None or api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    return api_key
