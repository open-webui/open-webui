"""Add is_pinned to note table

Revision ID: e2f3a4b5c6d7
Revises: b7c8d9e0f1a2
Create Date: 2026-04-14 22:00:00.000000

Note: Upstream originally used revision ID 'e1f2a3b4c5d6' which collided with
our local merge-heads migration of the same ID. Renamed to e2f3a4b5c6d7 during
the v0.9.5 merge to avoid the collision.
"""

from alembic import op
import sqlalchemy as sa

revision = 'e2f3a4b5c6d7'
down_revision = 'b7c8d9e0f1a2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('note', sa.Column('is_pinned', sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column('note', 'is_pinned')
