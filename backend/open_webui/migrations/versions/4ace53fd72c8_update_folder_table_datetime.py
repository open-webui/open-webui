"""Update folder table and change DateTime to BigInteger for timestamp fields

Revision ID: 4ace53fd72c8
Revises: af906e964978
Create Date: 2024-10-23 03:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = '4ace53fd72c8'
down_revision = 'af906e964978'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {c['name']: c for c in inspector.get_columns('folder')}

    created_at_col = columns.get('created_at')
    if not created_at_col:
        return

    # Only convert if still DateTime — skip if already BigInteger
    if isinstance(created_at_col['type'], sa.BigInteger):
        return

    # Perform safe alterations using batch operation
    with op.batch_alter_table('folder', schema=None) as batch_op:
        # Step 1: Remove server defaults for created_at and updated_at
        batch_op.alter_column(
            'created_at',
            server_default=None,  # Removing server default
        )
        batch_op.alter_column(
            'updated_at',
            server_default=None,  # Removing server default
        )

        # Step 2: Change the column types to BigInteger for created_at
        batch_op.alter_column(
            'created_at',
            type_=sa.BigInteger(),
            existing_type=sa.DateTime(),
            existing_nullable=False,
            postgresql_using='extract(epoch from created_at)::bigint',  # Conversion for PostgreSQL
        )

        # Change the column types to BigInteger for updated_at
        batch_op.alter_column(
            'updated_at',
            type_=sa.BigInteger(),
            existing_type=sa.DateTime(),
            existing_nullable=False,
            postgresql_using='extract(epoch from updated_at)::bigint',  # Conversion for PostgreSQL
        )


def downgrade():
    # Convert columns back to DateTime and restore defaults. Mirrors the
    # upgrade's postgresql_using cast — without it, Postgres can't
    # auto-cast BigInteger → timestamp and aborts with DatatypeMismatch.
    with op.batch_alter_table('folder', schema=None) as batch_op:
        batch_op.alter_column(
            'created_at',
            type_=sa.DateTime(),
            existing_type=sa.BigInteger(),
            existing_nullable=False,
            server_default=sa.func.now(),
            postgresql_using='to_timestamp(created_at)::timestamp without time zone',
        )
        batch_op.alter_column(
            'updated_at',
            type_=sa.DateTime(),
            existing_type=sa.BigInteger(),
            existing_nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            postgresql_using='to_timestamp(updated_at)::timestamp without time zone',
        )
