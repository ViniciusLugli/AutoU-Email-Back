from celery import Celery
import os
from pathlib import Path

DOTENV_PATH = Path(__file__).resolve().parents[2] / ".env"
if DOTENV_PATH.exists():
    try:
        with DOTENV_PATH.open("r") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                os.environ.setdefault(key, val)
    except Exception:
        pass

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

celery.conf.update(imports=("app.services.tasks",))