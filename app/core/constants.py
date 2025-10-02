from typing import List
from dotenv import load_dotenv
import os

load_dotenv()

#Database
DATABASE_URL: str =os.getenv("DATABASE_URL")

#Security
SECRET_KEY: str = os.getenv("SECRET_KEY", "your_super_secret_key")
ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60").strip())

#Celery
_raw_use_celery: str = os.getenv("USE_CELERY", "true").strip()
USE_CELERY: bool = _raw_use_celery.lower() in ("1", "true", "yes", "y", "on")
CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1").strip()
CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2").strip()
_raw_autoscale: str = os.getenv("CELERY_AUTOSCALE", "10,3").strip()

try:
	parts = [p.strip() for p in _raw_autoscale.split(",") if p.strip()]
	if len(parts) == 2:
		CELERY_AUTOSCALE: tuple[int, int] = (int(parts[0]), int(parts[1]))
	else:
		CELERY_AUTOSCALE: tuple[int, int] = (int(parts[0]), 1) if parts else (10, 3)
except Exception:
	CELERY_AUTOSCALE: tuple[int, int] = (10, 3)

CELERY_CONCURRENCY: int = int(os.getenv("CELERY_CONCURRENCY", "2").strip())

#NLP
DEFAULT_SPACY_MODEL: str = os.getenv("DEFAULT_SPACY_MODEL", "pt_core_news_sm")
NLP_WORKERS: int = int(os.getenv("NLP_WORKERS", "2").strip())
IA_ASYNC_WORKERS: int = int(os.getenv("IA_ASYNC_WORKERS", "2").strip())

#GenAI
GENAI_API_KEY: str = os.getenv("GENAI_API_KEY")
GENAI_MODEL: str = os.getenv("GENAI_MODEL", "gemma-3-27b-it")
GENAI_MAX_OUTPUT_TOKENS: int = int(os.getenv("GENAI_MAX_OUTPUT_TOKENS", "2056").strip())
GENAI_TEMPERATURE: float = float(os.getenv("GENAI_TEMPERATURE", "0.4").strip())

#CORS
ALLOWED_ORIGINS: List[str] = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173").strip().split(",")
_raw_allow_credentials = os.getenv("ALLOW_CREDENTIALS", "true").strip()
ALLOW_CREDENTIALS: bool = _raw_allow_credentials.lower() in ("1", "true", "yes", "y", "on")
ALLOWED_METHODS: List[str] = os.getenv("ALLOWED_METHODS", "GET,POST,PUT,DELETE,OPTIONS").strip().split(",")
ALLOWED_HEADERS: List[str] = os.getenv("ALLOWED_HEADERS", "*").strip().split(",")