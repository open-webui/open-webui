"""Add bookmarked_assistants table

Revision ID: 1e79125856a7
Revises: c58abeccc1d1
Create Date: 2025-05-29 19:55:37.626582

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = '1e79125856a7'
down_revision: Union[str, None] = 'c58abeccc1d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bookmarked_assistants',
        sa.Column('user_id', sa.String(), sa.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('model_id', sa.String(), sa.ForeignKey('model.id', ondelete='CASCADE'), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table('bookmarked_assistants')
