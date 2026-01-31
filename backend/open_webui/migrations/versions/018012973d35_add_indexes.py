"""Add indexes

Revision ID: 018012973d35
Revises: d31026856c01
Create Date: 2024-12-30 03:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = "018012973d35"
down_revision = "d31026856c01"
branch_labels = None
depends_on = None


def upgrade():
    # Check if indexes already exist (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    # Chat table indexes
    if "chat" in existing_tables:
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("chat")]
        indexes_to_create = [
            ("folder_id_idx", ["folder_id"]),
            ("user_id_pinned_idx", ["user_id", "pinned"]),
            ("user_id_archived_idx", ["user_id", "archived"]),
            ("updated_at_user_id_idx", ["updated_at", "user_id"]),
            ("folder_id_user_id_idx", ["folder_id", "user_id"]),
        ]
        for idx_name, columns in indexes_to_create:
            if idx_name not in existing_indexes:
                op.create_index(idx_name, "chat", columns)

    # Tag table index
    if "tag" in existing_tables:
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("tag")]
        if "user_id_idx" not in existing_indexes:
            op.create_index("user_id_idx", "tag", ["user_id"])

    # Function table index
    if "function" in existing_tables:
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("function")]
        if "is_global_idx" not in existing_indexes:
            op.create_index("is_global_idx", "function", ["is_global"])


def downgrade():
    # Check if indexes exist before dropping
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    # Chat table indexes
    if "chat" in existing_tables:
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("chat")]
        indexes_to_drop = [
            "folder_id_idx",
            "user_id_pinned_idx",
            "user_id_archived_idx",
            "updated_at_user_id_idx",
            "folder_id_user_id_idx",
        ]
        for idx_name in indexes_to_drop:
            if idx_name in existing_indexes:
                op.drop_index(idx_name, table_name="chat")

    # Tag table index
    if "tag" in existing_tables:
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("tag")]
        if "user_id_idx" in existing_indexes:
            op.drop_index("user_id_idx", table_name="tag")

    # Function table index
    if "function" in existing_tables:
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("function")]
        if "is_global_idx" in existing_indexes:
            op.drop_index("is_global_idx", table_name="function")
