"""
Merge assignment session activity and consent audit heads

Revision ID: h23i45j67k89
Revises: g12h34i56j78, c3d4e5f6a7b8
Create Date: 2025-01-20
"""

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401

# revision identifiers, used by Alembic.
revision = "h23i45j67k89"
down_revision = ("g12h34i56j78", "c3d4e5f6a7b8")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge-only revision; no ops needed
    pass


def downgrade() -> None:
    # Merge-only revision; no ops needed
    pass

