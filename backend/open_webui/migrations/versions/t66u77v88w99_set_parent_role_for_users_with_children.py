"""set parent role for users with children

Revision ID: t66u77v88w99
Revises: s55t66u77v88
Create Date: 2026-02-01 22:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = "t66u77v88w99"
down_revision: Union[str, None] = "s55t66u77v88"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Set role='parent' for users who have role='user' and at least one child."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    if "user" not in inspector.get_table_names():
        return

    op.execute("""
        UPDATE "user"
        SET role = 'parent'
        WHERE role = 'user'
          AND id IN (SELECT DISTINCT parent_id FROM "user" WHERE parent_id IS NOT NULL)
    """)


def downgrade() -> None:
    """No-op: cannot safely revert without knowing original roles."""
    pass
