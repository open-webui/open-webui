"""Add first_name, last_name columns to user table

Revision ID: 05d6d7fcdffe
Revises: 9ca0154d9246
Create Date: 2025-04-22 13:08:18.220772

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = '05d6d7fcdffe'
down_revision: Union[str, None] = '9ca0154d9246'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('user', 'name')
    op.add_column('user', sa.Column('first_name', sa.String(length=255), nullable=False, server_default='SYSTEM'))
    op.add_column('user', sa.Column('last_name', sa.String(length=255), nullable=False, server_default='SYSTEM'))

def downgrade() -> None:
    op.drop_column('user', 'first_name')
    op.drop_column('user', 'last_name')
