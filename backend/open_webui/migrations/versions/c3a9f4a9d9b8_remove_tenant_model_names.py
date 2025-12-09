"""Remove tenant-specific model assignments

Revision ID: c3a9f4a9d9b8
Revises: bc3c0cc2e7ba
Create Date: 2025-02-14 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from open_webui.internal.db import JSONField

# revision identifiers, used by Alembic.
revision: str = "c3a9f4a9d9b8"
down_revision: Union[str, None] = "bc3c0cc2e7ba"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("tenant") as batch_op:
        batch_op.drop_column("model_names")


def downgrade() -> None:
    with op.batch_alter_table("tenant") as batch_op:
        batch_op.add_column(sa.Column("model_names", JSONField(), nullable=True))

    connection = op.get_bind()
    connection.execute(sa.text("UPDATE tenant SET model_names = '[]'"))

    with op.batch_alter_table("tenant") as batch_op:
        batch_op.alter_column(
            "model_names",
            existing_type=JSONField(),
            nullable=False,
        )
