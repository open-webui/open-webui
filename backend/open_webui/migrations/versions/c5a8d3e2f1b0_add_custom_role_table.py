"""Add custom_role table

Revision ID: c5a8d3e2f1b0
Revises: 6d09d1bf1f23
Create Date: 2026-08-21 00:00:00.000000

Phase 1 of custom-role foundation: creates the registry table that backs
opaque ``custom:<uuid>`` references stored in the existing ``User.role`` column.

Invariants enforced at the application layer (not DB CHECK constraints):
- Reserved role names (admin, user, pending) cannot be inserted.
- Role names are stored normalized (lowercased, trimmed).
- Role IDs are immutable UUID4 primary keys.
- Permission documents are validated against a fixed server-owned catalog
  and normalised to a canonical full boolean tree (omissions are False).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from open_webui.migrations.util import get_existing_tables

# revision identifiers, used by Alembic.
revision: str = 'c5a8d3e2f1b0'
down_revision: Union[str, None] = '6d09d1bf1f23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing_tables = get_existing_tables()

    if 'custom_role' not in existing_tables:
        op.create_table(
            'custom_role',
            sa.Column('id', sa.Text(), nullable=False, primary_key=True),
            sa.Column('name', sa.Text(), nullable=False, unique=True),
            sa.Column('display_name', sa.Text(), nullable=False),
            sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
            # permissions: JSON tree validated against the server-owned
            # _PERMISSION_CATALOG.  Stored as TEXT via JSONField for
            # SQLite/Postgres portability.  Application validation
            # normalises omissions to False (fail-closed).
            sa.Column('permissions', sa.Text(), nullable=False, server_default='{}'),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
        )
        op.create_index(
            'ix_custom_role_name',
            'custom_role',
            ['name'],
            unique=True,
        )


def downgrade() -> None:
    existing_tables = get_existing_tables()
    if 'custom_role' in existing_tables:
        op.drop_index('ix_custom_role_name', table_name='custom_role')
        op.drop_table('custom_role')
