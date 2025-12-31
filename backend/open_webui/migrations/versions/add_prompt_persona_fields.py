"""Add prompt persona fields

Revision ID: add_prompt_persona_fields
Revises: (set to latest revision)
Create Date: 2024-12-31

This migration adds persona-based prompt support:
- prompt_type: 'base', 'proficiency', 'style', or None (backward compatible)
- persona_value: '1','2','3' for proficiency or 'simple','detailed' for style
"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = "add_prompt_persona_fields"
down_revision = None  # TODO: Set to the latest revision ID
branch_labels = None
depends_on = None


def upgrade():
    # Add prompt_type column to prompt table
    # This field identifies the type of prompt: base, proficiency, style, or None
    with op.batch_alter_table("prompt", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("prompt_type", sa.String(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("persona_value", sa.String(), nullable=True)
        )

    # Create index for faster persona-based queries
    op.create_index(
        "idx_prompt_type_persona",
        "prompt",
        ["prompt_type", "persona_value"],
        unique=False
    )


def downgrade():
    # Drop index first
    op.drop_index("idx_prompt_type_persona", table_name="prompt")

    # Remove the new columns
    with op.batch_alter_table("prompt", schema=None) as batch_op:
        batch_op.drop_column("persona_value")
        batch_op.drop_column("prompt_type")
