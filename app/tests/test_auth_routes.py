import pytest
from sqlmodel import select
from sqlalchemy import delete

from app.db import async_session
from app.models import User


@pytest.mark.asyncio
async def test_register_and_login(async_client):
    email = "route_test@example.com"
    username = "route_test_user"
    password = "strongpassword"

    async def _cleanup():
        async with async_session() as sess:
            res = await sess.execute(select(User).where(User.email == email))
            user = res.scalars().first()
            if user:
                await sess.execute(delete(User).where(User.email == email))
                await sess.commit()

    await _cleanup()

    try:
        # Register
        resp = await async_client.post("/auth/register", json={
            "username": username,
            "email": email,
            "password": password,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == email
        assert body["username"] == username

        # Login
        resp = await async_client.post("/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200
        token_body = resp.json()
        assert "access_token" in token_body
        assert "user_id" in token_body

        # Wrong password
        resp = await async_client.post("/auth/login", json={"email": email, "password": "wrong"})
        assert resp.status_code == 401
    finally:
        await _cleanup()
