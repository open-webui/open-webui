"""
Tests for API usage tracking via ChatMessage with source='api'.

These tests use an in-memory SQLite DB so no server is required.
Run with:  pytest backend/tests/test_api_usage_tracking.py -v
"""

import asyncio
import time
import uuid
from typing import Optional

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Minimal in-memory schema — mirrors only what the tests need
# ---------------------------------------------------------------------------

metadata = sa.MetaData()

chat_message_table = sa.Table(
    'chat_message',
    metadata,
    sa.Column('id', sa.Text, primary_key=True),
    sa.Column('chat_id', sa.Text, nullable=True),
    sa.Column('user_id', sa.Text),
    sa.Column('source', sa.Text, nullable=True),
    sa.Column('role', sa.Text, nullable=False),
    sa.Column('parent_id', sa.Text, nullable=True),
    sa.Column('content', sa.JSON, nullable=True),
    sa.Column('output', sa.JSON, nullable=True),
    sa.Column('model_id', sa.Text, nullable=True),
    sa.Column('files', sa.JSON, nullable=True),
    sa.Column('sources', sa.JSON, nullable=True),
    sa.Column('embeds', sa.JSON, nullable=True),
    sa.Column('meta', sa.JSON, nullable=True),
    sa.Column('done', sa.Boolean, default=True),
    sa.Column('status_history', sa.JSON, nullable=True),
    sa.Column('error', sa.JSON, nullable=True),
    sa.Column('usage', sa.JSON, nullable=True),
    sa.Column('context_summary', sa.Text, nullable=True),
    sa.Column('created_at', sa.BigInteger),
    sa.Column('updated_at', sa.BigInteger),
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def engine():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:', echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session(engine):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now():
    return int(time.time())


def _usage(inp=100, out=50):
    return {'input_tokens': inp, 'output_tokens': out, 'total_tokens': inp + out}


async def _insert(session: AsyncSession, *, chat_id=None, user_id='u1', model_id='gpt-4o',
                  source=None, usage=None, created_at=None):
    msg_id = str(uuid.uuid4())
    row_id = f'{chat_id}-{msg_id}' if chat_id else msg_id
    await session.execute(
        chat_message_table.insert().values(
            id=row_id,
            chat_id=chat_id,
            user_id=user_id,
            source=source,
            role='assistant',
            model_id=model_id,
            usage=usage or _usage(),
            done=True,
            created_at=created_at or _now(),
            updated_at=_now(),
        )
    )
    await session.commit()
    return row_id


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_message_allows_null_chat_id(session):
    """chat_id=NULL must be accepted (no FK constraint)."""
    row_id = await _insert(session, chat_id=None, source='api')
    result = await session.execute(
        sa.select(chat_message_table).where(chat_message_table.c.id == row_id)
    )
    row = result.fetchone()
    assert row is not None
    assert row.chat_id is None
    assert row.source == 'api'


@pytest.mark.asyncio
async def test_chat_message_null_source_for_regular_chat(session):
    """Regular chat rows have source=NULL."""
    row_id = await _insert(session, chat_id='chat-abc', source=None)
    result = await session.execute(
        sa.select(chat_message_table).where(chat_message_table.c.id == row_id)
    )
    row = result.fetchone()
    assert row.source is None
    assert row.chat_id == 'chat-abc'


# ---------------------------------------------------------------------------
# Analytics filter tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_analytics_excludes_api_rows(session):
    """Existing analytics (source IS NULL) must not count API rows."""
    await _insert(session, chat_id='chat-1', source=None, model_id='claude-3')
    await _insert(session, chat_id='chat-2', source=None, model_id='claude-3')
    await _insert(session, chat_id=None, source='api', model_id='claude-3')  # API row

    # Simulate existing analytics query: source IS NULL
    result = await session.execute(
        sa.select(chat_message_table.c.model_id, sa.func.count().label('cnt'))
        .where(chat_message_table.c.role == 'assistant')
        .where(chat_message_table.c.source.is_(None))
        .group_by(chat_message_table.c.model_id)
    )
    row = result.fetchone()
    assert row is not None
    assert row.cnt == 2  # only the 2 chat rows, not the API row


@pytest.mark.asyncio
async def test_api_analytics_excludes_chat_rows(session):
    """API analytics (source='api') must not count chat rows."""
    await _insert(session, chat_id='chat-1', source=None, model_id='gpt-4o')
    await _insert(session, chat_id=None, source='api', model_id='gpt-4o')
    await _insert(session, chat_id=None, source='api', model_id='gpt-4o')

    result = await session.execute(
        sa.select(chat_message_table.c.model_id, sa.func.count().label('cnt'))
        .where(chat_message_table.c.role == 'assistant')
        .where(chat_message_table.c.source == 'api')
        .group_by(chat_message_table.c.model_id)
    )
    row = result.fetchone()
    assert row is not None
    assert row.cnt == 2  # only the 2 API rows


@pytest.mark.asyncio
async def test_api_count_by_user(session):
    """API analytics per-user count is correct."""
    await _insert(session, chat_id=None, source='api', user_id='alice', model_id='gpt-4o')
    await _insert(session, chat_id=None, source='api', user_id='alice', model_id='claude-3')
    await _insert(session, chat_id=None, source='api', user_id='bob', model_id='gpt-4o')
    await _insert(session, chat_id='chat-1', source=None, user_id='alice', model_id='gpt-4o')  # should NOT count

    result = await session.execute(
        sa.select(chat_message_table.c.user_id, sa.func.count().label('cnt'))
        .where(chat_message_table.c.role == 'assistant')
        .where(chat_message_table.c.source == 'api')
        .group_by(chat_message_table.c.user_id)
        .order_by(chat_message_table.c.user_id)
    )
    rows = {r.user_id: r.cnt for r in result.fetchall()}
    assert rows == {'alice': 2, 'bob': 1}


@pytest.mark.asyncio
async def test_token_usage_aggregation(session):
    """Token sums are correct for API rows only."""
    await _insert(session, chat_id=None, source='api', user_id='alice',
                  model_id='gpt-4o', usage=_usage(200, 100))
    await _insert(session, chat_id=None, source='api', user_id='alice',
                  model_id='gpt-4o', usage=_usage(300, 150))
    await _insert(session, chat_id='c1', source=None, user_id='alice',
                  model_id='gpt-4o', usage=_usage(999, 999))  # chat row — excluded

    # SQLite JSON extraction via json_extract
    input_col = sa.cast(sa.func.json_extract(chat_message_table.c.usage, '$.input_tokens'), sa.Integer)
    output_col = sa.cast(sa.func.json_extract(chat_message_table.c.usage, '$.output_tokens'), sa.Integer)

    result = await session.execute(
        sa.select(
            sa.func.coalesce(sa.func.sum(input_col), 0).label('total_in'),
            sa.func.coalesce(sa.func.sum(output_col), 0).label('total_out'),
        )
        .where(chat_message_table.c.role == 'assistant')
        .where(chat_message_table.c.source == 'api')
        .where(chat_message_table.c.usage.isnot(None))
    )
    row = result.fetchone()
    assert row.total_in == 500
    assert row.total_out == 250


@pytest.mark.asyncio
async def test_date_range_filter(session):
    """start_date / end_date filters work for API rows."""
    t_old = _now() - 10000
    t_new = _now()
    await _insert(session, chat_id=None, source='api', created_at=t_old)
    await _insert(session, chat_id=None, source='api', created_at=t_new)

    cutoff = _now() - 5000
    result = await session.execute(
        sa.select(sa.func.count().label('cnt'))
        .where(chat_message_table.c.source == 'api')
        .where(chat_message_table.c.created_at >= cutoff)
    )
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_empty_table_returns_zero(session):
    """Analytics on empty table returns 0, not an error."""
    result = await session.execute(
        sa.select(sa.func.count().label('cnt'))
        .where(chat_message_table.c.source == 'api')
    )
    assert result.scalar() == 0


@pytest.mark.asyncio
async def test_mixed_models_api_count(session):
    """Multiple models are counted independently."""
    await _insert(session, chat_id=None, source='api', model_id='gpt-4o')
    await _insert(session, chat_id=None, source='api', model_id='gpt-4o')
    await _insert(session, chat_id=None, source='api', model_id='claude-3')

    result = await session.execute(
        sa.select(chat_message_table.c.model_id, sa.func.count().label('cnt'))
        .where(chat_message_table.c.source == 'api')
        .group_by(chat_message_table.c.model_id)
        .order_by(chat_message_table.c.model_id)
    )
    rows = {r.model_id: r.cnt for r in result.fetchall()}
    assert rows == {'claude-3': 1, 'gpt-4o': 2}
