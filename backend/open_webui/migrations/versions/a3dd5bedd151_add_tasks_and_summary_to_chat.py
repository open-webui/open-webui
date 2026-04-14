"""Add tasks and summary columns to chat table

Revision ID: a3dd5bedd151
Revises: b2c3d4e5f6a7
Create Date: 2026-03-29 22:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a3dd5bedd151'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('chat', sa.Column('tasks', sa.JSON(), nullable=True))
    op.add_column('chat', sa.Column('summary', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('chat', 'summary')
    op.drop_column('chat', 'tasks')
