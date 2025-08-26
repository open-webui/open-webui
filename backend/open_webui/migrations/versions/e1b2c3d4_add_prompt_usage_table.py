"""add prompt usage table

Revision ID: e1b2c3d4
Revises: d31026856c01
Create Date: 2025-08-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db

# revision identifiers, used by Alembic.
revision: str = "e1b2c3d4"
down_revision: Union[str, None] = "d31026856c01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "prompt_usage",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("used_date", sa.Date(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.BigInteger()),
        sa.Column("updated_at", sa.BigInteger()),
        sa.UniqueConstraint("user_id", "prompt", "used_date", name="uq_user_prompt_date"),
        schema=open_webui.internal.db.metadata_obj.schema,
    )


def downgrade() -> None:
    op.drop_table("prompt_usage", schema=open_webui.internal.db.metadata_obj.schema) 