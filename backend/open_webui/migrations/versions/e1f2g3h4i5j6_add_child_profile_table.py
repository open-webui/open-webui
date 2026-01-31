"""Add child profile table

Revision ID: e1f2g3h4i5j6
Revises: d1e2f3a4b5c6
Create Date: 2024-12-19 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = "e1f2g3h4i5j6"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if table already exists (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "child_profile" not in existing_tables:
        # Create child_profile table
        op.create_table(
            "child_profile",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("child_age", sa.String(), nullable=True),
            sa.Column("child_gender", sa.String(), nullable=True),
            sa.Column("child_characteristics", sa.Text(), nullable=True),
            sa.Column("parenting_style", sa.String(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=True),
            sa.Column("updated_at", sa.BigInteger(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

        # Create indexes for efficient querying
        op.create_index("idx_child_profile_user_id", "child_profile", ["user_id"])
        op.create_index("idx_child_profile_created_at", "child_profile", ["created_at"])
    else:
        # Table exists, check if indexes exist
        existing_indexes = [
            idx["name"] for idx in inspector.get_indexes("child_profile")
        ]
        indexes_to_create = [
            ("idx_child_profile_user_id", ["user_id"]),
            ("idx_child_profile_created_at", ["created_at"]),
        ]
        for idx_name, columns in indexes_to_create:
            if idx_name not in existing_indexes:
                op.create_index(idx_name, "child_profile", columns)


def downgrade() -> None:
    # Check if table exists before dropping
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "child_profile" in existing_tables:
        # Drop indexes
        existing_indexes = [
            idx["name"] for idx in inspector.get_indexes("child_profile")
        ]
        indexes_to_drop = [
            "idx_child_profile_created_at",
            "idx_child_profile_user_id",
        ]
        for idx_name in indexes_to_drop:
            if idx_name in existing_indexes:
                op.drop_index(idx_name, table_name="child_profile")

        # Drop table
        op.drop_table("child_profile")
