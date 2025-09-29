import os
import asyncio
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, Any, Optional
import httpx

from app.models import Category

IA_API_URL = os.getenv("IA_API_URL")
IA_API_KEY = os.getenv("IA_API_KEY")
IA_TIMEOUT = float(os.getenv("IA_TIMEOUT", "30"))

def _get_gemini_config():
    return {
        "url": os.getenv("GEMINI_API_URL"),
        "key": os.getenv("GEMINI_API_KEY"),
        "timeout": float(os.getenv("GEMINI_TIMEOUT", "10")),
    }

DEFAULT_CLASSIFIER_MODEL = os.getenv("HF_MODEL", "pierreguillou/bert-base-cased-sentiment")
DEFAULT_GENERATOR_MODEL = os.getenv("HF_GEN_MODEL", "t5-small")
HF_CONFIDENCE_THRESHOLD = float(os.getenv("HF_THRESHOLD", "0.5"))
GEN_MAX_LENGTH = int(os.getenv("GEN_MAX_LENGTH", "128"))
GEN_TEMPERATURE = float(os.getenv("GEN_TEMPERATURE", "0.7"))

_infer_pipeline = None
_generator_pipeline = None


def _map_label_to_category(label: str, score: float) -> Category:
    lab = (label or "").lower()
    if score < HF_CONFIDENCE_THRESHOLD:
        return Category.IMPRODUTIVO
    if "produt" in lab or "positivo" in lab or "positive" in lab or lab.startswith("pos") or lab.endswith("_1"):
        return Category.PRODUTIVO
    return Category.IMPRODUTIVO


def _build_generation_prompt(category: Category, email_text: str) -> str:
    role = "responder com ação e próximos passos" if category is Category.PRODUTIVO else "responder brevemente e educadamente, sem solicitar ação imediata"
    prompt = (
        "Você é um assistente que gera respostas por e-mail.\n\n"
        "Contexto: classificado como '{}'.\n\n"
        "E-mail:\n"
        "-----\n"
        f"{email_text}\n"
        "-----\n\n"
        "Gere uma resposta apropriada seguindo este papel: {}. Seja específico, inclua perguntas relevantes e próximos passos quando apropriado. "
        "Resposta em português, curta e profissional.".format(category.value, role)
    )
    return prompt


def _ensure_classifier_loaded(model_name: str = DEFAULT_CLASSIFIER_MODEL):
    global _infer_pipeline
    if _infer_pipeline is None:
        from transformers import pipeline

        _infer_pipeline = pipeline("text-classification", model=model_name, truncation=True)
    return _infer_pipeline


def _ensure_generator_loaded(model_name: str = DEFAULT_GENERATOR_MODEL):
    global _generator_pipeline
    if _generator_pipeline is None:
        from transformers import pipeline

        try:
            _generator_pipeline = pipeline("text2text-generation", model=model_name)
        except Exception:
            _generator_pipeline = pipeline("text-generation", model=model_name)
    return _generator_pipeline


def _generate_response(category: Category, email_text: str) -> str:
    generator = _ensure_generator_loaded()
    prompt = _build_generation_prompt(category, email_text)
    try:
        out = generator(prompt, max_length=GEN_MAX_LENGTH, do_sample=True, temperature=GEN_TEMPERATURE, num_return_sequences=1)
        text = out[0].get("generated_text") or out[0].get("summary_text") or out[0].get("text", "")
    except Exception:
        text = (
            "[Erro ao gerar resposta automática] Sugestão: responda pedindo mais detalhes ou proponha próximos passos."
        )
    return text.strip()


def _infer_sync_local(text: str) -> Dict[str, Any]:
    # Local models removed. This function should not be called when Gemini-only is configured.
    raise RuntimeError("local inference removed; configure GEMINI_API_URL to use external IA service")


def _call_external_api_sync(text: str) -> Optional[Dict[str, Any]]:
    # Only Gemini API is supported now for sync inference
    cfg = _get_gemini_config()
    if not cfg.get("url"):
        raise RuntimeError("Gemini API not configured: set GEMINI_API_URL to enable inference")
    headers = {}
    if cfg.get("key"):
        headers["Authorization"] = f"Bearer {cfg.get('key')}"
    try:
        r = httpx.post(cfg.get("url"), json={"task": "infer", "text": text}, headers=headers, timeout=cfg.get("timeout"))
        r.raise_for_status()
        data = r.json()
        cat_raw = data.get("category")
        cat = Category(cat_raw) if cat_raw in (c.value for c in Category) else None
        return {"category": cat, "confidence": float(data.get("confidence", 0.0)), "generated_response": data.get("generated_response", "")}
    except Exception as exc:
        raise RuntimeError(f"Gemini IA API call failed: {exc}") from exc


async def _call_external_api_async(text: str) -> Optional[Dict[str, Any]]:
    # Only Gemini async endpoint supported
    cfg = _get_gemini_config()
    if not cfg.get("url"):
        raise RuntimeError("Gemini API not configured: set GEMINI_API_URL to enable inference")
    headers = {}
    if cfg.get("key"):
        headers["Authorization"] = f"Bearer {cfg.get('key')}"
    try:
        async with httpx.AsyncClient(timeout=cfg.get("timeout")) as client:
            r = await client.post(cfg.get("url"), json={"task": "infer", "text": text}, headers=headers)
            r.raise_for_status()
            data = r.json()
            cat_raw = data.get("category")
            cat = Category(cat_raw) if cat_raw in (c.value for c in Category) else None
            return {"category": cat, "confidence": float(data.get("confidence", 0.0)), "generated_response": data.get("generated_response", "")}
    except Exception as exc:
        raise RuntimeError(f"Gemini IA API async call failed: {exc}") from exc


def infer_sync(text: str) -> Dict[str, Any]:
    """Synchronous inference entrypoint. If IA_API_URL is set, call external API; otherwise run local model."""
    # Use Gemini-only sync inference
    external = _call_external_api_sync(text)
    if external.get("category") is None:
        external["category"] = Category.IMPRODUTIVO
    return external


_INFER_EXECUTOR = ProcessPoolExecutor(max_workers=int(os.getenv("IA_ASYNC_WORKERS", "1")))


async def infer_async(text: str) -> Dict[str, Any]:
    """Async inference entrypoint. Prefer external async API when available, else run local in process pool."""
    external = await _call_external_api_async(text)
    if external.get("category") is None:
        external["category"] = Category.IMPRODUTIVO
    return external
