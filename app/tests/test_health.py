import pytest


@pytest.mark.asyncio
async def test_health_db(async_client):
    resp = await async_client.get("/health/db")
    assert resp.status_code == 200
    data = resp.json()
    assert "db" in data
    assert isinstance(data["db"], bool)
