"""merge_scenario_tracking_heads

Revision ID: ae8bccdc8e36
Revises: 84b2215f7772, o00p11q22r33
Create Date: 2026-01-06 15:33:20.575245

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = 'ae8bccdc8e36'
down_revision: Union[str, None] = ('84b2215f7772', 'o00p11q22r33')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
