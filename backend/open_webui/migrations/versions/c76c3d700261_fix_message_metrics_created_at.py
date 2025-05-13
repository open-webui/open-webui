"""Fix message_metrics created_at

Revision ID: c76c3d700261
Revises: 634499cd1681
Create Date: 2025-05-12 11:42:45.632822

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


# revision identifiers, used by Alembic.
revision: str = "c76c3d700261"
down_revision: Union[str, None] = "634499cd1681"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    message_metrics = table("message_metrics", column("created_at", sa.BigInteger))
    op.execute(
        message_metrics.update().values(
            {"created_at": message_metrics.c.created_at / 1000000000}
        )
    )


def downgrade() -> None:
    message_metrics = table("message_metrics", column("created_at", sa.BigInteger))
    op.execute(
        message_metrics.update().values(
            {"created_at": message_metrics.c.created_at * 1000000000}
        )
    )
