"""
Optuna hyperparameter optimization — 50-trial Bayesian HPO.
"""

from __future__ import annotations

import optuna
import pandas as pd
from sklearn.metrics import f1_score
from sklearn.model_selection import cross_val_score, train_test_split
from xgboost import XGBClassifier

from sentinel.ml.train import find_dataset


def objective(trial: optuna.Trial, X: pd.DataFrame, y: pd.Series) -> float:
    """Single Optuna trial — returns cross-validated F1 score."""
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 50, 300),
        "max_depth": trial.suggest_int("max_depth", 3, 10),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "scale_pos_weight": trial.suggest_int("scale_pos_weight", 50, 200),
        "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
        "subsample": trial.suggest_float("subsample", 0.5, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "eval_metric": "logloss",
        "random_state": 42,
    }

    model = XGBClassifier(**params)
    scores = cross_val_score(model, X, y, cv=3, scoring="f1", n_jobs=-1)
    return float(scores.mean())


def run_tuning(n_trials: int = 50) -> dict:
    """Run Optuna HPO and return best parameters."""
    csv_path = find_dataset()
    df = pd.read_csv(csv_path)
    df = df[df["type"].isin(["CASH_OUT", "TRANSFER"])]

    df["type"] = df["type"].map({"CASH_OUT": 0, "TRANSFER": 1})
    df["errorBalanceOrg"] = df["newbalanceOrig"] + df["amount"] - df["oldbalanceOrg"]
    df["amount_to_balance_ratio"] = df["amount"] / (df["oldbalanceOrg"] + 1e-9)
    df["is_zero_balance_after"] = (df["newbalanceOrig"] == 0).astype(int)  # type: ignore[union-attr]
    df["is_round_amount"] = (df["amount"] % 1000 == 0).astype(int)  # type: ignore[union-attr]

    feature_cols = [
        "type", "amount", "oldbalanceOrg", "newbalanceOrig",
        "errorBalanceOrg", "amount_to_balance_ratio",
        "is_zero_balance_after", "is_round_amount",
    ]
    X = df[feature_cols]
    y = df["isFraud"]

    study = optuna.create_study(direction="maximize")
    study.optimize(lambda trial: objective(trial, X, y), n_trials=n_trials)

    print(f"Best F1: {study.best_value:.4f}")
    print(f"Best params: {study.best_params}")

    return study.best_params


if __name__ == "__main__":
    run_tuning()
