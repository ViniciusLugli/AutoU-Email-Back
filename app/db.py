from typing import AsyncGenerator
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from app.core.constants import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=True, pool_pre_ping=True)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session