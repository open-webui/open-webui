"""
Regression test for https://github.com/open-webui/open-webui/issues/32646

"Archive All Chats" marks every chat as archived. Like archiving a single chat
(since 7cf07b7e9), it must also remove the chats from their sidebar folders,
otherwise deleting a folder permanently deletes the archived chats in it.
"""

import time

from open_webui.internal.db import get_async_db
from open_webui.models.chats import Chat, Chats
from open_webui.models.folders import Folder

USER_ID = 'user-1'
FOLDER_ID = 'folder-1'
CHAT_ID = 'chat-1'


def _make_chat_row(chat_id: str, folder_id: str | None) -> Chat:
    now = int(time.time())
    return Chat(
        id=chat_id,
        user_id=USER_ID,
        title='Test chat',
        chat={'history': {'messages': {}}},
        folder_id=folder_id,
        meta={},
        created_at=now,
        updated_at=now,
        last_read_at=now,
    )


async def _insert(row):
    async with get_async_db() as session:
        session.add(row)
        await session.commit()


async def test_archive_all_chats_removes_chats_from_folders():
    await _insert(Folder(id=FOLDER_ID, user_id=USER_ID, name='F', created_at=0, updated_at=0))
    await _insert(_make_chat_row(CHAT_ID, FOLDER_ID))

    result = await Chats.archive_all_chats_by_user_id(USER_ID)
    assert result is True

    async with get_async_db() as session:
        chat = await session.get(Chat, CHAT_ID)
    assert chat is not None
    assert chat.archived is True
    # The chat must no longer belong to the folder, the same way a single-chat
    # archive detaches it (toggle_chat_archive_by_id sets folder_id = None).
    assert chat.folder_id is None


async def test_delete_folder_after_archive_all_keeps_archived_chats():
    await _insert(Folder(id=FOLDER_ID, user_id=USER_ID, name='F', created_at=0, updated_at=0))
    await _insert(_make_chat_row(CHAT_ID, FOLDER_ID))

    await Chats.archive_all_chats_by_user_id(USER_ID)
    # Deleting the folder removes every chat still assigned to it.
    await Chats.delete_chats_by_user_id_and_folder_id(USER_ID, FOLDER_ID)

    async with get_async_db() as session:
        chat = await session.get(Chat, CHAT_ID)
    assert chat is not None, 'archived chat must survive folder deletion'
    assert chat.archived is True
