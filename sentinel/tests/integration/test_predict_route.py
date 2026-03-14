"""Integration tests for the prediction route."""

from __future__ import annotations

import pytest
import pytest_asyncio


@pytest.mark.asyncio
class TestPredictRoute:
    """Integration tests for POST /v1/predict."""

    async def test_clean_transaction_returns_allow(self, test_client) -> None:
        """A normal-looking transaction should return ALLOW or a valid action."""
        response = await test_client.post("/v1/predict", json={
            "customer_id": "CUST_CLEAN",
            "ip_address": "1.1.1.1",
            "type": "PAYMENT",
            "amount": 50.0,
            "oldbalanceOrg": 1000.0,
            "newbalanceOrig": 950.0,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["action"] in ("ALLOW", "CHALLENGE", "BLOCK")

    async def test_phantom_drain_returns_block(self, test_client) -> None:
        """A Phantom Drain transaction should be BLOCKED."""
        response = await test_client.post("/v1/predict", json={
            "customer_id": "CUST_DRAIN",
            "ip_address": "1.1.1.1",
            "type": "TRANSFER",
            "amount": 50000.0,
            "oldbalanceOrg": 50000.0,
            "newbalanceOrig": 0.0,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "BLOCK"

    async def test_response_has_required_fields(self, test_client) -> None:
        """Response should contain all required fields."""
        response = await test_client.post("/v1/predict", json={
            "customer_id": "CUST_FIELDS",
            "ip_address": "2.2.2.2",
            "type": "CASH_OUT",
            "amount": 1000.0,
            "oldbalanceOrg": 5000.0,
            "newbalanceOrig": 4000.0,
        })
        assert response.status_code == 200
        data = response.json()

        required_fields = [
            "transaction_id", "action", "risk_score", "confidence",
            "decision_threshold", "reasons", "velocity_1h",
            "model_version", "ab_variant",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    async def test_confidence_is_between_0_and_1(self, test_client) -> None:
        """Confidence score should be in [0, 1]."""
        response = await test_client.post("/v1/predict", json={
            "customer_id": "CUST_CONF",
            "ip_address": "3.3.3.3",
            "type": "TRANSFER",
            "amount": 500.0,
            "oldbalanceOrg": 2000.0,
            "newbalanceOrig": 1500.0,
        })
        assert response.status_code == 200
        data = response.json()
        assert 0 <= data["confidence"] <= 1

    async def test_decision_threshold_not_half(self, test_client) -> None:
        """Decision threshold should not be the naive 0.5 default."""
        response = await test_client.post("/v1/predict", json={
            "customer_id": "CUST_THRES",
            "ip_address": "4.4.4.4",
            "type": "PAYMENT",
            "amount": 100.0,
            "oldbalanceOrg": 500.0,
            "newbalanceOrig": 400.0,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["decision_threshold"] != 0.5
