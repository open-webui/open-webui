"""Add chapter_id to message_tag_definition and blacklisted_tags to tagging_daemon_config

Revision ID: add_message_tag_chapter_and_blacklist
Revises: add_message_tagging_tables
Create Date: 2025-01-02

This migration adds:
- chapter_id column to message_tag_definition for linking tags to textbook chapters
- blacklisted_tags column to tagging_daemon_config for preventing certain tags
"""

from alembic import op
import sqlalchemy as sa

revision = "add_message_tag_chapter_and_blacklist"
down_revision = "add_message_tagging_tables"
branch_labels = None
depends_on = None


def upgrade():
    # Add chapter_id to message_tag_definition
    op.add_column(
        "message_tag_definition",
        sa.Column("chapter_id", sa.String(), nullable=True)
    )

    # Create index for chapter_id
    op.create_index(
        "idx_message_tag_def_chapter",
        "message_tag_definition",
        ["chapter_id"]
    )

    # Add blacklisted_tags to tagging_daemon_config
    op.add_column(
        "tagging_daemon_config",
        sa.Column("blacklisted_tags", sa.JSON(), nullable=True)
    )


def downgrade():
    # Drop blacklisted_tags column
    op.drop_column("tagging_daemon_config", "blacklisted_tags")

    # Drop chapter_id index and column
    op.drop_index("idx_message_tag_def_chapter", table_name="message_tag_definition")
    op.drop_column("message_tag_definition", "chapter_id")
