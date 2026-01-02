"""Merge analytics branch with main branch

Revision ID: merge_analytics_001
Revises: b8c3a5e91f24, f334c211be92
Create Date: 2026-01-02

This migration merges the analytics tables branch with the main migration branch
to resolve the multiple heads issue.
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "merge_analytics_001"
down_revision = ("b8c3a5e91f24", "f334c211be92")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This is a merge migration - no schema changes needed
    pass


def downgrade() -> None:
    # This is a merge migration - no schema changes needed
    pass
