import os
from typing import AsyncGenerator
from sqlmodel import SQLModel, create_engine
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from app.core.constants import DATABASE_URL

DATABASE_URL_SYNC = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://") if DATABASE_URL else None

engine = create_async_engine(DATABASE_URL, echo=True, pool_pre_ping=True)

sync_engine = create_engine(DATABASE_URL_SYNC, echo=True, pool_pre_ping=True) if DATABASE_URL_SYNC else None

engine.sync_engine = sync_engine

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session