"""add context summary to chat message

Revision ID: 4c5ce3d2f27f
Revises: 3ff2c63645b8
Create Date: 2026-06-18 23:48:08.310063

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c5ce3d2f27f'
down_revision: Union[str, None] = '3ff2c63645b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {column['name'] for column in inspector.get_columns('chat_message')}

    if 'context_summary' not in columns:
        op.add_column('chat_message', sa.Column('context_summary', sa.Text(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {column['name'] for column in inspector.get_columns('chat_message')}

    if 'context_summary' in columns:
        op.drop_column('chat_message', 'context_summary')
