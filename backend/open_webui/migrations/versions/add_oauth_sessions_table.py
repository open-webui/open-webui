"""add oauth sessions table

Revision ID: 4bc7f8e9d2a1
Revises: 3af16a1c9fb6
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4bc7f8e9d2a1"
down_revision: Union[str, None] = "3af16a1c9fb6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create oauth_session table
    op.create_table(
        "oauth_session",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("encrypted_tokens", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
    )
    
    # Create indexes for better performance
    op.create_index("idx_oauth_session_user_id", "oauth_session", ["user_id"])
    op.create_index("idx_oauth_session_expires_at", "oauth_session", ["expires_at"])
    op.create_index("idx_oauth_session_user_provider", "oauth_session", ["user_id", "provider"])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index("idx_oauth_session_user_provider", table_name="oauth_session")
    op.drop_index("idx_oauth_session_expires_at", table_name="oauth_session")
    op.drop_index("idx_oauth_session_user_id", table_name="oauth_session")
    
    # Drop the table
    op.drop_table("oauth_session")
