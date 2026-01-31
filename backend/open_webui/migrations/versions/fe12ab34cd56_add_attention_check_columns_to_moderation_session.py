"""
Add attention check columns to moderation_session

Revision ID: fe12ab34cd56
Revises: cc33dd44ee55
Create Date: 2025-10-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = "fe12ab34cd56"
down_revision = "cc33dd44ee55"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if columns already exist (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "moderation_session" in existing_tables:
        moderation_session_columns = [
            col["name"] for col in inspector.get_columns("moderation_session")
        ]
        columns_to_add = [
            ("is_attention_check", sa.Boolean(), False),
            ("attention_check_selected", sa.Boolean(), False),
            ("attention_check_passed", sa.Boolean(), False),
        ]

        # Add columns one at a time to avoid circular dependency
        for col_name, col_type, default in columns_to_add:
            if col_name not in moderation_session_columns:
                op.add_column(
                    "moderation_session",
                    sa.Column(
                        col_name,
                        col_type,
                        nullable=False,
                        server_default=sa.text(str(default).lower()),
                    ),
                )


def downgrade() -> None:
    # Check if columns exist before dropping
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "moderation_session" in existing_tables:
        moderation_session_columns = [
            col["name"] for col in inspector.get_columns("moderation_session")
        ]
        columns_to_drop = [
            "attention_check_passed",
            "attention_check_selected",
            "is_attention_check",
        ]
        for col_name in columns_to_drop:
            if col_name in moderation_session_columns:
                op.drop_column("moderation_session", col_name)
