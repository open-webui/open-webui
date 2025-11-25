"""add_window_duration_to_token_groups

Revision ID: f334c211be92
Revises: e223b100ad81
Create Date: 2025-11-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = 'f334c211be92'
down_revision: Union[str, None] = 'e223b100ad81'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add window_duration column to token_group table
    # flexible unit, implies seconds if not specified otherwise by UI, but defined as BigInteger
    op.add_column('token_group', sa.Column('window_duration', sa.BigInteger(), nullable=True))


def downgrade() -> None:
    # Remove window_duration column
    op.drop_column('token_group', 'window_duration')
