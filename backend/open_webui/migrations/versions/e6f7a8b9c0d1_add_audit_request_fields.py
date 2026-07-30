"""Add extracted request fields to audit logs.

Revision ID: e6f7a8b9c0d1
Revises: c2a4f28d7b1e
Create Date: 2026-07-30 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'e6f7a8b9c0d1'
down_revision: Union[str, None] = 'c2a4f28d7b1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


REQUEST_FIELD_COLUMNS = (
    ('skill_ids', sa.JSON()),
    ('tool_ids', sa.JSON()),
    ('response_format', sa.JSON()),
    ('extra_body', sa.JSON()),
    ('system_messages', sa.JSON()),
    ('user_messages', sa.JSON()),
)


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'audit_log' not in inspector.get_table_names():
        return

    columns = {column['name'] for column in inspector.get_columns('audit_log')}
    for name, column_type in REQUEST_FIELD_COLUMNS:
        if name not in columns:
            op.add_column('audit_log', sa.Column(name, column_type, nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'audit_log' not in inspector.get_table_names():
        return

    columns = {column['name'] for column in inspector.get_columns('audit_log')}
    with op.batch_alter_table('audit_log') as batch_op:
        for name, _ in REQUEST_FIELD_COLUMNS:
            if name in columns:
                batch_op.drop_column(name)
