"""
Request ID injection, structured logging, and Prometheus instrumentation.
"""

from __future__ import annotations

from uuid import uuid4

import structlog
from fastapi import Request, Response
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()

# ── Prometheus metrics ───────────────────────────────────────────────

PREDICTIONS_TOTAL = Counter(
    "sentinel_predictions_total",
    "Total predictions made",
    ["action", "risk_score", "ab_variant"],
)

PREDICTION_LATENCY = Histogram(
    "sentinel_request_duration_seconds",
    "Prediction endpoint latency",
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

FRAUD_RATE = Gauge(
    "sentinel_fraud_rate_1h",
    "Fraud rate in last hour (BLOCK decisions / total)",
)

ACTIVE_WS_CONNECTIONS = Gauge(
    "sentinel_websocket_connections_active",
    "Active WebSocket connections",
)

MODEL_CONFIDENCE = Histogram(
    "sentinel_model_confidence",
    "Distribution of model confidence scores",
    ["ab_variant"],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)


# ── Request ID middleware ────────────────────────────────────────────

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Inject a unique request ID into every HTTP request."""

    async def dispatch(self, request: Request, call_next):
        """Add request context and X-Request-ID header."""
        request_id = str(uuid4())
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            path=request.url.path,
            method=request.method,
        )
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        structlog.contextvars.unbind_contextvars("request_id", "path", "method")
        return response


def get_metrics_response() -> bytes:
    """Return Prometheus metrics in text exposition format."""
    return generate_latest()
