"""Unit tests for feature engineering pipeline."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from sentinel.ml.features import (
    FEATURES_REQUIRED,
    TYPE_MAP,
    compute_optimal_threshold,
    engineer_features,
    validate_features,
)


def _make_df(**overrides) -> pd.DataFrame:
    """Helper to create a single-row transaction DataFrame."""
    base = {
        "type": "TRANSFER",
        "amount": 5000.0,
        "oldbalanceOrg": 10000.0,
        "newbalanceOrig": 5000.0,
    }
    base.update(overrides)
    return pd.DataFrame([base])


class TestTypeMapping:
    """Tests for transaction type encoding."""

    def test_type_mapping_all_types(self) -> None:
        """All known types should map to their correct integer."""
        for type_name, expected_int in TYPE_MAP.items():
            df = _make_df(type=type_name)
            result = engineer_features(df)
            assert result["type"].iloc[0] == expected_int

    def test_unknown_type_defaults_to_zero(self) -> None:
        """Unknown transaction type should default to 0."""
        df = _make_df(type="REFUND")
        result = engineer_features(df)
        assert result["type"].iloc[0] == 0


class TestFeatureComputation:
    """Tests for engineered feature calculations."""

    def test_error_balance_computed_correctly(self) -> None:
        """errorBalanceOrg = newbalanceOrig + amount - oldbalanceOrg."""
        df = _make_df(amount=1000, oldbalanceOrg=5000, newbalanceOrig=4000)
        result = engineer_features(df)
        assert result["errorBalanceOrg"].iloc[0] == 4000 + 1000 - 5000  # 0

    def test_amount_to_balance_ratio(self) -> None:
        """Ratio should be amount / (oldbalanceOrg + epsilon)."""
        df = _make_df(amount=5000, oldbalanceOrg=10000)
        result = engineer_features(df)
        expected = 5000 / (10000 + 1e-9)
        assert abs(result["amount_to_balance_ratio"].iloc[0] - expected) < 1e-6

    def test_is_zero_balance_after(self) -> None:
        """Binary flag should be 1 when newbalanceOrig == 0."""
        df = _make_df(newbalanceOrig=0)
        result = engineer_features(df)
        assert result["is_zero_balance_after"].iloc[0] == 1

    def test_is_zero_balance_after_nonzero(self) -> None:
        """Binary flag should be 0 when newbalanceOrig != 0."""
        df = _make_df(newbalanceOrig=100)
        result = engineer_features(df)
        assert result["is_zero_balance_after"].iloc[0] == 0

    def test_is_round_amount(self) -> None:
        """Binary flag should be 1 for amounts divisible by 1000."""
        df = _make_df(amount=5000)
        result = engineer_features(df)
        assert result["is_round_amount"].iloc[0] == 1

    def test_is_not_round_amount(self) -> None:
        """Binary flag should be 0 for amounts not divisible by 1000."""
        df = _make_df(amount=5432.10)
        result = engineer_features(df)
        assert result["is_round_amount"].iloc[0] == 0


class TestValidation:
    """Tests for input validation."""

    def test_missing_column_raises_value_error(self) -> None:
        """Missing required input column should raise ValueError."""
        df = pd.DataFrame([{"type": "TRANSFER", "amount": 100}])
        with pytest.raises(ValueError, match="Missing input columns"):
            engineer_features(df)

    def test_output_has_exactly_required_columns(self) -> None:
        """Output DataFrame should have exactly FEATURES_REQUIRED columns."""
        df = _make_df()
        result = engineer_features(df)
        assert list(result.columns) == FEATURES_REQUIRED

    def test_nan_input_raises_value_error(self) -> None:
        """NaN values in features should raise ValueError."""
        df = _make_df(amount=float("nan"))
        result = engineer_features(df)
        with pytest.raises(ValueError, match="NaN"):
            validate_features(result)

    def test_inf_input_raises_value_error(self) -> None:
        """Infinite values should raise ValueError."""
        df = _make_df(amount=float("inf"))
        result = engineer_features(df)
        with pytest.raises(ValueError, match="Infinite"):
            validate_features(result)


class TestCostThreshold:
    """Tests for optimal threshold computation."""

    def test_default_cost_ratio(self) -> None:
        """Default FP=$5, FN=$850 should give a low threshold (clamped >= 0.05)."""
        threshold = compute_optimal_threshold(5.0, 850.0)
        assert 0.05 <= threshold <= 0.95

    def test_equal_costs(self) -> None:
        """Equal FP and FN costs should give threshold ≈ 0.5."""
        threshold = compute_optimal_threshold(100.0, 100.0)
        assert abs(threshold - 0.5) < 0.01

    def test_clamping_lower(self) -> None:
        """Very small FP cost relative to FN should clamp at 0.05."""
        threshold = compute_optimal_threshold(0.001, 1000.0)
        assert threshold == 0.05
