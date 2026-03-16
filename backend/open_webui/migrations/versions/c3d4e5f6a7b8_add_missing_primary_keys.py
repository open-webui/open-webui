"""add missing primary keys to legacy peewee tables

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-13 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = [
    ("chat", "id"),
    ("chatidtag", "id"),
    ("file", "id"),
    ("function", "id"),
    ("memory", "id"),
    ("model", "id"),
    ("tool", "id"),
]


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    for table, column in TABLES:
        pk = inspector.get_pk_constraint(table)
        if column in (pk.get("constrained_columns") or []):
            continue

        unique_constraints = inspector.get_unique_constraints(table)
        with op.batch_alter_table(table, schema=None) as batch_op:
            for uc in unique_constraints:
                if uc.get("column_names") == [column]:
                    batch_op.drop_constraint(uc["name"], type_="unique")
            batch_op.create_primary_key(f"pk_{column}", [column])


def downgrade() -> None:
    for table, column in TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_constraint(f"pk_{column}", type_="primary")
