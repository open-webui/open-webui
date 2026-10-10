"""Add a PostgreSQL index for pending knowledge files."""

import logging

import sqlalchemy as sa
from alembic import op

revision = 'b8f2c6d91a04'
down_revision = 'f8c0e5b134cd'
branch_labels = None
depends_on = None

INDEX_NAME = 'file_pending_knowledge_idx'


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != 'postgresql':
        return

    try:
        with conn.begin_nested():
            op.create_index(
                INDEX_NAME,
                'file',
                [sa.text("((meta -> 'data') ->> 'knowledge_id')")],
                postgresql_where=sa.text("(data ->> 'status') IN ('pending', 'processing')"),
                if_not_exists=True,
            )
    except sa.exc.DBAPIError as exc:
        if exc.connection_invalidated:
            raise
        # Alembic records a skipped attempt too; it will not retry on every startup.
        logging.getLogger(__name__).warning('Skipped PostgreSQL index %s: %s', INDEX_NAME, exc)


def downgrade() -> None:
    if op.get_bind().dialect.name == 'postgresql':
        op.drop_index(INDEX_NAME, table_name='file', if_exists=True)
