import os
import warnings
import sys
from pathlib import Path
import asyncio
import tempfile

import pytest
import pytest_asyncio

import httpx
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

_tmp_db = tempfile.NamedTemporaryFile(prefix="test_db_", suffix=".sqlite", delete=False)
_tmp_db_path = _tmp_db.name
_tmp_db.close()
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_tmp_db_path}")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")

warnings.filterwarnings(
    "ignore",
    message=".*Accessing argon2.__version__ is deprecated.*",
    category=DeprecationWarning,
)

from app.main import app
from app.db import init_db
import os

try:
    from app.services.celery import celery as _celery_app

    os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "1")
    os.environ.setdefault("CELERY_TASK_EAGER_PROPAGATES", "1")

    _celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)
except Exception:
    pass


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def async_client():
    # Use in-process ASGI transport so exceptions are visible in pytest output
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture(scope="session", autouse=False)
async def live_server(prepare_db):
    """Optional fixture to start a real Uvicorn server in a subprocess.

    Disabled by default; tests use in-process ASGI client which is faster and
    surfaces exceptions during testing.
    """
    import subprocess
    import sys
    import time
    import os

    env = os.environ.copy()
    proc = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"
    ], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Wait for server to become responsive
    for _ in range(60):
        try:
            r = httpx.get("http://127.0.0.1:8000/health/db", timeout=1.0)
            if r.status_code < 500:
                break
        except Exception:
            pass
        time.sleep(0.2)
    else:
        proc.terminate()
        raise RuntimeError("Uvicorn server failed to start for tests")

    yield

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_db():
    import importlib
    importlib.import_module("app.models")
    await init_db()
    yield


@pytest.fixture(scope="session", autouse=True)
def _cleanup_db_file():
    yield
    try:
        os.remove(_tmp_db_path)
    except OSError:
        pass


@pytest_asyncio.fixture
async def create_user(async_client):
    async def _create(username: str, email: str, password: str):
        resp = await async_client.post("/auth/register", json={
            "username": username,
            "email": email,
            "password": password,
        })
        return resp

    return _create


@pytest_asyncio.fixture
async def get_token(async_client, create_user):
    async def _get(email: str, password: str):
        await create_user("testuser", email, password)
        resp = await async_client.post("/auth/login", json={"email": email, "password": password})
        return resp

    return _get
