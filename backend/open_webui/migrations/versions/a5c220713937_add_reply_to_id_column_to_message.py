"""Add reply_to_id column to message

Revision ID: a5c220713937
Revises: 38d63c18f30f
Create Date: 2025-09-27 02:24:18.058455

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = "a5c220713937"
down_revision: Union[str, None] = "38d63c18f30f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if column already exists (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()
    
    if "message" in existing_tables:
        message_columns = [col["name"] for col in inspector.get_columns("message")]
        if "reply_to_id" not in message_columns:
            # Add 'reply_to_id' column to the 'message' table for replying to messages
            op.add_column(
                "message",
                sa.Column("reply_to_id", sa.Text(), nullable=True),
            )


def downgrade() -> None:
    # Check if column exists before dropping
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()
    
    if "message" in existing_tables:
        message_columns = [col["name"] for col in inspector.get_columns("message")]
        if "reply_to_id" in message_columns:
            # Remove 'reply_to_id' column from the 'message' table
            op.drop_column("message", "reply_to_id")
