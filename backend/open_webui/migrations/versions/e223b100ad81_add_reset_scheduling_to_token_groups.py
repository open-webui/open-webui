"""add_reset_scheduling_to_token_groups

Revision ID: e223b100ad81
Revises: 3ff60f68c4f4
Create Date: 2025-08-08 21:03:04.785726

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = 'e223b100ad81'
down_revision: Union[str, None] = '3ff60f68c4f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add scheduling columns to token_group table
    op.add_column('token_group', sa.Column('reset_time', sa.Text(), nullable=True, default='00:00'))
    op.add_column('token_group', sa.Column('reset_timezone', sa.Text(), nullable=True, default='UTC'))
    
    # Add last_reset_timestamp column to token_usage table for precise scheduling
    op.add_column('token_usage', sa.Column('last_reset_timestamp', sa.BigInteger(), nullable=True))


def downgrade() -> None:
    # Remove scheduling columns
    op.drop_column('token_group', 'reset_timezone')
    op.drop_column('token_group', 'reset_time')
    op.drop_column('token_usage', 'last_reset_timestamp')
