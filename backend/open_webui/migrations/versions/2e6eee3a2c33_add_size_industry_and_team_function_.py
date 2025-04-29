"""Add size, industry and team function columns to company table

Revision ID: 2e6eee3a2c33
Revises: f6829f0e06bf
Create Date: 2025-04-29 16:46:09.236955

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = '2e6eee3a2c33'
down_revision: Union[str, None] = 'f6829f0e06bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('company', sa.Column('size', sa.Integer(), nullable=True))
    op.add_column('company', sa.Column('industry', sa.String(), nullable=True))
    op.add_column('company', sa.Column('team_function', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('company', 'size')
    op.drop_column('company', 'industry')
    op.drop_column('company', 'team_function')

