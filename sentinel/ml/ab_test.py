"""
A/B test routing and outcome logging.

Uses MD5 hash of customer_id for deterministic routing — same customer
always gets the same model variant across requests and server restarts.
"""

from __future__ import annotations

import hashlib
from typing import Literal

import structlog

logger = structlog.get_logger()


class ABRouter:
    """
    Deterministic A/B routing for champion vs. challenger models.

    Uses MD5 hash of customer_id modulo 100 to assign a stable bucket,
    ensuring reproducibility without any server-side state.
    """

    def __init__(self, challenger_pct: int = 10) -> None:
        self.challenger_pct = challenger_pct

    def route(self, customer_id: str) -> Literal["champion", "challenger"]:
        """Return the model variant for this customer."""
        bucket = int(hashlib.md5(customer_id.encode()).hexdigest(), 16) % 100
        return "challenger" if bucket < self.challenger_pct else "champion"


def log_ab_outcome(
    transaction_id: str,
    variant: str,
    confidence: float,
    action: str,
) -> None:
    """
    Log an A/B test outcome for later analysis.

    In production this would write to a dedicated ab_outcomes table;
    for now we log structured data that can be aggregated.
    """
    logger.info(
        "ab_outcome",
        transaction_id=transaction_id,
        variant=variant,
        confidence=confidence,
        action=action,
    )
