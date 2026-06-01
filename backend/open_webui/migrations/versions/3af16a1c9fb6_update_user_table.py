"""update user table

Revision ID: 3af16a1c9fb6
Revises: 018012973d35
Create Date: 2025-08-21 02:07:18.078283

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '3af16a1c9fb6'
down_revision: Union[str, None] = '018012973d35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    user_cols = {c['name'] for c in inspector.get_columns('user')}

    if 'username' not in user_cols:
        op.add_column('user', sa.Column('username', sa.String(length=50), nullable=True))
    if 'bio' not in user_cols:
        op.add_column('user', sa.Column('bio', sa.Text(), nullable=True))
    if 'gender' not in user_cols:
        op.add_column('user', sa.Column('gender', sa.Text(), nullable=True))
    if 'date_of_birth' not in user_cols:
        op.add_column('user', sa.Column('date_of_birth', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('user', 'username')
    op.drop_column('user', 'bio')
    op.drop_column('user', 'gender')
    op.drop_column('user', 'date_of_birth')
