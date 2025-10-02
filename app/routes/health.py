
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session

router = APIRouter(prefix="/health")

@router.get("/db")
async def health_db(session: AsyncSession = Depends(get_session)):
  result = await session.execute(text("SELECT 1"))
  value = result.scalar_one_or_none()
  return {"db": bool(value == 1)}

@router.get("/ping")
async def health_ping():
  return {"ping": "pong!"}

@router.get("/")
async def health_check():
  return {"status": "ok"}