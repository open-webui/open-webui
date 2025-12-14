"""Add message tagging tables

Revision ID: add_message_tagging_tables
Revises: alter_chat_settings_to_text
Create Date: 2025-01-02

This migration adds tables for:
- message_tag_definition: System-wide tag definitions for messages
- message_tag: Links messages to tags with summaries
- tagging_daemon_config: Configuration for the background daemon
"""

from alembic import op
import sqlalchemy as sa

revision = "add_message_tagging_tables"
down_revision = ("alter_chat_settings_to_text", "add_prompt_group_tables")  # Merge multiple heads
branch_labels = None
depends_on = None


def upgrade():
    # Create message_tag_definition table
    op.create_table(
        "message_tag_definition",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("usage_count", sa.Integer(), default=0),
        sa.Column("is_protected", sa.Boolean(), default=False),  # Admin-created tags that can't be auto-deleted
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )

    # Create message_tag table with unique constraint
    op.create_table(
        "message_tag",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("chat_id", sa.String(), nullable=False),
        sa.Column("message_id", sa.String(), nullable=False),
        sa.Column("tag_id", sa.String(), nullable=False),
        sa.Column("summary", sa.String(100), nullable=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint("chat_id", "message_id", "tag_id", name="uq_chat_message_tag"),
    )

    # Create tagging_daemon_config table
    op.create_table(
        "tagging_daemon_config",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("enabled", sa.Boolean(), default=True),
        sa.Column("schedule", sa.String(), default="daily"),
        sa.Column("run_time", sa.String(), default="03:00"),
        sa.Column("lookback_days", sa.Integer(), default=7),
        sa.Column("batch_size", sa.Integer(), default=10),
        sa.Column("max_tags", sa.Integer(), default=100),
        sa.Column("consolidation_threshold", sa.Integer(), default=90),
        sa.Column("custom_tagging_prompt", sa.Text(), nullable=True),  # Custom prompt for AI tagging
        sa.Column("custom_system_instruction", sa.Text(), nullable=True),  # Custom system instruction
        sa.Column("last_run_at", sa.BigInteger(), nullable=True),
        sa.Column("last_run_status", sa.String(), nullable=True),
        sa.Column("lock_acquired_at", sa.BigInteger(), nullable=True),
        sa.Column("lock_instance_id", sa.String(), nullable=True),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )

    # Create indexes for message_tag
    op.create_index("idx_message_tag_chat_message", "message_tag", ["chat_id", "message_id"])
    op.create_index("idx_message_tag_tag", "message_tag", ["tag_id"])
    op.create_index("idx_message_tag_user", "message_tag", ["user_id"])

    # Create index for message_tag_definition
    op.create_index("idx_message_tag_def_usage", "message_tag_definition", ["usage_count"])


def downgrade():
    # Drop indexes
    op.drop_index("idx_message_tag_def_usage", table_name="message_tag_definition")
    op.drop_index("idx_message_tag_user", table_name="message_tag")
    op.drop_index("idx_message_tag_tag", table_name="message_tag")
    op.drop_index("idx_message_tag_chat_message", table_name="message_tag")

    # Drop tables (unique constraint is dropped with table)
    op.drop_table("tagging_daemon_config")
    op.drop_table("message_tag")
    op.drop_table("message_tag_definition")
