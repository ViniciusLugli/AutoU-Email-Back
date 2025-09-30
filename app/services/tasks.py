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


def process_pipeline_sync(file_path: str = None, text: str = None, user_id: int | None = None, top_n: int = 15):
    import logging
    logger = logging.getLogger("app.services.tasks")
    logger.info("process_pipeline_sync entry: file=%s text_len=%s user_id=%s", bool(file_path), len(text) if text else 0, user_id)

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

        ia_cat = ia_res.get("category")
        if isinstance(ia_cat, Category):
            category_enum = ia_cat
        elif isinstance(ia_cat, str):
            low = ia_cat.strip().lower()
            if low.startswith("prod"):
                category_enum = Category.PRODUTIVO
            elif low.startswith("improd") or low.startswith("im"):
                category_enum = Category.IMPRODUTIVO
            else:
                try:
                    category_enum = Category(ia_cat)
                except Exception:
                    category_enum = Category.IMPRODUTIVO
        else:
            category_enum = Category.IMPRODUTIVO

        final_generated = ia_res.get("generated_response") or ia_res.get("raw_response_clean") or ia_res.get("raw_response") or ""

        result = {
            "id": created.id if created else None,
            "user_id": user_id,
            "original_text": content_text,
            "category": category_enum.value,
            "generated_response": final_generated,
            "status": Status.COMPLETED.value,
            "file_name": os.path.basename(file_path) if file_path else None,
            "created_at": None,
        }

        if created is not None:
            try:
                with Session(engine.sync_engine) as session:
                    db_te = session.get(TextEntry, created.id)
                    if db_te:
                        db_te.category = category_enum
                        db_te.generated_response = final_generated
                        db_te.status = Status.COMPLETED
                        session.add(db_te)
                        session.commit()
            except Exception:
                pass
        return result
    
    except Exception as e:
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
        try:
            if file_path and Path(file_path).exists():
                Path(file_path).unlink()
        except Exception:
            pass


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

        ia_cat = ia_res.get("category")
        if isinstance(ia_cat, Category):
            category_enum = ia_cat
        elif isinstance(ia_cat, str):
            low = ia_cat.strip().lower()
            if low.startswith("prod"):
                category_enum = Category.PRODUTIVO
            elif low.startswith("improd") or low.startswith("im"):
                category_enum = Category.IMPRODUTIVO
            else:
                try:
                    category_enum = Category(ia_cat)
                except Exception:
                    category_enum = Category.IMPRODUTIVO
        else:
            category_enum = Category.IMPRODUTIVO

        final_generated = ia_res.get("generated_response") or ia_res.get("raw_response_clean") or ia_res.get("raw_response") or ""

        result = {
            "category": category_enum.value,
            "confidence": ia_res.get("confidence"),
            "generated_response": final_generated,
            "nlp": nlp_res,
        }

        if created is not None:
            try:
                with Session(engine.sync_engine) as session:
                    db_te = session.get(TextEntry, created.id)
                    if db_te:
                        db_te.category = category_enum
                        db_te.generated_response = final_generated
                        db_te.status = Status.COMPLETED
                        session.add(db_te)
                        session.commit()
            except Exception:
                pass

        return result
    except Exception as e:
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
        try:
            if file_path and Path(file_path).exists():
                Path(file_path).unlink()
        except Exception:
            pass