"""
Merge workflow-related heads (stage 1)

Revision ID: k56l67m78n89
Revises: aa11bb22cc33, ab12cd34ef56, gg11hh22ii33
Create Date: 2025-01-20
"""

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401

# revision identifiers, used by Alembic.
revision = "k56l67m78n89"
down_revision = (
    "aa11bb22cc33",
    "ab12cd34ef56",
    "gg11hh22ii33",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge-only revision; no ops needed
    pass


def downgrade() -> None:
    # Merge-only revision; no ops needed
    pass


