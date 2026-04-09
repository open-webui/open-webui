"""add sw_chapter table

Revision ID: e5378ca1825b
Revises: ec1fee5202dc
Create Date: 2026-04-09 15:06:14.611107

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = 'e5378ca1825b'
down_revision: Union[str, None] = 'ec1fee5202dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sw_chapter',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('novel_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('order', sa.BigInteger(), nullable=False, default=0),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('sw_chapter')
