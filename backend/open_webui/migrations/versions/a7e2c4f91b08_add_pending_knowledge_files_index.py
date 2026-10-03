"""add pending knowledge files index

Revision ID: a7e2c4f91b08
Revises: d4c1a8e37b62
Create Date: 2026-09-14 13:42:18.905331

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a7e2c4f91b08'
down_revision: str | None = 'd4c1a8e37b62'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # SQLite does not fold bound parameters when matching an expression index, so it could never use this one.
    if op.get_bind().dialect.name == 'postgresql':
        op.create_index(
            'file_pending_knowledge_idx',
            'file',
            [sa.text("((meta -> 'data') ->> 'knowledge_id')")],
            postgresql_where=sa.text("(data ->> 'status') IN ('pending', 'processing')"),
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == 'postgresql':
        op.drop_index('file_pending_knowledge_idx', table_name='file')
