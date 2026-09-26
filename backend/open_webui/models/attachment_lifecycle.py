"""Reclaim chat file attachments when chats are permanently deleted.

The ``chat`` row is removed by the chat model layer, but the ``chat_file``
link rows, the corresponding ``file`` rows, and the physical uploads are
otherwise orphaned. SQLite does not honour the ``ondelete='CASCADE'``
declared on the FK columns while ``PRAGMA foreign_keys`` is off, so the links
and files must be removed explicitly.

The two helpers here are used in the same transaction as the chat deletion
(``detach_chat_files`` never commits) and after it commits
(``cleanup_orphan_storage`` performs best-effort physical/vector cleanup).
"""

from __future__ import annotations

import asyncio
import inspect as pyinspect
import logging
from dataclasses import dataclass
from typing import Awaitable, Callable, Iterable

from sqlalchemy import bindparam, inspect, text
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

# Tables that keep a ``file_id`` column referencing the ``file`` table. A file
# row is removed only when no row in any of these tables still references it.
_REFERENCE_TABLES = (
    'chat_file',
    'knowledge_file',
    'channel_file',
)


@dataclass(frozen=True)
class OrphanedFile:
    file_id: str
    path: str | None
    filename: str | None
    unlink_path: bool


async def _has_table(session: AsyncSession, table_name: str) -> bool:
    connection = await session.connection()
    return await connection.run_sync(lambda sync_connection: inspect(sync_connection).has_table(table_name))


async def detach_chat_files(
    session: AsyncSession,
    chat_ids: Iterable[str],
) -> list[OrphanedFile]:
    """Remove chat links and delete only file rows with no surviving owner.

    This function never commits. The caller must keep it in the same
    transaction as permanent chat deletion. Physical storage is deliberately
    handled only after that transaction commits.
    """

    ids = sorted({chat_id for chat_id in chat_ids if chat_id})
    if not ids:
        return []

    chat_ids_param = bindparam('chat_ids', expanding=True)
    linked = await session.execute(
        text('SELECT DISTINCT file_id FROM chat_file WHERE chat_id IN :chat_ids').bindparams(chat_ids_param),
        {'chat_ids': ids},
    )
    file_ids = sorted({row[0] for row in linked if row[0]})

    await session.execute(
        text('DELETE FROM chat_file WHERE chat_id IN :chat_ids').bindparams(chat_ids_param),
        {'chat_ids': ids},
    )
    if not file_ids:
        return []

    present_reference_tables = [name for name in _REFERENCE_TABLES if await _has_table(session, name)]
    removed: list[OrphanedFile] = []

    for file_id in file_ids:
        referenced = False
        for table_name in present_reference_tables:
            result = await session.execute(
                text(f'SELECT 1 FROM {table_name} WHERE file_id=:file_id LIMIT 1'),
                {'file_id': file_id},
            )
            if result.first() is not None:
                referenced = True
                break
        if referenced:
            continue

        row = (
            await session.execute(
                text('SELECT id,path,filename FROM file WHERE id=:file_id'),
                {'file_id': file_id},
            )
        ).first()
        if row is None:
            continue

        same_path_remains = False
        if row.path:
            same_path_remains = (
                await session.execute(
                    text('SELECT 1 FROM file WHERE path=:path AND id<>:file_id LIMIT 1'),
                    {'path': row.path, 'file_id': file_id},
                )
            ).first() is not None

        await session.execute(text('DELETE FROM file WHERE id=:file_id'), {'file_id': file_id})
        removed.append(
            OrphanedFile(
                file_id=file_id,
                path=row.path,
                filename=row.filename,
                unlink_path=bool(row.path) and not same_path_remains,
            )
        )

    return removed


async def _call(callback, value) -> None:
    result = callback(value)
    if pyinspect.isawaitable(result):
        await result


async def cleanup_orphan_storage(
    files: Iterable[OrphanedFile],
    *,
    delete_storage: Callable[[str], Awaitable[None] | None] | None = None,
    delete_vector: Callable[[str], Awaitable[None] | None] | None = None,
) -> None:
    """Best-effort post-commit cleanup for rows removed by detach_chat_files."""

    files = list(files)
    if not files:
        return

    if delete_storage is None:
        from open_webui.storage.provider import Storage

        async def delete_storage(path: str) -> None:
            await asyncio.to_thread(Storage.delete_file, path)

    if delete_vector is None:
        from open_webui.retrieval.vector.async_client import ASYNC_VECTOR_DB_CLIENT

        async def delete_vector(collection_name: str) -> None:
            await ASYNC_VECTOR_DB_CLIENT.delete(collection_name=collection_name)

    for file in files:
        if file.unlink_path and file.path:
            try:
                await _call(delete_storage, file.path)
            except Exception:
                log.exception('Post-commit storage cleanup failed for orphan file %s', file.file_id)
        try:
            await _call(delete_vector, f'file-{file.file_id}')
        except Exception:
            log.exception('Post-commit vector cleanup failed for orphan file %s', file.file_id)
