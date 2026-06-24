"""
Celery application configuration.

Broker: Redis (message queue)
Backend: Redis (temporary task state)
Persistent storage: PostgreSQL (via document_tasks.py)
"""

from celery import Celery
from app.core.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

celery_app = Celery(
    "intellicheck",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["app.workers.document_tasks"],
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Task tracking
    task_track_started=True,

    # Time limits (per task)
    task_time_limit=600,           # 10 min hard kill
    task_soft_time_limit=540,      # 9 min soft limit (raises SoftTimeLimitExceeded)

    # Worker reliability
    worker_prefetch_multiplier=1,       # Fetch 1 task at a time (fair scheduling)
    task_acks_late=True,                # Acknowledge AFTER task completes (no lost tasks)
    task_reject_on_worker_lost=True,    # Re-queue task if worker crashes mid-processing
    worker_max_memory_per_child=2_000_000,  # Restart worker at ~2 GB RAM

    # Result expiry (Redis only — PostgreSQL is permanent)
    result_expires=86400,  # 24 hours
)
