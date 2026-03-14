"""Unit tests for the A/B router."""

from __future__ import annotations

from sentinel.src.services.detection import ABRouter


class TestABRouter:
    """Tests for deterministic A/B routing."""

    def test_same_customer_always_same_variant(self) -> None:
        """Same customer_id should always get the same variant."""
        router = ABRouter(challenger_pct=10)
        results = {router.route("CUST_STABLE") for _ in range(100)}
        assert len(results) == 1

    def test_challenger_pct_respected(self) -> None:
        """With 10% challenger, roughly 10% of 1000 customers should get challenger."""
        router = ABRouter(challenger_pct=10)
        variants = [router.route(f"CUST_{i}") for i in range(1000)]
        challenger_count = variants.count("challenger")
        # Allow ±5% tolerance for hash distribution
        assert 50 <= challenger_count <= 150

    def test_zero_challenger_pct_all_champion(self) -> None:
        """0% challenger means all customers get champion."""
        router = ABRouter(challenger_pct=0)
        variants = [router.route(f"CUST_{i}") for i in range(100)]
        assert all(v == "champion" for v in variants)

    def test_100_challenger_pct_all_challenger(self) -> None:
        """100% challenger means all customers get challenger."""
        router = ABRouter(challenger_pct=100)
        variants = [router.route(f"CUST_{i}") for i in range(100)]
        assert all(v == "challenger" for v in variants)
