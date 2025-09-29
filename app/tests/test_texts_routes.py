import pytest
from sqlmodel import select
from sqlalchemy import delete
from app.db import async_session
from app.models import User, TextEntry, Status, Category
from app.core.config import get_data_dir
from app.services.tasks import process_pipeline_task


@pytest.mark.asyncio
async def test_processar_email_and_list(async_client, create_user, get_token):
    # Create and login
    email = "texts_route@example.com"
    password = "password123"
    await create_user("tuser", email, password)
    token_resp = await get_token(email, password)
    assert token_resp.status_code == 200
    token = token_resp.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}

    # Patch apply_async to avoid Redis/Celery in tests
    class FakeAsyncResult:
        def __init__(self):
            self.id = "fake-task-id"

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(process_pipeline_task, "apply_async", lambda *args, **kwargs: FakeAsyncResult())

    # Post a text (form field 'text')
    resp = await async_client.post("/texts/processar_email", data={"text": "Este é um email de teste #123"}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "queued"
    assert "task_id" in body

    # Simulate that a TextEntry was created by the worker (since Celery runs outside tests)
    async def _create_textentry_async():
        async with async_session() as sess:
            res = await sess.execute(select(User).where(User.email == email))
            user = res.scalars().first()
            te = TextEntry(
                user_id=user.id,
                original_text="Este é um email de teste #123",
                category=Category.PRODUTIVO,
                generated_response="",
                status=Status.COMPLETED,
                file_path=str(get_data_dir()),
            )
            sess.add(te)
            await sess.commit()
            await sess.refresh(te)
            return te

    te = await _create_textentry_async()

    # Call list endpoint to ensure it returns our persisted entry
    resp = await async_client.get("/texts/", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    assert any(i["id"] == te.id for i in items)

    # Cleanup
    async def _cleanup():
        async with async_session() as sess:
            await sess.execute(delete(TextEntry).where(TextEntry.user_id == te.user_id))
            await sess.execute(delete(User).where(User.email == email))
            await sess.commit()

    await _cleanup()
    monkeypatch.undo()
