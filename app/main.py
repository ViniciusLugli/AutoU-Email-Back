from contextlib import asynccontextmanager
from sqlalchemy import text
from fastapi import FastAPI

from app.db import init_db
from app.routes import health, users

@asynccontextmanager
async def lifespan(app: FastAPI):
  await init_db()
  yield

app = FastAPI(lifespan=lifespan)

app.include_router(users.router)
app.include_router(health.router)