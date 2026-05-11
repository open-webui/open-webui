"""Add Gmail sync status table

Revision ID: 33cc3721a72
Revises: 018012973d35
Create Date: 2025-01-17 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

from open_webui.migrations.util import get_existing_tables

revision = "33cc3721a72"
down_revision = "018012973d35"
branch_labels = None
depends_on = None


def upgrade():
    existing_tables = set(get_existing_tables())
    if "gmail_sync_status" in existing_tables:
        return

    # Create Gmail sync status table
    op.create_table(
        'gmail_sync_status',
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('last_sync_timestamp', sa.BigInteger(), nullable=True),
        sa.Column('last_sync_history_id', sa.String(), nullable=True),
        sa.Column('last_sync_email_id', sa.String(), nullable=True),
        sa.Column('total_emails_synced', sa.Integer(), nullable=False, default=0),
        sa.Column('last_sync_count', sa.Integer(), nullable=False, default=0),
        sa.Column('last_sync_duration', sa.Integer(), nullable=False, default=0),
        sa.Column('sync_status', sa.String(), nullable=False, default='never'),
        sa.Column('sync_enabled', sa.Boolean(), nullable=False, default=True),
        sa.Column('auto_sync_enabled', sa.Boolean(), nullable=False, default=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('error_count', sa.Integer(), nullable=False, default=0),
        sa.Column('sync_frequency_hours', sa.Integer(), nullable=False, default=24),
        sa.Column('max_emails_per_sync', sa.Integer(), nullable=False, default=100),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('user_id'),
    )

    # Create indexes for common queries
    op.create_index('gmail_sync_user_id_idx', 'gmail_sync_status', ['user_id'])
    op.create_index('gmail_sync_status_idx', 'gmail_sync_status', ['sync_status'])
    op.create_index('gmail_sync_enabled_idx', 'gmail_sync_status', ['sync_enabled', 'auto_sync_enabled'])
    op.create_index('gmail_sync_last_sync_idx', 'gmail_sync_status', ['last_sync_timestamp'])


def downgrade():
    # Drop indexes
    op.drop_index('gmail_sync_last_sync_idx', table_name='gmail_sync_status')
    op.drop_index('gmail_sync_enabled_idx', table_name='gmail_sync_status')
    op.drop_index('gmail_sync_status_idx', table_name='gmail_sync_status')
    op.drop_index('gmail_sync_user_id_idx', table_name='gmail_sync_status')

    # Drop table
    op.drop_table('gmail_sync_status')
