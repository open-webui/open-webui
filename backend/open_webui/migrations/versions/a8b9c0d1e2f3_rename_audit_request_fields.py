"""Rename extracted audit request fields.

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-07-30 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a8b9c0d1e2f3'
down_revision: Union[str, None] = 'f7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


REQUEST_FIELD_RENAMES = (
    ('extra', 'request_extra', sa.JSON()),
    ('skill_ids', 'request_skill_ids', sa.JSON()),
    ('tool_ids', 'request_tool_ids', sa.JSON()),
    ('response_format', 'request_response_format', sa.JSON()),
    ('extra_body', 'request_extra_body', sa.JSON()),
    ('system_messages', 'request_system_messages', sa.JSON()),
    ('user_messages', 'request_user_messages', sa.JSON()),
)


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'audit_log' not in inspector.get_table_names():
        return

    columns = {column['name'] for column in inspector.get_columns('audit_log')}
    with op.batch_alter_table('audit_log') as batch_op:
        for old_name, new_name, column_type in REQUEST_FIELD_RENAMES:
            if old_name in columns and new_name not in columns:
                batch_op.alter_column(old_name, new_column_name=new_name, existing_type=column_type)
        if 'request_model' not in columns:
            batch_op.add_column(sa.Column('request_model', sa.Text(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'audit_log' not in inspector.get_table_names():
        return

    columns = {column['name'] for column in inspector.get_columns('audit_log')}
    with op.batch_alter_table('audit_log') as batch_op:
        if 'request_model' in columns:
            batch_op.drop_column('request_model')
        for old_name, new_name, column_type in REQUEST_FIELD_RENAMES:
            if new_name in columns and old_name not in columns:
                batch_op.alter_column(new_name, new_column_name=old_name, existing_type=column_type)
