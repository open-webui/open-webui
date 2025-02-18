"""Create completion table

Revision ID: 7bd38c980997
Revises: a3117163d6ce
Create Date: 2025-02-18 14:22:48.782795

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = '7bd38c980997'
down_revision: Union[str, None] = 'a3117163d6ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'completion',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('chat_id', sa.String(), nullable=True),
        sa.Column('model', sa.Text(), nullable=True),
        sa.Column('credits_used', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='SET NULL')
    )


def downgrade() -> None:
    op.drop_table('completion')
