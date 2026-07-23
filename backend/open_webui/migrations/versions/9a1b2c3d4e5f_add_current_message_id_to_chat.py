"""add current_message_id to chat

Revision ID: 9a1b2c3d4e5f
Revises: 856c5b02fb54
Create Date: 2026-07-23 00:00:00.000000

"""

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '9a1b2c3d4e5f'
down_revision: Union[str, None] = '856c5b02fb54'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    columns = [col['name'] for col in sa.inspect(conn).get_columns('chat')]
    if 'current_message_id' not in columns:
        op.add_column('chat', sa.Column('current_message_id', sa.Text(), nullable=True))

    chat = sa.table(
        'chat',
        sa.column('id', sa.String()),
        sa.column('chat', sa.Text()),
        sa.column('current_message_id', sa.Text()),
    )
    chat_message = sa.table(
        'chat_message',
        sa.column('id', sa.Text()),
        sa.column('chat_id', sa.Text()),
        sa.column('parent_id', sa.Text()),
        sa.column('created_at', sa.BigInteger()),
    )

    messages_by_chat: dict[str, dict[str, dict]] = {}
    for row in conn.execute(
        sa.select(
            chat_message.c.chat_id,
            chat_message.c.id,
            chat_message.c.parent_id,
            chat_message.c.created_at,
        )
    ):
        values = row._mapping
        chat_id = values['chat_id']
        prefix = f'{chat_id}-'
        message_id = values['id']
        if message_id and message_id.startswith(prefix):
            message_id = message_id[len(prefix) :]
        if not message_id:
            continue
        parent_id = values['parent_id']
        if parent_id and parent_id.startswith(prefix):
            parent_id = parent_id[len(prefix) :]
        messages_by_chat.setdefault(chat_id, {})[message_id] = {
            'parent_id': parent_id,
            'created_at': values['created_at'] or 0,
        }

    for row in conn.execute(sa.select(chat.c.id, chat.c.chat, chat.c.current_message_id)):
        values = row._mapping
        chat_id = values['id']
        prefix = f'{chat_id}-'
        chat_messages = messages_by_chat.get(chat_id, {})

        chat_data = {}
        if isinstance(values['chat'], dict):
            chat_data = values['chat']
        elif isinstance(values['chat'], str):
            try:
                parsed = json.loads(values['chat'])
                chat_data = parsed if isinstance(parsed, dict) else {}
            except (TypeError, ValueError, json.JSONDecodeError):
                chat_data = {}

        history = chat_data.get('history') if isinstance(chat_data.get('history'), dict) else {}
        messages = history.get('messages') if isinstance(history.get('messages'), dict) else {}
        if not messages and isinstance(chat_data.get('messages'), list):
            messages = {
                message['id']: message
                for message in chat_data['messages']
                if isinstance(message, dict) and message.get('id')
            }
        json_messages = {
            message_id: {
                'parent_id': message.get('parentId') if isinstance(message, dict) else None,
                'created_at': message.get('timestamp', 0) if isinstance(message, dict) else 0,
            }
            for message_id, message in messages.items()
        }
        available_messages = chat_messages or json_messages
        candidates = [
            values['current_message_id'],
            history.get('currentId'),
            chat_data.get('currentId'),
            chat_data.get('branchPointMessageId'),
        ]

        current_message_id = next(
            (
                candidate[len(prefix) :] if candidate.startswith(prefix) else candidate
                for candidate in candidates
                if candidate
                and (
                    not available_messages
                    or (candidate[len(prefix) :] if candidate.startswith(prefix) else candidate) in available_messages
                )
            ),
            None,
        )

        if not current_message_id and available_messages:
            parent_ids = {
                message['parent_id']
                for message in available_messages.values()
                if message.get('parent_id') in available_messages
            }
            leaf_ids = [message_id for message_id in available_messages if message_id not in parent_ids]
            current_message_id = max(
                leaf_ids or list(available_messages),
                key=lambda message_id: available_messages[message_id].get('created_at') or 0,
            )

        if current_message_id and current_message_id != values['current_message_id']:
            conn.execute(
                sa.update(chat)
                .where(chat.c.id == chat_id)
                .values(current_message_id=current_message_id)
            )


def downgrade() -> None:
    op.drop_column('chat', 'current_message_id')
