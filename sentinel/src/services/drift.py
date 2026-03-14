"""
Drift monitoring using PSI (Population Stability Index).

Computes PSI between training reference data and recent transactions
to detect feature distribution changes that may degrade model performance.
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd
import structlog

from sentinel.ml.features import engineer_features

logger = structlog.get_logger()

# ── Standalone PSI computation ───────────────────────────────────────
# We implement PSI directly instead of requiring Evidently as a hard
# dependency at runtime — Evidently is heavy and the PSI formula is simple.


def _compute_psi(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    """
    Compute Population Stability Index between two distributions.

    PSI < 0.1  → distributions are similar (stable)
    PSI 0.1–0.2 → moderate change (warning)
    PSI > 0.2  → significant change (drift detected)
    """
    eps = 1e-6
    breakpoints = np.histogram_bin_edges(reference, bins=bins)
    ref_counts = np.histogram(reference, bins=breakpoints)[0] / len(reference)
    cur_counts = np.histogram(current, bins=breakpoints)[0] / len(current)

    # Add epsilon to avoid log(0)
    ref_counts = np.clip(ref_counts, eps, None)
    cur_counts = np.clip(cur_counts, eps, None)

    psi = np.sum((cur_counts - ref_counts) * np.log(cur_counts / ref_counts))
    return float(psi)


async def compute_drift_report(
    recent_transactions: list[dict],
    reference_path: str = "ml/reference_data.csv",
) -> dict:
    """
    Compute PSI between training reference data and recent transactions.

    Args:
        recent_transactions: List of dicts with raw transaction fields.
        reference_path: Path to the reference CSV (first 10k training rows).

    Returns:
        Dict with drift status, per-feature PSI, sample size, and timestamp.
    """
    try:
        reference_df = pd.read_csv(reference_path)
    except FileNotFoundError:
        return {"status": "reference_data_missing", "message": f"File not found: {reference_path}"}

    if len(recent_transactions) < 100:
        return {
            "status": "insufficient_data",
            "min_required": 100,
            "current_count": len(recent_transactions),
        }

    current_df = pd.DataFrame(recent_transactions)

    try:
        reference_features = engineer_features(reference_df)
        current_features = engineer_features(current_df)
    except (ValueError, KeyError) as exc:
        logger.warning("drift_feature_engineering_failed", error=str(exc))
        return {"status": "feature_engineering_error", "error": str(exc)}

    # Compute PSI for each numeric feature
    feature_psi: dict[str, float] = {}
    numeric_cols = reference_features.select_dtypes(include=[np.number]).columns

    for col in numeric_cols:
        ref_vals = reference_features[col].dropna().values
        cur_vals = current_features[col].dropna().values
        if len(ref_vals) > 0 and len(cur_vals) > 0:
            psi_value = _compute_psi(ref_vals, cur_vals)
            feature_psi[col] = round(psi_value, 4)  # type: ignore[call-overload]

    max_psi = max(feature_psi.values()) if feature_psi else 0.0

    return {
        "status": "drift_detected" if max_psi > 0.2 else "stable",
        "max_psi": round(max_psi, 4),  # type: ignore[call-overload]
        "features": feature_psi,
        "sample_size": len(current_df),
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }
