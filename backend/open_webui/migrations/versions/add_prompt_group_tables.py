"""Add prompt group tables

Revision ID: add_prompt_group_tables
Revises: add_prompt_persona_fields
Create Date: 2024-12-31

This migration adds the prompt group system:
- prompt_group: Groups of prompts that work together
- prompt_group_mapping: Maps prompts to groups with ordering
"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = "add_prompt_group_tables"
down_revision = "add_prompt_persona_fields"  # Depends on Phase 1 migration
branch_labels = None
depends_on = None


def upgrade():
    # Create prompt_group table
    op.create_table(
        "prompt_group",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.Column("access_control", sa.JSON(), nullable=True),
    )

    # Create prompt_group_mapping table
    op.create_table(
        "prompt_group_mapping",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("group_id", sa.String(), nullable=False),
        sa.Column("prompt_command", sa.String(), nullable=False),
        sa.Column("order", sa.Integer(), default=0, nullable=False),
    )

    # Create indexes for better query performance
    op.create_index(
        "idx_prompt_group_user",
        "prompt_group",
        ["user_id"],
        unique=False
    )

    op.create_index(
        "idx_prompt_group_mapping_group",
        "prompt_group_mapping",
        ["group_id"],
        unique=False
    )

    op.create_index(
        "idx_prompt_group_mapping_prompt",
        "prompt_group_mapping",
        ["prompt_command"],
        unique=False
    )

    # Create unique constraint to prevent duplicate prompt in same group
    op.create_index(
        "idx_prompt_group_mapping_unique",
        "prompt_group_mapping",
        ["group_id", "prompt_command"],
        unique=True
    )


def downgrade():
    # Drop indexes
    op.drop_index("idx_prompt_group_mapping_unique", table_name="prompt_group_mapping")
    op.drop_index("idx_prompt_group_mapping_prompt", table_name="prompt_group_mapping")
    op.drop_index("idx_prompt_group_mapping_group", table_name="prompt_group_mapping")
    op.drop_index("idx_prompt_group_user", table_name="prompt_group")

    # Drop tables
    op.drop_table("prompt_group_mapping")
    op.drop_table("prompt_group")
