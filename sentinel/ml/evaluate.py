"""
Model evaluation — PR-AUC, F1, calibration, cost curve metrics.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_recall_curve,
    roc_auc_score,
)


def evaluate_model(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    fp_cost: float = 5.0,
    fn_cost: float = 850.0,
) -> dict:
    """Compute comprehensive evaluation metrics."""
    y_pred = (y_proba >= 0.5).astype(int)

    f1 = f1_score(y_true, y_pred)
    pr_auc = average_precision_score(y_true, y_proba)
    roc = roc_auc_score(y_true, y_proba)

    # Cost curve
    thresholds = np.linspace(0.01, 0.99, 100)
    costs = []
    for t in thresholds:
        preds = (y_proba >= t).astype(int)
        fp = ((preds == 1) & (y_true == 0)).sum()  # type: ignore[union-attr]
        fn = ((preds == 0) & (y_true == 1)).sum()  # type: ignore[union-attr]
        cost = fp * fp_cost + fn * fn_cost
        costs.append(float(cost))

    optimal_idx = int(np.argmin(costs))
    optimal_threshold = float(thresholds[optimal_idx])

    # Calibration
    prob_true, prob_pred = calibration_curve(y_true, y_proba, n_bins=10)

    return {
        "f1": round(f1, 4),
        "pr_auc": round(pr_auc, 4),
        "roc_auc": round(roc, 4),
        "optimal_threshold": round(optimal_threshold, 4),  # type: ignore[call-overload]
        "min_cost": round(costs[optimal_idx], 2),  # type: ignore[call-overload]
        "calibration_error": round(float(np.mean(np.abs(prob_true - prob_pred))), 4),  # type: ignore[call-overload]
    }
