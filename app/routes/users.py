from fastapi import APIRouter, Depends, HTTPException

from app.db import get_session
from app.schemas import UserResponse, UserUpdateRequest
from app.crud import delete_user_by_id, get_user_by_id, get_users, update_current_user
from app.core.security import get_current_user

router = APIRouter(prefix="/users")


@router.get("/", response_model=list[UserResponse])
async def get_users_list(session=Depends(get_session), current_user=Depends(get_current_user)):
    return await get_users(session)

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(session=Depends(get_session), current_user=Depends(get_current_user)):
    return await get_user_by_id(session, current_user.id)

@router.put("/me", response_model=UserResponse)
async def update_current_user_info(
    user_update: UserUpdateRequest,
    session=Depends(get_session), 
    current_user=Depends(get_current_user)
    ):

    updated = await update_current_user(session, user_update, current_user)
    if updated is None:
        raise HTTPException(status_code=404, detail="User not found")
    return updated

@router.delete("/me", status_code=204)
async def delete_current_user(session=Depends(get_session), current_user=Depends(get_current_user)):
    success = await delete_user_by_id(session, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return