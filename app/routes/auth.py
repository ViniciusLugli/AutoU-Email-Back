from fastapi import APIRouter, Depends

from app.db import get_session
from app.schemas import UserCreateRequest, UserResponse
from app.services.user_service import register_user

router = APIRouter(prefix="/auth")

@router.post("/register", response_model=UserResponse)
async def register(data: UserCreateRequest, session=Depends(get_session)):
    created = await register_user(session, data)
    return created
  
