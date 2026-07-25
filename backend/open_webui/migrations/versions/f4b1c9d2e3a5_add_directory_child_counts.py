"""add immediate-children counts to knowledge_directory

Adds a ``meta`` JSON column storing cached counts of a directory's *immediate*
children: ``{'file_count': int, 'directory_count': int}``. Backfills existing
rows from the source of truth (knowledge_file / knowledge_directory).

Revision ID: f4b1c9d2e3a5
Revises: 7e4d1a9c2b83
Create Date: 2026-07-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f4b1c9d2e3a5'
down_revision: Union[str, None] = '7e4d1a9c2b83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('knowledge_directory', sa.Column('meta', sa.JSON(), nullable=True))

    # Backfill immediate-children counts for any pre-existing directories.
    bind = op.get_bind()
    directory = sa.table(
        'knowledge_directory',
        sa.column('id', sa.String),
        sa.column('meta', sa.JSON),
    )
    rows = bind.execute(sa.text('SELECT id FROM knowledge_directory')).fetchall()
    for (dir_id,) in rows:
        file_count = (
            bind.execute(
                sa.text('SELECT COUNT(*) FROM knowledge_file WHERE directory_id = :d'), {'d': dir_id}
            ).scalar()
            or 0
        )
        directory_count = (
            bind.execute(
                sa.text('SELECT COUNT(*) FROM knowledge_directory WHERE parent_id = :d'), {'d': dir_id}
            ).scalar()
            or 0
        )
        bind.execute(
            directory.update()
            .where(directory.c.id == dir_id)
            .values(meta={'file_count': file_count, 'directory_count': directory_count})
        )


def downgrade() -> None:
    op.drop_column('knowledge_directory', 'meta')
