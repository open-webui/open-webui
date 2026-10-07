"""add MFA state and account session stamps

Revision ID: a7d3e9f2b641
Revises: d4c1a8e37b62
"""

import sqlalchemy as sa
from alembic import op

revision = 'a7d3e9f2b641'
down_revision = 'd4c1a8e37b62'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('auth', sa.Column('mfa', sa.JSON(), nullable=True))
    op.add_column('auth', sa.Column('session_stamp', sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('auth') as batch:
        batch.drop_column('session_stamp')
        batch.drop_column('mfa')
