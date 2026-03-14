"""
Full PaySim training pipeline with MLflow experiment tracking.

Refactored from the original scripts/train.py — adds proper feature
engineering, evaluation metrics, and model registry integration.
"""

from __future__ import annotations

import os

import mlflow
import mlflow.sklearn
import pandas as pd
import structlog
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    f1_score,
    precision_recall_curve,
)
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from sentinel.ml.features import TYPE_MAP

logger = structlog.get_logger()

DATA_DIR = "data"
MODEL_OUTPUT = "fraud_model"


def find_dataset() -> str:
    """Locate the PaySim CSV in the data directory."""
    if not os.path.exists(DATA_DIR):
        raise FileNotFoundError(f"Data directory not found: {DATA_DIR}")
    for f in os.listdir(DATA_DIR):
        if f.endswith(".csv"):
            return os.path.join(DATA_DIR, f)
    raise FileNotFoundError("No CSV file found in data/ directory")


def train(data_path: str | None = None) -> None:
    """Run the full training pipeline."""
    csv_path = data_path or find_dataset()
    logger.info("training_started", data_path=csv_path)

    # 1. Load & preprocess
    df = pd.read_csv(csv_path)
    df = df[df["type"].isin(["CASH_OUT", "TRANSFER"])]

    # Feature engineering (same as inference pipeline)
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

    # 2. Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # 3. Save reference data for drift monitoring
    reference_path = "ml/reference_data.csv"
    X_train.head(10000).to_csv(reference_path, index=False)
    logger.info("reference_data_saved", path=reference_path, rows=min(10000, len(X_train)))

    # 4. Train with MLflow tracking
    mlflow.set_experiment("Fraud_Detection_System")

    with mlflow.start_run():
        model = XGBClassifier(
            scale_pos_weight=99,
            eval_metric="logloss",
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
        )
        model.fit(X_train, y_train)

        # 5. Evaluate
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]

        f1 = f1_score(y_test, y_pred)
        pr_auc = average_precision_score(y_test, y_proba)

        # 6. Log metrics
        mlflow.log_metric("f1_score", f1)
        mlflow.log_metric("pr_auc", pr_auc)
        mlflow.log_param("n_estimators", 100)
        mlflow.log_param("max_depth", 6)
        mlflow.log_param("scale_pos_weight", 99)

        # 7. Log and save model
        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="model",
            registered_model_name="FraudGuard",
        )
        mlflow.sklearn.save_model(model, MODEL_OUTPUT)

        logger.info(
            "training_complete",
            f1_score=round(f1, 4),
            pr_auc=round(pr_auc, 4),
        )

        print(f"✅ Training complete — F1: {f1:.4f}, PR-AUC: {pr_auc:.4f}")
        print(classification_report(y_test, y_pred))


if __name__ == "__main__":
    train()
