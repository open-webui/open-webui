"""merge gmail sync and main branch migrations

Revision ID: 0b80d222da03
Revises: 33cc3721a72, 9ff8e65eafda
Create Date: 2025-10-17 13:30:54.585477

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = '0b80d222da03'
down_revision: Union[str, None] = ('33cc3721a72', '80d73eec17ce')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
