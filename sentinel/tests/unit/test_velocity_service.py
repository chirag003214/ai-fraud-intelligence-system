"""Unit tests for the Redis velocity service."""

from __future__ import annotations

import pytest
import pytest_asyncio

from sentinel.src.services.velocity import get_velocity, increment_velocity


@pytest.fixture
def redis_client():
    """Create a fakeredis async client."""
    try:
        import fakeredis.aioredis
        return fakeredis.aioredis.FakeRedis(decode_responses=True)
    except ImportError:
        pytest.skip("fakeredis not installed")


@pytest.mark.asyncio
class TestVelocityService:
    """Tests for Redis-based velocity tracking."""

    async def test_first_transaction_returns_1(self, redis_client) -> None:
        """First increment for a new customer should return 1."""
        count = await increment_velocity(redis_client, "CUST_NEW")
        assert count == 1

    async def test_velocity_increments(self, redis_client) -> None:
        """Multiple increments should return increasing counts."""
        await increment_velocity(redis_client, "CUST_INC")
        await increment_velocity(redis_client, "CUST_INC")
        count = await increment_velocity(redis_client, "CUST_INC")
        assert count == 3

    async def test_get_velocity_returns_current_count(self, redis_client) -> None:
        """get_velocity should return the current count without incrementing."""
        await increment_velocity(redis_client, "CUST_GET")
        await increment_velocity(redis_client, "CUST_GET")
        count = await get_velocity(redis_client, "CUST_GET")
        assert count == 2

    async def test_get_velocity_returns_zero_for_unknown(self, redis_client) -> None:
        """get_velocity should return 0 for unknown customers."""
        count = await get_velocity(redis_client, "CUST_UNKNOWN")
        assert count == 0

    async def test_different_customers_independent(self, redis_client) -> None:
        """Different customers should have independent velocity counts."""
        await increment_velocity(redis_client, "CUST_A")
        await increment_velocity(redis_client, "CUST_A")
        await increment_velocity(redis_client, "CUST_B")

        count_a = await get_velocity(redis_client, "CUST_A")
        count_b = await get_velocity(redis_client, "CUST_B")

        assert count_a == 2
        assert count_b == 1

    async def test_velocity_key_has_ttl(self, redis_client) -> None:
        """Velocity keys should have a TTL set."""
        await increment_velocity(redis_client, "CUST_TTL")
        ttl = await redis_client.ttl("velocity:CUST_TTL")
        assert 0 < ttl <= 3600
