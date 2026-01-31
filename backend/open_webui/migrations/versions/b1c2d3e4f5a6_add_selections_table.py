"""Add selections table

Revision ID: b1c2d3e4f5a6
Revises: 38d63c18f30f
Create Date: 2024-01-01 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = "b1c2d3e4f5a6"
down_revision = "38d63c18f30f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if table already exists (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "selection" not in existing_tables:
        # Create selections table
        op.create_table(
            "selection",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("chat_id", sa.String(), nullable=False),
            sa.Column("message_id", sa.String(), nullable=False),
            sa.Column("role", sa.String(), nullable=False),
            sa.Column("selected_text", sa.Text(), nullable=False),
            sa.Column("context", sa.Text(), nullable=True),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=True),
            sa.Column("updated_at", sa.BigInteger(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

        # Create indexes for efficient querying
        op.create_index("idx_selection_user_id", "selection", ["user_id"])
        op.create_index("idx_selection_chat_id", "selection", ["chat_id"])
        op.create_index("idx_selection_message_id", "selection", ["message_id"])
        op.create_index("idx_selection_created_at", "selection", ["created_at"])
    else:
        # Table exists, check if indexes exist
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("selection")]
        indexes_to_create = [
            ("idx_selection_user_id", ["user_id"]),
            ("idx_selection_chat_id", ["chat_id"]),
            ("idx_selection_message_id", ["message_id"]),
            ("idx_selection_created_at", ["created_at"]),
        ]
        for idx_name, columns in indexes_to_create:
            if idx_name not in existing_indexes:
                op.create_index(idx_name, "selection", columns)


def downgrade() -> None:
    # Check if table exists before dropping
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "selection" in existing_tables:
        # Drop indexes
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("selection")]
        indexes_to_drop = [
            "idx_selection_created_at",
            "idx_selection_message_id",
            "idx_selection_chat_id",
            "idx_selection_user_id",
        ]
        for idx_name in indexes_to_drop:
            if idx_name in existing_indexes:
                op.drop_index(idx_name, table_name="selection")

        # Drop table
        op.drop_table("selection")
