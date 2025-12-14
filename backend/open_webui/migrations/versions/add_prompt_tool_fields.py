"""Add prompt tool fields

Revision ID: add_prompt_tool_fields
Revises: add_rag_store_names_to_config
Create Date: 2025-01-02

This migration adds tool-related fields to the prompt table for tool gating:
- tool_description: Short description for tool catalog (50-100 chars)
- tool_priority: Priority for ordering tools (higher = more priority)
"""

from alembic import op
import sqlalchemy as sa

revision = "add_prompt_tool_fields"
down_revision = "add_rag_store_names_to_config"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "prompt",
        sa.Column("tool_description", sa.Text(), nullable=True)
    )
    op.add_column(
        "prompt",
        sa.Column("tool_priority", sa.Integer(), nullable=True, default=0)
    )


def downgrade():
    op.drop_column("prompt", "tool_priority")
    op.drop_column("prompt", "tool_description")
