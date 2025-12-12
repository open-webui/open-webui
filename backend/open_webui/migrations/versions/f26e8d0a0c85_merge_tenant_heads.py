"""Merge tenant schema heads

Revision ID: f26e8d0a0c85
Revises: c3a9f4a9d9b8, e6e6f4c2d451
Create Date: 2025-02-25 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f26e8d0a0c85"
down_revision: Union[str, Sequence[str], None] = ("c3a9f4a9d9b8", "e6e6f4c2d451")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Schema already migrated by parent revisions."""
    pass


def downgrade() -> None:
    """Downgrade handled by individual parent revisions."""
    pass
