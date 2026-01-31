"""
Add Step 2-3 columns to moderation_session

Revision ID: a1b2c3d4e5f7
Revises: fe12ab34cd56
Create Date: 2025-01-XX
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f7"
down_revision = "fe12ab34cd56"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add Step 2-3 columns to moderation_session table.
    Migration is idempotent - checks for column existence before adding.
    """
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_columns = [
        col["name"] for col in inspector.get_columns("moderation_session")
    ]

    with op.batch_alter_table("moderation_session") as batch_op:
        # Step 2 fields
        if "concern_reason" not in existing_columns:
            batch_op.add_column(sa.Column("concern_reason", sa.Text(), nullable=True))

        # Step 3 fields
        if "satisfaction_level" not in existing_columns:
            batch_op.add_column(
                sa.Column("satisfaction_level", sa.Integer(), nullable=True)
            )
        if "satisfaction_reason" not in existing_columns:
            batch_op.add_column(
                sa.Column("satisfaction_reason", sa.Text(), nullable=True)
            )
        if "next_action" not in existing_columns:
            batch_op.add_column(sa.Column("next_action", sa.Text(), nullable=True))

        # Timestamp fields
        if "decided_at" not in existing_columns:
            batch_op.add_column(sa.Column("decided_at", sa.BigInteger(), nullable=True))
        if "highlights_saved_at" not in existing_columns:
            batch_op.add_column(
                sa.Column("highlights_saved_at", sa.BigInteger(), nullable=True)
            )
        if "saved_at" not in existing_columns:
            batch_op.add_column(sa.Column("saved_at", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("moderation_session") as batch_op:
        batch_op.drop_column("saved_at")
        batch_op.drop_column("highlights_saved_at")
        batch_op.drop_column("decided_at")
        batch_op.drop_column("next_action")
        batch_op.drop_column("satisfaction_reason")
        batch_op.drop_column("satisfaction_level")
        batch_op.drop_column("concern_reason")
