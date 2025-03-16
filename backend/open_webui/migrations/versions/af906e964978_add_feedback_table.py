"""Add feedback table

Revision ID: af906e964978
Revises: c29facfe716b
Create Date: 2024-10-20 17:02:35.241684

"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = "af906e964978"
down_revision = "c29facfe716b"
branch_labels = None
depends_on = None


def upgrade():
    # ### Create feedback table ###
    op.create_table(
        "feedback",
        sa.Column(
            "id", sa.Text(), primary_key=True
        ),  # Unique identifier for each feedback (TEXT type)
        sa.Column(
            "user_id", sa.Text(), nullable=True
        ),  # ID of the user providing the feedback (TEXT type)
        sa.Column(
            "version", sa.BigInteger(), default=0
        ),  # Version of feedback (BIGINT type)
        sa.Column("type", sa.Text(), nullable=True),  # Type of feedback (TEXT type)
        sa.Column("data", sa.JSON(), nullable=True),  # Feedback data (JSON type)
        sa.Column(
            "meta", sa.JSON(), nullable=True
        ),  # Metadata for feedback (JSON type)
        sa.Column(
            "snapshot", sa.JSON(), nullable=True
        ),  # snapshot data for feedback (JSON type)
        sa.Column(
            "created_at", sa.BigInteger(), nullable=False
        ),  # Feedback creation timestamp (BIGINT representing epoch)
        sa.Column(
            "updated_at", sa.BigInteger(), nullable=False
        ),  # Feedback update timestamp (BIGINT representing epoch)
    )


def downgrade():
    # ### Drop feedback table ###
    op.drop_table("feedback")
