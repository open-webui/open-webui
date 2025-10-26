"""add_last_reset_date_to_token_usage

Revision ID: 3ff60f68c4f4
Revises: 10vr9xyets5m
Create Date: 2025-08-08 17:00:02.225386

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = '3ff60f68c4f4'
down_revision: Union[str, None] = '10vr9xyets5m'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add last_reset_date column to track when tokens were last reset (for daily limits)
    op.add_column('token_usage', sa.Column('last_reset_date', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove last_reset_date column
    op.drop_column('token_usage', 'last_reset_date')
