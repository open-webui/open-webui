"""Merge email 2FA and eula heads

Revision ID: 2f7a4f1c9b2a
Revises: 1d2f0c5a0b1e, 2e91d6c25ecd
Create Date: 2025-03-06 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2f7a4f1c9b2a"
down_revision: Union[str, Sequence[str], None] = ("1d2f0c5a0b1e", "2e91d6c25ecd")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge heads only."""
    pass


def downgrade() -> None:
    """Downgrade handled by individual parent revisions."""
    pass
