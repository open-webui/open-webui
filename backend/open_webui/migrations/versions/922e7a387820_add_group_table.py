"""Add group table

Revision ID: 922e7a387820
Revises: 4ace53fd72c8
Create Date: 2024-11-14 03:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "922e7a387820"
down_revision = "4ace53fd72c8"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    op.create_table(
        "group",
        sa.Column("id", sa.String(length=255), nullable=False, primary_key=True, unique=True),
        sa.Column("user_id", sa.String(length=255), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("permissions", sa.JSON(), nullable=True),
        sa.Column("user_ids", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.BigInteger(), nullable=True),
    )

    def column_missing(table_name: str, column_name: str) -> bool:
        if table_name not in existing_tables:
            return False
        return column_name not in {col["name"] for col in inspector.get_columns(table_name)}

    # Add 'access_control' column to 'model' table
    if column_missing("model", "access_control"):
        op.add_column(
            "model",
            sa.Column("access_control", sa.JSON(), nullable=True),
        )

    # Add 'is_active' column to 'model' table
    if column_missing("model", "is_active"):
        op.add_column(
            "model",
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.sql.expression.true(),
            ),
        )

    # Add 'access_control' column to 'knowledge' table
    if column_missing("knowledge", "access_control"):
        op.add_column(
            "knowledge",
            sa.Column("access_control", sa.JSON(), nullable=True),
        )

    # Add 'access_control' column to 'prompt' table
    if column_missing("prompt", "access_control"):
        op.add_column(
            "prompt",
            sa.Column("access_control", sa.JSON(), nullable=True),
        )

    # Add 'access_control' column to 'tools' table
    if column_missing("tool", "access_control"):
        op.add_column(
            "tool",
            sa.Column("access_control", sa.JSON(), nullable=True),
        )


def downgrade():
    op.drop_table("group")

    # Drop 'access_control' column from 'model' table
    op.drop_column("model", "access_control")

    # Drop 'is_active' column from 'model' table
    op.drop_column("model", "is_active")

    # Drop 'access_control' column from 'knowledge' table
    op.drop_column("knowledge", "access_control")

    # Drop 'access_control' column from 'prompt' table
    op.drop_column("prompt", "access_control")

    # Drop 'access_control' column from 'tools' table
    op.drop_column("tool", "access_control")
