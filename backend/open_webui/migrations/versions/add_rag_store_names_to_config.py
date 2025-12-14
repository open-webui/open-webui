"""Add rag_store_names to tagging_daemon_config

Revision ID: add_rag_store_names_to_config
Revises: add_message_tag_chapter_and_blacklist
Create Date: 2025-01-02

This migration adds rag_store_names column to tagging_daemon_config
for storing selected RAG stores to use during tagging.
"""

from alembic import op
import sqlalchemy as sa

revision = "add_rag_store_names_to_config"
down_revision = "add_message_tag_chapter_and_blacklist"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "tagging_daemon_config",
        sa.Column("rag_store_names", sa.JSON(), nullable=True)
    )


def downgrade():
    op.drop_column("tagging_daemon_config", "rag_store_names")
