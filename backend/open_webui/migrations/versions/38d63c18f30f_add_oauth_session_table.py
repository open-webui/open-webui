"""Add oauth_session table

Revision ID: 38d63c18f30f
Revises: 3af16a1c9fb6
Create Date: 2025-09-08 14:19:59.583921

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "38d63c18f30f"
down_revision: Union[str, None] = "3af16a1c9fb6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create oauth_session table
    op.create_table(
        "oauth_session",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
    )

    # Create indexes for better performance
    op.create_index("idx_oauth_session_user_id", "oauth_session", ["user_id"])
    op.create_index("idx_oauth_session_expires_at", "oauth_session", ["expires_at"])
    op.create_index(
        "idx_oauth_session_user_provider", "oauth_session", ["user_id", "provider"]
    )


def downgrade() -> None:
    # Drop indexes first
    op.drop_index("idx_oauth_session_user_provider", table_name="oauth_session")
    op.drop_index("idx_oauth_session_expires_at", table_name="oauth_session")
    op.drop_index("idx_oauth_session_user_id", table_name="oauth_session")

    # Drop the table
    op.drop_table("oauth_session")
