from fastapi import APIRouter, Depends, HTTPException

from app.db import get_session
from app.schemas import TokenResponse, UserCreateRequest, UserLoginRequest, UserResponse
from app.services.user_service import authenticate_user, register_user

router = APIRouter(prefix="/auth")

@router.post("/register", response_model=UserResponse)
async def register(user: UserCreateRequest, session=Depends(get_session)):
    created = await register_user(session, user)
    return created
  
@router.post("/login", response_model=TokenResponse)
async def login(user: UserLoginRequest, session=Depends(get_session)):
    token_resp = await authenticate_user(session, user)
    if not token_resp:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return token_resp