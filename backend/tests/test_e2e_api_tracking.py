"""
End-to-end tests for API usage tracking via ChatMessage with source='api'.

Tests ORM model methods directly against an in-memory SQLite database with
get_async_db_context patched to avoid the real DB connection.

Covers:
  - upsert_message with chat_id=None stores source='api', chat_id=NULL
  - Chat analytics methods exclude source='api' rows  (source IS NULL filter)
  - API analytics methods include only source='api' rows
  - Token aggregation correctness for both chat and API paths
  - Date range filtering for API rows
  - Daily/hourly count methods isolation

Run with:  pytest backend/tests/test_e2e_api_tracking.py -v
"""

import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ── env setup must happen before open_webui imports ──────────────────────────
import os
os.environ.setdefault('WEBUI_SECRET_KEY', 'test-secret-key-for-unit-tests')
# DATABASE_URL intentionally not overridden: the default file-based SQLite URL
# is compatible with the pool_size args in internal/db.py.  The global engine
# is irrelevant because every test patches get_async_db_context to use an
# isolated in-memory engine instead.
# ─────────────────────────────────────────────────────────────────────────────

from open_webui.models.chat_messages import Base, ChatMessage, ChatMessages  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine('sqlite+aiosqlite:///:memory:', echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_patch(session_factory):
    """
    Patch get_async_db_context in chat_messages so all ORM calls
    use the test in-memory engine instead of the real one.
    """
    @asynccontextmanager
    async def _ctx(db: Optional[AsyncSession] = None):
        async with session_factory() as s:
            yield s

    with patch('open_webui.models.chat_messages.get_async_db_context', _ctx):
        yield


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _now():
    return int(time.time())


def _usage(inp=100, out=50):
    return {'input_tokens': inp, 'output_tokens': out, 'total_tokens': inp + out}


async def _insert_chat(model_id='claude-3', user_id='u1', chat_id=None, usage=None):
    """Insert a regular chat message (source=NULL)."""
    chat_id = chat_id or str(uuid.uuid4())
    return await ChatMessages.upsert_message(
        message_id=str(uuid.uuid4()),
        chat_id=chat_id,
        user_id=user_id,
        data={
            'role': 'assistant',
            'model_id': model_id,
            'usage': usage or _usage(),
            'done': True,
        },
    )


async def _insert_api(model_id='gpt-4o', user_id='u1', usage=None, created_at=None):
    """Insert a direct API call row (source='api', chat_id=NULL)."""
    msg = await ChatMessages.upsert_message(
        message_id=str(uuid.uuid4()),
        chat_id=None,
        user_id=user_id,
        data={
            'role': 'assistant',
            'model_id': model_id,
            'usage': usage or _usage(),
            'source': 'api',
            'done': True,
        },
    )
    return msg


# ─────────────────────────────────────────────────────────────────────────────
# 1. upsert_message behaviour
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upsert_api_row_has_null_chat_id_and_api_source(db_patch):
    """upsert_message(chat_id=None, source='api') → chat_id=NULL, source='api'."""
    row = await _insert_api(model_id='gpt-4o', user_id='alice')
    assert row is not None
    assert row.chat_id is None
    assert row.source == 'api'
    assert row.model_id == 'gpt-4o'
    assert row.user_id == 'alice'


@pytest.mark.asyncio
async def test_upsert_chat_row_has_chat_id_and_null_source(db_patch):
    """upsert_message(chat_id=<uuid>) → source=NULL (regular chat)."""
    cid = str(uuid.uuid4())
    row = await _insert_chat(model_id='claude-3', chat_id=cid)
    assert row is not None
    assert row.chat_id == cid
    assert row.source is None


@pytest.mark.asyncio
async def test_api_row_id_is_bare_message_uuid(db_patch):
    """API rows use bare UUID as ID (no composite chat_id prefix)."""
    msg_id = str(uuid.uuid4())
    row = await ChatMessages.upsert_message(
        message_id=msg_id,
        chat_id=None,
        user_id='u1',
        data={'role': 'assistant', 'model_id': 'gpt-4o', 'source': 'api', 'done': True},
    )
    assert row.id == msg_id  # bare UUID, not "{chat_id}-{msg_id}"


@pytest.mark.asyncio
async def test_chat_row_id_is_composite(db_patch):
    """Chat rows use composite {chat_id}-{message_id} as row ID."""
    cid = str(uuid.uuid4())
    mid = str(uuid.uuid4())
    row = await ChatMessages.upsert_message(
        message_id=mid,
        chat_id=cid,
        user_id='u1',
        data={'role': 'assistant', 'model_id': 'gpt-4o', 'done': True},
    )
    assert row.id == f'{cid}-{mid}'


# ─────────────────────────────────────────────────────────────────────────────
# 2. Chat analytics exclude API rows
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_chat_model_count_excludes_api_rows(db_patch):
    """get_message_count_by_model must not count API rows."""
    await _insert_chat(model_id='claude-3')
    await _insert_chat(model_id='claude-3')
    await _insert_api(model_id='claude-3')   # must be excluded

    counts = await ChatMessages.get_message_count_by_model()
    assert counts.get('claude-3') == 2


@pytest.mark.asyncio
async def test_chat_user_count_excludes_api_rows(db_patch):
    """get_message_count_by_user must not count API rows."""
    await _insert_chat(model_id='gpt-4o', user_id='alice')
    await _insert_api(model_id='gpt-4o', user_id='alice')  # must be excluded

    counts = await ChatMessages.get_message_count_by_user()
    assert counts.get('alice') == 1


@pytest.mark.asyncio
async def test_chat_token_usage_excludes_api_rows(db_patch):
    """get_token_usage_by_model must not include API token usage."""
    await _insert_chat(model_id='gpt-4o')
    await _insert_api(model_id='gpt-4o', usage=_usage(999, 999))  # must be excluded

    usage = await ChatMessages.get_token_usage_by_model()
    gpt_usage = usage.get('gpt-4o', {})
    assert gpt_usage.get('input_tokens') == 100   # only chat row's 100
    assert gpt_usage.get('output_tokens') == 50   # only chat row's 50


@pytest.mark.asyncio
async def test_chat_daily_counts_exclude_api_rows(db_patch):
    """get_daily_message_counts_by_model must not include API rows."""
    await _insert_chat(model_id='gpt-4o')
    await _insert_api(model_id='gpt-4o')   # must be excluded

    daily = await ChatMessages.get_daily_message_counts_by_model()
    # Sum all counts across all days — should only be 1 (the chat row)
    total = sum(sum(m.values()) for m in daily.values())
    assert total == 1


# ─────────────────────────────────────────────────────────────────────────────
# 3. API analytics include only API rows
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_model_count_excludes_chat_rows(db_patch):
    """get_api_message_count_by_model must not count chat rows."""
    await _insert_chat(model_id='gpt-4o')    # must be excluded
    await _insert_api(model_id='gpt-4o')
    await _insert_api(model_id='gpt-4o')

    counts = await ChatMessages.get_api_message_count_by_model()
    assert counts.get('gpt-4o') == 2


@pytest.mark.asyncio
async def test_api_user_count_excludes_chat_rows(db_patch):
    """get_api_message_count_by_user must not count chat rows."""
    await _insert_chat(model_id='gpt-4o', user_id='alice')  # must be excluded
    await _insert_api(model_id='gpt-4o', user_id='alice')
    await _insert_api(model_id='gpt-4o', user_id='bob')

    counts = await ChatMessages.get_api_message_count_by_user()
    assert counts == {'alice': 1, 'bob': 1}


@pytest.mark.asyncio
async def test_api_unique_users_per_model(db_patch):
    """get_api_unique_users_by_model counts distinct users for API rows only."""
    await _insert_api(model_id='gpt-4o', user_id='alice')
    await _insert_api(model_id='gpt-4o', user_id='alice')   # duplicate — same user
    await _insert_api(model_id='gpt-4o', user_id='bob')
    await _insert_chat(model_id='gpt-4o', user_id='carol')  # must be excluded

    unique = await ChatMessages.get_api_unique_users_by_model()
    assert unique.get('gpt-4o') == 2  # alice + bob only


@pytest.mark.asyncio
async def test_api_token_usage_excludes_chat_rows(db_patch):
    """get_api_token_usage_by_model sums only API-origin token usage."""
    await _insert_api(model_id='gpt-4o', usage=_usage(200, 100))
    await _insert_api(model_id='gpt-4o', usage=_usage(300, 150))
    await _insert_chat(model_id='gpt-4o', usage=_usage(999, 999))   # must be excluded

    usage = await ChatMessages.get_api_token_usage_by_model()
    gpt_usage = usage.get('gpt-4o', {})
    assert gpt_usage.get('input_tokens') == 500
    assert gpt_usage.get('output_tokens') == 250
    assert gpt_usage.get('total_tokens') == 750


@pytest.mark.asyncio
async def test_api_token_usage_by_user(db_patch):
    """get_api_token_usage_by_user aggregates per user for API rows only."""
    await _insert_api(model_id='gpt-4o', user_id='alice', usage=_usage(100, 50))
    await _insert_api(model_id='gpt-4o', user_id='alice', usage=_usage(200, 100))
    await _insert_chat(model_id='gpt-4o', user_id='alice')  # must be excluded

    usage = await ChatMessages.get_api_token_usage_by_user()
    alice = usage.get('alice', {})
    assert alice.get('input_tokens') == 300
    assert alice.get('output_tokens') == 150


@pytest.mark.asyncio
async def test_api_daily_counts_exclude_chat_rows(db_patch):
    """get_api_daily_counts_by_model must not include chat rows."""
    await _insert_api(model_id='gpt-4o')
    await _insert_api(model_id='gpt-4o')
    await _insert_chat(model_id='gpt-4o')   # must be excluded

    daily = await ChatMessages.get_api_daily_counts_by_model()
    total = sum(sum(m.values()) for m in daily.values())
    assert total == 2


# ─────────────────────────────────────────────────────────────────────────────
# 4. Isolation: mixed models
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mixed_models_tracked_independently(db_patch):
    """API and chat counts are correct across multiple models simultaneously."""
    # Chat rows
    await _insert_chat(model_id='claude-3')
    await _insert_chat(model_id='claude-3')
    await _insert_chat(model_id='gpt-4o')
    # API rows
    await _insert_api(model_id='gpt-4o')
    await _insert_api(model_id='gpt-4o')
    await _insert_api(model_id='claude-3')

    chat_counts = await ChatMessages.get_message_count_by_model()
    api_counts = await ChatMessages.get_api_message_count_by_model()

    assert chat_counts == {'claude-3': 2, 'gpt-4o': 1}
    assert api_counts == {'gpt-4o': 2, 'claude-3': 1}


# ─────────────────────────────────────────────────────────────────────────────
# 5. Date range filtering
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_date_range_filter(db_patch, session_factory):
    """start_date/end_date correctly filter API rows."""
    t_old = _now() - 10_000
    t_new = _now()

    # Manually insert rows with controlled timestamps via raw ORM
    async with session_factory() as s:
        s.add(ChatMessage(
            id=str(uuid.uuid4()),
            chat_id=None,
            user_id='u1',
            source='api',
            role='assistant',
            model_id='gpt-4o',
            done=True,
            created_at=t_old,
            updated_at=t_old,
        ))
        s.add(ChatMessage(
            id=str(uuid.uuid4()),
            chat_id=None,
            user_id='u1',
            source='api',
            role='assistant',
            model_id='gpt-4o',
            done=True,
            created_at=t_new,
            updated_at=t_new,
        ))
        await s.commit()

    cutoff = _now() - 5_000
    counts = await ChatMessages.get_api_message_count_by_model(start_date=cutoff)
    # Only the new row should be counted
    assert counts.get('gpt-4o') == 1


@pytest.mark.asyncio
async def test_chat_date_range_filter(db_patch, session_factory):
    """start_date/end_date correctly filter chat rows."""
    t_old = _now() - 10_000
    t_new = _now()
    cid = str(uuid.uuid4())

    async with session_factory() as s:
        s.add(ChatMessage(
            id=f'{cid}-old',
            chat_id=cid,
            user_id='u1',
            source=None,
            role='assistant',
            model_id='claude-3',
            done=True,
            created_at=t_old,
            updated_at=t_old,
        ))
        s.add(ChatMessage(
            id=f'{cid}-new',
            chat_id=cid,
            user_id='u1',
            source=None,
            role='assistant',
            model_id='claude-3',
            done=True,
            created_at=t_new,
            updated_at=t_new,
        ))
        await s.commit()

    cutoff = _now() - 5_000
    counts = await ChatMessages.get_message_count_by_model(start_date=cutoff)
    assert counts.get('claude-3') == 1


# ─────────────────────────────────────────────────────────────────────────────
# 6. Empty DB edge cases
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_empty_db_api_counts_return_empty(db_patch):
    """All API analytics methods return empty dicts on empty DB."""
    assert await ChatMessages.get_api_message_count_by_model() == {}
    assert await ChatMessages.get_api_message_count_by_user() == {}
    assert await ChatMessages.get_api_unique_users_by_model() == {}
    assert await ChatMessages.get_api_token_usage_by_model() == {}
    assert await ChatMessages.get_api_token_usage_by_user() == {}
    assert await ChatMessages.get_api_daily_counts_by_model() == {}


@pytest.mark.asyncio
async def test_empty_db_chat_counts_return_empty(db_patch):
    """All chat analytics methods return empty dicts on empty DB."""
    assert await ChatMessages.get_message_count_by_model() == {}
    assert await ChatMessages.get_message_count_by_user() == {}
    assert await ChatMessages.get_token_usage_by_model() == {}
    assert await ChatMessages.get_daily_message_counts_by_model() == {}
