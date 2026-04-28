"""add last_read_at to chat

Revision ID: b7c8d9e0f1a2
Revises: d4e5f6a7b8c9
Create Date: 2026-04-01 04:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7c8d9e0f1a2'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='chat' AND column_name='last_read_at'"
    ))
    if result.fetchone() is None:
        op.add_column('chat', sa.Column('last_read_at', sa.BigInteger(), nullable=True))
        op.execute('UPDATE chat SET last_read_at = updated_at')


def downgrade():
    op.drop_column('chat', 'last_read_at')
