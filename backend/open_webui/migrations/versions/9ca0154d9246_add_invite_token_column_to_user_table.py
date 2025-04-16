"""Add invite_token column to user table

Revision ID: 9ca0154d9246
Revises: 8bc701296ffa
Create Date: 2025-04-16 10:52:06.269215

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9ca0154d9246'
down_revision: Union[str, None] = '8bc701296ffa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user', sa.Column('invite_token', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('user', 'invite_token')

