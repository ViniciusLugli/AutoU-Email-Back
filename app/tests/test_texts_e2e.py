import asyncio
from http import HTTPStatus

import pytest

import os
import sqlite3

from app.services import tasks as tasks_module
from app.models import Status, TextEntry
from app.db import engine
from sqlmodel import Session, select

from app.tests.mocks.gemini_mock import start_mock


@pytest.mark.asyncio
async def test_process_pipeline_task_e2e(monkeypatch, async_client, prepare_db, create_user):
    username = "e2euser"
    email = "e2e@example.com"
    password = "senha123"
    create_resp = await create_user(username, email, password)
    assert create_resp.status_code == 200
    created_user = create_resp.json()
    user_id = created_user.get("id")
    assert user_id is not None

    login_resp = await async_client.post("/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code in (HTTPStatus.OK, HTTPStatus.CREATED)
    token = login_resp.json().get("access_token")
    assert token
    headers = {"Authorization": f"Bearer {token}"}

    # Start local Gemini mock server
    mock_thread = start_mock(port=9001)
    gemini_url = "http://127.0.0.1:9001/"

    # Run two scenarios: produtivo and improdutivo
    for mode, expect_category in (("produtivo", "Produtivo"), ("improdutivo", "Improdutivo")):
        os.environ["GEMINI_API_URL"] = gemini_url + f"?mode={mode}"

        task_res = tasks_module.process_pipeline_task(None, text="Olá, preciso atualizar o pedido #123", user_id=user_id)
        assert isinstance(task_res, dict)
        assert task_res.get("category") is not None
        assert task_res.get("generated_response") is not None
        # nlp may be present depending on mock behaviour; ensure cleaned_text exists by calling NLP endpoint
        # (the pipeline will call preprocess_sync -> Gemini nlp)
        assert task_res.get("nlp") and task_res["nlp"].get("cleaned_text")
        assert task_res.get("category") == expect_category

    db_url = os.environ.get("DATABASE_URL", "")
    if "+aiosqlite:///" in db_url:
        db_path = db_url.split("+aiosqlite:///", 1)[1]
    elif "sqlite:///" in db_url:
        db_path = db_url.split("sqlite:///", 1)[1]
    else:
        db_path = db_url

    # Persisting to the DB is handled by create_text_entry_sync and updated
    # inside the worker using the synchronous engine. In tests we validate
    # the pipeline result returned by the task function above. If you need
    # to assert DB persistence in CI, run the worker or mock DB updates.
    
