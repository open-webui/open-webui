"""Remove parenting_style column from child_profile table

Revision ID: gg11hh22ii33
Revises: fedcba987654
Create Date: 2025-01-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = "gg11hh22ii33"
down_revision = "fedcba987654"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if column exists before dropping (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "child_profile" in existing_tables:
        child_profile_columns = [
            col["name"] for col in inspector.get_columns("child_profile")
        ]
        if "parenting_style" in child_profile_columns:
            # Remove parenting_style column from child_profile table
            with op.batch_alter_table("child_profile") as batch_op:
                batch_op.drop_column("parenting_style")


def downgrade() -> None:
    # Check if column exists before adding (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "child_profile" in existing_tables:
        child_profile_columns = [
            col["name"] for col in inspector.get_columns("child_profile")
        ]
        if "parenting_style" not in child_profile_columns:
            # Add parenting_style column back for rollback
            with op.batch_alter_table("child_profile") as batch_op:
                batch_op.add_column(
                    sa.Column("parenting_style", sa.String(), nullable=True)
                )
