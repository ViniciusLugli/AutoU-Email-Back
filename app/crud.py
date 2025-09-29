from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select
from app.models import User, TextEntry
from app.db import engine
from sqlmodel import Session
from app.schemas import TextEntryCreateRequest
from app.models import Status

async def create_user(db: AsyncSession, user: User) -> User:
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def get_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).options(selectinload(User.texts)))
    return result.scalars().all()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()

async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()

async def create_text_entry(db: AsyncSession, text_entry_req: TextEntryCreateRequest) -> TextEntry:
    te = TextEntry(
        user_id=text_entry_req.user_id,
        original_text=text_entry_req.original_text or "",
        file_name=text_entry_req.file_name,
        category=None,
        generated_response="",
        status=Status.PROCESSING,
    )
    db.add(te)
    await db.commit()
    await db.refresh(te)
    return te


async def get_texts_by_user(db: AsyncSession, user_id: int) -> list[TextEntry]:
    result = await db.execute(select(TextEntry).where(TextEntry.user_id == user_id))
    return result.scalars().all()


def create_text_entry_sync(text_entry_req: TextEntryCreateRequest) -> TextEntry:
    """Persist TextEntry de forma síncrona (para uso em workers Celery)."""
    te = TextEntry(
        user_id=text_entry_req.user_id,
        original_text=text_entry_req.original_text or "",
        file_name=text_entry_req.file_name,
        category=None,
        generated_response="",
        status=Status.PROCESSING,
    )
    with Session(engine.sync_engine) as session:
        session.add(te)
        session.commit()
        session.refresh(te)
        return te