import os
from contextlib import asynccontextmanager

os.environ.setdefault('WEBUI_SECRET_KEY', 'chat-storage-tests-only-secret-key')

import open_webui.models.chat_messages as chat_messages_module
import open_webui.models.chats as chats_module
import open_webui.models.shared_chats as shared_chats_module
import pytest
import pytest_asyncio
from open_webui.models.chat_messages import ChatMessage, ChatMessages
from open_webui.models.chats import Chat, ChatImportForm, Chats
from open_webui.models.shared_chats import SharedChat, SharedChats
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def session_factory(tmp_path, monkeypatch):
    database_path = tmp_path / 'chat-storage.db'
    engine = create_async_engine(f'sqlite+aiosqlite:///{database_path}')
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Chat.__table__.create)
        await connection.run_sync(ChatMessage.__table__.create)
        await connection.run_sync(SharedChat.__table__.create)

    @asynccontextmanager
    async def test_db_context(db=None):
        if db is not None:
            yield db
            return
        async with factory() as session:
            yield session

    monkeypatch.setattr(chat_messages_module, 'get_async_db_context', test_db_context)
    monkeypatch.setattr(chats_module, 'get_async_db_context', test_db_context)
    monkeypatch.setattr(shared_chats_module, 'get_async_db_context', test_db_context)
    yield factory
    await engine.dispose()


def legacy_chat():
    return {
        'title': 'Legacy',
        'models': ['model'],
        'history': {
            'currentId': 'leaf',
            'messages': {
                'root': {
                    'id': 'root',
                    'parentId': None,
                    'childrenIds': ['leaf'],
                    'role': 'user',
                    'content': 'root',
                    'timestamp': 1,
                    'arbitrary': {'kept': True},
                },
                'leaf': {
                    'id': 'leaf',
                    'parentId': 'root',
                    'childrenIds': [],
                    'role': 'assistant',
                    'content': 'leaf',
                    'timestamp': 2,
                    'done': True,
                },
            },
        },
    }


async def insert_chat(session, chat_id='chat'):
    session.add(
        Chat(
            id=chat_id,
            user_id='user',
            title='Legacy',
            chat=legacy_chat(),
            created_at=1,
            updated_at=1,
            archived=False,
            pinned=False,
            meta={},
        )
    )
    await session.commit()


@pytest.mark.asyncio
async def test_legacy_chat_is_reconciled_compacted_and_windowed(session_factory):
    async with session_factory() as session:
        await insert_chat(session)
        await ChatMessages.bulk_upsert_messages(
            'chat',
            'user',
            {
                'stale': {
                    'id': 'stale',
                    'parentId': None,
                    'childrenIds': [],
                    'role': 'user',
                    'content': 'stale',
                    'timestamp': 0,
                }
            },
            db=session,
        )

        compact = await Chats.get_chat_by_id('chat', db=session, include_messages=False)
        normalized = await ChatMessages.get_message_data_map_by_chat_id('chat', db=session)
        full = await Chats.get_chat_by_id('chat', db=session, include_messages=True)
        window = await Chats.get_chat_window(compact, limit=1, db=session)

    assert 'messages' not in compact.chat['history']
    assert compact.chat['history']['messageStorage'] == {'version': 1}
    assert set(normalized) == {'root', 'leaf'}
    assert normalized['root']['arbitrary'] == {'kept': True}
    assert full.chat['history']['messages']['root']['content'] == 'root'
    assert full.chat['messages'][-1]['id'] == 'leaf'
    assert window.chat['history']['messages']['root']['__loaded'] is False
    assert window.chat['history']['messages']['leaf']['__loaded'] is True


@pytest.mark.asyncio
async def test_window_update_only_appends_new_messages(session_factory):
    async with session_factory() as session:
        await insert_chat(session)
        await Chats.get_chat_by_id('chat', db=session, include_messages=False)

        await Chats.update_chat_window_by_id(
            'chat',
            {
                'history': {
                    'currentId': 'branch',
                    'messages': {
                        'leaf': {
                            'id': 'leaf',
                            'parentId': 'root',
                            'childrenIds': [],
                            'role': 'assistant',
                            'content': 'stale browser copy',
                            'timestamp': 2,
                        },
                        'branch': {
                            'id': 'branch',
                            'parentId': 'root',
                            'childrenIds': [],
                            'role': 'assistant',
                            'content': 'new branch',
                            'timestamp': 3,
                        },
                    },
                    'messageWindow': {'loadedIds': ['leaf', 'branch']},
                }
            },
            db=session,
        )
        messages = await ChatMessages.get_message_data_map_by_chat_id('chat', db=session)
        persisted = await session.get(Chat, 'chat')

    assert set(messages) == {'root', 'leaf', 'branch'}
    assert messages['root']['content'] == 'root'
    assert messages['leaf']['content'] == 'leaf'
    assert messages['branch']['content'] == 'new branch'
    assert persisted.chat['history']['currentId'] == 'branch'
    assert persisted.current_message_id == 'branch'


@pytest.mark.asyncio
async def test_single_message_read_lazily_normalizes_legacy_chat(session_factory):
    async with session_factory() as session:
        await insert_chat(session)

    message = await Chats.get_message_by_id_and_message_id('chat', 'root')

    async with session_factory() as session:
        persisted = await session.get(Chat, 'chat')
        messages = await ChatMessages.get_message_data_map_by_chat_id('chat', db=session)

    assert message['content'] == 'root'
    assert message['arbitrary'] == {'kept': True}
    assert 'messages' not in persisted.chat['history']
    assert persisted.chat['history']['messageStorage'] == {'version': 1}
    assert set(messages) == {'root', 'leaf'}


@pytest.mark.asyncio
async def test_search_falls_back_to_legacy_json_then_returns_normalized_snippet(session_factory):
    async with session_factory() as session:
        await insert_chat(session)
        results = await Chats.get_chats_by_user_id_and_search_text(
            'user',
            'root',
            db=session,
        )
        persisted = await session.get(Chat, 'chat')
        messages = await ChatMessages.get_message_data_map_by_chat_id('chat', db=session)

    assert [chat.id for chat in results] == ['chat']
    assert results[0].snippet == 'root'
    assert 'messages' not in persisted.chat['history']
    assert set(messages) == {'root', 'leaf'}


@pytest.mark.asyncio
async def test_single_message_hot_path_preserves_history_and_updates_topology(session_factory):
    async with session_factory() as session:
        await insert_chat(session)
        await Chats.get_chat_by_id('chat', db=session, include_messages=False)

    compact = await Chats.upsert_message_to_chat_by_id_and_message_id(
        'chat',
        'leaf',
        {'content': 'streamed update', 'partial': {'kept': True}},
    )
    created = await Chats.upsert_message_to_chat_by_id_and_message_id(
        'chat',
        'branch',
        {'parentId': 'root', 'content': 'new branch'},
    )

    async with session_factory() as session:
        messages = await ChatMessages.get_message_data_map_by_chat_id('chat', db=session)
        persisted = await session.get(Chat, 'chat')

    assert 'messages' not in compact.chat['history']
    assert 'messages' not in created.chat['history']
    assert persisted.chat['history']['currentId'] == 'branch'
    assert persisted.current_message_id == 'branch'
    assert messages['root']['arbitrary'] == {'kept': True}
    assert messages['root']['childrenIds'] == ['leaf', 'branch']
    assert messages['leaf']['content'] == 'streamed update'
    assert messages['leaf']['done'] is True
    assert messages['leaf']['partial'] == {'kept': True}
    assert messages['branch']['parentId'] == 'root'
    assert messages['branch']['role'] == 'assistant'

    full = await Chats.upsert_message_to_chat_by_id_and_message_id(
        'chat',
        'branch',
        {'content': 'final branch'},
        include_messages=True,
    )
    assert full.chat['history']['messages']['branch']['content'] == 'final branch'
    assert full.chat['history']['messages']['root']['arbitrary'] == {'kept': True}


@pytest.mark.asyncio
async def test_updating_an_existing_ancestor_does_not_change_the_active_branch(session_factory):
    async with session_factory() as session:
        await insert_chat(session)
        await Chats.get_chat_by_id('chat', db=session, include_messages=False)

        updated = await Chats.upsert_message_to_chat_by_id_and_message_id(
            'chat',
            'root',
            {'status': {'done': True}},
        )

    assert updated.chat['history']['currentId'] == 'leaf'


@pytest.mark.asyncio
async def test_window_repairs_invalid_normalized_current_id(session_factory):
    async with session_factory() as session:
        await insert_chat(session)
        compact = await Chats.get_chat_by_id('chat', db=session, include_messages=False)
        row = await session.get(Chat, 'chat')
        row.chat = {
            **row.chat,
            'history': {**row.chat['history'], 'currentId': 'missing'},
        }
        await session.commit()
        await session.refresh(row)
        compact = compact.model_copy(update={'chat': row.chat})

        window = await Chats.get_chat_window(compact, limit=1, db=session)
        await session.refresh(row)

    assert window.chat['history']['currentId'] == 'leaf'
    assert row.chat['history']['currentId'] == 'leaf'


@pytest.mark.asyncio
async def test_single_message_patch_preserves_topology_and_updates_only_message_data(session_factory):
    async with session_factory() as session:
        await insert_chat(session)
        await Chats.get_chat_by_id('chat', db=session, include_messages=False)

        updated = await Chats.patch_message_by_chat_id_and_message_id(
            'chat',
            'leaf',
            {
                'id': 'wrong-id',
                'parentId': None,
                'childrenIds': ['wrong-child'],
                'role': 'user',
                'timestamp': 999,
                '__loaded': True,
                'content': 'edited leaf',
                'annotation': {'rating': 1},
                'feedbackId': 'feedback-id',
            },
            db=session,
        )
        chat = await Chats.get_chat_by_id('chat', db=session, include_messages=False)
        messages = await ChatMessages.get_message_data_map_by_chat_id('chat', db=session)

    assert updated['id'] == 'leaf'
    assert updated['parentId'] == 'root'
    assert updated['childrenIds'] == []
    assert updated['role'] == 'assistant'
    assert updated['timestamp'] == 2
    assert updated['content'] == 'edited leaf'
    assert updated['annotation'] == {'rating': 1}
    assert updated['feedbackId'] == 'feedback-id'
    assert chat.chat['history']['currentId'] == 'leaf'
    assert 'messages' not in chat.chat['history']
    assert messages['root']['content'] == 'root'


@pytest.mark.asyncio
async def test_message_file_and_status_appends_handle_null_storage_without_hydrating_chat(session_factory):
    async with session_factory() as session:
        await insert_chat(session)
        await Chats.get_chat_by_id('chat', db=session, include_messages=False)

    await Chats.patch_message_by_chat_id_and_message_id('chat', 'leaf', {'files': None})
    files = await Chats.add_message_files_by_id_and_message_id(
        'chat',
        'leaf',
        [{'id': 'file-id', 'type': 'file'}],
    )
    files = await Chats.add_message_files_by_id_and_message_id(
        'chat',
        'leaf',
        [{'id': 'file-id', 'type': 'file'}],
    )
    compact = await Chats.add_message_status_to_chat_by_id_and_message_id(
        'chat',
        'leaf',
        {'done': True, 'description': 'complete'},
    )
    message = await Chats.get_message_by_id_and_message_id('chat', 'leaf')

    assert files == [{'id': 'file-id', 'type': 'file'}]
    assert message['files'] == files
    assert message['statusHistory'] == [{'done': True, 'description': 'complete'}]
    assert compact.chat['history']['currentId'] == 'leaf'
    assert 'messages' not in compact.chat['history']


@pytest.mark.asyncio
async def test_explicit_delete_updates_chat_and_message_rows_together(session_factory):
    async with session_factory() as session:
        await insert_chat(session)
        await Chats.get_chat_by_id('chat', db=session, include_messages=False)

        updated = await Chats.delete_message_from_chat_by_id_and_message_id('chat', 'leaf')
        messages = await ChatMessages.get_message_data_map_by_chat_id('chat', db=session)

    assert set(messages) == {'root'}
    assert updated.chat['history']['currentId'] == 'root'
    assert updated.current_message_id == 'root'
    assert updated.chat['history']['messages']['root']['childrenIds'] == []


@pytest.mark.asyncio
async def test_compact_delete_reparents_grandchildren_without_hydrating_all_messages(session_factory):
    branched = legacy_chat()
    branched['history'] = {
        'currentId': 'grandchild',
        'messages': {
            'root': {
                'id': 'root',
                'parentId': None,
                'childrenIds': ['target', 'sibling'],
                'role': 'user',
                'content': 'root',
                'timestamp': 1,
            },
            'target': {
                'id': 'target',
                'parentId': 'root',
                'childrenIds': ['child'],
                'role': 'assistant',
                'content': 'target',
                'timestamp': 2,
            },
            'child': {
                'id': 'child',
                'parentId': 'target',
                'childrenIds': ['grandchild'],
                'role': 'user',
                'content': 'child',
                'timestamp': 3,
            },
            'grandchild': {
                'id': 'grandchild',
                'parentId': 'child',
                'childrenIds': [],
                'role': 'assistant',
                'content': 'grandchild',
                'timestamp': 4,
            },
            'sibling': {
                'id': 'sibling',
                'parentId': 'root',
                'childrenIds': [],
                'role': 'assistant',
                'content': 'sibling',
                'timestamp': 5,
            },
        },
    }

    async with session_factory() as session:
        await insert_chat(session)
        row = await session.get(Chat, 'chat')
        row.chat = branched
        await session.commit()

        updated = await Chats.delete_message_from_chat_by_id_and_message_id(
            'chat',
            'target',
            include_messages=False,
            db=session,
        )
        messages = await ChatMessages.get_message_data_map_by_chat_id('chat', db=session)

    assert 'messages' not in updated.chat['history']
    assert updated.chat['history']['currentId'] == 'grandchild'
    assert set(messages) == {'root', 'grandchild', 'sibling'}
    assert messages['root']['childrenIds'] == ['sibling', 'grandchild']
    assert messages['grandchild']['parentId'] == 'root'
    assert messages['grandchild']['content'] == 'grandchild'


@pytest.mark.asyncio
async def test_empty_legacy_snapshot_removes_stale_normalized_rows(session_factory):
    async with session_factory() as session:
        await insert_chat(session)
        row = await session.get(Chat, 'chat')
        row.chat = {'title': 'Empty', 'history': {'currentId': None, 'messages': {}}}
        await session.commit()
        await ChatMessages.bulk_upsert_messages(
            'chat',
            'user',
            {
                'stale': {
                    'id': 'stale',
                    'parentId': None,
                    'childrenIds': [],
                    'role': 'user',
                    'content': 'stale',
                    'timestamp': 1,
                }
            },
            db=session,
        )

        compact = await Chats.get_chat_by_id('chat', db=session, include_messages=False)
        messages = await ChatMessages.get_message_data_map_by_chat_id('chat', db=session)

    assert messages == {}
    assert 'messages' not in compact.chat['history']


@pytest.mark.asyncio
async def test_shared_snapshot_rehydrates_compacted_chat(session_factory):
    async with session_factory() as session:
        await insert_chat(session)
        compact = await Chats.get_chat_by_id('chat', db=session, include_messages=False)
        assert 'messages' not in compact.chat['history']

        shared = await SharedChats.create('chat', 'user', db=session)

    assert shared.chat['history']['messages']['root']['content'] == 'root'
    assert shared.chat['history']['messages']['leaf']['content'] == 'leaf'
    assert shared.chat['messages'][-1]['id'] == 'leaf'


@pytest.mark.asyncio
async def test_import_writes_messages_under_new_chat_id(session_factory):
    async with session_factory() as session:
        await insert_chat(session)
        full = await Chats.get_chat_by_id('chat', db=session, include_messages=True)
        imported = await Chats.import_chats(
            'user',
            [ChatImportForm(chat={**full.chat, 'title': 'Imported'})],
            db=session,
        )
        imported_messages = await ChatMessages.get_message_data_map_by_chat_id(
            imported[0].id,
            db=session,
        )

    assert imported[0].id != 'chat'
    assert imported[0].chat['history']['messages']['root']['arbitrary'] == {'kept': True}
    assert set(imported_messages) == {'root', 'leaf'}


@pytest.mark.asyncio
async def test_normalization_failure_retains_legacy_window(session_factory, monkeypatch):
    async with session_factory() as session:
        await insert_chat(session)

        async def fail_replace(*args, **kwargs):
            raise RuntimeError('injected failure')

        monkeypatch.setattr(ChatMessages, 'replace_messages_in_session', fail_replace)
        chat = await Chats.get_chat_by_id('chat', db=session, include_messages=False)
        window = await Chats.get_chat_window(chat, limit=1, db=session)
        persisted = await session.get(Chat, 'chat')

    assert 'messages' in persisted.chat['history']
    assert window.chat['history']['messages']['root']['__loaded'] is False
    assert window.chat['history']['messages']['leaf']['content'] == 'leaf'
