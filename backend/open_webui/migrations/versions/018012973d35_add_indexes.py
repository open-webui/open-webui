"""Add indexes

Revision ID: 018012973d35
Revises: d31026856c01
Create Date: 2025-08-13 03:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "018012973d35"
down_revision = "d31026856c01"
branch_labels = None
depends_on = None


def upgrade():
    # Chat table indexes
    op.create_index("folder_id_idx", "chat", ["folder_id"])
    op.create_index("user_id_pinned_idx", "chat", ["user_id", "pinned"])
    op.create_index("user_id_archived_idx", "chat", ["user_id", "archived"])
    op.create_index("updated_at_user_id_idx", "chat", ["updated_at", "user_id"])
    op.create_index("folder_id_user_id_idx", "chat", ["folder_id", "user_id"])

    # Tag table index
    op.create_index("user_id_idx", "tag", ["user_id"])

    # Function table index
    op.create_index("is_global_idx", "function", ["is_global"])


def downgrade():
    # Chat table indexes
    op.drop_index("folder_id_idx", table_name="chat")
    op.drop_index("user_id_pinned_idx", table_name="chat")
    op.drop_index("user_id_archived_idx", table_name="chat")
    op.drop_index("updated_at_user_id_idx", table_name="chat")
    op.drop_index("folder_id_user_id_idx", table_name="chat")

    # Tag table index
    op.drop_index("user_id_idx", table_name="tag")

    # Function table index

    op.drop_index("is_global_idx", table_name="function")
