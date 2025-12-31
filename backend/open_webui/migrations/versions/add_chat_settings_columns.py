"""Add proficiency_level and response_style columns to chat table

Revision ID: add_chat_settings_columns
Revises: add_chapter_id_to_chat
Create Date: 2024-12-13 22:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "add_chat_settings_columns"
down_revision = "add_chapter_id_to_chat"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "chat",
        sa.Column("proficiency_level", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "chat",
        sa.Column("response_style", sa.BigInteger(), nullable=True),
    )


def downgrade():
    op.drop_column("chat", "proficiency_level")
    op.drop_column("chat", "response_style")
