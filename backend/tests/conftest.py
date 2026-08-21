"""Shared test fixtures for backend custom-role tests.

Uses a temp-file SQLite database so tests are fast, isolated, and
require no external services.  The module-level bootstrap must happen
BEFORE any open_webui import so the env var overrides take effect when
db.py reads them at import time.

Test isolation is ensured by wrapping each test session in a nested
transaction (savepoint).  When code under test calls ``session.commit()``,
only the savepoint is committed, not the outer transaction.  After each
test the outer transaction is rolled back, undoing all changes.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile

# ---------------------------------------------------------------------------
# Environment bootstrap — MUST happen before any open_webui import.
# ---------------------------------------------------------------------------

os.environ['ENABLE_DB_MIGRATIONS'] = 'false'
os.environ['DATABASE_SCHEMA'] = ''
os.environ['REDIS_URL'] = ''
os.environ['OFFLINE_MODE'] = 'true'
os.environ['WEBUI_AUTH'] = 'true'
os.environ['ENABLE_PASSWORD_VALIDATION'] = 'false'
os.environ['ENV'] = 'test'
os.environ['ENABLE_OTEL'] = ''
os.environ['ENABLE_PLUGINS'] = 'false'
os.environ['WEBUI_SECRET_KEY'] = 'test-secret-key-for-unit-tests-only-1234'
os.environ['DATABASE_POOL_SIZE'] = ''
os.environ['DATABASE_POOL_MAX_OVERFLOW'] = '0'
os.environ['DATABASE_POOL_TIMEOUT'] = '30'
os.environ['DATABASE_POOL_RECYCLE'] = '0'
os.environ['DATABASE_SQLITE_PRAGMA_BUSY_TIMEOUT'] = ''
os.environ['DATABASE_SQLITE_PRAGMA_CACHE_SIZE'] = ''
os.environ['DATABASE_SQLITE_PRAGMA_JOURNAL_SIZE_LIMIT'] = ''
os.environ['DATABASE_SQLITE_PRAGMA_MMAP_SIZE'] = ''
os.environ['DATABASE_SQLITE_PRAGMA_SYNCHRONOUS'] = ''
os.environ['DATABASE_SQLITE_PRAGMA_TEMP_STORE'] = ''
os.environ['DATABASE_ENABLE_SESSION_SHARING'] = 'true'

# Create a temp file for SQLite so pool_size works (in-memory is incompatible)
_tmp_db_fd, _tmp_db_path = tempfile.mkstemp(suffix='.db', prefix='owui_test_')
os.close(_tmp_db_fd)
os.environ['DATABASE_URL'] = f'sqlite+aiosqlite:///{_tmp_db_path}'

# Ensure the backend package is importable
_backend_dir = os.path.join(os.path.dirname(__file__), '..')
if _backend_dir not in sys.path:
    sys.path.insert(0, os.path.abspath(_backend_dir))

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Database engine & session
# ---------------------------------------------------------------------------

@pytest.fixture(scope='session')
def event_loop():
    """Use a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope='session')
async def _engine():
    """Create an async SQLite engine and create all tables."""
    from open_webui.internal.db import Base
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(os.environ['DATABASE_URL'], echo=False)

    # Enable SQLite FK enforcement for the test engine (mirrors db.py's
    # _apply_sqlite_pragmas which only runs on the production engine).
    from sqlalchemy import event as sa_event

    def _on_connect(dbapi_conn, _rec):
        cursor = dbapi_conn.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()

    sa_event.listen(engine.sync_engine, 'connect', _on_connect)

    # Import all models so their tables are registered on Base.metadata
    from open_webui.models.access_grants import AccessGrant  # noqa: F401
    from open_webui.models.auths import Auth  # noqa: F401
    from open_webui.models.config import Config  # noqa: F401
    from open_webui.models.custom_roles import CustomRole  # noqa: F401
    from open_webui.models.groups import (  # noqa: F401
        Group,
        GroupMember,
        GroupOwnedAsset,  # noqa: F401
    )
    from open_webui.models.knowledge import Knowledge, KnowledgeDirectory  # noqa: F401
    from open_webui.models.prompts import Prompt  # noqa: F401
    from open_webui.models.skills import Skill  # noqa: F401
    from open_webui.models.tools import Tool  # noqa: F401
    from open_webui.models.users import ApiKey, User  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db(_engine):
    """Provide an isolated transactional session.

    Uses a nested transaction (savepoint) so that ``session.commit()`` calls
    inside the code under test only commit the savepoint, not the outer
    transaction.  After the test, the outer transaction is rolled back,
    ensuring complete isolation between tests.
    """
    from sqlalchemy.ext.asyncio import AsyncSession

    connection = await _engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)

    # Begin a nested transaction (savepoint).  When the code under test
    # calls session.commit(), SQLAlchemy will commit only the savepoint
    # and automatically begin a new one, keeping the outer transaction alive.
    _ = await session.begin_nested()

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture
async def fresh_session(_engine):
    """Provide a fresh session NOT in any transaction.

    This is used for tests that need to exercise ``group_manager_tx`` on
    a truly fresh session (which ``group_manager_tx`` requires — it
    rejects sessions already in a transaction).
    """
    from sqlalchemy.ext.asyncio import AsyncSession

    session = AsyncSession(bind=_engine, expire_on_commit=False)

    yield session

    await session.close()


@pytest_asyncio.fixture
async def manager_db(_engine):
    """Provide a fresh session for group-manager transaction tests.

    Unlike the ``db`` fixture (savepoint-based), this session starts
    outside any transaction so ``group_manager_tx`` can issue BEGIN
    IMMEDIATE as its first statement.  Setup helpers detect the
    ``manager_setup`` marker in ``session.info`` and auto-commit after
    flush so data is visible to subsequent transactions.

    All committed rows are cleaned up after each test.
    """
    from open_webui.models.access_grants import AccessGrant
    from open_webui.models.custom_roles import CustomRole
    from open_webui.models.groups import Group, GroupMember, GroupOwnedAsset
    from open_webui.models.skills import Skill
    from open_webui.models.tools import Tool
    from open_webui.models.users import User
    from sqlalchemy import delete as sa_delete
    from sqlalchemy.ext.asyncio import AsyncSession

    session = AsyncSession(bind=_engine, expire_on_commit=False)
    session.info['manager_setup'] = True

    yield session

    await session.close()

    # Clean committed rows in FK-safe order (child → parent).
    conn = await _engine.connect()
    try:
        await conn.execute(sa_delete(AccessGrant))
        await conn.execute(sa_delete(GroupOwnedAsset))
        await conn.execute(sa_delete(Skill))
        await conn.execute(sa_delete(Tool))
        await conn.execute(sa_delete(GroupMember))
        await conn.execute(sa_delete(Group))
        await conn.execute(sa_delete(CustomRole))
        await conn.execute(sa_delete(User))
        await conn.commit()
    finally:
        await conn.close()
