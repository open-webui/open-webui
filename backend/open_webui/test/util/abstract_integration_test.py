"""
Base class for FastAPI router tests against a disposable SQLite DB.

Despite the historical name, CI/local runs use isolated SQLite (see ``test/conftest.py``),
not PostgreSQL.

Uses a **minimal** ASGI app (auths / users / models / chats only) so pytest does not
import ``open_webui.main`` (which pulls optional heavy stacks like langchain/sklearn).
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from urllib.parse import urlencode

from fastapi import FastAPI
from starlette.requests import Request

# Before ``open_webui.config`` loads: skip optional ``chromadb`` import.
os.environ.setdefault('VECTOR_DB', 'test')

import open_webui.config as cfg  # noqa: E402
from open_webui.config import PersistentConfig  # noqa: E402
from open_webui.internal.db import Base, ScopedSession, engine  # noqa: E402
from open_webui.routers import auths, chats, models, users  # noqa: E402
from open_webui.utils.auth import get_http_authorization_cred  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

from .mock_user import get_optional_mock_headers


def _create_minimal_router_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.startup_complete = True
        yield

    application = FastAPI(lifespan=lifespan)
    application.state.startup_complete = True
    application.state.WEBUI_NAME = cfg.WEBUI_NAME
    application.state.redis = None
    application.state.config = cfg.AppConfig(
        redis_url=None,
        redis_sentinels=[],
        redis_cluster=False,
        redis_key_prefix=cfg.REDIS_KEY_PREFIX,
    )

    for name in dir(cfg):
        if name.startswith('_') or name in ('AppConfig', 'PersistentConfig', 'Field', 'BaseModel'):
            continue
        try:
            val = getattr(cfg, name)
        except Exception:
            continue
        if isinstance(val, PersistentConfig):
            setattr(application.state.config, name, val)

    class _OAuthStub:
        def get_server_metadata_url(self, *a, **k):
            return ''

        def get_client(self, *a, **k):
            return None

    application.state.oauth_manager = _OAuthStub()
    application.state.oauth_client_manager = _OAuthStub()

    @application.middleware('http')
    async def commit_session_after_request(request: Request, call_next):
        response = await call_next(request)
        try:
            ScopedSession.commit()
        finally:
            ScopedSession.remove()
        return response

    @application.middleware('http')
    async def check_url(request: Request, call_next):
        request.state.token = get_http_authorization_cred(request.headers.get('Authorization'))
        if request.state.token is None and request.cookies.get('token'):
            from fastapi.security import HTTPAuthorizationCredentials

            request.state.token = HTTPAuthorizationCredentials(
                scheme='Bearer', credentials=request.cookies.get('token')
            )
        request.state.enable_api_keys = application.state.config.ENABLE_API_KEYS
        return await call_next(request)

    application.include_router(auths.router, prefix='/api/v1/auths', tags=['auths'])
    application.include_router(users.router, prefix='/api/v1/users', tags=['users'])
    application.include_router(models.router, prefix='/api/v1/models', tags=['models'])
    application.include_router(chats.router, prefix='/api/v1/chats', tags=['chats'])

    return application


def _clear_all_tables():
    from sqlalchemy import text

    url = str(engine.url)
    if 'sqlite' in url:
        with engine.begin() as conn:
            conn.execute(text('PRAGMA foreign_keys = OFF'))
            rows = conn.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
            ).fetchall()
            for (tbl,) in rows:
                if tbl == 'alembic_version':
                    continue
                conn.execute(text(f'DELETE FROM "{tbl}"'))
            conn.execute(text('PRAGMA foreign_keys = ON'))
    else:
        with engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(table.delete())


class _AuthInjectingClient:
    __slots__ = ('_c',)

    def __init__(self, client: TestClient):
        self._c = client

    def _merge_headers(self, kwargs: dict) -> dict:
        ctx = get_optional_mock_headers()
        if not ctx:
            return kwargs
        out = dict(kwargs)
        h = dict(out.get('headers') or {})
        h.update(ctx)
        out['headers'] = h
        return out

    def get(self, *a, **k):
        return self._c.get(*a, **self._merge_headers(k))

    def post(self, *a, **k):
        return self._c.post(*a, **self._merge_headers(k))

    def put(self, *a, **k):
        return self._c.put(*a, **self._merge_headers(k))

    def patch(self, *a, **k):
        return self._c.patch(*a, **self._merge_headers(k))

    def delete(self, *a, **k):
        return self._c.delete(*a, **self._merge_headers(k))


class AbstractPostgresTest:
    BASE_PATH = ''

    _test_client_cm = None
    fast_api_client: _AuthInjectingClient

    @classmethod
    def setup_class(cls):
        cls._app = _create_minimal_router_app()
        cls._test_client_cm = TestClient(cls._app)
        cls._raw_client = cls._test_client_cm.__enter__()
        cls.fast_api_client = _AuthInjectingClient(cls._raw_client)

    @classmethod
    def teardown_class(cls):
        if cls._test_client_cm is not None:
            cls._test_client_cm.__exit__(None, None, None)
            cls._test_client_cm = None

    def setup_method(self):
        _clear_all_tables()

    def create_url(self, path: str = '', query_params: dict | None = None) -> str:
        base = self.BASE_PATH.rstrip('/')
        if path:
            suffix = path if path.startswith('/') else f'/{path}'
            url = f'{base}{suffix}'
        else:
            url = base
        if query_params:
            url = f'{url}?{urlencode(query_params)}'
        return url
