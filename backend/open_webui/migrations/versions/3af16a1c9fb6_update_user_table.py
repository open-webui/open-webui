"""update user table

Revision ID: 3af16a1c9fb6
Revises: 018012973d35
Create Date: 2025-08-21 02:07:18.078283

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = "3af16a1c9fb6"
down_revision: Union[str, None] = "018012973d35"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if columns already exist (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "user" in existing_tables:
        user_columns = [col["name"] for col in inspector.get_columns("user")]
        columns_to_add = [
            ("username", sa.String(length=50)),
            ("bio", sa.Text()),
            ("gender", sa.Text()),
            ("date_of_birth", sa.Date()),
        ]
        for col_name, col_type in columns_to_add:
            if col_name not in user_columns:
                op.add_column("user", sa.Column(col_name, col_type, nullable=True))


def downgrade() -> None:
    # Check if columns exist before dropping
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "user" in existing_tables:
        user_columns = [col["name"] for col in inspector.get_columns("user")]
        columns_to_drop = ["username", "bio", "gender", "date_of_birth"]
        for col_name in columns_to_drop:
            if col_name in user_columns:
                op.drop_column("user", col_name)
