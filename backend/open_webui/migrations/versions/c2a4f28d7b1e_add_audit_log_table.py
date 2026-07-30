"""Add audit log table.

Revision ID: c2a4f28d7b1e
Revises: f0bd01a18a3d
Create Date: 2026-07-29 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c2a4f28d7b1e'
down_revision: Union[str, None] = 'f0bd01a18a3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if 'audit_log' in inspector.get_table_names():
        return

    op.create_table(
        'audit_log',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.Text(), nullable=True),
        sa.Column('user_snapshot', sa.JSON(), nullable=True),
        sa.Column('audit_level', sa.Text(), nullable=False),
        sa.Column('verb', sa.Text(), nullable=False),
        sa.Column('request_path', sa.Text(), nullable=False),
        sa.Column('request_uri', sa.Text(), nullable=False),
        sa.Column('response_status_code', sa.Integer(), nullable=True),
        sa.Column('source_ip', sa.Text(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('request_object', sa.Text(), nullable=True),
        sa.Column('response_object', sa.Text(), nullable=True),
        sa.Column('request_truncated', sa.Boolean(), nullable=True),
        sa.Column('response_truncated', sa.Boolean(), nullable=True),
        sa.Column('extra', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_log_created_at', 'audit_log', ['created_at'])
    op.create_index('ix_audit_log_user_id', 'audit_log', ['user_id'])
    op.create_index('audit_log_path_created_idx', 'audit_log', ['request_path', 'created_at'])
    op.create_index('audit_log_user_created_idx', 'audit_log', ['user_id', 'created_at'])
    op.create_index('audit_log_status_created_idx', 'audit_log', ['response_status_code', 'created_at'])


def downgrade() -> None:
    op.drop_table('audit_log')
