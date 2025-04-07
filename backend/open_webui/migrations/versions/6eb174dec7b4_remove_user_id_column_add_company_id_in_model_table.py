"""Remove user_id column, add company_id column in model table

Revision ID: 6eb174dec7b4
Revises: 9ca43b058511
Create Date: 2025-02-10 16:14:39.127920

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = '6eb174dec7b4'
down_revision: Union[str, None] = '9ca43b058511'

def column_exists(table, column):
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = inspector.get_columns(table)
    return any(c["name"] == column for c in columns)


def upgrade() -> None:
    return None

def downgrade() -> None:
    return None