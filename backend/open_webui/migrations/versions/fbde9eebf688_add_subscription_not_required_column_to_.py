"""Add subscription_not_required column to company table

Revision ID: fbde9eebf688
Revises: c58abeccc1d1
Create Date: 2025-06-03 20:49:37.175519

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = 'fbde9eebf688'
down_revision: Union[str, None] = 'c58abeccc1d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('company', sa.Column('subscription_not_required', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('company', 'subscription_not_required')
