"""add tenant table

Revision ID: f2c9b3e46a8e
Revises: a5c220713937
Create Date: 2025-11-17 10:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from open_webui.internal.db import JSONField

# revision identifiers, used by Alembic.
revision: str = "f2c9b3e46a8e"
down_revision: Union[str, None] = "a5c220713937"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenant",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("model_names", JSONField(), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.add_column("user", sa.Column("tenant_id", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("user", "tenant_id")
    op.drop_table("tenant")
