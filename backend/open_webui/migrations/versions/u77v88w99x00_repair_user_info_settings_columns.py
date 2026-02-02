"""repair user info/settings column names

Repairs state where b10670c03dd5 converted info/settings to JSON but the
rename step (info_json -> info, settings_json -> settings) did not complete,
leaving the table with *_json columns that the User model does not expect.

Revision ID: u77v88w99x00
Revises: t66u77v88w99
Create Date: 2026-02-02 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = "u77v88w99x00"
down_revision: Union[str, None] = "t66u77v88w99"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    if "user" not in inspector.get_table_names():
        return

    columns = [col["name"] for col in inspector.get_columns("user")]

    # Repair: if we have *_json but not the final column name, rename (SQLite 3.25+)
    if "info_json" in columns and "info" not in columns:
        op.execute(sa.text('ALTER TABLE "user" RENAME COLUMN info_json TO info'))
    if "settings_json" in columns and "settings" not in columns:
        op.execute(sa.text('ALTER TABLE "user" RENAME COLUMN settings_json TO settings'))


def downgrade() -> None:
    """No-op; repair is one-way."""
    pass
