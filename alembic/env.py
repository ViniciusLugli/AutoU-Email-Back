import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import create_engine
from sqlalchemy import text
from sqlalchemy import engine_from_config
from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# importe aqui o metadata do seu projeto
from app.models import SQLModel  # para type only import; SQLModel.metadata estará disponível
from sqlmodel import SQLModel as _SQLModel
target_metadata = _SQLModel.metadata

config = context.config
fileConfig(config.config_file_name)

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations():
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online():
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()