from fastapi import APIRouter, Depends

from app.db import get_session
from app.schemas import UserCreateRequest, UserResponse
from app.services.user_service import register_user
from app.crud import get_users

router = APIRouter(prefix="/users")

@router.get("/", response_model=list[UserResponse])
async def get_users_list(session=Depends(get_session)):
    return await get_users(session)


