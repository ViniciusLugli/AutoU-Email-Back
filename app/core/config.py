import os
from pathlib import Path
from typing import List

from app.core.constants import ALLOW_CREDENTIALS, ALLOWED_HEADERS, ALLOWED_ORIGINS, ALLOWED_METHODS, USE_CELERY

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "data"

if not DATA_DIR.exists():
    DATA_DIR.mkdir(parents=True)

def get_data_dir() -> Path:
    return DATA_DIR

class Settings:
    ALLOWED_ORIGINS: List[str] = ALLOWED_ORIGINS
    ALLOW_CREDENTIALS: bool = ALLOW_CREDENTIALS == True
    ALLOWED_METHODS: List[str] = ALLOWED_METHODS
    ALLOWED_HEADERS: List[str] = ALLOWED_HEADERS

    USE_CELERY: bool = USE_CELERY == True

settings = Settings()