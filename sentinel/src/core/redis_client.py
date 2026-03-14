"""
Async Redis connection pool and lifecycle management.

Provides O(1) velocity tracking to replace the original O(n) SQLite
COUNT query — see services/velocity.py for the velocity logic itself.
"""

from __future__ import annotations

from redis.asyncio import ConnectionPool, Redis

from sentinel.src.core.config import settings

# ── Module-level pool (created once at startup) ──────────────────────

_pool: ConnectionPool | None = None
_redis: Redis | None = None


async def init_redis() -> Redis:
    """Create the async Redis connection pool. Called once at startup."""
    global _pool, _redis  # noqa: PLW0603
    _pool = ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)
    _redis = Redis(connection_pool=_pool)
    return _redis


async def close_redis() -> None:
    """Tear down the Redis connection pool. Called at shutdown."""
    global _pool, _redis  # noqa: PLW0603
    if _redis is not None:
        await _redis.close()
        _redis = None
    if _pool is not None:
        await _pool.disconnect()
        _pool = None


def get_redis() -> Redis:
    """Return the active Redis instance (for dependency injection)."""
    if _redis is None:
        raise RuntimeError("Redis not initialized — call init_redis() first")
    return _redis
