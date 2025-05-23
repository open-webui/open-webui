"""Add bookmarked flag to model and prompt tables

Revision ID: c58abeccc1d1
Revises: a5c7d9e1f2b3
Create Date: 2025-05-23 14:49:45.384919

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = 'c58abeccc1d1'
down_revision: Union[str, None] = 'a5c7d9e1f2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('prompt', sa.Column('bookmarked', sa.Boolean(), nullable=True))
    op.add_column('model', sa.Column('bookmarked', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('prompt', 'bookmarked')
    op.drop_column('model', 'bookmarked')

