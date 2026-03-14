"""
Async SHAP + LLM explanation service.

The original explain_fraud() function blocked the prediction response.
This module makes explanation non-blocking: the prediction returns
immediately, and SHAP/LLM results are computed in Celery background
tasks and stored in the database.
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger()


class ExplainerService:
    """Triggers async SHAP and LLM explanation tasks."""

    def trigger_async_explanation(
        self,
        txn_id: str,
        features: dict,
        model_variant: str,
    ) -> None:
        """
        Queue SHAP + LLM explanation. Non-blocking. Returns immediately.

        SHAP is queued first (fast, local computation), then the LLM
        task (slow, remote API call). Both write results back to the
        transactions table independently.
        """
        try:
            from sentinel.workers.tasks.shap_task import compute_shap_task
            from sentinel.workers.tasks.llm_task import generate_llm_explanation_task

            compute_shap_task.delay(txn_id, features, model_variant)
            generate_llm_explanation_task.delay(txn_id, features)

            logger.info(
                "explanation_queued",
                txn_id=txn_id,
                model_variant=model_variant,
            )
        except Exception as exc:
            # Explanation failure must NEVER affect the prediction result
            logger.warning(
                "explanation_queue_failed",
                txn_id=txn_id,
                error=str(exc),
            )
