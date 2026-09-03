import importlib.util
import json
import sys
import types
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

ROOT = Path(__file__).parents[1]


@pytest.fixture(scope='module')
def responses_state_module():
    source = ROOT / 'backend/open_webui/utils/responses_state.py'
    spec = importlib.util.spec_from_file_location('open_webui_storage_test_responses_state', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def chat_messages_module(monkeypatch):
    database_module = types.ModuleType('open_webui.internal.db')
    database_module.Base = declarative_base()
    sa.Table(
        'chat',
        database_module.Base.metadata,
        sa.Column('id', sa.Text(), primary_key=True),
    )

    @asynccontextmanager
    async def unavailable_database_context(*_args, **_kwargs):
        raise RuntimeError('Test database context has not been installed')
        yield

    database_module.get_async_db_context = unavailable_database_context

    response_module = types.ModuleType('open_webui.utils.response')
    response_module.normalize_usage = lambda value: value
    response_module.merge_usage = lambda existing, new: {**(existing or {}), **(new or {})}

    monkeypatch.setitem(sys.modules, 'open_webui.internal.db', database_module)
    monkeypatch.setitem(sys.modules, 'open_webui.utils.response', response_module)

    source = ROOT / 'backend/open_webui/models/chat_messages.py'
    spec = importlib.util.spec_from_file_location('open_webui_test_chat_messages', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest_asyncio.fixture
async def chat_message_table(chat_messages_module, monkeypatch):
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    async with engine.begin() as connection:
        await connection.exec_driver_sql(
            """
            CREATE TABLE chat_message (
                id TEXT PRIMARY KEY,
                chat_id TEXT NOT NULL,
                user_id TEXT,
                role TEXT NOT NULL,
                parent_id TEXT,
                content JSON,
                output JSON,
                model_id TEXT,
                response_id TEXT,
                files JSON,
                sources JSON,
                embeds JSON,
                meta JSON,
                done BOOLEAN,
                status_history JSON,
                error JSON,
                usage JSON,
                context_summary TEXT,
                created_at BIGINT,
                updated_at BIGINT
            )
            """
        )

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def database_context(session=None):
        if session is not None:
            yield session
            return
        async with session_factory() as created_session:
            yield created_session

    monkeypatch.setattr(chat_messages_module, 'get_async_db_context', database_context)
    yield chat_messages_module.ChatMessageTable()
    await engine.dispose()


@pytest.mark.asyncio
async def test_response_id_round_trip_through_normalized_message_table(chat_message_table):
    await chat_message_table.upsert_message(
        message_id='assistant-1',
        chat_id='chat-1',
        user_id='user-1',
        data={
            'role': 'assistant',
            'model': 'hermes',
            'responseId': 'resp_first',
            'content': 'First response',
        },
    )

    messages = await chat_message_table.get_messages_map_by_chat_id('chat-1')
    assert messages['assistant-1']['responseId'] == 'resp_first'
    assert 'response_id' not in messages['assistant-1']

    await chat_message_table.upsert_message(
        message_id='assistant-1',
        chat_id='chat-1',
        user_id='user-1',
        data={'response_id': 'resp_second'},
    )

    messages = await chat_message_table.get_messages_map_by_chat_id('chat-1')
    assert messages['assistant-1']['responseId'] == 'resp_second'


@pytest.mark.asyncio
async def test_next_turn_uses_persisted_response_id_without_replaying_history(
    chat_message_table,
    responses_state_module,
):
    await chat_message_table.upsert_messages(
        chat_id='chat-2',
        user_id='user-1',
        messages={
            'user-1': {
                'role': 'user',
                'content': 'First question',
            },
            'assistant-1': {
                'role': 'assistant',
                'parentId': 'user-1',
                'model': 'hermes',
                'responseId': 'resp_previous',
                'content': 'First answer',
            },
            'user-2': {
                'role': 'user',
                'parentId': 'assistant-1',
                'content': 'Follow-up question',
            },
        },
    )

    messages = await chat_message_table.get_messages_map_by_chat_id('chat-2')
    response_id = responses_state_module.get_stateful_response_id(messages, 'user-2', 'hermes')
    replay = [
        {'role': 'system', 'content': 'Managed instructions'},
        messages['user-1'],
        messages['assistant-1'],
        messages['user-2'],
    ]
    payload = responses_state_module.apply_responses_stateful_payload(
        {
            'messages': responses_state_module.trim_stateful_messages(replay),
            'previous_response_id': response_id,
        },
        is_responses=True,
        enabled=True,
    )

    assert payload['previous_response_id'] == 'resp_previous'
    assert payload['store'] is True
    assert [message['content'] for message in payload['messages']] == [
        'Managed instructions',
        'Follow-up question',
    ]


def load_response_id_migration(monkeypatch):
    alembic_module = types.ModuleType('alembic')
    alembic_module.op = None
    monkeypatch.setitem(sys.modules, 'alembic', alembic_module)

    source = ROOT / 'backend/open_webui/migrations/versions/e2a43c7819b6_add_response_id_to_chat_message.py'
    spec = importlib.util.spec_from_file_location('open_webui_test_response_id_migration', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_response_id_migration_adds_backfills_and_drops_column(monkeypatch):
    engine = sa.create_engine('sqlite:///:memory:')
    metadata = sa.MetaData()
    chat = sa.Table(
        'chat',
        metadata,
        sa.Column('id', sa.Text(), primary_key=True),
        sa.Column('chat', sa.JSON()),
    )
    chat_message = sa.Table(
        'chat_message',
        metadata,
        sa.Column('id', sa.Text(), primary_key=True),
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(
            chat.insert(),
            [
                {
                    'id': 'chat-1',
                    'chat': {
                        'history': {
                            'messages': {
                                'assistant-1': {'role': 'assistant', 'responseId': 'resp_existing'},
                                'user-1': {'role': 'user'},
                            }
                        }
                    },
                },
                {'id': 'chat-invalid', 'chat': json.dumps({'history': {'messages': []}})},
            ],
        )
        connection.execute(chat_message.insert(), {'id': 'chat-1-assistant-1'})

        migration = load_response_id_migration(monkeypatch)

        class MigrationOperations:
            @staticmethod
            def get_bind():
                return connection

            @staticmethod
            def add_column(table_name, column):
                connection.execute(sa.text(f'ALTER TABLE {table_name} ADD COLUMN {column.name} TEXT'))

            @staticmethod
            def drop_column(table_name, column_name):
                connection.execute(sa.text(f'ALTER TABLE {table_name} DROP COLUMN {column_name}'))

        migration.op = MigrationOperations
        migration.upgrade()

        reflected = sa.Table('chat_message', sa.MetaData(), autoload_with=connection)
        response_id = connection.execute(
            sa.select(reflected.c.response_id).where(reflected.c.id == 'chat-1-assistant-1')
        ).scalar_one()
        assert response_id == 'resp_existing'

        migration.downgrade()
        assert 'response_id' not in {column['name'] for column in sa.inspect(connection).get_columns('chat_message')}

    engine.dispose()
