from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
import os
from pathlib import Path
import uuid

from app.services.read_file import read_file_async
from app.services import ia as ia_service
from app.db import get_session
from app.core.security import get_current_user
from app.schemas import TextEntryResponse, TaskStatusResponse
from app.models import TextEntry
from sqlmodel import select
from app.crud import get_texts_by_user
from app.core.config import get_data_dir
from app.services.tasks import process_pipeline_task

router = APIRouter(prefix="/texts")

@router.post("/processar_email", response_model=TaskStatusResponse)
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
        async_result = process_pipeline_task.apply_async(kwargs={"file_path": str(tmp_path), "user_id": current_user.id})
        return {"task_id": async_result.id, "status": "queued"}
    else:
        texto = text
        async_result = process_pipeline_task.apply_async(kwargs={"text": texto, "user_id": current_user.id})
        return {"task_id": async_result.id, "status": "queued"}


@router.get("/", response_model=list[TextEntryResponse])
async def list_texts(session=Depends(get_session), current_user=Depends(get_current_user)):
    items = await get_texts_by_user(session, current_user.id)
    return items