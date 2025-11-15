"""Migration bridge from dev_api_improvements branch

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2024-12-20 13:00:00.000000

This is a no-op migration file that exists to handle the case where the database
was migrated using the dev_api_improvements branch (which includes performance
indexes and GIN indexes on JSONB columns), but the current branch doesn't include
those migration files.

This migration acts as a bridge so Alembic can recognize the database state
without requiring the actual migration files from dev_api_improvements.

IMPORTANT: This migration should NOT be applied if it hasn't already been applied.
If the database is at an earlier revision, Alembic will try to upgrade to this
revision, but since this is a no-op, it's safe.

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    """
    No-op upgrade function.
    
    This migration exists only to bridge the gap when switching branches.
    The database may already have indexes and JSONB columns from the
    dev_api_improvements branch, but we don't want to recreate them here.
    
    If the database is already at this revision, this function does nothing.
    If the database is at 3781e22d8b01, this function does nothing (no-op),
    but Alembic will mark the database as being at this revision.
    """
    # No operations needed - this is just a marker migration
    pass


def downgrade():
    """
    No-op downgrade function.
    
    This migration cannot be properly downgraded without the original
    migration files from dev_api_improvements. However, since this is
    a no-op, downgrading is also a no-op.
    """
    # No operations needed
    pass

