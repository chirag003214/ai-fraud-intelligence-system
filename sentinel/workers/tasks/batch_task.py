"""
Celery task: batch CSV processing with webhook notification.
"""

from __future__ import annotations

import structlog

from sentinel.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(bind=True, name="sentinel.workers.tasks.batch_task.process_batch")
def process_batch(self, task_id: str, transactions: list[dict], webhook_url: str | None = None) -> dict:
    """Process a batch of transactions and optionally notify via webhook."""
    logger.info("batch_processing_started", task_id=task_id, count=len(transactions))

    results = []
    for txn_data in transactions:
        # In production, each would go through the full detection pipeline
        results.append({"status": "processed", "data": txn_data})

    if webhook_url:
        try:
            import requests
            requests.post(webhook_url, json={"task_id": task_id, "results": results}, timeout=30)
            logger.info("batch_webhook_sent", task_id=task_id, url=webhook_url)
        except Exception as exc:
            logger.warning("batch_webhook_failed", task_id=task_id, error=str(exc))

    logger.info("batch_processing_complete", task_id=task_id, count=len(results))
    return {"task_id": task_id, "processed": len(results)}
