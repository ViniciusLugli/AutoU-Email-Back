import pytest


class DummyAsyncResult:
    def __init__(self, id_="dummy-id"):
        self.id = id_


@pytest.mark.asyncio
async def test_process_text_requires_auth(async_client):
    resp = await async_client.post("/texts/processar_email", json={"text": "Olá"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_process_text_queue(async_client, get_token, monkeypatch):
    import app.routes.texts as texts_module

    class DummyTask:
        def apply_async(self, kwargs=None):
            return DummyAsyncResult("task-123")

    monkeypatch.setattr(texts_module, "process_pipeline_task", DummyTask())

    login_resp = await get_token("charlie@example.com", "pass")
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # send text
    resp = await async_client.post("/texts/processar_email", headers=headers, data={"text": "Teste"})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "queued"
    assert "task_id" in data
