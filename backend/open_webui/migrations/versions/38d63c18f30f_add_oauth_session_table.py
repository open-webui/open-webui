"""Add oauth_session table

Revision ID: 38d63c18f30f
Revises: 3af16a1c9fb6
Create Date: 2025-09-08 14:19:59.583921

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = "38d63c18f30f"
down_revision: Union[str, None] = "3af16a1c9fb6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if table already exists (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()
    
    if "oauth_session" not in existing_tables:
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
    else:
        # Table exists, check if indexes exist
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("oauth_session")]
        indexes_to_create = [
            ("idx_oauth_session_user_id", ["user_id"]),
            ("idx_oauth_session_expires_at", ["expires_at"]),
            ("idx_oauth_session_user_provider", ["user_id", "provider"]),
        ]
        for idx_name, columns in indexes_to_create:
            if idx_name not in existing_indexes:
                op.create_index(idx_name, "oauth_session", columns)


def downgrade() -> None:
    # Check if table exists before dropping
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()
    
    if "oauth_session" in existing_tables:
        # Drop indexes first
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("oauth_session")]
        indexes_to_drop = [
            "idx_oauth_session_user_provider",
            "idx_oauth_session_expires_at",
            "idx_oauth_session_user_id",
        ]
        for idx_name in indexes_to_drop:
            if idx_name in existing_indexes:
                op.drop_index(idx_name, table_name="oauth_session")

        # Drop the table
        op.drop_table("oauth_session")
