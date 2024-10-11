"""add attached prompt property

Revision ID: 9d8f40f46d40
Revises: 242a2047eae0
Create Date: 2024-10-10 14:29:26.684870

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.apps.webui.internal.db
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9d8f40f46d40"
down_revision: Union[str, None] = "242a2047eae0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("prompt", sa.Column("attached", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("prompt", "attached")
