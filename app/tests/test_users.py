import pytest


@pytest.mark.asyncio
async def test_get_users_requires_auth(async_client):
    resp = await async_client.get("/users/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_users_list(async_client, get_token):
    login_resp = await get_token("bob@example.com", "mypassword")
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    resp = await async_client.get("/users/", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
