"""Add config table.

Revision ID: ca81bd47c050
Revises: 7e5b5dc7342b
Create Date: 2024-08-25 15:26:35.241684
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'ca81bd47c050'
down_revision: Union[str, None] = '7e5b5dc7342b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create a key-value config table with versioning."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if 'config' not in existing_tables:
        op.create_table(
            'config',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('data', sa.JSON(), nullable=False),
            sa.Column('version', sa.Integer, nullable=False),
            sa.Column(
                'created_at',
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                'updated_at',
                sa.DateTime(),
                nullable=True,
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
            ),
        )


def downgrade() -> None:
    """Drop the config table."""
    op.drop_table('config')
