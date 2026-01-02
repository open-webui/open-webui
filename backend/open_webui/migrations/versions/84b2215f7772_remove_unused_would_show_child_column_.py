"""Remove unused would_show_child column from moderation_session

Revision ID: 84b2215f7772
Revises: x1y2z3a4b5c6
Create Date: 2025-12-31 16:46:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = "84b2215f7772"
down_revision: Union[str, None] = "x1y2z3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove would_show_child column from moderation_session table.
    
    This column was deprecated and is no longer used in the application.
    It exists in the database but is not defined in the SQLAlchemy model,
    causing potential runtime errors.
    """
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()
    
    if "moderation_session" in existing_tables:
        moderation_session_columns = [col["name"] for col in inspector.get_columns("moderation_session")]
        if "would_show_child" in moderation_session_columns:
            op.drop_column("moderation_session", "would_show_child")


def downgrade() -> None:
    """
    Re-add would_show_child column for rollback purposes.
    """
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()
    
    if "moderation_session" in existing_tables:
        moderation_session_columns = [col["name"] for col in inspector.get_columns("moderation_session")]
        if "would_show_child" not in moderation_session_columns:
            op.add_column("moderation_session", sa.Column("would_show_child", sa.Text(), nullable=True))
