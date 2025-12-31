"""Add chapter_id column to chat table

Revision ID: add_chapter_id_to_chat
Revises: 37f288994c47
Create Date: 2024-12-13 21:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "add_chapter_id_to_chat"
down_revision = "37f288994c47"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "chat",
        sa.Column("chapter_id", sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_column("chat", "chapter_id")
