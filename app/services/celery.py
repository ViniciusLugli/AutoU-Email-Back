from celery import Celery
import os
from pathlib import Path
from app.core.constants import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

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

celery = Celery("autou", broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_max_tasks_per_child=100,
)

celery.conf.update(imports=("app.services.tasks",))