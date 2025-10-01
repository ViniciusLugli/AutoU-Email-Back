from app.services.celery import celery
from app.services.read_file import read_file_sync
from app.services import nlp as nlp_service
from app.services import ia as ia_service
from app.models import Category, Status, User
from app.schemas import TextEntryCreateRequest
from app.db import async_session
from app.crud import create_text_entry, update_text_entry_by_id, get_user_by_id
from pathlib import Path
import os


async def process_pipeline_async(file_path: str = None, text: str = None, user_id: int | None = None, username: str | None = None, top_n: int = 15):

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
            created = await create_text_entry(te_req)
        except Exception:
            created = None

    try:
        nlp_res = nlp_service.preprocess_sync(content_text, top_n=top_n)
        username = None
        if user_id is not None:
            try:
                async with async_session() as s:
                    ux = await get_user_by_id(s, user_id)
                    username = getattr(ux, "username", None) if ux else None
            except Exception:
                username = None
            ia_res = await ia_service.infer_async(nlp_res["cleaned_text"], username=username)

        ia_cat = ia_res.get("category")
        category_enum = None
        if isinstance(ia_cat, Category):
            category_enum = ia_cat
        elif isinstance(ia_cat, str):
            try:
                category_enum = Category(ia_cat)
            except Exception:
                low = ia_cat.strip().lower()
                if low.startswith("prod"):
                    category_enum = Category.PRODUTIVO
                elif low.startswith("improd") or low.startswith("im"):
                    category_enum = Category.IMPRODUTIVO
                else:
                    category_enum = Category.SEM_CLASSIFICACAO
        else:
            category_enum = Category.SEM_CLASSIFICACAO

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
            "nlp": nlp_res if isinstance(nlp_res, dict) else None,
        }

        if created is not None:
            try:
                db_update_kwargs = {"generated_response": final_generated, "status": Status.COMPLETED.value}
                if category_enum != Category.SEM_CLASSIFICACAO:
                    db_update_kwargs["category"] = category_enum.value
                await update_text_entry_by_id(created.id, **db_update_kwargs)
            except Exception:
                pass
        return result
    except Exception as e:
        if created is not None:
            try:
                async with async_session() as s:
                    await update_text_entry_by_id(created.id, status=Status.FAILED.value)
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
def process_pipeline_task(self, file_path: str = None, text: str = None, user_id: int | None = None, username: str | None = None, top_n: int = 15):
    if not file_path and not text:
        raise ValueError("file_path ou text obrigatório")

    return __import__("asyncio").run(process_pipeline_async(file_path=file_path, text=text, user_id=user_id, username=username, top_n=top_n))