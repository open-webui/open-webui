"""add Responses status to chat message

Revision ID: f7d8e9a0b1c2
Revises: e2a43c7819b6
Create Date: 2026-09-04 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'f7d8e9a0b1c2'
down_revision: str | None = 'e2a43c7819b6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('chat_message', sa.Column('response_status', sa.Text(), nullable=True))
    op.add_column('chat_message', sa.Column('incomplete_details', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('chat_message', 'incomplete_details')
    op.drop_column('chat_message', 'response_status')
