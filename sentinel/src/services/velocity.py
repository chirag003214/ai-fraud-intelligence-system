"""
Redis TTL-based velocity tracking — O(1) per operation.

Replaces the original O(n) SQLite COUNT query from backend/database.py.
Redis INCR + EXPIRE gives us a sliding-window counter with automatic
cleanup — no need to scan the transactions table.
"""

from __future__ import annotations

from redis.asyncio import Redis


async def increment_velocity(redis: Redis, customer_id: str) -> int:
    """
    Increment transaction count for a customer. TTL = 3600s (1 hour).

    Returns the new count after incrementing.
    """
    key = f"velocity:{customer_id}"
    pipe = redis.pipeline()
    await pipe.incr(key)
    await pipe.expire(key, 3600)
    results = await pipe.execute()
    return int(results[0])


async def get_velocity(redis: Redis, customer_id: str) -> int:
    """Get the current transaction count in the last hour for a customer."""
    value = await redis.get(f"velocity:{customer_id}")
    return int(value) if value else 0
