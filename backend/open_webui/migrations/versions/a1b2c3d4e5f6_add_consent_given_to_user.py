"""add_consent_given_to_user

Revision ID: a1b2c3d4e5f6
Revises: fedcba987654
Create Date: 2025-01-15 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "fedcba987654"
branch_labels = None
depends_on = None


def upgrade():
    # Check if column already exists (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "user" in existing_tables:
        user_columns = [col["name"] for col in inspector.get_columns("user")]
        if "consent_given" not in user_columns:
            # Add consent_given column to user table
            op.add_column(
                "user",
                sa.Column(
                    "consent_given",
                    sa.Boolean(),
                    nullable=True,
                    server_default=sa.text("false"),
                ),
            )


def downgrade():
    # Check if column exists before dropping
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "user" in existing_tables:
        user_columns = [col["name"] for col in inspector.get_columns("user")]
        if "consent_given" in user_columns:
            # Remove consent_given column
            op.drop_column("user", "consent_given")
