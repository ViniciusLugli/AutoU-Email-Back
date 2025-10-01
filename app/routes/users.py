from fastapi import APIRouter, Depends, HTTPException

from app.db import get_session
from app.schemas import UserResponse
from app.crud import delete_user_by_id, get_user_by_id, get_users
from app.core.security import get_current_user, hash_password

router = APIRouter(prefix="/users")


@router.get("/", response_model=list[UserResponse])
async def get_users_list(session=Depends(get_session), current_user=Depends(get_current_user)):
    return await get_users(session)

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user=Depends(get_current_user)):
    return await get_user_by_id(current_user.id)

@router.put("/me", response_model=UserResponse)
async def update_current_user_info(username: str | None = None, email: str | None = None, password: str | None = None, session=Depends(get_session), current_user=Depends(get_current_user)):
    update_data = {}
    if username:
        update_data["username"] = username
    if email:
        update_data["email"] = email
    if password:
        update_data["hashed_password"] = hash_password(password)
    if not update_data:
        return current_user
    updated_user = await get_user_by_id(session, current_user.id)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    for key, value in update_data.items():
        setattr(updated_user, key, value)
    session.add(updated_user)
    await session.commit()
    await session.refresh(updated_user)
    return updated_user

@router.delete("/me", status_code=204)
async def delete_current_user(session=Depends(get_session), current_user=Depends(get_current_user)):
    success = await delete_user_by_id(session, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return