"""Shared fixtures for backend integration tests.

The env below is forced **before** any ``open_webui`` import because the DB
engine and Alembic migrations bind to ``DATABASE_URL`` at import time. Forcing
a throwaway temp SQLite DB (rather than ``setdefault``) guarantees a test run
can never touch a real database, even if one is configured in the shell.
"""

import os
import tempfile
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix='owui-test-')
_DATA_DIR = Path(_TMP) / 'data'
os.makedirs(_DATA_DIR / 'uploads', exist_ok=True)

os.environ['DATA_DIR'] = str(_DATA_DIR)
os.environ['DATABASE_URL'] = f"sqlite:///{Path(_TMP) / 'test.db'}"
os.environ.setdefault('WEBUI_SECRET_KEY', 'test-secret')
os.environ.setdefault('ENABLE_BASE_MODELS_CACHE', 'false')

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from open_webui.main import app as _app
from open_webui.models.users import UserModel, Users
from open_webui.utils.auth import get_verified_user


@pytest.fixture(scope='session')
def app():
    return _app


@pytest_asyncio.fixture
async def test_user() -> UserModel:
    """A real user row (idempotent across tests).

    The upload route only needs the auth-injected identity, but the background
    worker reloads the user from the DB by id — so it must actually exist.
    """
    existing = await Users.get_user_by_id('test-user-id')
    if existing:
        return existing
    return await Users.insert_new_user(
        id='test-user-id',
        name='Test User',
        email='test@example.com',
        role='user',
    )


@pytest_asyncio.fixture
async def async_client(test_user):
    """AsyncClient bound to the ASGI app with auth stubbed.

    ASGITransport does not run the app lifespan, so the background file
    worker never auto-starts — the processing queue stays fully under the
    test's control.
    """
    _app.dependency_overrides[get_verified_user] = lambda: test_user
    try:
        transport = ASGITransport(app=_app)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            yield client
    finally:
        _app.dependency_overrides.pop(get_verified_user, None)
