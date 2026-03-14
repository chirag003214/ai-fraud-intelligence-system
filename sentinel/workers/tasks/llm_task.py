"""
Celery task: generate LLM fraud analyst explanation via HuggingFace.

Uses Llama 3-8B to produce a one-sentence risk narrative.
Failures are graceful — the prediction has already been returned.
"""

from __future__ import annotations

import structlog

from sentinel.workers.celery_app import celery_app

logger = structlog.get_logger()


def _build_analyst_prompt(features: dict) -> str:
    """Build a prompt for the fraud analyst LLM."""
    return (
        f"Analyze this transaction:\n"
        f"- Type: {features.get('type', 'UNKNOWN')}\n"
        f"- Amount: ${features.get('amount', 0):,.2f}\n"
        f"- Sender Old Balance: ${features.get('oldbalanceOrg', 0):,.2f}\n"
        f"- Sender New Balance: ${features.get('newbalanceOrig', 0):,.2f}\n"
        f"Explain the risk in exactly one sentence under 30 words."
    )


@celery_app.task(bind=True, max_retries=2, name="sentinel.workers.tasks.llm_task.generate_llm_explanation_task")
def generate_llm_explanation_task(self, txn_id: str, features: dict) -> None:
    """Generate one-sentence fraud analyst narrative using Llama 3-8B."""
    try:
        from huggingface_hub import InferenceClient

        from sentinel.src.core.config import settings

        if not settings.HF_TOKEN:
            logger.info("llm_skipped_no_token", txn_id=txn_id)
            return

        client = InferenceClient(token=settings.HF_TOKEN)
        prompt = _build_analyst_prompt(features)

        response = client.chat_completion(
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior fraud analyst. "
                        "Summarize the risk in exactly one sentence under 30 words."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=60,
        )

        narrative = response.choices[0].message.content.strip()
        _update_explanation_sync(txn_id, llm_explanation=narrative)

        logger.info("llm_explanation_generated", txn_id=txn_id)

    except Exception as exc:
        # LLM failure must NEVER affect the prediction result
        logger.warning("llm_task_failed", txn_id=txn_id, error=str(exc))


def _update_explanation_sync(txn_id: str, llm_explanation: str | None = None) -> None:
    """Synchronous DB update for use inside Celery worker."""
    import asyncio

    from sentinel.src.core.database import async_session_factory, update_explanation

    async def _run() -> None:
        async with async_session_factory() as session:
            await update_explanation(session, txn_id, llm_explanation=llm_explanation)

    asyncio.run(_run())
