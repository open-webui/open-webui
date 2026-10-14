"""add missing auth rows

Revision ID: 0bd252b206fb
Revises: c92da83b017f
"""

import sqlalchemy as sa
from alembic import op

revision = '0bd252b206fb'
down_revision = 'c92da83b017f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    user = sa.table('user', sa.column('id', sa.Text), sa.column('email', sa.Text))
    auth = sa.table(
        'auth',
        sa.column('id', sa.Text),
        sa.column('email', sa.Text),
        sa.column('password', sa.Text),
        sa.column('active', sa.Boolean),
    )
    # An empty password hash never verifies; existing credentials remain untouched.
    missing = sa.select(user.c.id, user.c.email, sa.literal(''), sa.true()).where(
        ~sa.exists().where(auth.c.id == user.c.id)
    )
    op.execute(auth.insert().from_select(['id', 'email', 'password', 'active'], missing))


def downgrade() -> None:
    # Backfilled accounts may have acquired credentials or MFA state since the upgrade.
    pass
