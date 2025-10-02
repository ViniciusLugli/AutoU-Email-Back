from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form, Request
import os
from pathlib import Path
import uuid

from app.db import get_session
from app.core.security import get_current_user
from app.schemas import TextEntryResponse
from app.crud import get_texts_by_user, get_text_by_id, delete_text_entry_by_id
from app.core.config import get_data_dir, settings
from app.services.tasks import process_pipeline_task


router = APIRouter(prefix="/texts")

@router.post("/processar_email")
async def processar_email(request: Request, file: UploadFile | None = File(None), text: str | None = Form(None), session=Depends(get_session), current_user=Depends(get_current_user)):
    try:
        content_type = request.headers.get("content-type")
    except Exception:
        pass
    try:
        if file is None and not text:
            raise HTTPException(status_code=400, detail="Enviar 'text' ou 'file'")
    except Exception:
        raise

    if file:
        data_dir: Path = get_data_dir()
        suffix = os.path.splitext(file.filename or "")[1] or ""
        unique_name = f"upload-{uuid.uuid4().hex}{suffix}"
        tmp_path = data_dir / unique_name
        content = await file.read()
        tmp_path.write_bytes(content)
        process_kwargs = {"file_path": str(tmp_path), "user_id": current_user.id, "username": getattr(current_user, 'username', None)}
    else:
        process_kwargs = {"text": text, "user_id": current_user.id, "username": getattr(current_user, 'username', None)}

    try:
        task_obj = process_pipeline_task
        async_result = task_obj.apply_async(kwargs=process_kwargs)
        return {"task_id": getattr(async_result, "id", None), "status": "queued"}
    except Exception:
        raise HTTPException(status_code=503, detail="Serviço de processamento indisponível; tente novamente mais tarde")


@router.get("/", response_model=list[TextEntryResponse])
async def list_texts(session=Depends(get_session), current_user=Depends(get_current_user)):
    items = await get_texts_by_user(session, current_user.id)
    return items

@router.delete("/{text_id}", status_code=204)
async def delete_text(text_id: int, session=Depends(get_session), current_user=Depends(get_current_user)):

    text_entry = await get_text_by_id(session, text_id)
    if not text_entry or text_entry.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Text entry not found")

    await delete_text_entry_by_id(session, text_id)
    return