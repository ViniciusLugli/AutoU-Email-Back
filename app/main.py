from contextlib import asynccontextmanager
from sqlalchemy import text
from fastapi import FastAPI

from app.db import init_db
from app.routes import auth, health, texts, users

@asynccontextmanager
async def lifespan(app: FastAPI):
  await init_db()
  yield

app = FastAPI(lifespan=lifespan)

app.include_router(users.router)
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(texts.router)