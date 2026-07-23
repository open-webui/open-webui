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

BATCH_SIZE = 150


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('chat')]
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

    has_chat_message = 'chat_message' in inspector.get_table_names()
    result = conn.execute(
        sa.select(chat.c.id, chat.c.chat, chat.c.current_message_id).execution_options(
            yield_per=BATCH_SIZE,
            stream_results=True,
        )
    )

    while True:
        rows = result.fetchmany(BATCH_SIZE)
        if not rows:
            break

        batch_chat_ids: list[str] = []
        candidates_by_chat: dict[str, list[str]] = {}
        current_by_chat: dict[str, str | None] = {}
        json_messages_by_chat: dict[str, dict[str, dict]] = {}

        for row in rows:
            values = row._mapping
            chat_id = values['id']
            prefix = f'{chat_id}-'
            batch_chat_ids.append(chat_id)
            current_by_chat[chat_id] = values['current_message_id']

            chat_data = {}
            if isinstance(values['chat'], dict):
                chat_data = values['chat']
            elif isinstance(values['chat'], str):
                try:
                    parsed = json.loads(values['chat'])
                    chat_data = parsed if isinstance(parsed, dict) else {}
                except (TypeError, ValueError, json.JSONDecodeError):
                    pass

            history = chat_data.get('history') if isinstance(chat_data.get('history'), dict) else {}
            candidates_by_chat[chat_id] = []
            for candidate in (
                values['current_message_id'],
                history.get('currentId'),
                chat_data.get('currentId'),
                chat_data.get('branchPointMessageId'),
            ):
                if not isinstance(candidate, str) or not candidate:
                    continue
                candidate = candidate[len(prefix) :] if candidate.startswith(prefix) else candidate
                if candidate not in candidates_by_chat[chat_id]:
                    candidates_by_chat[chat_id].append(candidate)

            messages = history.get('messages') if isinstance(history.get('messages'), dict) else {}
            if not messages and isinstance(chat_data.get('messages'), list):
                messages = {
                    message['id']: message
                    for message in chat_data['messages']
                    if isinstance(message, dict) and message.get('id')
                }
            if messages:
                json_messages_by_chat[chat_id] = {
                    message_id: {
                        'parent_id': message.get('parentId') if isinstance(message, dict) else None,
                        'created_at': message.get('timestamp', 0) if isinstance(message, dict) else 0,
                    }
                    for message_id, message in messages.items()
                }

        resolved: dict[str, str] = {}

        if has_chat_message:
            candidate_ids = {
                f'{chat_id}-{candidate}'
                for chat_id, candidates in candidates_by_chat.items()
                for candidate in candidates
            }
            if candidate_ids:
                valid_by_chat: dict[str, set[str]] = {}
                for row in conn.execute(
                    sa.select(chat_message.c.chat_id, chat_message.c.id).where(
                        chat_message.c.chat_id.in_(batch_chat_ids),
                        chat_message.c.id.in_(candidate_ids),
                    )
                ):
                    values = row._mapping
                    chat_id = values['chat_id']
                    prefix = f'{chat_id}-'
                    message_id = values['id']
                    if message_id and message_id.startswith(prefix):
                        message_id = message_id[len(prefix) :]
                    if message_id:
                        valid_by_chat.setdefault(chat_id, set()).add(message_id)
                for chat_id, candidates in candidates_by_chat.items():
                    valid_ids = valid_by_chat.get(chat_id, set())
                    for candidate in candidates:
                        if candidate in valid_ids:
                            resolved[chat_id] = candidate
                            break

            unresolved_chat_ids = [chat_id for chat_id in batch_chat_ids if chat_id not in resolved]
            messages_by_chat: dict[str, dict[str, dict]] = {}
            if unresolved_chat_ids:
                for row in conn.execute(
                    sa.select(
                        chat_message.c.chat_id,
                        chat_message.c.id,
                        chat_message.c.parent_id,
                        chat_message.c.created_at,
                    ).where(chat_message.c.chat_id.in_(unresolved_chat_ids))
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

            for chat_id, messages in messages_by_chat.items():
                parent_ids = {
                    message['parent_id']
                    for message in messages.values()
                    if message.get('parent_id') in messages
                }
                leaf_ids = [message_id for message_id in messages if message_id not in parent_ids]
                resolved[chat_id] = max(
                    leaf_ids or list(messages),
                    key=lambda message_id: messages[message_id].get('created_at') or 0,
                )

        for chat_id in batch_chat_ids:
            if chat_id in resolved:
                continue

            messages = json_messages_by_chat.get(chat_id, {})
            valid_candidate = next(
                (candidate for candidate in candidates_by_chat[chat_id] if candidate in messages),
                None,
            )
            if valid_candidate:
                resolved[chat_id] = valid_candidate
            elif messages:
                parent_ids = {
                    message['parent_id']
                    for message in messages.values()
                    if message.get('parent_id') in messages
                }
                leaf_ids = [message_id for message_id in messages if message_id not in parent_ids]
                resolved[chat_id] = max(
                    leaf_ids or list(messages),
                    key=lambda message_id: messages[message_id].get('created_at') or 0,
                )

        updates = [
            {'chat_id': chat_id, 'current_message_id': message_id}
            for chat_id, message_id in resolved.items()
            if message_id and message_id != current_by_chat.get(chat_id)
        ]
        if updates:
            conn.execute(
                sa.update(chat)
                .where(chat.c.id == sa.bindparam('update_chat_id'))
                .values(current_message_id=sa.bindparam('update_current_message_id')),
                [
                    {
                        'update_chat_id': row['chat_id'],
                        'update_current_message_id': row['current_message_id'],
                    }
                    for row in updates
                ],
            )


def downgrade() -> None:
    op.drop_column('chat', 'current_message_id')
