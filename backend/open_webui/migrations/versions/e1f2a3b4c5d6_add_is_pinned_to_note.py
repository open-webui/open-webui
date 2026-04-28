"""Add is_pinned to note table

Revision ID: e1f2a3b4c5d6
Revises: b7c8d9e0f1a2
Create Date: 2026-04-14 22:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = 'e1f2a3b4c5d6'
down_revision = 'b7c8d9e0f1a2'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='note' AND column_name='is_pinned'"
    ))
    if result.fetchone() is None:
        op.add_column('note', sa.Column('is_pinned', sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column('note', 'is_pinned')
