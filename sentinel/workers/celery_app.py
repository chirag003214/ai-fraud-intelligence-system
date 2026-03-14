"""
Celery app configuration with Redis broker.
"""

from __future__ import annotations

from celery import Celery

from sentinel.src.core.config import settings

celery_app = Celery(
    "sentinel",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "sentinel.workers.tasks.shap_task",
        "sentinel.workers.tasks.llm_task",
        "sentinel.workers.tasks.batch_task",
        "sentinel.workers.tasks.retrain_task",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Scheduled tasks (Celery Beat)
celery_app.conf.beat_schedule = {
    "check-drift-every-24h": {
        "task": "sentinel.workers.tasks.retrain_task.check_drift_and_retrain",
        "schedule": 86400.0,  # 24 hours
    },
}
