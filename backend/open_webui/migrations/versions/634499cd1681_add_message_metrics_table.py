"""add message metrics table

Revision ID: 634499cd1681
Revises: 5233b3d5b959
Create Date: 2025-04-04 10:51:42.318906

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "634499cd1681"
down_revision: Union[str, None] = "5233b3d5b959"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "message_metrics",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("user_id", sa.Text, nullable=False),
        sa.Column("user_domain", sa.Text, nullable=False),
        sa.Column("model", sa.Text, nullable=False),
        sa.Column("completion_tokens", sa.BigInteger, nullable=False),
        sa.Column("prompt_tokens", sa.BigInteger, nullable=False),
        sa.Column("total_tokens", sa.BigInteger, nullable=False),
        sa.Column("created_at", sa.BigInteger, nullable=False),
    )


def downgrade():
    op.drop_table("message_metrics")
