from calendar import c
import enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select
from app.models import User, TextEntry
from app.db import async_session
from sqlmodel import Session
from app.schemas import TextEntryCreateRequest, UserUpdateRequest
from app.models import Status
from sqlalchemy import update as sa_update

"""
    FUNÇÕES PARA USER
"""

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

async def update_current_user(db: AsyncSession, user_update: UserUpdateRequest, current_user: User) -> User | None:
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalars().first()
    
    if not user:
        return None

    update_data = {}
    if user_update.username:
        update_data["username"] = user_update.username
        
    if user_update.email:
        update_data["email"] = user_update.email

    if user_update.current_password:
        from app.core.security import verify_password, hash_password
        from fastapi import HTTPException

        if not verify_password(user_update.current_password, user.hash_password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")

        if user_update.new_password:
            update_data["hash_password"] = hash_password(user_update.new_password)

    if not update_data:
        return user
    
    for key, value in update_data.items():
        setattr(user, key, value)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def delete_user_by_id(db: AsyncSession, user_id: int) -> bool:
    user = await get_user_by_id(db, user_id)
    if not user:
        return False
    
    texts = await get_texts_by_user(db, user_id)
    for text in texts:
        await db.delete(text)
    
    await db.delete(user)
    await db.commit()
    return True

"""
    FUNÇÕES PARA TEXTENTRY
"""

async def create_text_entry(text_entry_req: TextEntryCreateRequest) -> TextEntry:
    te = TextEntry(
        user_id=text_entry_req.user_id,
        original_text=text_entry_req.original_text or "",
        file_name=text_entry_req.file_name,
        category="Sem classificação",
        generated_response="",
        status=Status.PROCESSING.value,
    )
    async with async_session() as session:
        session.add(te)
        try:
            await session.commit()
            await session.refresh(te)
            return te
        except Exception as e:
            await session.rollback()
            raise
    
async def get_texts_by_user(db: AsyncSession, user_id: int) -> list[TextEntry]:
    result = await db.execute(select(TextEntry).where(TextEntry.user_id == user_id))
    return result.scalars().all()

async def get_text_entry(db: AsyncSession) -> list[TextEntry]:
    result = await db.execute(select(TextEntry))
    return result.scalars().all()

async def get_text_by_id(db: AsyncSession, text_entry_id: int) -> TextEntry | None:
    result = await db.execute(select(TextEntry).where(TextEntry.id == text_entry_id))
    return result.scalars().first()

async def update_text_entry(db: AsyncSession, text_entry_id: int, **kwargs) -> TextEntry | None:
    result = await db.execute(select(TextEntry).where(TextEntry.id == text_entry_id))
    text_entry = result.scalars().first()
    if not text_entry:
        return None
    for key, value in kwargs.items():
        if isinstance(value, enum.Enum):
            value = value.value
        setattr(text_entry, key, value)
    await db.add(text_entry)
    await db.commit()
    await db.refresh(text_entry)
    return text_entry

async def update_text_entry_by_id(text_entry_id: int, **kwargs) -> TextEntry | None:
    async with async_session() as session:
        result = await session.execute(select(TextEntry).where(TextEntry.id == text_entry_id))
        text_entry = result.scalars().first()
        if not text_entry:
            return None
        for key, value in kwargs.items():
            if isinstance(value, enum.Enum):
                value = value.value
            setattr(text_entry, key, value)
        session.add(text_entry)
        try:
            await session.commit()
            await session.refresh(text_entry)
            return text_entry
        except Exception:
            await session.rollback()
            raise

def create_text_entry_sync(engine_obj, text_entry_req: TextEntryCreateRequest) -> TextEntry:
    te = TextEntry(
        user_id=text_entry_req.user_id,
        original_text=text_entry_req.original_text or "",
        file_name=text_entry_req.file_name,
        category="Sem classificação",
        generated_response="",
        status=Status.PROCESSING.value,
    )
    with Session(engine_obj) as session:
        session.add(te)
        try:
            session.commit()
            session.refresh(te)
            return te
        except Exception as e:
            session.rollback()
            raise

def update_text_entry_sync(engine_obj, text_entry_id: int, **kwargs) -> TextEntry | None:
    with Session(engine_obj) as session:
        te = session.get(TextEntry, text_entry_id)
        if not te:
            return None
        for key, value in kwargs.items():
            if isinstance(value, enum.Enum):
                value = value.value
            setattr(te, key, value)
        session.add(te)
        try:
            session.commit()
            session.refresh(te)
            return te
        except Exception as e:
            session.rollback()
            raise

async def delete_text_entry_by_id(db: AsyncSession, text_entry_id: int) -> bool:
    result = await db.execute(select(TextEntry).where(TextEntry.id == text_entry_id))
    text_entry = result.scalars().first()
    if not text_entry:
        return False
    await db.delete(text_entry)
    await db.commit()
    return True