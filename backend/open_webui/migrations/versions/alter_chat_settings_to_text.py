"""Alter proficiency_level and response_style to Text columns

Revision ID: alter_chat_settings_to_text
Revises: add_prompt_group_tables
Create Date: 2024-12-31 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "alter_chat_settings_to_text"
down_revision = "add_textbook_tables"
branch_labels = None
depends_on = None


def upgrade():
    """
    Alter proficiency_level and response_style columns from BigInteger to Text.

    This migration handles the conversion of these columns to support string values
    like "beginner", "intermediate", "advanced" instead of numeric codes.
    """
    # SQLite doesn't support ALTER COLUMN directly, so we need to:
    # 1. Create new columns with the correct type
    # 2. Copy data from old columns
    # 3. Drop old columns
    # 4. Rename new columns to original names

    with op.batch_alter_table("chat") as batch_op:
        # Add temporary columns with Text type
        batch_op.add_column(
            sa.Column("proficiency_level_new", sa.Text(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("response_style_new", sa.Text(), nullable=True)
        )

    # Copy data from old columns to new columns (converting to string)
    op.execute("""
        UPDATE chat
        SET proficiency_level_new = CAST(proficiency_level AS TEXT),
            response_style_new = CAST(response_style AS TEXT)
        WHERE proficiency_level IS NOT NULL OR response_style IS NOT NULL
    """)

    with op.batch_alter_table("chat") as batch_op:
        # Drop old columns
        batch_op.drop_column("proficiency_level")
        batch_op.drop_column("response_style")

        # Rename new columns to original names
        batch_op.alter_column(
            "proficiency_level_new",
            new_column_name="proficiency_level"
        )
        batch_op.alter_column(
            "response_style_new",
            new_column_name="response_style"
        )


def downgrade():
    """
    Revert back to BigInteger columns.

    Note: This may cause data loss if string values cannot be converted to integers.
    """
    with op.batch_alter_table("chat") as batch_op:
        # Add temporary columns with BigInteger type
        batch_op.add_column(
            sa.Column("proficiency_level_new", sa.BigInteger(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("response_style_new", sa.BigInteger(), nullable=True)
        )

    # Copy data, attempting to convert strings to integers
    # Non-numeric strings will become NULL
    op.execute("""
        UPDATE chat
        SET proficiency_level_new = CASE
                WHEN proficiency_level GLOB '[0-9]*' THEN CAST(proficiency_level AS INTEGER)
                ELSE NULL
            END,
            response_style_new = CASE
                WHEN response_style GLOB '[0-9]*' THEN CAST(response_style AS INTEGER)
                ELSE NULL
            END
        WHERE proficiency_level IS NOT NULL OR response_style IS NOT NULL
    """)

    with op.batch_alter_table("chat") as batch_op:
        # Drop old columns
        batch_op.drop_column("proficiency_level")
        batch_op.drop_column("response_style")

        # Rename new columns to original names
        batch_op.alter_column(
            "proficiency_level_new",
            new_column_name="proficiency_level"
        )
        batch_op.alter_column(
            "response_style_new",
            new_column_name="response_style"
        )
