"""Clean null bytes stored in chats, shared chats and chat messages.

Revision ID: 5d2b7e9c4a10
Revises: 9f6c2a8d1b43
"""

import sqlalchemy as sa
from alembic import op

revision = '5d2b7e9c4a10'
down_revision = '9f6c2a8d1b43'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != 'postgresql':
        return

    for table, column in (
        ('chat', 'chat'),
        ('shared_chat', 'chat'),
        ('chat_message', 'content'),
        ('chat_message', 'usage'),
    ):
        # The lookbehind skips escaped backslashes, so a typed "\u0000" stays as text.
        conn.execute(
            sa.text(
                rf"""
                UPDATE {table}
                SET {column} = regexp_replace({column}::text, '(?<!\\)((?:\\\\)*)\\u0000', '\1', 'g')::json
                WHERE strpos({column}::text, '\u0000') > 0
                """
            )
        )


def downgrade() -> None:
    pass
