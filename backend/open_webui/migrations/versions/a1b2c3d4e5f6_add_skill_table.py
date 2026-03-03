"""Add skill table

Revision ID: a1b2c3d4e5f6
Revises: f1e2d3c4b5a6
Create Date: 2026-02-11 09:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from open_webui.migrations.util import get_existing_tables

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f1e2d3c4b5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing_tables = set(get_existing_tables())

    if "skill" not in existing_tables:
        op.create_table(
            "skill",
            sa.Column("id", sa.String(), nullable=False, primary_key=True),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("name", sa.Text(), nullable=False, unique=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
        )
        op.create_index("idx_skill_user_id", "skill", ["user_id"])
        op.create_index("idx_skill_updated_at", "skill", ["updated_at"])


def downgrade() -> None:
    op.drop_index("idx_skill_updated_at", table_name="skill")
    op.drop_index("idx_skill_user_id", table_name="skill")
    op.drop_table("skill")
