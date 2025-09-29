import os
import asyncio
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List, Tuple
from collections import Counter
import re
import warnings
import httpx

DEFAULT_SPACY_MODEL = os.getenv("DEFAULT_SPACY_MODEL", "pt_core_news_sm")
NLP_WORKERS = int(os.getenv("NLP_WORKERS", "2"))
def _get_gemini_config():
    return {
        "url": os.getenv("GEMINI_API_URL"),
        "key": os.getenv("GEMINI_API_KEY"),
        "timeout": float(os.getenv("GEMINI_TIMEOUT", "10")),
    }

_nlp = None

def _ensure_model_loaded(model_name: str = DEFAULT_SPACY_MODEL):
    global _nlp
    # Local spaCy model removed: we no longer support local processing here.
    # Keep a placeholder to avoid breaking callers, but raise if called directly.
    raise RuntimeError("local spacy model support removed; set GEMINI_API_URL to use external NLP service")

def _preprocess_sync(text: str, top_n: int = 15) -> Dict:
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    # Only Gemini API is supported now — read config at call time
    cfg = _get_gemini_config()
    if not cfg["url"]:
        raise RuntimeError("Gemini API not configured: set GEMINI_API_URL to enable NLP preprocessing")
    try:
        payload = {"task": "nlp", "text": text, "top_n": top_n}
        headers = {}
        if cfg.get("key"):
            headers["Authorization"] = f"Bearer {cfg.get('key')}"
        r = httpx.post(cfg.get("url"), json=payload, headers=headers, timeout=cfg.get("timeout"))
        r.raise_for_status()
        data = r.json()
        # Validate shape
        if not data or not isinstance(data, dict) or not data.get("cleaned_text"):
            raise RuntimeError("Invalid response from Gemini NLP API")
        return {
            "cleaned_text": data.get("cleaned_text"),
            "tokens": data.get("tokens", []),
            "unique_tokens": int(data.get("unique_tokens", len(data.get("tokens", [])))),
            "total_tokens": int(data.get("total_tokens", len(data.get("tokens", [])))),
            "top_tokens": data.get("top_tokens", [])[:top_n],
            "original_len": int(data.get("original_len", len(text))),
        }
    except Exception as exc:
        raise RuntimeError(f"NLP preprocessing failed via Gemini API: {exc}") from exc

def preprocess_sync(text: str, top_n: int = 15) -> Dict:
    return _preprocess_sync(text, top_n=top_n)

_process_executor: ProcessPoolExecutor = ProcessPoolExecutor(max_workers=NLP_WORKERS)

async def preprocess_async(text: str, top_n: int = 15) -> Dict:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_process_executor, _preprocess_sync, text, top_n)
