"""
Celery task: compute SHAP TreeExplainer values for a prediction.

Stores the top 5 feature attributions as JSON in the transactions table.
"""

from __future__ import annotations

import json

import pandas as pd
import structlog

from sentinel.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(bind=True, max_retries=3, name="sentinel.workers.tasks.shap_task.compute_shap_task")
def compute_shap_task(self, txn_id: str, features: dict, model_variant: str) -> None:
    """Compute SHAP values and store to the database."""
    try:
        import shap

        from sentinel.ml.loader import model_registry

        model = model_registry.get_variant(model_variant)

        # Get the underlying booster for TreeExplainer
        underlying = getattr(model, "_model_impl", model)
        if hasattr(underlying, "get_booster"):
            explainer = shap.TreeExplainer(underlying)
        else:
            explainer = shap.TreeExplainer(underlying)

        feature_df = pd.DataFrame([features])
        shap_values = explainer.shap_values(feature_df)

        # Format top 5 features by absolute SHAP value
        feature_names = list(feature_df.columns)
        values = shap_values[0] if hasattr(shap_values, '__len__') else shap_values
        pairs = sorted(
            zip(feature_names, values),
            key=lambda x: abs(x[1]),
            reverse=True,
        )[:5]  # type: ignore[index]

        result = [{"feature": f, "shap": round(float(v), 4)} for f, v in pairs]  # type: ignore[call-overload]

        # Update database (sync call inside Celery worker)
        _update_explanation_sync(txn_id, shap_values=json.dumps(result))

        logger.info("shap_computed", txn_id=txn_id, top_feature=result[0]["feature"])

    except Exception as exc:
        logger.warning("shap_task_failed", txn_id=txn_id, error=str(exc))
        raise self.retry(exc=exc, countdown=30)


def _update_explanation_sync(txn_id: str, shap_values: str | None = None) -> None:
    """Synchronous DB update for use inside Celery worker."""
    import asyncio

    from sentinel.src.core.database import async_session_factory, update_explanation

    async def _run() -> None:
        async with async_session_factory() as session:
            await update_explanation(session, txn_id, shap_values=shap_values)

    asyncio.run(_run())
