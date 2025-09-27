from typing import AsyncGenerator
from sqlmodel import SQLModel, Session
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)


DATABASE_URL = "postgresql+asyncpg://postgres:root@localhost/postgres"

engine = create_async_engine(DATABASE_URL, echo=True, pool_pre_ping=True)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session