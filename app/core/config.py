import os
from pathlib import Path
from typing import List

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "data"

if not DATA_DIR.exists():
    DATA_DIR.mkdir(parents=True)

def get_data_dir() -> Path:
    return DATA_DIR

class Settings:
    # CORS Configuration
    ALLOWED_ORIGINS: List[str] = os.getenv(
        "ALLOWED_ORIGINS", 
        "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
    ).split(",")
    
    ALLOW_CREDENTIALS: bool = os.getenv("ALLOW_CREDENTIALS", "true").lower() == "true"
    ALLOWED_METHODS: List[str] = os.getenv("ALLOWED_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(",")
    ALLOWED_HEADERS: List[str] = os.getenv("ALLOWED_HEADERS", "*").split(",")
    
    # Celery/Redis Configuration  
    USE_CELERY: bool = os.getenv("USE_CELERY", "false").lower() == "true"

settings = Settings()