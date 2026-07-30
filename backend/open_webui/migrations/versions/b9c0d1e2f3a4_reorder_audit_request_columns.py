"""Place request_model after response_truncated.

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-07-30 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b9c0d1e2f3a4'
down_revision: Union[str, None] = 'a8b9c0d1e2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


AUDIT_LOG_COLUMN_ORDER = (
    'id',
    'created_at',
    'user_id',
    'user_snapshot',
    'audit_level',
    'verb',
    'request_path',
    'request_uri',
    'response_status_code',
    'source_ip',
    'user_agent',
    'request_object',
    'response_object',
    'response_id',
    'response_model',
    'response_finish_reasons',
    'request_truncated',
    'response_truncated',
    'request_model',
    'request_extra',
    'request_skill_ids',
    'request_tool_ids',
    'request_response_format',
    'request_extra_body',
    'request_system_messages',
    'request_user_messages',
)


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'audit_log' not in inspector.get_table_names():
        return

    columns = {column['name'] for column in inspector.get_columns('audit_log')}
    if not set(AUDIT_LOG_COLUMN_ORDER).issubset(columns):
        return

    with op.batch_alter_table(
        'audit_log',
        recreate='always',
        partial_reordering=[AUDIT_LOG_COLUMN_ORDER],
    ):
        pass


def downgrade() -> None:
    # Column order has no semantic effect and does not require a data change.
    pass
