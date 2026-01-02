"""Merge heads: step2_step3_columns and pre_moderation_judgment

Revision ID: x1y2z3a4b5c6
Revises: 19b49840514, a1b2c3d4e5f7
Create Date: 2025-01-XX
"""

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401

# revision identifiers, used by Alembic.
revision = "x1y2z3a4b5c6"
down_revision = ("19b49840514", "a1b2c3d4e5f7")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge-only revision; no ops needed
    # Both branches have already been applied
    pass


def downgrade() -> None:
    # Merge-only revision; no ops needed
    pass

