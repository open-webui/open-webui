"""merge_all_heads

Revision ID: df887c71f080
Revises: c440947495f3, mha2j7qa5ibz, r44s55t66u77
Create Date: 2026-01-31 17:36:42.585579

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = "df887c71f080"
down_revision: Union[str, None] = ("c440947495f3", "mha2j7qa5ibz", "r44s55t66u77")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
