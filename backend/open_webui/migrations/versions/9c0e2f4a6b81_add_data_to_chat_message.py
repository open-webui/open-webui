"""add lossless data to chat message

Revision ID: 9c0e2f4a6b81
Revises: 9a1b2c3d4e5f
Create Date: 2026-07-19 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '9c0e2f4a6b81'
down_revision: str | None = '9a1b2c3d4e5f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BATCH_SIZE = 1000
CHAT_BATCH_SIZE = 100

PROJECTION_TO_DATA_KEY = {
    'role': 'role',
    'parent_id': 'parentId',
    'children_ids': 'childrenIds',
    'content': 'content',
    'output': 'output',
    'model_id': 'model',
    'files': 'files',
    'sources': 'sources',
    'embeds': 'embeds',
    'meta': 'meta',
    'done': 'done',
    'status_history': 'statusHistory',
    'error': 'error',
    'usage': 'usage',
    'context_summary': 'contextSummary',
    'created_at': 'timestamp',
}


def _original_message_id(row_id: str, chat_id: str) -> str:
    prefix = f'{chat_id}-'
    return row_id[len(prefix) :] if row_id.startswith(prefix) else row_id


def _build_message_data(row) -> dict:
    values = row._mapping
    data = {'id': _original_message_id(values['id'], values['chat_id'])}

    for column_name, data_key in PROJECTION_TO_DATA_KEY.items():
        value = values[column_name]
        if value is not None:
            data[data_key] = value

    if values['usage'] is not None:
        data['info'] = {'usage': values['usage']}

    data.setdefault('content', '')
    return data


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {column['name'] for column in inspector.get_columns('chat_message')}

    if 'data' not in columns:
        op.add_column('chat_message', sa.Column('data', sa.JSON(), nullable=True))
    if 'children_ids' not in columns:
        op.add_column('chat_message', sa.Column('children_ids', sa.JSON(), nullable=True))

    chat_message = sa.table(
        'chat_message',
        sa.column('id', sa.Text()),
        sa.column('chat_id', sa.Text()),
        sa.column('role', sa.Text()),
        sa.column('parent_id', sa.Text()),
        sa.column('children_ids', sa.JSON()),
        sa.column('data', sa.JSON()),
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
        sa.column('created_at', sa.BigInteger()),
    )

    select_columns = [chat_message.c.id, chat_message.c.chat_id]
    select_columns.extend(getattr(chat_message.c, column_name) for column_name in PROJECTION_TO_DATA_KEY)
    result = conn.execute(
        sa.select(*select_columns)
        .where(chat_message.c.data.is_(None))
        .execution_options(yield_per=BATCH_SIZE, stream_results=True)
    )
    update_stmt = (
        sa.update(chat_message)
        .where(chat_message.c.id == sa.bindparam('message_row_id'))
        .values(data=sa.bindparam('message_data'))
    )

    for rows in result.partitions(BATCH_SIZE):
        conn.execute(
            update_stmt,
            [
                {
                    'message_row_id': row._mapping['id'],
                    'message_data': _build_message_data(row),
                }
                for row in rows
            ],
        )


def _json_value(value, default):
    if value is None:
        return default
    if isinstance(value, str):
        try:
            import json

            return json.loads(value)
        except (TypeError, ValueError):
            return default
    return value


def _active_branch(messages: dict[str, dict], current_id: str | None) -> list[dict]:
    branch = []
    visited = set()
    while current_id and current_id not in visited:
        visited.add(current_id)
        message = messages.get(current_id)
        if not isinstance(message, dict):
            break
        branch.append(message)
        current_id = message.get('parentId')
    branch.reverse()
    return branch


def _restore_compacted_chats(conn) -> None:  # noqa: C901
    inspector = sa.inspect(conn)
    if 'chat' not in inspector.get_table_names():
        return

    chat = sa.table(
        'chat',
        sa.column('id', sa.Text()),
        sa.column('chat', sa.JSON()),
    )
    chat_message = sa.table(
        'chat_message',
        sa.column('id', sa.Text()),
        sa.column('chat_id', sa.Text()),
        sa.column('parent_id', sa.Text()),
        sa.column('children_ids', sa.JSON()),
        sa.column('role', sa.Text()),
        sa.column('created_at', sa.BigInteger()),
        sa.column('data', sa.JSON()),
    )

    last_chat_id = None
    while True:
        stmt = sa.select(chat.c.id, chat.c.chat).order_by(chat.c.id).limit(CHAT_BATCH_SIZE)
        if last_chat_id is not None:
            stmt = stmt.where(chat.c.id > last_chat_id)
        chat_rows = conn.execute(stmt).all()
        if not chat_rows:
            break

        for chat_id, chat_data_value in chat_rows:
            chat_data = _json_value(chat_data_value, {})
            history = chat_data.get('history') if isinstance(chat_data, dict) else None
            storage = history.get('messageStorage') if isinstance(history, dict) else None
            if not isinstance(storage, dict) or storage.get('version') != 1 or 'messages' in history:
                continue

            rows = conn.execute(
                sa.select(
                    chat_message.c.id,
                    chat_message.c.parent_id,
                    chat_message.c.children_ids,
                    chat_message.c.role,
                    chat_message.c.created_at,
                    chat_message.c.data,
                )
                .where(chat_message.c.chat_id == chat_id)
                .order_by(chat_message.c.created_at, chat_message.c.id)
            ).all()

            prefix = f'{chat_id}-'
            messages = {}
            projected_children = {}
            fallback_children = {}
            for row_id, parent_id, children_ids, role, created_at, data_value in rows:
                message_id = row_id[len(prefix) :] if row_id.startswith(prefix) else row_id
                message = _json_value(data_value, {})
                message = dict(message) if isinstance(message, dict) else {}
                message['id'] = message_id
                message.setdefault('parentId', parent_id)
                message.setdefault('role', role)
                message.setdefault('timestamp', created_at)
                message.setdefault('content', '')
                messages[message_id] = message
                projected_children[message_id] = _json_value(children_ids, None)
                fallback_children[message_id] = []

            for message_id, message in messages.items():
                parent_id = message.get('parentId')
                if parent_id in fallback_children:
                    fallback_children[parent_id].append(message_id)

            for message_id, message in messages.items():
                ordered_children = projected_children[message_id]
                if not isinstance(ordered_children, list):
                    ordered_children = []
                children = [
                    child_id
                    for child_id in ordered_children
                    if child_id in messages and messages[child_id].get('parentId') == message_id
                ]
                children.extend(child_id for child_id in fallback_children[message_id] if child_id not in children)
                message['childrenIds'] = children

            history = dict(history)
            history.pop('messageStorage', None)
            history.pop('messageWindow', None)
            history['messages'] = messages
            restored_chat = dict(chat_data)
            restored_chat['history'] = history
            restored_chat['messages'] = _active_branch(messages, history.get('currentId'))
            conn.execute(sa.update(chat).where(chat.c.id == chat_id).values(chat=restored_chat))

        last_chat_id = chat_rows[-1][0]


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {column['name'] for column in inspector.get_columns('chat_message')}

    if 'data' in columns:
        _restore_compacted_chats(conn)

    if 'children_ids' in columns:
        op.drop_column('chat_message', 'children_ids')
    if 'data' in columns:
        op.drop_column('chat_message', 'data')
