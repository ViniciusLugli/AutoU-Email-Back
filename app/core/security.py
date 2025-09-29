import os
import warnings
from dotenv import load_dotenv

warnings.filterwarnings(
    "ignore",
    message=".*Accessing argon2.__version__ is deprecated.*",
    category=DeprecationWarning,
)

from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

from app.db import get_session
from app.crud import get_user_by_id
from sqlalchemy.ext.asyncio import AsyncSession

warnings.filterwarnings(
    "ignore",
    message=".*Accessing argon2.__version__ is deprecated.*",
    category=DeprecationWarning,
)

load_dotenv()

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

async def get_current_user(session: AsyncSession = Depends(get_session), token: str = Depends(oauth2_scheme)):
    if not SECRET_KEY or not ALGORITHM:
        raise HTTPException(status_code=500, detail="Auth not configured properly")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        user = await get_user_by_id(session, int(user_id))
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")