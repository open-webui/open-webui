"""Add workflow_reset_at to user table

Revision ID: v88w99x00y11
Revises: u77v88w99x00
Create Date: 2026-02-13 00:00:00.000000

Stores timestamp of last workflow reset. Moderation sessions created before
this time are excluded from workflow state (moderation_completed_count).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = "v88w99x00y11"
down_revision: Union[str, None] = "u77v88w99x00"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    if "user" not in inspector.get_table_names():
        return

    columns = [col["name"] for col in inspector.get_columns("user")]
    if "workflow_reset_at" not in columns:
        op.add_column(
            "user", sa.Column("workflow_reset_at", sa.BigInteger(), nullable=True)
        )


def downgrade() -> None:
    op.drop_column("user", "workflow_reset_at")
