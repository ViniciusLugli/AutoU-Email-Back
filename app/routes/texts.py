from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
import os
from pathlib import Path
import uuid
import logging

from app.db import get_session
from app.core.security import get_current_user
from app.schemas import TextEntryResponse
from sqlmodel import select
from app.crud import get_texts_by_user
from app.core.config import get_data_dir, settings
from app.services.tasks import process_pipeline_task, process_pipeline_sync

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/texts")

@router.post("/processar_email")
async def processar_email(file: UploadFile | None = File(None), text: str | None = Form(None), session=Depends(get_session), current_user=Depends(get_current_user)):
    if file is None and not text:
        raise HTTPException(status_code=400, detail="Enviar 'text' ou 'file'")

    if file:
        data_dir: Path = get_data_dir()
        suffix = os.path.splitext(file.filename or "")[1] or ""
        unique_name = f"upload-{uuid.uuid4().hex}{suffix}"
        tmp_path = data_dir / unique_name
        content = await file.read()
        tmp_path.write_bytes(content)
        process_kwargs = {"file_path": str(tmp_path), "user_id": current_user.id}
    else:
        process_kwargs = {"text": text, "user_id": current_user.id}
    
    logger.info("processar_email called: file=%s text_len=%s user_id=%s", bool(file), len(text) if text else 0, getattr(current_user, 'id', None))
    try:
        task_obj = process_pipeline_task
        try:
            # only import/override if the current task_obj doesn't support apply_async
            from app.services import tasks as tasks_mod
            if not (hasattr(task_obj, "apply_async") and callable(getattr(task_obj, "apply_async"))):
                task_obj = getattr(tasks_mod, "process_pipeline_task", task_obj)
        except Exception:
            pass

        if hasattr(task_obj, "apply_async") and callable(getattr(task_obj, "apply_async")):
            async_result = task_obj.apply_async(kwargs=process_kwargs)
            return {"task_id": getattr(async_result, "id", None), "status": "queued"}
    except Exception as e:
        logger.warning("Background task enqueue failed, falling back to synchronous processing: %s", e)
    
    try:
        logger.info("Falling back to synchronous processing")
        result = process_pipeline_sync(**process_kwargs)
        task_id = result.get("id") or "sync"
        if task_id != "sync":
            items = await get_texts_by_user(session, current_user.id)
            entry = next((i for i in items if i.id == result.get("id")), None)
            if entry:
                return entry
        return {"task_id": task_id, "status": "completed", "result": {"id": result.get("id"), "category": result.get("category"), "generated_response": result.get("generated_response")}}
    except Exception as e:
        logger.error(f"Erro no processamento: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar: {str(e)}")


@router.get("/", response_model=list[TextEntryResponse])
async def list_texts(session=Depends(get_session), current_user=Depends(get_current_user)):
    items = await get_texts_by_user(session, current_user.id)
    return items