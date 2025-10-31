"""
Merge heads for attention check columns

Revision ID: ff23ac45bd67
Revises: ee88bb99cc11, fe12ab34cd56
Create Date: 2025-10-30
"""

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401

# revision identifiers, used by Alembic.
revision = "ff23ac45bd67"
down_revision = ("ee88bb99cc11", "fe12ab34cd56")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge-only revision; no ops needed
    pass


def downgrade() -> None:
    # Merge-only revision; no ops needed
    pass
