import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

db_url = DATABASE_URL or context.config.get_main_option("sqlalchemy.url")

if not db_url:
    raise RuntimeError("DATABASE_URL is not set. Set the DATABASE_URL environment variable or configure sqlalchemy.url in alembic.ini")

from app.core.constants import DATABASE_URL
import app.models
from sqlmodel import SQLModel as _SQLModel
target_metadata = _SQLModel.metadata

config = context.config
fileConfig(config.config_file_name)

def run_migrations_offline():
    context.configure(url=db_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    connectable = create_async_engine(db_url, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()