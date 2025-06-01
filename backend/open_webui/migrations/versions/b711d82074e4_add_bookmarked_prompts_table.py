"""Add bookmarked_prompts table

Revision ID: b711d82074e4
Revises: 1e79125856a7
Create Date: 2025-06-01 19:42:43.873638

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = 'b711d82074e4'
down_revision: Union[str, None] = '1e79125856a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bookmarked_prompts',
        sa.Column('user_id', sa.String(), sa.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('prompt_command', sa.String(), sa.ForeignKey('prompt.command', ondelete='CASCADE'), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table('bookmarked_prompts')
