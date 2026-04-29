"""Add chat sidebar default index

Revision ID: 6f0d1234abcd
Revises: 56359461a091
Create Date: 2026-04-29 18:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = '6f0d1234abcd'
down_revision = '56359461a091'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        'chat_sidebar_default_idx',
        'chat',
        ['user_id', sa.text('updated_at DESC'), 'id'],
        sqlite_where=sa.text(
            'folder_id IS NULL AND archived = 0 AND (pinned = 0 OR pinned IS NULL)'
        ),
    )


def downgrade():
    op.drop_index('chat_sidebar_default_idx', table_name='chat')
