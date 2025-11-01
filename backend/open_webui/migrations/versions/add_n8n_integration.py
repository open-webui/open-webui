"""Add N8N Integration tables

Revision ID: add_n8n_integration
Revises: 018012973d35
Create Date: 2025-11-01 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "add_n8n_integration"
down_revision = "018012973d35"
branch_labels = None
depends_on = None


def upgrade():
    """
    Create N8N configuration and execution tables
    """
    # N8N Configuration table
    op.create_table(
        "n8n_config",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("n8n_url", sa.String(), nullable=False),
        sa.Column("webhook_id", sa.String(), nullable=False),
        sa.Column("api_key", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_streaming", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="120"),
        sa.Column("retry_config", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for n8n_config
    op.create_index("n8n_config_user_id_idx", "n8n_config", ["user_id"])
    op.create_index("n8n_config_is_active_idx", "n8n_config", ["is_active"])

    # N8N Workflow Execution table
    op.create_table(
        "n8n_executions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("config_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),  # pending, success, failed, timeout
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for n8n_executions
    op.create_index("n8n_executions_config_id_idx", "n8n_executions", ["config_id"])
    op.create_index("n8n_executions_user_id_idx", "n8n_executions", ["user_id"])
    op.create_index("n8n_executions_status_idx", "n8n_executions", ["status"])
    op.create_index("n8n_executions_created_at_idx", "n8n_executions", ["created_at"])


def downgrade():
    """
    Drop N8N integration tables
    """
    # Drop indexes
    op.drop_index("n8n_executions_created_at_idx", table_name="n8n_executions")
    op.drop_index("n8n_executions_status_idx", table_name="n8n_executions")
    op.drop_index("n8n_executions_user_id_idx", table_name="n8n_executions")
    op.drop_index("n8n_executions_config_id_idx", table_name="n8n_executions")

    op.drop_index("n8n_config_is_active_idx", table_name="n8n_config")
    op.drop_index("n8n_config_user_id_idx", table_name="n8n_config")

    # Drop tables
    op.drop_table("n8n_executions")
    op.drop_table("n8n_config")
