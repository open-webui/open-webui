"""Drop redundant chat_message single-column indexes

Revision ID: e2b7a4c91f05
Revises: d4c1a8e37b62
Create Date: 2026-08-03 16:22:10.581294

"""

import sqlalchemy as sa
from alembic import op

revision = 'e2b7a4c91f05'
down_revision = 'd4c1a8e37b62'
branch_labels = None
depends_on = None

# each is a strict prefix of a composite index that serves the same lookups
REDUNDANT_INDEXES = {
    'ix_chat_message_chat_id': 'chat_id',
    'ix_chat_message_user_id': 'user_id',
    'ix_chat_message_model_id': 'model_id',
}


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_indexes = {idx['name'] for idx in inspector.get_indexes('chat_message')}

    # 8452d01d26d7 early-returns on pre-existing tables, so the indexes may be absent
    for name in REDUNDANT_INDEXES:
        if name in existing_indexes:
            op.drop_index(name, table_name='chat_message')


def downgrade():
    for name, column in REDUNDANT_INDEXES.items():
        op.create_index(name, 'chat_message', [column])
