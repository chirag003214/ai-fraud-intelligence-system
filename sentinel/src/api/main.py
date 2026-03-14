"""
Sentinel Fraud Intelligence API — FastAPI app factory with lifespan.

This module is only wiring. No business logic lives here.
All behaviour is delegated to services, routes, and middleware.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sentinel.ml.loader import model_registry
from sentinel.src.api.middleware import RequestIDMiddleware
from sentinel.src.api.routes import explain, health, history, predict, websocket
from sentinel.src.core.config import configure_logging, settings
from sentinel.src.core.database import close_db, init_db
from sentinel.src.core.redis_client import close_redis, init_redis

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    # ── Startup ──────────────────────────────────────────────────────
    configure_logging()
    logger.info("sentinel_starting", environment=settings.ENVIRONMENT)

    await init_db()
    await init_redis()

    # Load ML model(s)
    model_registry.load(
        model_path=settings.MODEL_PATH,
        champion_version=os.getenv("CHAMPION_MODEL_VERSION", "latest"),
        challenger_path=os.getenv("CHALLENGER_MODEL_PATH"),
        challenger_version=os.getenv("CHALLENGER_MODEL_VERSION"),
    )

    # Set startup time for health endpoint
    from sentinel.src.api.routes.health import set_startup_time
    set_startup_time()

    logger.info(
        "sentinel_ready",
        model_path=settings.MODEL_PATH,
        model_loaded=model_registry.is_loaded,
        ab_challenger_pct=settings.AB_CHALLENGER_PCT,
    )

    yield

    # ── Shutdown ─────────────────────────────────────────────────────
    logger.info("sentinel_shutting_down")
    await close_redis()
    await close_db()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Sentinel Fraud Intelligence API",
        version="2.0.0",
        description=(
            "Production-grade fraud detection with XGBoost, SHAP explanations, "
            "cost-aware thresholding, and live A/B testing."
        ),
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIDMiddleware)

    # ── Routes ───────────────────────────────────────────────────────
    app.include_router(predict.router, prefix="/v1", tags=["predictions"])
    app.include_router(explain.router, prefix="/v1", tags=["explanations"])
    app.include_router(history.router, prefix="/v1", tags=["history"])
    app.include_router(health.router, prefix="/v1", tags=["health"])
    app.include_router(websocket.router, tags=["realtime"])

    # Root redirect to docs
    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        """Root endpoint redirects to API docs."""
        return {"message": "Sentinel Fraud Intelligence API v2.0.0", "docs": "/docs"}

    return app


# Module-level app instance for uvicorn
app = create_app()
