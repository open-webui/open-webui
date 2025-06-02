"""Create user_model_bookmark and user_prompt_bookmark tables

Revision ID: 0941dda0ddf4
Revises: c58abeccc1d1
Create Date: 2025-06-02 17:35:56.174902

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = '0941dda0ddf4'
down_revision: Union[str, None] = 'c58abeccc1d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_model_bookmark',
        sa.Column('user_id', sa.String(), sa.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('model_id', sa.String(), sa.ForeignKey('model.id', ondelete='CASCADE'), primary_key=True),
    )

    op.create_table(
        'user_prompt_bookmark',
        sa.Column('user_id', sa.String(), sa.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('prompt_command', sa.String(), sa.ForeignKey('prompt.command', ondelete='CASCADE'), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table('user_model_bookmark')
    op.drop_table('user_prompt_bookmark')
