from fastapi import APIRouter, Depends

from app.db import get_session
from app.schemas import UserResponse
from app.crud import get_users
from app.core.security import get_current_user

router = APIRouter(prefix="/users")


@router.get("/", response_model=list[UserResponse])
async def get_users_list(session=Depends(get_session), current_user=Depends(get_current_user)):
    return await get_users(session)
