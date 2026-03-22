"""Add external_resource table for Google Drive integration

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-22 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from open_webui.migrations.util import get_existing_tables

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing_tables = set(get_existing_tables())

    if 'external_resource' not in existing_tables:
        op.create_table(
            'external_resource',
            sa.Column('id', sa.Text(), nullable=False, primary_key=True),
            sa.Column('user_id', sa.Text(), nullable=False),
            sa.Column('knowledge_id', sa.Text(), sa.ForeignKey('knowledge.id', ondelete='CASCADE'), nullable=False),
            # Resource details
            sa.Column('resource_type', sa.String(50), nullable=False, server_default='google_drive'),
            sa.Column('resource_link', sa.Text(), nullable=False),
            sa.Column('resource_name', sa.Text(), nullable=True),
            # Sync configuration
            sa.Column('sync_enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('sync_interval_minutes', sa.Integer(), nullable=False, server_default='60'),
            # Sync state
            sa.Column('page_token', sa.Text(), nullable=True),
            sa.Column('last_synced_at', sa.BigInteger(), nullable=True),
            sa.Column('last_sync_status', sa.String(50), nullable=True),
            sa.Column('last_sync_error', sa.Text(), nullable=True),
            # Timestamps
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
        )
        # Create indexes for common queries
        op.create_index('idx_external_resource_user_id', 'external_resource', ['user_id'])
        op.create_index('idx_external_resource_knowledge_id', 'external_resource', ['knowledge_id'])
        op.create_index('idx_external_resource_sync_enabled', 'external_resource', ['sync_enabled'])


def downgrade() -> None:
    op.drop_index('idx_external_resource_sync_enabled', table_name='external_resource')
    op.drop_index('idx_external_resource_knowledge_id', table_name='external_resource')
    op.drop_index('idx_external_resource_user_id', table_name='external_resource')
    op.drop_table('external_resource')
