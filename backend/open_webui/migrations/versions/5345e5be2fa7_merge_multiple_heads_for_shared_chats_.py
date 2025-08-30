"""Merge multiple heads for shared-chats-page

Revision ID: 5345e5be2fa7
Revises: 3af16a1c9fb6, e32a8e081b4a
Create Date: 2025-08-31 08:59:23.147806

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = '5345e5be2fa7'
down_revision: Union[str, None] = ('3af16a1c9fb6', 'e32a8e081b4a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('chat', sa.Column('is_snapshot', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('chat', sa.Column('snapshot_chat', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('chat', 'snapshot_chat')
    op.drop_column('chat', 'is_snapshot')