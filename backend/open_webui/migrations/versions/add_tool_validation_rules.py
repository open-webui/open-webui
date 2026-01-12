"""Add validation_rules column for json_tool prompts

Revision ID: add_tool_validation_rules
Revises: add_tag_feedback_table
Create Date: 2025-01-05

This migration:
1. Adds validation_rules JSON column to prompt table (for json_tool type)
2. Migrates existing 'tool' prompts to 'json_tool' type

validation_rules format:
{
    "allow": {
        "pattern_name": "regex_pattern",
        ...
    },
    "forbidden": {
        "pattern_name": "regex_pattern",
        ...
    }
}
"""

from alembic import op
import sqlalchemy as sa

revision = "add_tool_validation_rules"
down_revision = "add_tag_feedback_table"
branch_labels = None
depends_on = None


def upgrade():
    # Add validation_rules column (JSON format)
    op.add_column(
        "prompt",
        sa.Column("validation_rules", sa.JSON(), nullable=True)
    )

    # Migrate existing 'tool' prompts to 'json_tool'
    op.execute(
        "UPDATE prompt SET prompt_type = 'json_tool' WHERE prompt_type = 'tool'"
    )


def downgrade():
    # Revert 'json_tool' back to 'tool'
    op.execute(
        "UPDATE prompt SET prompt_type = 'tool' WHERE prompt_type = 'json_tool'"
    )

    op.drop_column("prompt", "validation_rules")
