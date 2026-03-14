"""
Core fraud detection pipeline — rules → ML → cost threshold → decision.

This module has ZERO FastAPI imports. It is pure Python business logic,
fully testable without an HTTP server.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import uuid4

import pandas as pd
import structlog

from sentinel.ml.features import engineer_features

logger = structlog.get_logger()


# ── Data classes ─────────────────────────────────────────────────────

@dataclass
class DetectionResult:
    """Immutable result of evaluating a single transaction."""

    transaction_id: str
    action: Literal["ALLOW", "CHALLENGE", "BLOCK"]
    risk_score: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    confidence: float
    decision_threshold: float
    reasons: list[str]
    velocity_1h: int
    model_version: str
    ab_variant: str
    shap_values: list[dict[str, Any]] | None = None


# ── Rules engine ─────────────────────────────────────────────────────

class RulesEngine:
    """
    Hard rules run BEFORE the ML model.

    They are faster and more reliable for known attack patterns.
    Each rule is named after the fraud pattern it detects.
    """

    def check(self, txn_type: str, amount: float, old_balance: float, new_balance: float) -> list[str]:
        """Return a list of rule violation names for this transaction."""
        violations: list[str] = []

        # Phantom Drain: balance goes to exactly zero after transfer/cash-out
        if txn_type in ("TRANSFER", "CASH_OUT"):
            if old_balance > 0 and new_balance == 0:
                violations.append("Phantom Drain")

        # Magic Money: new balance exceeds old balance + amount (impossible)
        if new_balance > old_balance + amount + 1.0:
            violations.append("Magic Money")

        # Large Value flag (signal, not a hard block)
        if amount > 100_000:
            violations.append("Large Value (>$100k)")

        return violations


# ── Cost-aware threshold ─────────────────────────────────────────────

class CostThreshold:
    """
    Bayes-optimal classification threshold derived from cost matrix.

    threshold = FP_cost / (FP_cost + FN_cost)
    Clamped to [0.1, 0.9] to avoid extreme values.
    See docs/decisions/003-cost-threshold.md for the full derivation.
    """

    def __init__(self, fp_cost: float, fn_cost: float) -> None:
        self.raw_threshold = fp_cost / (fp_cost + fn_cost)
        self.threshold = max(0.1, min(0.9, self.raw_threshold))


# ── A/B Router ───────────────────────────────────────────────────────

class ABRouter:
    """
    Deterministic A/B routing using MD5 hash of customer_id.

    Same customer always gets the same model variant across requests
    and server restarts. Challenger percentage is configurable.
    """

    def __init__(self, challenger_pct: int = 10) -> None:
        self.challenger_pct = challenger_pct

    def route(self, customer_id: str) -> Literal["champion", "challenger"]:
        """Return the model variant for this customer."""
        bucket = int(hashlib.md5(customer_id.encode()).hexdigest(), 16) % 100
        return "challenger" if bucket < self.challenger_pct else "champion"


# ── Detection service ────────────────────────────────────────────────

class DetectionService:
    """
    Orchestrates the full detection pipeline for a single transaction.

    Pipeline stages:
      1. Velocity check (Redis, O(1))
      2. Hard rules (deterministic, sub-ms)
      3. ML inference (XGBoost, ~1ms)
      4. Decision fusion (rules + ML + velocity → action)
    """

    def __init__(self, model: Any, config: Any) -> None:
        self.rules = RulesEngine()
        self.threshold = CostThreshold(config.FRAUD_FP_COST, config.FRAUD_FN_COST)
        self.model = model
        self.ab_router = ABRouter(config.AB_CHALLENGER_PCT)
        self.model_version = getattr(model, "version", "1.0.0")

    def evaluate_sync(
        self,
        *,
        customer_id: str,
        ip_address: str,
        txn_type: str,
        amount: float,
        old_balance: float,
        new_balance: float,
        velocity: int,
    ) -> DetectionResult:
        """
        Synchronous evaluation — used after velocity has been fetched.

        This is separated from the async velocity call so the core logic
        remains pure-synchronous and trivially testable.
        """
        is_high_velocity = velocity >= 5

        # Phase 2: hard rules
        rule_violations = self.rules.check(txn_type, amount, old_balance, new_balance)

        # Phase 3: ML inference
        raw_data = pd.DataFrame([{
            "type": txn_type,
            "amount": amount,
            "oldbalanceOrg": old_balance,
            "newbalanceOrig": new_balance,
        }])
        features = engineer_features(raw_data)

        ab_variant = self.ab_router.route(customer_id)

        # The original model uses .predict() returning 0/1.
        # We try predict_proba first for confidence scoring.
        try:
            ml_proba = float(self.model.predict_proba(features)[0][1])
        except AttributeError:
            # MLflow pyfunc models only have .predict()
            prediction = float(self.model.predict(features)[0])
            ml_proba = prediction  # treat as probability when proba unavailable

        ml_fraud = ml_proba >= self.threshold.threshold

        # Phase 4: decision fusion
        reasons: list[str] = list(rule_violations)
        if ml_fraud:
            reasons.append(
                f"ML Score {ml_proba:.2f} ≥ threshold {self.threshold.threshold:.2f}"
            )
        if is_high_velocity:
            reasons.append(f"High Velocity ({velocity} txns/hr)")

        # Decision matrix:
        # BLOCK  — any rule fires OR ML says fraud
        # CHALLENGE — high velocity but ML says clean
        # ALLOW  — everything clean
        if rule_violations or ml_fraud:
            action: Literal["ALLOW", "CHALLENGE", "BLOCK"] = "BLOCK"
            risk_score: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "CRITICAL"
        elif is_high_velocity:
            action = "CHALLENGE"
            risk_score = "HIGH"
        else:
            action = "ALLOW"
            risk_score = "LOW" if ml_proba < 0.2 else "MEDIUM"

        result = DetectionResult(
            transaction_id=str(uuid4()),
            action=action,
            risk_score=risk_score,
            confidence=ml_proba,
            decision_threshold=self.threshold.threshold,
            reasons=reasons,
            velocity_1h=velocity,
            model_version=self.model_version,
            ab_variant=ab_variant,
            shap_values=None,
        )

        logger.info(
            "detection_complete",
            transaction_id=result.transaction_id,
            action=result.action,
            confidence=result.confidence,
            ab_variant=result.ab_variant,
        )

        return result
