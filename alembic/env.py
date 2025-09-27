import asyncio
from logging.config import fileConfig
from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.engine import create_engine
from sqlalchemy import text
from sqlalchemy import engine_from_config
from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

# Prefer DATABASE_URL env var; fall back to alembic.ini sqlalchemy.url if not set
db_url = os.getenv("DATABASE_URL") or context.config.get_main_option("sqlalchemy.url")

if not db_url:
    raise RuntimeError("DATABASE_URL is not set. Set the DATABASE_URL environment variable or configure sqlalchemy.url in alembic.ini")

# import app models so SQLModel metadata is registered for autogenerate
import app.models  # noqa: F401
from sqlmodel import SQLModel as _SQLModel
target_metadata = _SQLModel.metadata

config = context.config
fileConfig(config.config_file_name)

def run_migrations_offline():
    # In offline mode, use the URL directly
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
    # Run the async migration helper
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()