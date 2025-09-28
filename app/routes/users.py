import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from app.db import get_session
from app.schemas import UserResponse
from app.crud import get_users
from jose import jwt, JWTError

router = APIRouter(prefix="/users")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

@router.get("/", response_model=list[UserResponse])
async def get_users_list(session=Depends(get_session), token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return await get_users(session)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
