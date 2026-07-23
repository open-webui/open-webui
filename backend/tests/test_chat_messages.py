import importlib
import json
import os
import sys
from contextlib import asynccontextmanager
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

os.environ.setdefault('WEBUI_SECRET_KEY', 'chat-message-tests-only-secret-key')

import open_webui.models.chat_messages as chat_messages_module
import pytest
import pytest_asyncio
from alembic.migration import MigrationContext
from alembic.operations import Operations
from open_webui.models.chat_messages import ChatMessage, ChatMessageTable
from open_webui.models.chats import Chat
from sqlalchemy import create_engine, event, func, inspect, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def session_factory(tmp_path, monkeypatch):
    database_path = tmp_path / 'chat-messages.db'
    engine = create_async_engine(f'sqlite+aiosqlite:///{database_path}')
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Chat.__table__.create)
        await connection.run_sync(ChatMessage.__table__.create)

    @asynccontextmanager
    async def test_db_context(db=None):
        if db is not None:
            yield db
            return
        async with factory() as session:
            yield session

    monkeypatch.setattr(chat_messages_module, 'get_async_db_context', test_db_context)
    yield factory
    await engine.dispose()


def message(role, parent_id, content, timestamp, **extra):
    return {
        'role': role,
        'parentId': parent_id,
        'childrenIds': [],
        'content': content,
        'timestamp': timestamp,
        **extra,
    }


@pytest.mark.asyncio
async def test_lossless_bulk_upsert_uses_one_commit_and_preserves_usage(session_factory):
    table = ChatMessageTable()
    payload = message(
        'assistant',
        None,
        'original',
        100,
        modelName='custom-model-name',
        model='provider-model',
        annotation={'rating': 5},
        arbitrary={'nested': ['value', {'kept': True}]},
        usage={'prompt_tokens': 4, 'completion_tokens': 2},
    )

    async with session_factory() as session:
        commits = 0
        select_count = 0

        @event.listens_for(session.sync_session, 'after_commit')
        def count_commit(_session):
            nonlocal commits
            commits += 1

        @event.listens_for(session.bind.sync_engine, 'before_cursor_execute')
        def count_select(_conn, _cursor, statement, _parameters, _context, _executemany):
            nonlocal select_count
            if statement.lstrip().upper().startswith('SELECT'):
                select_count += 1

        rows = await table.bulk_upsert_messages('chat', 'user', {'message': payload}, db=session)
        assert commits == 1
        assert select_count == 1
        assert rows[0].data['arbitrary'] == payload['arbitrary']

        await table.upsert_message(
            'message',
            'chat',
            'user',
            {'content': 'updated', 'model': None, 'usage': payload['usage']},
            db=session,
        )
        data_map = await table.get_message_data_map_by_chat_id('chat', db=session)
        model_id = await session.scalar(select(ChatMessage.model_id).where(ChatMessage.chat_id == 'chat'))

    stored = data_map['message']
    assert stored['content'] == 'updated'
    assert stored['modelName'] == 'custom-model-name'
    assert stored['annotation'] == {'rating': 5}
    assert stored['arbitrary'] == payload['arbitrary']
    assert stored['model'] is None
    assert model_id is None
    assert stored['usage']['input_tokens'] == 4
    assert stored['usage']['output_tokens'] == 2


@pytest.mark.asyncio
async def test_bulk_upsert_rolls_back_the_whole_batch(session_factory, monkeypatch):
    table = ChatMessageTable()
    original_apply = table._apply_message_data

    def fail_second(message_row, message_id, user_id, data, now, *, is_new):
        original_apply(message_row, message_id, user_id, data, now, is_new=is_new)
        if message_id == 'second':
            raise RuntimeError('injected batch failure')

    monkeypatch.setattr(table, '_apply_message_data', fail_second)

    async with session_factory() as session:
        with pytest.raises(RuntimeError, match='injected batch failure'):
            await table.bulk_upsert_messages(
                'chat',
                'user',
                {
                    'first': message('user', None, 'first', 1),
                    'second': message('assistant', 'first', 'second', 2),
                },
                db=session,
            )

    async with session_factory() as session:
        count = await session.scalar(select(func.count()).select_from(ChatMessage))
    assert count == 0


@pytest.mark.asyncio
async def test_replace_messages_repairs_missing_and_removes_stale_rows(session_factory):
    table = ChatMessageTable()
    async with session_factory() as session:
        await table.bulk_upsert_messages(
            'chat',
            'user',
            {
                'keep': message('user', None, 'old', 1),
                'stale': message('assistant', 'keep', 'stale', 2),
            },
            db=session,
        )
        await table.bulk_upsert_messages(
            'other-chat',
            'user',
            {'other': message('user', None, 'other', 1)},
            db=session,
        )

        commits = 0

        @event.listens_for(session.sync_session, 'after_commit')
        def count_commit(_session):
            nonlocal commits
            commits += 1

        await table.replace_messages_by_chat_id(
            'chat',
            'user',
            {
                'keep': message('user', None, 'updated', 1),
                'missing': message('assistant', 'keep', 'new', 3),
            },
            db=session,
        )

        data_map = await table.get_message_data_map_by_chat_id('chat', db=session)
        other_map = await table.get_message_data_map_by_chat_id('other-chat', db=session)

    assert commits == 1
    assert set(data_map) == {'keep', 'missing'}
    assert data_map['keep']['content'] == 'updated'
    assert set(other_map) == {'other'}


@pytest.mark.asyncio
async def test_message_window_paginates_only_current_ancestry(session_factory):
    table = ChatMessageTable()
    messages = {
        'root': message('user', None, 'root body', 1, custom='root'),
        'assistant': message('assistant', 'root', 'assistant body', 2),
        'left': message('user', 'assistant', 'left body', 3),
        'right': message('user', 'assistant', 'right body', 3, custom='right'),
        'leaf': message('assistant', 'right', 'leaf body', 4, custom='leaf'),
    }

    async with session_factory() as session:
        await table.bulk_upsert_messages('chat', 'user', messages, db=session)
        first = await table.get_message_window_by_chat_id('chat', 'leaf', limit=2, db=session)
        second = await table.get_message_window_by_chat_id(
            'chat',
            'leaf',
            limit=2,
            before_id='right',
            db=session,
        )
        branch = await table.get_message_branch_by_chat_id('chat', 'leaf', db=session)

    assert set(first) == {'topology', 'messages', 'loaded_ids', 'has_more', 'current_id'}
    assert set(first['topology']) == set(messages)
    assert first['loaded_ids'] == ['right', 'leaf']
    assert list(first['messages']) == ['right', 'leaf']
    assert first['messages']['leaf']['custom'] == 'leaf'
    assert first['has_more'] is True
    assert first['current_id'] == 'leaf'
    assert second['loaded_ids'] == ['root', 'assistant']
    assert second['has_more'] is False
    assert [item['id'] for item in branch] == ['root', 'assistant', 'right', 'leaf']
    assert branch[-1]['custom'] == 'leaf'


@pytest.mark.asyncio
async def test_message_branch_fails_closed_when_parent_row_is_missing(session_factory):
    table = ChatMessageTable()

    async with session_factory() as session:
        await table.bulk_upsert_messages(
            'chat',
            'user',
            {'leaf': message('assistant', 'missing-parent', 'leaf', 2)},
            db=session,
        )
        with pytest.raises(ValueError, match='missing parent: missing-parent'):
            await table.get_message_branch_by_chat_id('chat', 'leaf', db=session)
        with pytest.raises(ValueError, match='missing parent: missing-parent'):
            await table.get_message_window_by_chat_id('chat', 'leaf', db=session)


@pytest.mark.asyncio
async def test_last_request_usage_is_kept_separate_from_accumulated_usage(session_factory):
    table = ChatMessageTable()

    async with session_factory() as session:
        await table.upsert_message(
            'assistant',
            'chat',
            'user',
            message(
                'assistant',
                None,
                'first',
                1,
                usage={'input_tokens': 100, 'output_tokens': 20},
            ),
            db=session,
        )
        await table.upsert_message(
            'assistant',
            'chat',
            'user',
            {'usage': {'input_tokens': 40, 'output_tokens': 10}},
            db=session,
        )
        stored = await table.get_message_data_map_by_chat_id('chat', db=session)

    assert stored['assistant']['usage']['input_tokens'] == 140
    assert stored['assistant']['usage']['output_tokens'] == 30
    assert stored['assistant']['usage']['total_tokens'] == 170
    assert stored['assistant']['lastRequestUsage']['input_tokens'] == 40
    assert stored['assistant']['lastRequestUsage']['output_tokens'] == 10


@pytest.mark.asyncio
async def test_internal_leaf_query_and_latest_parent_use_normalized_rows(session_factory):
    table = ChatMessageTable()
    internal_subagent = {'internal': True, 'type': 'subagent', 'status': 'pending'}
    internal_timer = {'internal': True, 'type': 'timer', 'timer_id': 'timer'}

    async with session_factory() as session:
        await table.bulk_upsert_messages(
            'chat',
            'user',
            {
                'complete': message('assistant', None, 'complete', 1, done=True),
                'legacy-complete': message('assistant', 'complete', 'legacy', 2, done=None),
                'running': message('assistant', 'legacy-complete', 'running', 3, done=False),
                'pending-leaf': message(
                    'user',
                    'legacy-complete',
                    'pending',
                    4,
                    model='model',
                    meta=internal_subagent,
                ),
                'pending-parent': message(
                    'user',
                    'legacy-complete',
                    'not a leaf',
                    5,
                    model='model',
                    meta=internal_subagent,
                ),
                'pending-child': message('assistant', 'pending-parent', '', 6, done=False),
                'finished-subagent': message(
                    'user',
                    'legacy-complete',
                    'finished',
                    7,
                    meta={'internal': True, 'type': 'subagent', 'status': 'complete'},
                ),
                'timer-leaf': message(
                    'user',
                    'legacy-complete',
                    'timer',
                    8,
                    model='model',
                    meta=internal_timer,
                ),
                'ordinary': message(
                    'user',
                    'legacy-complete',
                    'ordinary',
                    9,
                    meta={'internal': False, 'type': 'subagent'},
                ),
            },
            db=session,
        )

        pending = await table.get_pending_internal_leaf_messages_in_session(session, 'chat')
        latest_parent = await table.get_latest_eligible_assistant_id_in_session(session, 'chat')

    assert [item['id'] for item in pending] == ['pending-leaf', 'timer-leaf']
    assert all(item['childrenIds'] == [] for item in pending)
    assert latest_parent == 'legacy-complete'


@pytest.mark.asyncio
async def test_in_session_delete_does_not_commit_and_can_be_rolled_back(session_factory):
    table = ChatMessageTable()

    async with session_factory() as session:
        await table.bulk_upsert_messages(
            'chat',
            'user',
            {
                'keep': message('user', None, 'keep', 1),
                'delete': message('assistant', 'keep', 'delete', 2),
            },
            db=session,
        )
        commits = 0

        @event.listens_for(session.sync_session, 'after_commit')
        def count_commit(_session):
            nonlocal commits
            commits += 1

        await table.delete_message_ids_in_session(session, 'chat', {'delete'})
        assert commits == 0
        assert await session.get(ChatMessage, 'chat-delete') is None
        await session.rollback()

    async with session_factory() as session:
        remaining = await table.get_message_data_map_by_chat_id('chat', db=session)

    assert set(remaining) == {'keep', 'delete'}


@pytest.mark.asyncio
async def test_subagent_pending_merge_normalizes_legacy_history_in_one_transaction(
    session_factory,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv('STATIC_DIR', str(tmp_path / 'static'))
    import open_webui.utils.subagents as subagents

    legacy_messages = {
        'root': message('user', None, 'root', 1, childrenIds=['parent']),
        'parent': message(
            'assistant',
            'root',
            'parent',
            2,
            done=True,
            childrenIds=['pending-1', 'pending-2'],
        ),
        'pending-1': message(
            'user',
            'parent',
            'first result',
            3,
            model='model',
            meta={
                'internal': True,
                'type': 'subagent',
                'status': 'pending',
                'delegation_id': 'first',
            },
        ),
        'pending-2': message(
            'user',
            'parent',
            'second result',
            4,
            model='model',
            meta={
                'internal': True,
                'type': 'subagent',
                'status': 'pending',
                'delegation_id': 'second',
            },
        ),
    }
    async with session_factory() as session:
        session.add(
            Chat(
                id='parent-chat',
                user_id='user',
                title='Parent',
                chat={
                    'history': {
                        'currentId': 'pending-2',
                        'messages': legacy_messages,
                    }
                },
                meta={},
                created_at=1,
                updated_at=1,
            )
        )
        await session.commit()

    commits = 0

    @asynccontextmanager
    async def tracked_db():
        nonlocal commits
        async with session_factory() as session:

            @event.listens_for(session.sync_session, 'after_commit')
            def count_commit(_session):
                nonlocal commits
                commits += 1

            yield session

    handler = AsyncMock()
    app = SimpleNamespace(state=SimpleNamespace(redis=object(), CHAT_COMPLETION_HANDLER=handler))
    source_request = SimpleNamespace(app=app)
    fake_socket = ModuleType('open_webui.socket.main')
    fake_socket.sio = SimpleNamespace(emit=AsyncMock())

    monkeypatch.setattr(subagents, 'get_async_db', tracked_db)
    monkeypatch.setattr(subagents, 'has_active_tasks', AsyncMock(return_value=False))
    monkeypatch.setattr(subagents.Users, 'get_user_by_id', AsyncMock(return_value=SimpleNamespace(id='user')))
    monkeypatch.setattr(subagents, '_build_request', lambda source, *_args, **_kwargs: source)
    monkeypatch.setitem(sys.modules, 'open_webui.socket.main', fake_socket)
    subagents._parent_locks.pop('parent-chat', None)

    await subagents.process_pending_internal_messages(
        source_request,
        'parent-chat',
        'user',
        {'model_id': 'model'},
    )

    table = ChatMessageTable()
    async with session_factory() as session:
        parent = await session.get(Chat, 'parent-chat')
        stored = await table.get_message_data_map_by_chat_id('parent-chat', db=session)
        topology = await table.get_message_topology_by_chat_id('parent-chat', db=session)

    assert commits == 1
    assert 'messages' not in parent.chat['history']
    assert parent.chat['history']['messageStorage'] == {'version': 1}
    assert {'pending-1', 'pending-2'}.isdisjoint(stored)
    combined = [
        item
        for item in stored.values()
        if item.get('role') == 'user' and (item.get('meta') or {}).get('type') == 'subagent'
    ]
    assert len(combined) == 1
    assert combined[0]['content'] == 'first result\n\nsecond result'
    current_id = parent.chat['history']['currentId']
    assert stored[current_id]['role'] == 'assistant'
    assert stored[current_id]['parentId'] == combined[0]['id']
    assert topology['parent']['childrenIds'] == [combined[0]['id']]
    handler.assert_awaited_once()
    submitted = handler.await_args.args[1]
    assert [item['content'] for item in submitted['messages']] == [
        'root',
        'parent',
        'first result\n\nsecond result',
    ]


@pytest.mark.asyncio
async def test_due_timer_appends_normalized_rows_and_current_id_in_one_transaction(
    session_factory,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv('STATIC_DIR', str(tmp_path / 'static'))
    import open_webui.utils.subagents as subagents
    import open_webui.utils.timers as timers

    timer_meta = {
        'status': 'running',
        'timer_claim_id': 'claim',
        'parent_chat_id': 'parent-chat',
        'parent_message_id': 'eligible',
        'timer_task_message_id': 'timer-task',
        'run': {'model_id': 'model'},
    }
    async with session_factory() as session:
        session.add_all(
            [
                Chat(
                    id='parent-chat',
                    user_id='user',
                    title='Parent',
                    chat={
                        'history': {
                            'currentId': 'running',
                            'messageStorage': {'version': 1},
                        }
                    },
                    meta={},
                    created_at=1,
                    updated_at=1,
                ),
                Chat(
                    id='timer-chat',
                    user_id='user',
                    title='Timer',
                    chat={'history': {'currentId': None, 'messageStorage': {'version': 1}}},
                    meta=timer_meta,
                    created_at=1,
                    updated_at=1,
                ),
            ]
        )
        await session.commit()
        await ChatMessageTable().bulk_upsert_messages(
            'parent-chat',
            'user',
            {
                'root': message('user', None, 'root', 1, childrenIds=['eligible', 'running']),
                'eligible': message('assistant', 'root', 'eligible', 2, done=True),
                'running': message('assistant', 'root', 'running', 3, done=False),
            },
            db=session,
        )

    commits = 0

    @asynccontextmanager
    async def tracked_db():
        nonlocal commits
        async with session_factory() as session:

            @event.listens_for(session.sync_session, 'after_commit')
            def count_commit(_session):
                nonlocal commits
                commits += 1

            yield session

    timer_model = SimpleNamespace(id='timer-chat', user_id='user', meta=timer_meta)
    handler = AsyncMock()
    app = SimpleNamespace(state=SimpleNamespace(redis=object(), CHAT_COMPLETION_HANDLER=handler))
    fake_socket = ModuleType('open_webui.socket.main')
    fake_socket.sio = SimpleNamespace(emit=AsyncMock())

    monkeypatch.setattr(timers, 'get_async_db', tracked_db)
    monkeypatch.setattr(timers.Chats, 'get_chat_by_id', AsyncMock(return_value=timer_model))
    monkeypatch.setattr(timers.Chats, 'get_chat_by_id_and_user_id', AsyncMock(return_value=SimpleNamespace()))
    monkeypatch.setattr(
        timers.Chats,
        'get_message_by_id_and_message_id',
        AsyncMock(return_value={'content': 'timer prompt'}),
    )
    monkeypatch.setattr(timers.Users, 'get_user_by_id', AsyncMock(return_value=SimpleNamespace(id='user')))
    monkeypatch.setattr(timers, 'has_active_tasks', AsyncMock(return_value=False))
    monkeypatch.setitem(sys.modules, 'open_webui.socket.main', fake_socket)
    timers._timer_locks.pop('timer-chat', None)
    subagents._parent_locks.pop('parent-chat', None)

    await timers.execute_due_timer(app, 'timer-chat', 'claim')

    table = ChatMessageTable()
    async with session_factory() as session:
        parent = await session.get(Chat, 'parent-chat')
        timer_row = await session.get(Chat, 'timer-chat')
        stored = await table.get_message_data_map_by_chat_id('parent-chat', db=session)

    assert commits == 1
    assert 'messages' not in parent.chat['history']
    assert timer_row.meta['status'] == 'completed'
    timer_users = [
        item
        for item in stored.values()
        if item.get('role') == 'user' and (item.get('meta') or {}).get('type') == 'timer'
    ]
    assert len(timer_users) == 1
    assert timer_users[0]['parentId'] == 'eligible'
    current_id = parent.chat['history']['currentId']
    assert stored[current_id]['role'] == 'assistant'
    assert stored[current_id]['parentId'] == timer_users[0]['id']
    handler.assert_awaited_once()
    submitted = handler.await_args.args[1]
    assert submitted['parent_id'] == 'eligible'
    assert [item['content'] for item in submitted['messages']] == ['root', 'eligible', 'timer prompt']


@pytest.mark.asyncio
async def test_message_window_handles_empty_chat_and_missing_current_id(session_factory):
    table = ChatMessageTable()

    async with session_factory() as session:
        empty = await table.get_message_window_by_chat_id('chat', None, db=session)
        await table.bulk_upsert_messages(
            'chat',
            'user',
            {
                'root': message('user', None, 'root', 1),
                'leaf': message('assistant', 'root', 'leaf', 2),
            },
            db=session,
        )
        inferred = await table.get_message_window_by_chat_id('chat', None, db=session)

    assert empty == {
        'topology': {},
        'messages': {},
        'loaded_ids': [],
        'has_more': False,
        'current_id': None,
    }
    assert inferred['current_id'] == 'leaf'
    assert inferred['loaded_ids'] == ['root', 'leaf']


@pytest.mark.asyncio
async def test_topology_keeps_messages_with_duplicate_timestamps(session_factory):
    table = ChatMessageTable()
    messages = {
        'c': message('user', None, 'c', 10),
        'a': message('user', None, 'a', 10),
        'b': message('user', None, 'b', 10),
    }

    async with session_factory() as session:
        await table.bulk_upsert_messages('chat', 'user', messages, db=session)
        topology = await table.get_message_topology_by_chat_id('chat', db=session)

    assert list(topology) == ['a', 'b', 'c']
    assert len(topology) == 3


@pytest.mark.asyncio
async def test_topology_preserves_projected_sibling_order(session_factory):
    table = ChatMessageTable()
    messages = {
        'root': message('assistant', None, 'root', 1, childrenIds=['z-child', 'a-child']),
        'a-child': message('user', 'root', 'a', 2),
        'm-child': message('user', 'root', 'm', 2),
        'z-child': message('user', 'root', 'z', 2),
    }

    async with session_factory() as session:
        await table.bulk_upsert_messages('chat', 'user', messages, db=session)
        topology = await table.get_message_topology_by_chat_id('chat', db=session)

    assert topology['root']['childrenIds'] == ['z-child', 'a-child', 'm-child']


@pytest.mark.asyncio
async def test_topology_rebuilds_missing_sibling_projection_stably(session_factory):
    table = ChatMessageTable()
    messages = {
        'root': {'role': 'assistant', 'parentId': None, 'content': 'root', 'timestamp': 1},
        'z-child': {'role': 'user', 'parentId': 'root', 'content': 'z', 'timestamp': 2},
        'a-child': {'role': 'user', 'parentId': 'root', 'content': 'a', 'timestamp': 2},
    }

    async with session_factory() as session:
        await table.bulk_upsert_messages('chat', 'user', messages, db=session)
        topology = await table.get_message_topology_by_chat_id('chat', db=session)

    assert topology['root']['childrenIds'] == ['a-child', 'z-child']


@pytest.mark.asyncio
async def test_content_snippets_return_one_match_per_chat_in_one_query(session_factory):
    table = ChatMessageTable()
    async with session_factory() as session:
        await table.bulk_upsert_messages(
            'chat-1',
            'user',
            {
                'first': message('user', None, 'prefix needle first suffix', 1),
                'second': message('assistant', 'first', 'needle second', 2),
            },
            db=session,
        )
        await table.bulk_upsert_messages(
            'chat-2',
            'user',
            {'only': message('user', None, 'nothing relevant', 1)},
            db=session,
        )
        await table.bulk_upsert_messages(
            'chat-3',
            'user',
            {'only': message('user', None, 'another needle match', 1)},
            db=session,
        )

        query_count = 0

        @event.listens_for(session.bind.sync_engine, 'before_cursor_execute')
        def count_query(_conn, _cursor, _statement, _parameters, _context, _executemany):
            nonlocal query_count
            query_count += 1

        snippets = await table.get_content_snippets_by_chat_ids(
            ['chat-1', 'chat-2', 'chat-3'],
            'needle',
            max_length=30,
            db=session,
        )
        no_matches = await table.get_content_snippets_by_chat_ids(
            ['chat-1', 'chat-2', 'chat-3'],
            'absent',
            db=session,
        )

    assert query_count == 2
    assert snippets == {
        'chat-1': 'prefix needle first suffix',
        'chat-3': 'another needle match',
    }
    assert no_matches == {}


def test_data_migration_backfills_and_downgrades(tmp_path, monkeypatch):
    migration = importlib.import_module('open_webui.migrations.versions.9c0e2f4a6b81_add_data_to_chat_message')
    engine = create_engine(f'sqlite:///{tmp_path / "migration.db"}')

    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE chat (id TEXT PRIMARY KEY, chat JSON)'))
        connection.execute(
            text(
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
        )
        connection.execute(
            text(
                """
                INSERT INTO chat_message (
                    id, chat_id, user_id, role, content, model_id, done, usage, created_at, updated_at
                ) VALUES (
                    :id, :chat_id, :user_id, :role, :content, :model_id, :done, :usage, :created_at, :updated_at
                )
                """
            ),
            {
                'id': 'chat-message',
                'chat_id': 'chat',
                'user_id': 'user',
                'role': 'assistant',
                'content': json.dumps('hello'),
                'model_id': 'model',
                'done': True,
                'usage': json.dumps({'prompt_tokens': 2}),
                'created_at': 123,
                'updated_at': 123,
            },
        )

        context = MigrationContext.configure(connection)
        monkeypatch.setattr(migration, 'op', Operations(context))
        migration.upgrade()

        columns = {column['name'] for column in inspect(connection).get_columns('chat_message')}
        data, children_ids = connection.execute(
            text('SELECT data, children_ids FROM chat_message WHERE id = :id'),
            {'id': 'chat-message'},
        ).one()
        payload = json.loads(data)

        assert {'data', 'children_ids'} <= columns
        assert payload['id'] == 'message'
        assert payload['content'] == 'hello'
        assert payload['model'] == 'model'
        assert payload['timestamp'] == 123
        assert children_ids is None

        connection.execute(
            text('INSERT INTO chat (id, chat) VALUES (:id, :chat)'),
            {
                'id': 'chat',
                'chat': json.dumps(
                    {
                        'title': 'Compacted',
                        'history': {
                            'currentId': 'message',
                            'messageStorage': {'version': 1},
                        },
                    }
                ),
            },
        )

        migration.downgrade()
        columns = {column['name'] for column in inspect(connection).get_columns('chat_message')}
        restored_chat = connection.execute(text('SELECT chat FROM chat WHERE id = :id'), {'id': 'chat'}).scalar_one()
        restored_chat = json.loads(restored_chat)
        assert 'data' not in columns
        assert 'children_ids' not in columns
        assert restored_chat['history']['messages']['message']['content'] == 'hello'
        assert restored_chat['messages'][0]['id'] == 'message'
        assert 'messageStorage' not in restored_chat['history']

    engine.dispose()
