"""
Feature engineering pipeline — consolidates all transformations in one place.

The original code had inline feature engineering inside the predict function.
This module extracts it into a testable, reusable pipeline that guarantees
the model always receives exactly the features it expects.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# ── Feature configuration ────────────────────────────────────────────

FEATURES_REQUIRED: list[str] = [
    "type",
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "errorBalanceOrg",
    "amount_to_balance_ratio",
    "is_zero_balance_after",
    "is_round_amount",
]

# The original training script used this mapping —
# must stay in sync with scripts/train.py
TYPE_MAP: dict[str, int] = {
    "CASH_OUT": 0,
    "TRANSFER": 1,
    "PAYMENT": 3,
    "CASH_IN": 4,
    "DEBIT": 5,
}


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply all feature transformations.

    Accepts a DataFrame with raw transaction fields (type, amount,
    oldbalanceOrg, newbalanceOrig) and returns a new DataFrame with
    exactly ``FEATURES_REQUIRED`` columns.

    Raises ``ValueError`` if required input columns are missing.
    """
    required_inputs = {"type", "amount", "oldbalanceOrg", "newbalanceOrig"}
    missing_inputs = required_inputs - set(df.columns)
    if missing_inputs:
        raise ValueError(f"Missing input columns: {missing_inputs}")

    df = df.copy()

    # Map transaction type string → int
    df["type"] = df["type"].map(TYPE_MAP).fillna(0).astype(int)

    # Original engineered feature — error between expected and actual balance
    df["errorBalanceOrg"] = (
        df["newbalanceOrig"] + df["amount"] - df["oldbalanceOrg"]
    )

    # Ratio of transaction amount to sender balance.
    # Near-1.0 or >1.0 values are suspicious (draining the account).
    df["amount_to_balance_ratio"] = df["amount"] / (df["oldbalanceOrg"] + 1e-9)

    # Binary flag: balance drops to exactly zero (common in Phantom Drain attacks).
    df["is_zero_balance_after"] = (df["newbalanceOrig"] == 0).astype(int)  # type: ignore[union-attr]

    # Binary flag: round-number amounts are more likely social engineering.
    df["is_round_amount"] = (df["amount"] % 1000 == 0).astype(int)  # type: ignore[union-attr]

    # Validate output
    missing_output = set(FEATURES_REQUIRED) - set(df.columns)
    if missing_output:
        raise ValueError(f"Feature engineering failed, missing: {missing_output}")

    return df[FEATURES_REQUIRED]


def validate_features(df: pd.DataFrame) -> None:
    """
    Check for NaN, inf, and out-of-range values in engineered features.

    Raises ``ValueError`` with a descriptive message if any problem is found.
    """
    if df.isnull().any().any():
        bad_cols = df.columns[df.isnull().any()].tolist()
        raise ValueError(f"NaN values detected in columns: {bad_cols}")

    for col in df.select_dtypes(include=[np.number]).columns:
        if np.isinf(df[col]).any():
            raise ValueError(f"Infinite values detected in column: {col}")

    if (df["amount"] < 0).any():
        raise ValueError("Negative transaction amounts detected")


def compute_optimal_threshold(fp_cost: float, fn_cost: float) -> float:
    """
    Bayes-optimal decision threshold from cost matrix.

    Derivation:
      We minimise expected cost = P(fraud) * FN_cost * (1 - recall)
                                + P(legit) * FP_cost * FPR
      The cost-minimising threshold is:
        t* = FP_cost / (FP_cost + FN_cost)

    Example:
      FP_cost = $5 (analyst investigation time)
      FN_cost = $850 (average fraud loss)
      t* = 5 / (5 + 850) ≈ 0.0059 → clamped to [0.05, 0.95]
    """
    raw = fp_cost / (fp_cost + fn_cost)
    return max(0.05, min(0.95, raw))
