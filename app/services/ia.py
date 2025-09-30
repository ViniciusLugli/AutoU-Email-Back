import os
import asyncio
import json
import logging
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, Any, Optional
import google.genai as genai
from app.models import Category

logger = logging.getLogger("app.services.ia")

GENAI_API_KEY = os.getenv("GENAI_API_KEY")
GENAI_MODEL = os.getenv("GENAI_MODEL", "gemma-3-1b-it")

if GENAI_API_KEY:
    try:
        if hasattr(genai, "configure"):
            genai.configure(api_key=GENAI_API_KEY)
        else:
            os.environ.setdefault("GOOGLE_API_KEY", GENAI_API_KEY)
    except Exception:
        pass


def _call_external_api_sync(text: str) -> Optional[Dict[str, Any]]:

    genai_api_url = os.getenv("GENAI_API_URL")
    if genai_api_url:
        try:
            import json as _json
            from urllib.request import Request, urlopen
            payload = _json.dumps({"task": "infer", "text": text}).encode("utf-8")
            req = Request(genai_api_url, data=payload, method="POST", headers={"Content-Type": "application/json"})
            with urlopen(req, timeout=10) as resp:
                body = resp.read().decode("utf-8")
                parsed = _json.loads(body)

            cat = parsed.get("category")
            conf = parsed.get("confidence")
            gen = parsed.get("generated_response") or parsed.get("generated") or ""

            return {
                "category": cat,
                "confidence": conf,
                "generated_response": gen,
            }
        except Exception as exc:
            logger.exception("Failed to call GENAI_API_URL mock: %s", exc)
            raise RuntimeError(f"Failed to call GENAI_API_URL mock: {exc}") from exc

    if not GENAI_API_KEY and not os.getenv("GENAI_API_URL"):
        raise RuntimeError("GenAI API not configured: set GENAI_API_KEY or GENAI_API_URL for tests/mocks")
    if not hasattr(genai, "Client"):
        raise RuntimeError("google.genai client (genai.Client) is not available in this environment")

    try:
        try:
            from google.genai import types as genai_types
        except Exception:
            genai_types = None
        client = genai.Client(api_key=GENAI_API_KEY)

        if genai_types is not None:
            contents = [
                genai_types.Content(
                    role="user",
                    parts=[genai_types.Part.from_text(text=text)],
                )
            ]
            config = genai_types.GenerateContentConfig()

            if hasattr(client.models, "generate_content_stream"):
                response_text = ""
                for chunk in client.models.generate_content_stream(model=GENAI_MODEL, contents=contents, config=config):
                    chunk_text = getattr(chunk, "text", None) or getattr(chunk, "delta", None) or str(chunk)
                    response_text += str(chunk_text)
            else:
                resp = client.models.generate_content(model=GENAI_MODEL, contents=contents, config=config)
                response_text = getattr(resp, "text", str(resp))
        else:
            resp = client.models.generate_content(model=GENAI_MODEL, contents=[{"role": "user", "content": [{"type": "text", "text": text}]}])
            response_text = getattr(resp, "text", str(resp))
    except Exception as exc:
        logger.exception("genai.Client call failed: %s", exc)
        raise RuntimeError(f"genai.Client call failed: {exc}") from exc

    rt_upper = (response_text or "").upper()
    if "PRODUTIVO" in rt_upper:
        category = Category.PRODUTIVO
        confidence = 0.8
    elif "IMPRODUTIVO" in rt_upper:
        category = Category.IMPRODUTIVO
        confidence = 0.8
    else:
        category = Category.IMPRODUTIVO
        confidence = 0.5

    def _clean_sdk_artifacts(s: str) -> str:
        if not s:
            return s
        import re

        out = s
        out = re.sub(r"sdk_http_response=HttpResponse\([^\)]*\)", "", out)
        out = re.sub(r"candidates=\[.*?\]\s*", "", out, flags=re.DOTALL)
        out = re.sub(r"usage_metadata=[^\n]*", "", out)
        out = re.sub(r"parsed=[^,\n]*", "", out)
        out = re.sub(r"\n{2,}", "\n\n", out)
        return out.strip()

    cleaned = _clean_sdk_artifacts(response_text)
    lines = [l.strip() for l in (cleaned or "").split("\n") if l.strip()]
    parsed_generated = None
    if len(lines) >= 1 and lines[0].upper() in {"PRODUTIVO", "IMPRODUTIVO"}:
        parsed_cat = lines[0].upper()
        if parsed_cat == "PRODUTIVO":
            category = Category.PRODUTIVO
        else:
            category = Category.IMPRODUTIVO
        parsed_generated = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
    else:
        parsed_generated = cleaned.strip() if cleaned else ""

    return {
        "category": category,
        "confidence": confidence,
        "generated_response": parsed_generated or "",
    }


async def _call_external_api_async(text: str) -> Optional[Dict[str, Any]]:
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_INFER_EXECUTOR, _call_external_api_sync, text)
    except Exception as exc:
        raise RuntimeError(f"GenAI IA API async call failed: {exc}") from exc


def infer_sync(text: str) -> Dict[str, Any]:
    external = _call_external_api_sync(text)
    if external.get("category") is None:
        external["category"] = Category.IMPRODUTIVO
    return external


_INFER_EXECUTOR = ProcessPoolExecutor(max_workers=int(os.getenv("IA_ASYNC_WORKERS", "1")))


async def infer_async(text: str) -> Dict[str, Any]:
    external = await _call_external_api_async(text)
    if external.get("category") is None:
        external["category"] = Category.IMPRODUTIVO
    return external

