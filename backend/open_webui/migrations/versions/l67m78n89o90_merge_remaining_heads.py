"""
Merge all remaining heads (final merge)

Revision ID: l67m78n89o90
Revises: k56l67m78n89, i34j45k56l67
Create Date: 2025-01-20

Note: Only merging the two heads that are actually in the database.
Other heads (ee88bb99cc11, f2g3h4i5j6k7, fe12ab34cd56) will be merged separately
if they get applied to the database.
"""

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401

# revision identifiers, used by Alembic.
revision = "l67m78n89o90"
down_revision = (
    "k56l67m78n89",
    "i34j45k56l67",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge-only revision; no ops needed
    pass


def downgrade() -> None:
    # Merge-only revision; no ops needed
    pass

