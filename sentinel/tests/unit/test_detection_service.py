"""Unit tests for the DetectionService."""

from __future__ import annotations

import pytest

from sentinel.src.services.detection import CostThreshold, DetectionService


class MockConfig:
    """Mock configuration for testing."""
    FRAUD_FP_COST = 5.0
    FRAUD_FN_COST = 850.0
    AB_CHALLENGER_PCT = 10


class MockModel:
    """Mock ML model."""
    version = "test-1.0"

    def predict_proba(self, X):
        import numpy as np
        return np.array([[0.1, 0.9]] * len(X))

    def get_variant(self, variant):
        return self

    @property
    def is_loaded(self):
        return True


class CleanMockModel(MockModel):
    """Mock model that predicts clean."""
    def predict_proba(self, X):
        import numpy as np
        return np.array([[0.95, 0.05]] * len(X))


class TestDetectionService:
    """Tests for the core detection pipeline."""

    def test_block_on_phantom_drain(self) -> None:
        """Phantom Drain rule should cause BLOCK action."""
        service = DetectionService(model=MockModel(), config=MockConfig())
        result = service.evaluate_sync(
            customer_id="CUST_001",
            ip_address="1.1.1.1",
            txn_type="TRANSFER",
            amount=5000,
            old_balance=5000,
            new_balance=0,
            velocity=1,
        )
        assert result.action == "BLOCK"
        assert "Phantom Drain" in result.reasons

    def test_allow_on_clean_transaction(self) -> None:
        """Clean transaction with low ML score should ALLOW."""
        service = DetectionService(model=CleanMockModel(), config=MockConfig())
        result = service.evaluate_sync(
            customer_id="CUST_002",
            ip_address="1.1.1.1",
            txn_type="PAYMENT",
            amount=50,
            old_balance=1000,
            new_balance=950,
            velocity=1,
        )
        assert result.action == "ALLOW"

    def test_challenge_on_high_velocity(self) -> None:
        """High velocity (>=5) with clean ML should CHALLENGE."""
        service = DetectionService(model=CleanMockModel(), config=MockConfig())
        result = service.evaluate_sync(
            customer_id="CUST_003",
            ip_address="1.1.1.1",
            txn_type="PAYMENT",
            amount=100,
            old_balance=1000,
            new_balance=900,
            velocity=5,
        )
        assert result.action == "CHALLENGE"
        assert result.risk_score == "HIGH"

    def test_block_on_ml_fraud(self) -> None:
        """High ML score should cause BLOCK."""
        service = DetectionService(model=MockModel(), config=MockConfig())
        result = service.evaluate_sync(
            customer_id="CUST_004",
            ip_address="1.1.1.1",
            txn_type="PAYMENT",
            amount=100,
            old_balance=1000,
            new_balance=900,
            velocity=1,
        )
        assert result.action == "BLOCK"
        assert result.risk_score == "CRITICAL"

    def test_result_has_required_fields(self) -> None:
        """DetectionResult must contain all expected fields."""
        service = DetectionService(model=MockModel(), config=MockConfig())
        result = service.evaluate_sync(
            customer_id="CUST_005",
            ip_address="2.2.2.2",
            txn_type="TRANSFER",
            amount=1000,
            old_balance=5000,
            new_balance=4000,
            velocity=2,
        )
        assert result.transaction_id
        assert result.confidence >= 0
        assert result.decision_threshold > 0
        assert isinstance(result.reasons, list)
        assert result.model_version
        assert result.ab_variant in ("champion", "challenger")

    def test_threshold_included_in_result(self) -> None:
        """Decision threshold must be included and not 0.5."""
        service = DetectionService(model=MockModel(), config=MockConfig())
        result = service.evaluate_sync(
            customer_id="CUST_006",
            ip_address="1.1.1.1",
            txn_type="PAYMENT",
            amount=100,
            old_balance=1000,
            new_balance=900,
            velocity=1,
        )
        assert result.decision_threshold != 0.5
        assert 0.1 <= result.decision_threshold <= 0.9


class TestCostThreshold:
    """Tests for cost-aware threshold computation."""

    def test_default_costs(self) -> None:
        """Default FP=$5, FN=$850 gives a low threshold."""
        ct = CostThreshold(5.0, 850.0)
        assert 0.1 <= ct.threshold <= 0.9

    def test_clamping(self) -> None:
        """Extreme values should be clamped."""
        ct = CostThreshold(0.001, 10000)
        assert ct.threshold >= 0.1
