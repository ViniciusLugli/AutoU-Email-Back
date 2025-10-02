import asyncio
import logging
from app.core.security import hash_password, verify_password
from app.crud import create_user, get_user_by_email
from app.models import User
from app.schemas import TokenResponse, UserCreateRequest, UserLoginRequest, UserResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth_service import create_access_token

async def register_user(session: AsyncSession, data: UserCreateRequest) -> User | None:
  hash_pw = await asyncio.to_thread(hash_password, data.password)
  logger = logging.getLogger("app.services.user_service")
  logger.info("register_user: email=%s hash_preview=%s", data.email, hash_pw[:24])
  print(f"register_user: email={data.email} password_repr={repr(data.password)} hash_preview={hash_pw[:24]}")

  db_user = User(
      username=data.username.strip(),
      email=data.email,
      hash_password=hash_pw
  )
  user = await create_user(session, db_user)
  return UserResponse(
      id=user.id,
      username=user.username,
      email=user.email,
      texts=[],
  )
  
async def authenticate_user(session: AsyncSession, data: UserLoginRequest) -> TokenResponse | None:
  logger = logging.getLogger("app.services.user_service")
  user = await get_user_by_email(session, data.email)
  if not user:
    logger.info("authenticate_user: user not found for email=%s", data.email)
    print(f"authenticate_user: user not found for email={data.email}")
    return None

  logger.info("authenticate_user: stored_hash_preview=%s", (user.hash_password or '')[:24])
  print(f"authenticate_user: checking password_repr={repr(data.password)} stored_hash_preview={(user.hash_password or '')[:24]}")
  verified = verify_password(data.password, user.hash_password)
  logger.info("authenticate_user: user_found id=%s email=%s verified=%s", getattr(user, "id", None), data.email, verified)
  print(f"authenticate_user: user_found id={getattr(user, 'id', None)} email={data.email} verified={verified}")
  if not verified:
    return None

  token = create_access_token({"sub": str(user.id), "email": user.email})
  return TokenResponse(access_token=token, user_id=user.id)