from celery import Celery
import os

CELERY_BROKER = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
CELERY_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

celery = Celery("autou", broker=CELERY_BROKER, backend=CELERY_BACKEND)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_max_tasks_per_child=100,
)