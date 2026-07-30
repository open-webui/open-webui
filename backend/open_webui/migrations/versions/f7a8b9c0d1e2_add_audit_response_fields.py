"""Add extracted response fields to audit logs.

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-07-30 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, None] = 'e6f7a8b9c0d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


RESPONSE_FIELD_COLUMNS = (
    ('response_id', sa.Text()),
    ('response_model', sa.Text()),
    ('response_finish_reasons', sa.JSON()),
)


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'audit_log' not in inspector.get_table_names():
        return

    columns = {column['name'] for column in inspector.get_columns('audit_log')}
    for name, column_type in RESPONSE_FIELD_COLUMNS:
        if name not in columns:
            op.add_column('audit_log', sa.Column(name, column_type, nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'audit_log' not in inspector.get_table_names():
        return

    columns = {column['name'] for column in inspector.get_columns('audit_log')}
    with op.batch_alter_table('audit_log') as batch_op:
        for name, _ in RESPONSE_FIELD_COLUMNS:
            if name in columns:
                batch_op.drop_column(name)
