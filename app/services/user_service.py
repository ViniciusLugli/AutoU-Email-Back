import asyncio
from app.core.security import hash_password
from app.crud import create_user
from app.models import User
from app.schemas import UserCreateRequest, UserResponse
from sqlalchemy.ext.asyncio import AsyncSession

async def register_user(session: AsyncSession, data: UserCreateRequest) -> User | None:
  hash_pw = await asyncio.to_thread(hash_password, data.password)
  
  db_user = User(
      username=data.username.strip(),
      email=data.email,
      hash_password=hash_pw
  )
  user = await create_user(session, db_user)
  return UserResponse.from_orm(user)
  