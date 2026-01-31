"""add_consent_audit_table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-01-15 11:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    # Check if table already exists (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "consent_audit" not in existing_tables:
        op.create_table(
            "consent_audit",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("timestamp_utc", sa.BigInteger(), nullable=False),
            sa.Column("consent_version", sa.String(), nullable=True),
            sa.Column("prolific_pid", sa.String(), nullable=True),
            sa.Column("study_id", sa.String(), nullable=True),
            sa.Column("session_id", sa.String(), nullable=True),
            sa.Column("ui_version", sa.String(), nullable=True),
            sa.Column("user_agent", sa.Text(), nullable=True),
            sa.Column(
                "consent_given",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.PrimaryKeyConstraint("id"),
        )

        op.create_index("idx_consent_audit_user", "consent_audit", ["user_id"])
        op.create_index(
            "idx_consent_audit_timestamp", "consent_audit", ["timestamp_utc"]
        )
        op.create_index("idx_consent_audit_prolific", "consent_audit", ["prolific_pid"])
    else:
        # Table exists, check if indexes exist
        existing_indexes = [
            idx["name"] for idx in inspector.get_indexes("consent_audit")
        ]
        indexes_to_create = [
            ("idx_consent_audit_user", ["user_id"]),
            ("idx_consent_audit_timestamp", ["timestamp_utc"]),
            ("idx_consent_audit_prolific", ["prolific_pid"]),
        ]
        for idx_name, columns in indexes_to_create:
            if idx_name not in existing_indexes:
                op.create_index(idx_name, "consent_audit", columns)


def downgrade():
    # Check if table exists before dropping
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "consent_audit" in existing_tables:
        existing_indexes = [
            idx["name"] for idx in inspector.get_indexes("consent_audit")
        ]
        indexes_to_drop = [
            "idx_consent_audit_prolific",
            "idx_consent_audit_timestamp",
            "idx_consent_audit_user",
        ]
        for idx_name in indexes_to_drop:
            if idx_name in existing_indexes:
                op.drop_index(idx_name, table_name="consent_audit")
        op.drop_table("consent_audit")
