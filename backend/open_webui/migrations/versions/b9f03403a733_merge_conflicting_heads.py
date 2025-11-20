"""merge conflicting heads

Revision ID: b9f03403a733
Revises: a5c220713937, 8257b99d21e3
Create Date: 2025-09-24 23:21:06.424390

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


revision: str = "b9f03403a733"
down_revision: Union[str, Sequence[str], None] = ("a5c220713937", "8257b99d21e3")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No-op merge; both branches are already applied.
    pass


def downgrade() -> None:
    # No-op; to fully undo you'd need to downgrade past both parents.
    pass