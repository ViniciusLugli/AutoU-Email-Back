import pytest


@pytest.mark.asyncio
async def test_register_and_login(async_client):
    user = {"username": "alice", "email": "alice@example.com", "password": "secret"}
    resp = await async_client.post("/auth/register", json=user)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == user["email"]

    # login
    resp2 = await async_client.post("/auth/login", json={"email": user["email"], "password": user["password"]})
    assert resp2.status_code == 200
    token = resp2.json()
    assert "access_token" in token
    assert token["user_id"] == data["id"]

@pytest.mark.asyncio
async def test_login_invalid(async_client):
    resp = await async_client.post("/auth/login", json={"email": "noone@example.com", "password": "x"})
    assert resp.status_code == 401
