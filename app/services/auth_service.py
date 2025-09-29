from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from jose import jwt
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")

def _get_access_token_expire_minutes() -> int:
    try:
        return int(ACCESS_TOKEN_EXPIRE_MINUTES) if ACCESS_TOKEN_EXPIRE_MINUTES is not None else 30
    except ValueError:
        return 30

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy() if data else {}
    minutes = _get_access_token_expire_minutes()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=minutes))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt