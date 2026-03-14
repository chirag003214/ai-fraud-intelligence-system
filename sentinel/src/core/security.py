"""
JWT creation / validation and API-key authentication.

Supports dual auth: Bearer JWT *or* x-api-key header. This lets the
Streamlit frontend exchange its static API key for a proper JWT token.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from sentinel.src.core.config import settings

ALGORITHM = "HS256"
DEFAULT_EXPIRY = timedelta(hours=24)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT with an expiry claim."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or DEFAULT_EXPIRY)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT. Returns the payload or raises ValueError."""
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )
        return payload
    except JWTError as exc:
        raise ValueError(f"Invalid token: {exc}") from exc
