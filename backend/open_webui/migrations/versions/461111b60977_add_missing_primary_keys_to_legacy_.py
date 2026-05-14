"""add missing primary keys to legacy peewee tables

Revision ID: 461111b60977
Revises: 3c9b0ca343fd
Create Date: 2026-05-14 04:38:14.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '461111b60977'
down_revision: Union[str, None] = '3c9b0ca343fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables bootstrapped by the old Peewee migration layer that may have
# UNIQUE(id) but no PRIMARY KEY constraint.  Fresh Alembic installs
# already have correct PKs from 7e5b5dc7342b_init.py.
LEGACY_TABLES = [
    'auth', 'chat', 'chatidtag', 'document', 'file',
    'function', 'memory', 'model', 'prompt', 'tag', 'tool', 'user',
]


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    for table_name in LEGACY_TABLES:
        if table_name not in existing_tables:
            continue

        pk = inspector.get_pk_constraint(table_name)
        pk_cols = pk.get('constrained_columns', [])

        # Already has a proper PK on 'id' — nothing to do
        if pk_cols == ['id']:
            continue

        # Check that an 'id' column actually exists
        columns = {c['name'] for c in inspector.get_columns(table_name)}
        if 'id' not in columns:
            continue

        print(f"Promoting UNIQUE(id) → PRIMARY KEY for '{table_name}'")

        with op.batch_alter_table(table_name) as batch_op:
            # Drop existing PK if any (e.g. on wrong column)
            if pk_cols and pk.get('name'):
                batch_op.drop_constraint(pk['name'], type_='primary')

            batch_op.create_primary_key(f'pk_{table_name}_id', ['id'])


def downgrade() -> None:
    # Downgrade is a no-op — we don't want to remove PKs
    pass
