"""add embedding status to knowledge_file

Adds per-(knowledge_base, file) embedding tracking so ingestion can upload
first and embed asynchronously in a durable worker:
  - status: 'pending' | 'processing' | 'completed' | 'failed'
  - error:  failure detail for the 'failed' state

Existing link rows are backfilled to 'completed' — a row only ever existed
before this change once a file was successfully embedded/linked, so they
must not be re-processed.

Revision ID: a1b2c3d4e5f6
Revises: 461111b60977
Create Date: 2026-06-21 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '461111b60977'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'knowledge_file' not in set(inspector.get_table_names()):
        return

    existing_columns = {c['name'] for c in inspector.get_columns('knowledge_file')}

    with op.batch_alter_table('knowledge_file') as batch_op:
        if 'status' not in existing_columns:
            batch_op.add_column(sa.Column('status', sa.Text(), nullable=True))
        if 'error' not in existing_columns:
            batch_op.add_column(sa.Column('error', sa.Text(), nullable=True))

    # Backfill: any pre-existing link was already successfully embedded.
    conn.execute(
        sa.text("UPDATE knowledge_file SET status = 'completed' WHERE status IS NULL")
    )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'knowledge_file' not in set(inspector.get_table_names()):
        return

    existing_columns = {c['name'] for c in inspector.get_columns('knowledge_file')}
    with op.batch_alter_table('knowledge_file') as batch_op:
        if 'error' in existing_columns:
            batch_op.drop_column('error')
        if 'status' in existing_columns:
            batch_op.drop_column('status')
