"""
Add child quiz research fields to child_profile

Revision ID: ee77aa33bb22
Revises: ee55ff66aa77
Create Date: 2025-10-29 12:50:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = "ee77aa33bb22"
down_revision = "ee55ff66aa77"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if columns already exist (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "child_profile" in existing_tables:
        child_profile_columns = [
            col["name"] for col in inspector.get_columns("child_profile")
        ]
        columns_to_add = [
            ("is_only_child", sa.Boolean(), None),
            ("child_has_ai_use", sa.String(), None),
            ("child_ai_use_contexts", None, None),  # JSON or Text
            ("parent_llm_monitoring_level", sa.String(), None),
        ]

        # Add columns one at a time to avoid circular dependency
        for col_name, col_type, _ in columns_to_add:
            if col_name not in child_profile_columns:
                if col_name == "child_ai_use_contexts":
                    # Use JSON if available; fall back to TEXT if driver doesn't support JSON
                    try:
                        op.add_column(
                            "child_profile",
                            sa.Column(col_name, sa.JSON(), nullable=True),
                        )
                    except Exception:
                        op.add_column(
                            "child_profile",
                            sa.Column(col_name, sa.Text(), nullable=True),
                        )
                else:
                    op.add_column(
                        "child_profile", sa.Column(col_name, col_type, nullable=True)
                    )


def downgrade() -> None:
    # Check if columns exist before dropping
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "child_profile" in existing_tables:
        child_profile_columns = [
            col["name"] for col in inspector.get_columns("child_profile")
        ]
        columns_to_drop = [
            "parent_llm_monitoring_level",
            "child_ai_use_contexts",
            "child_has_ai_use",
            "is_only_child",
        ]
        for col_name in columns_to_drop:
            if col_name in child_profile_columns:
                op.drop_column("child_profile", col_name)
