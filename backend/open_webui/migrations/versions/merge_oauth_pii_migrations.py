"""Merge oauth_session and pii_detection migrations

Revision ID: merge_oauth_pii_001
Revises: 38d63c18f30f, aac72a474c6b
Create Date: 2025-01-27 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "merge_oauth_pii_001"
down_revision: Union[str, None] = ("38d63c18f30f", "aac72a474c6b")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This is a merge migration - no database changes needed
    # Both migrations have already been applied
    pass


def downgrade() -> None:
    # This is a merge migration - no database changes needed
    pass
