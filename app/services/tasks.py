from app.services.celery import celery
from app.services.read_file import read_file_sync
from app.services import nlp as nlp_service
from app.services import ia as ia_service
from app.models import Category, Status, TextEntry
from app.schemas import TextEntryCreateRequest
from app.db import engine
from sqlmodel import Session
from app.crud import create_text_entry_sync
from pathlib import Path
import os


@celery.task(bind=True, name="process_pipeline_task")
def process_pipeline_task(self, file_path: str = None, text: str = None, user_id: int | None = None, top_n: int = 15):
    if not file_path and not text:
        raise ValueError("file_path ou text obrigatório")

    content_text = read_file_sync(file_path) if file_path else text

    created = None
    if user_id is not None:
        try:
            te_req = TextEntryCreateRequest(
                user_id=user_id,
                original_text=content_text,
                file_name=os.path.basename(file_path) if file_path else None,
            )
            created = create_text_entry_sync(te_req)
        except Exception:
            created = None

    try:
        nlp_res = nlp_service.preprocess_sync(content_text, top_n=top_n)
        ia_res = ia_service.infer_sync(nlp_res["cleaned_text"])

        category_value = ia_res["category"].value if isinstance(ia_res["category"], Category) else ia_res["category"]

        result = {
            "category": category_value,
            "confidence": ia_res.get("confidence"),
            "generated_response": ia_res.get("generated_response"),
            "nlp": nlp_res,
        }

        if created is not None:
            try:
                with Session(engine.sync_engine) as session:
                    db_te = session.get(TextEntry, created.id)
                    if db_te:
                        db_te.category = category_value
                        db_te.generated_response = ia_res.get("generated_response")
                        db_te.status = Status.COMPLETED
                        session.add(db_te)
                        session.commit()
            except Exception:
                # swallow DB update errors
                pass

        return result
    except Exception as e:
        # mark as FAILED if we have a created record
        if created is not None:
            try:
                with Session(engine.sync_engine) as session:
                    db_te = session.get(TextEntry, created.id)
                    if db_te:
                        db_te.status = Status.FAILED
                        session.add(db_te)
                        session.commit()
            except Exception:
                pass
        raise e
    finally:
        # best effort: delete file
        try:
            if file_path and Path(file_path).exists():
                Path(file_path).unlink()
        except Exception:
            pass