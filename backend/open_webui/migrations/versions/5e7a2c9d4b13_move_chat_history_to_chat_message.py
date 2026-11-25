"""Keep chat messages only in chat_message rows

Revision ID: 5e7a2c9d4b13
Revises: d2f86c0b41ae
"""

import json
import logging
import math
import time
from collections.abc import Iterator
from typing import Any

import sqlalchemy as sa
from alembic import op

log = logging.getLogger(__name__)

revision = '5e7a2c9d4b13'
down_revision = 'd2f86c0b41ae'
branch_labels = None
depends_on = None

BATCH_SIZE = 100

DB_TO_JSON_KEY_MAP = {
    'parent_id': 'parentId',
    'model_id': 'model',
    'status_history': 'statusHistory',
    'context_summary': 'contextSummary',
    'created_at': 'timestamp',
}

chat_table = sa.table(
    'chat',
    sa.column('id', sa.Text()),
    sa.column('user_id', sa.Text()),
    sa.column('chat', sa.JSON()),
    sa.column('current_message_id', sa.Text()),
)

chat_message_table = sa.table(
    'chat_message',
    sa.column('id', sa.Text()),
    sa.column('chat_id', sa.Text()),
    sa.column('user_id', sa.Text()),
    sa.column('role', sa.Text()),
    sa.column('parent_id', sa.Text()),
    sa.column('content', sa.JSON()),
    sa.column('output', sa.JSON()),
    sa.column('model_id', sa.Text()),
    sa.column('files', sa.JSON()),
    sa.column('sources', sa.JSON()),
    sa.column('embeds', sa.JSON()),
    sa.column('meta', sa.JSON()),
    sa.column('done', sa.Boolean()),
    sa.column('status_history', sa.JSON()),
    sa.column('error', sa.JSON()),
    sa.column('usage', sa.JSON()),
    sa.column('context_summary', sa.Text()),
    sa.column('data', sa.JSON()),
    sa.column('created_at', sa.BigInteger()),
    sa.column('updated_at', sa.BigInteger()),
)


def _recorded_timestamp(value: Any) -> int | None:
    try:
        value = float(value)
        if value > 10_000_000_000:
            value /= 1000
        return int(value) if math.isfinite(value) and 1577836800 <= value <= time.time() + 86400 else None
    except (ValueError, TypeError, OverflowError):
        return None


def _history_messages(chat: dict) -> dict:
    """The chat's messages by id; a legacy message list becomes a chain, as the frontend reads it."""
    history = chat.get('history') if isinstance(chat.get('history'), dict) else {}
    messages = history.get('messages') if isinstance(history.get('messages'), dict) else None
    if messages is None and isinstance(chat.get('messages'), list):
        messages = {}
        parent_id = None
        for index, message in enumerate(chat['messages']):
            if isinstance(message, dict):
                message_id = str(message.get('id') or index)
                messages[message_id] = {**message, 'parentId': message.get('parentId') or parent_id}
                parent_id = message_id
    return {message_id: message for message_id, message in (messages or {}).items() if isinstance(message, dict)}


def _message_columns(message: dict) -> dict:
    """The message columns taken from the blob, without output and usage."""

    def as_text(*keys: str) -> str | None:
        value = next((message[key] for key in keys if message.get(key)), None)
        return value if isinstance(value, str) else None

    return {
        'role': as_text('role') or '',
        'parent_id': as_text('parent_id', 'parentId'),
        'content': message.get('content'),
        'model_id': as_text('model_id', 'model'),
        'files': message.get('files'),
        'sources': message.get('sources'),
        'embeds': message.get('embeds'),
        'meta': message.get('meta'),
        'done': message['done'] if isinstance(message.get('done'), bool) else None,
        'status_history': message.get('status_history') or message.get('statusHistory'),
        'error': message.get('error'),
        'context_summary': as_text('context_summary', 'contextSummary'),
    }


def _column_message(row: dict) -> dict:
    """The message a row reads back as, before its `data`."""
    message = {'id': row['id'].removeprefix(f'{row["chat_id"]}-')}
    for column, value in row.items():
        if column not in ('id', 'chat_id', 'updated_at', 'data') and value is not None:
            message[DB_TO_JSON_KEY_MAP.get(column, column)] = value
    if message.get('role') == '':
        del message['role']
    message.setdefault('content', '')
    return message


def _with_data(row: dict, message: dict) -> dict:
    """The row plus `data`: every message key its columns would read back differently."""
    from_columns = _column_message(row)
    data = {
        key: value
        for key, value in message.items()
        if key not in ('id', 'user_id', 'output') and (key not in from_columns or from_columns[key] != value)
    }
    return {**row, 'data': data}


def _without_nul(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace('\x00', '')
    if isinstance(value, list):
        return [_without_nul(item) for item in value]
    if isinstance(value, dict):
        return {_without_nul(key): _without_nul(item) for key, item in value.items()}
    return value


def _drop_saved_list_entries(chat_id: str, messages: dict, existing: dict) -> None:
    """Old lists give an entry no id of its own although its row exists; its children move to that row."""
    unclaimed = [row for row in existing.values() if row.id.removeprefix(f'{chat_id}-') not in messages]
    for message_id, message in list(messages.items()):
        if 'id' in message or f'{chat_id}-{message_id}' in existing:
            continue
        saved = next(
            (row for row in unclaimed if row.role == message.get('role') and row.content == message.get('content')),
            None,
        )
        if saved:
            unclaimed.remove(saved)
            del messages[message_id]
            for child in messages.values():
                if child.get('parentId') == message_id:
                    child['parentId'] = saved.id.removeprefix(f'{chat_id}-')


def _move_chat_history(
    conn: sa.Connection, chat_id: str, owner_id: str, chat: dict, current_message_id: str | None
) -> None:
    """Save the messages the chat's blob holds as its rows, then drop them from the blob."""
    messages = _history_messages(chat)
    columns = chat_message_table.c
    existing = {
        row.id: row
        for row in conn.execute(
            sa.select(
                columns.id,
                columns.user_id,
                columns.role,
                columns.content,
                columns.output,
                columns.usage,
                columns.created_at,
            ).where(columns.chat_id == chat_id)
        )
    }
    history = chat.get('history') if isinstance(chat.get('history'), dict) else {}
    # The web client used to delete messages by saving the chat without them, which left their rows.
    if isinstance(history.get('messages'), dict):
        deleted_ids = existing.keys() - {f'{chat_id}-{message_id}' for message_id in history['messages']}
        if deleted_ids:
            conn.execute(sa.delete(chat_message_table).where(columns.id.in_(deleted_ids)))
    else:
        _drop_saved_list_entries(chat_id, messages, existing)

    now = int(time.time())
    updates, inserts = [], []
    for message_id, message in messages.items():
        row_id = f'{chat_id}-{message_id}'
        created_at = _recorded_timestamp(message.get('timestamp'))
        author = message.get('user') if isinstance(message.get('user'), dict) else {}
        author_id = message.get('user_id') or author.get('id')
        if row_id in existing:
            stored = existing[row_id]
            row = {
                'id': row_id,
                'chat_id': chat_id,
                'user_id': author_id if isinstance(author_id, str) else stored.user_id,
                'output': stored.output,
                'usage': stored.usage,
                'created_at': created_at or stored.created_at,
                **_message_columns(message),
            }
            updates.append(_with_data(row, message))
        else:
            row = {
                'id': row_id,
                'chat_id': chat_id,
                'user_id': author_id if isinstance(author_id, str) else owner_id,
                'output': message.get('output'),
                # Raw usage could break the analytics casts.
                'usage': None,
                'created_at': created_at or 0,
                **_message_columns(message),
            }
            inserts.append(_with_data(row, message))
    kept_columns = ('id', 'chat_id', 'output', 'usage')
    updates = [
        {
            'row_id': row['id'],
            'updated_at': now,
            **{key: value for key, value in row.items() if key not in kept_columns},
        }
        for row in updates
    ]
    for row in inserts:
        row['updated_at'] = now
    if updates:
        conn.execute(
            sa.update(chat_message_table)
            .where(columns.id == sa.bindparam('row_id'))
            .values({key: sa.bindparam(key) for key in updates[0] if key != 'row_id'}),
            updates,
        )
    if inserts:
        conn.execute(sa.insert(chat_message_table), inserts)

    conn.execute(
        sa.update(chat_table)
        .where(chat_table.c.id == chat_id)
        .values(
            chat={key: value for key, value in chat.items() if key not in ('history', 'messages')},
            current_message_id=current_message_id or history.get('currentId'),
        )
    )


def _chat_blob(chat: Any) -> dict:
    """The stored chat as a dict; older versions saved some as a JSON string."""
    if isinstance(chat, str):
        try:
            chat = json.loads(chat)
        except ValueError:
            return {}
    return chat if isinstance(chat, dict) else {}


def _blob_has_history(chat: dict) -> bool:
    return 'history' in chat or 'messages' in chat


def _batches(conn: sa.Connection) -> Iterator[list[str]]:
    """Chat ids in primary key order, a batch at a time."""
    last_id = ''
    while True:
        chat_ids = (
            conn.execute(
                sa.select(chat_table.c.id).where(chat_table.c.id > last_id).order_by(chat_table.c.id).limit(BATCH_SIZE)
            )
            .scalars()
            .all()
        )
        if not chat_ids:
            return
        yield chat_ids
        last_id = chat_ids[-1]


def _rows_to_messages(rows: list[sa.Row]) -> dict:
    messages = {}
    for row in rows:
        message = {**_column_message(dict(row._mapping)), **(row.data or {})}
        messages[message['id']] = message
    child_ids_by_parent = {}
    for message_id, message in messages.items():
        if isinstance(message.get('parentId'), str):
            child_ids_by_parent.setdefault(message['parentId'], []).append(message_id)
    for message_id, message in messages.items():
        saved_ids = message.get('childrenIds') if isinstance(message.get('childrenIds'), list) else []
        saved_ids = [
            child_id
            for child_id in saved_ids
            if isinstance(child_id, str) and messages.get(child_id, {}).get('parentId', message_id) == message_id
        ]
        message['childrenIds'] = list(dict.fromkeys([*saved_ids, *child_ids_by_parent.get(message_id, [])]))
    return messages


def upgrade() -> None:
    conn = op.get_bind()
    if 'data' not in {column['name'] for column in sa.inspect(conn).get_columns('chat_message')}:
        op.add_column('chat_message', sa.Column('data', sa.JSON(), nullable=True))
    if conn.dialect.name == 'postgresql':
        # PostgreSQL's json operators refuse the \u0000 that older versions stored.
        chat_ids = conn.execute(
            sa.text('SELECT id FROM chat WHERE strpos(chat::text, :escape) > 0'), {'escape': '\\u0000'}
        ).scalars()
        for chat_id in chat_ids.all():
            raw = conn.execute(sa.text('SELECT chat::text FROM chat WHERE id = :id'), {'id': chat_id}).scalar_one()
            conn.execute(
                sa.update(chat_table)
                .where(chat_table.c.id == chat_id)
                .values(chat=_without_nul(_chat_blob(json.loads(raw))))
            )

    checked = 0
    with op.get_context().autocommit_block():
        for chat_ids in _batches(conn):
            conn.exec_driver_sql('BEGIN')
            for chat_id in chat_ids:
                owner_id, chat, current_message_id = conn.execute(
                    sa.select(chat_table.c.user_id, chat_table.c.chat, chat_table.c.current_message_id).where(
                        chat_table.c.id == chat_id
                    )
                ).one()
                chat = _chat_blob(chat)
                # Checked here, not in SQL: older SQLite refuses blobs holding NaN.
                if _blob_has_history(chat):
                    _move_chat_history(conn, chat_id, owner_id, chat, current_message_id)
            conn.exec_driver_sql('COMMIT')
            checked += len(chat_ids)
            log.info('Migration progress: moved the messages of %s chats into chat_message', checked)


def downgrade() -> None:
    conn = op.get_bind()
    with op.get_context().autocommit_block():
        for chat_ids in _batches(conn):
            conn.exec_driver_sql('BEGIN')
            for chat_id in chat_ids:
                chat, current_message_id = conn.execute(
                    sa.select(chat_table.c.chat, chat_table.c.current_message_id).where(chat_table.c.id == chat_id)
                ).one()
                chat = _chat_blob(chat)
                if _blob_has_history(chat):
                    continue
                rows = conn.execute(
                    sa.select(chat_message_table)
                    .where(chat_message_table.c.chat_id == chat_id)
                    .order_by(chat_message_table.c.created_at, chat_message_table.c.id)
                ).all()
                conn.execute(
                    sa.update(chat_table)
                    .where(chat_table.c.id == chat_id)
                    .values(
                        chat={
                            **chat,
                            'history': {'messages': _rows_to_messages(rows), 'currentId': current_message_id},
                        }
                    )
                )
            conn.exec_driver_sql('COMMIT')
    # Older code reads `done` as a boolean that defaults to true.
    op.execute(sa.update(chat_message_table).where(chat_message_table.c.done.is_(None)).values(done=True))
    op.drop_column('chat_message', 'data')
