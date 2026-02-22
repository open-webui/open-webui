"""Drop unique index on tag(id) if it exists

The tag table uses a composite PK (id, user_id). A leftover unique index on
tag.id alone (from the original schema) can cause duplicate-key errors when
different users create tags with the same name. This migration drops any such
index if it exists.

Fixes: #21737

Revision ID: c8d4e5f6a7b8
Revises: a5c220713937
Create Date: 2025-02-22 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = "c8d4e5f6a7b8"
down_revision: Union[str, None] = "a5c220713937"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    if "tag" not in inspector.get_table_names():
        return

    indexes = inspector.get_indexes("tag")
    for idx in indexes:
        # Look for unique indexes on "id" alone (conflicts with composite PK)
        if not idx.get("unique"):
            continue
        columns = idx.get("column_names") or []
        if columns == ["id"]:
            index_name = idx.get("name")
            if index_name:
                with op.batch_alter_table("tag", schema=None) as batch_op:
                    try:
                        batch_op.drop_index(index_name)
                    except Exception:
                        pass  # Index may not exist or have different name


def downgrade() -> None:
    # No-op: we don't recreate the problematic index
    pass
