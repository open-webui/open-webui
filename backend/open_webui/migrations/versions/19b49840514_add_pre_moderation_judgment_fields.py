"""add_pre_moderation_judgment_fields

Revision ID: 19b49840514
Revises: e90f6b649d97
Create Date: 2025-01-22 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = '19b49840514'
down_revision: Union[str, None] = 'e90f6b649d97'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add pre-moderation judgment fields to moderation_session table.
    
    These fields are collected in Step 3 before any moderation/editing:
    - concern_level: Integer 1-5 (Likert scale for concern level)
    - would_show_child: String 'yes' | 'no' (whether parent would show child response as-is)
    
    Migration is idempotent - checks for column existence before adding.
    """
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_columns = [col["name"] for col in inspector.get_columns("moderation_session")]
    
    with op.batch_alter_table("moderation_session") as batch_op:
        if "concern_level" not in existing_columns:
            batch_op.add_column(sa.Column("concern_level", sa.Integer(), nullable=True))
        if "would_show_child" not in existing_columns:
            batch_op.add_column(sa.Column("would_show_child", sa.Text(), nullable=True))


def downgrade() -> None:
    """
    Remove pre-moderation judgment fields from moderation_session table.
    """
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_columns = [col["name"] for col in inspector.get_columns("moderation_session")]
    
    with op.batch_alter_table("moderation_session") as batch_op:
        if "concern_level" in existing_columns:
            batch_op.drop_column("concern_level")
        if "would_show_child" in existing_columns:
            batch_op.drop_column("would_show_child")


