"""Add partial index for pending knowledge files

Adds a partial expression index supporting
Files.get_pending_files_for_knowledge, whose query filters on
file.meta->data->knowledge_id and file.data->status. Without it, every
call (driven by the knowledge-base pending-files polling) performs a full
sequential scan of the file table, which is expensive because file.data
stores full extracted document content. The index keeps the lookup cost
proportional to the number of pending files rather than total content size.

Revision ID: b9f3c1d7a2e4
Revises: 461111b60977
Create Date: 2026-06-04 12:35:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = 'b9f3c1d7a2e4'
down_revision = '461111b60977'
branch_labels = None
depends_on = None

INDEX_NAME = 'idx_file_pending_knowledge'


def upgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name
    existing_indexes = {idx['name'] for idx in sa.inspect(conn).get_indexes('file')}

    if INDEX_NAME in existing_indexes:
        return

    if dialect == 'postgresql':
        op.execute(
            f'CREATE INDEX {INDEX_NAME} ON file '
            "((meta -> 'data' ->> 'knowledge_id')) "
            "WHERE (data ->> 'status') IN ('pending', 'processing')"
        )
    elif dialect == 'sqlite':
        op.execute(
            f'CREATE INDEX {INDEX_NAME} ON file '
            "(json_extract(meta, '$.data.knowledge_id')) "
            "WHERE json_extract(data, '$.status') IN ('pending', 'processing')"
        )


def downgrade():
    conn = op.get_bind()
    existing_indexes = {idx['name'] for idx in sa.inspect(conn).get_indexes('file')}

    if INDEX_NAME in existing_indexes:
        op.drop_index(INDEX_NAME, table_name='file')
