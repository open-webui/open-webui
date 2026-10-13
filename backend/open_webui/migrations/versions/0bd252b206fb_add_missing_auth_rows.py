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

_user = sa.table('user', sa.column('id', sa.Text), sa.column('email', sa.Text))
_auth = sa.table(
    'auth',
    sa.column('id', sa.Text),
    sa.column('email', sa.Text),
    sa.column('password', sa.Text),
    sa.column('active', sa.Boolean),
)


def upgrade() -> None:
    # An empty password never verifies, so these accounts stay SSO-only.
    users_without_auth = sa.select(_user.c.id, _user.c.email, sa.literal_column("''"), sa.true()).where(
        ~sa.exists().where(_auth.c.id == _user.c.id)
    )
    op.execute(_auth.insert().from_select(['id', 'email', 'password', 'active'], users_without_auth))


def downgrade() -> None:
    pass
