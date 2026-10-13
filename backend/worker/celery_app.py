from celery import Celery
from kombu import Queue

from backend.core.config import settings

celery_app = Celery(
    "resume_analyzer_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,  # Reduce task loss if worker restarts
    worker_prefetch_multiplier=1,  # Single task per process for heavy CPU workloads
    task_queues=[
        Queue("resume_queue", routing_key="resume.#"),
        Queue("explanation_queue", routing_key="explanation.#"),
    ],
    task_default_queue="resume_queue",
    task_default_exchange="tasks",
    task_default_routing_key="resume.process",
)
