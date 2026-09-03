"""add response id to chat message

Revision ID: e2a43c7819b6
Revises: d4c1a8e37b62
Create Date: 2026-09-03 00:00:00.000000

"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'e2a43c7819b6'
down_revision: str | None = 'd4c1a8e37b62'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _iter_response_id_updates(conn, chat):
    for chat_id, chat_data in conn.execute(sa.select(chat.c.id, chat.c.chat)):
        if isinstance(chat_data, str):
            try:
                chat_data = json.loads(chat_data)
            except (TypeError, ValueError):
                continue
        if not isinstance(chat_data, dict):
            continue

        messages = chat_data.get('history', {}).get('messages', {})
        if not isinstance(messages, dict):
            continue

        for message_id, message in messages.items():
            if not isinstance(message, dict):
                continue
            response_id = message.get('responseId') or message.get('response_id')
            if isinstance(response_id, str) and response_id:
                yield {
                    'message_row_id': f'{chat_id}-{message_id}',
                    'response_id_value': response_id,
                }


def upgrade() -> None:
    op.add_column('chat_message', sa.Column('response_id', sa.Text(), nullable=True))

    conn = op.get_bind()
    chat = sa.table(
        'chat',
        sa.column('id', sa.Text()),
        sa.column('chat', sa.JSON()),
    )
    chat_message = sa.table(
        'chat_message',
        sa.column('id', sa.Text()),
        sa.column('response_id', sa.Text()),
    )
    update_statement = (
        chat_message.update()
        .where(chat_message.c.id == sa.bindparam('message_row_id'))
        .values(response_id=sa.bindparam('response_id_value'))
    )

    updates = []
    for update in _iter_response_id_updates(conn, chat):
        updates.append(update)
        if len(updates) >= 1000:
            conn.execute(update_statement, updates)
            updates.clear()

    if updates:
        conn.execute(update_statement, updates)


def downgrade() -> None:
    op.drop_column('chat_message', 'response_id')
