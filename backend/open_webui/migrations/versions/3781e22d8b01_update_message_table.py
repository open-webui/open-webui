"""Update message & channel tables

Revision ID: 3781e22d8b01
Revises: 7826ab40b532
Create Date: 2024-12-30 03:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = "3781e22d8b01"
down_revision = "7826ab40b532"
branch_labels = None
depends_on = None


def upgrade():
    # Check if columns/tables already exist (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()
    
    # Add 'type' column to the 'channel' table if it doesn't exist
    if "channel" in existing_tables:
        channel_columns = [col["name"] for col in inspector.get_columns("channel")]
        if "type" not in channel_columns:
            op.add_column(
                "channel",
                sa.Column("type", sa.Text(), nullable=True),
            )
    
    # Add 'parent_id' column to the 'message' table if it doesn't exist
    if "message" in existing_tables:
        message_columns = [col["name"] for col in inspector.get_columns("message")]
        if "parent_id" not in message_columns:
            op.add_column(
                "message",
                sa.Column("parent_id", sa.Text(), nullable=True),
            )
    
    # Create 'message_reaction' table if it doesn't exist
    if "message_reaction" not in existing_tables:
        op.create_table(
            "message_reaction",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True, unique=True),
            sa.Column("user_id", sa.Text(), nullable=False),
            sa.Column("message_id", sa.Text(), nullable=False),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("created_at", sa.BigInteger(), nullable=True),
        )
    
    # Create 'channel_member' table if it doesn't exist
    if "channel_member" not in existing_tables:
        op.create_table(
            "channel_member",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True, unique=True),
            sa.Column("channel_id", sa.Text(), nullable=False),
            sa.Column("user_id", sa.Text(), nullable=False),
            sa.Column("created_at", sa.BigInteger(), nullable=True),
        )


def downgrade():
    # Check if columns/tables exist before dropping
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()
    
    # Drop 'type' column from 'channel' table if it exists
    if "channel" in existing_tables:
        channel_columns = [col["name"] for col in inspector.get_columns("channel")]
        if "type" in channel_columns:
            op.drop_column("channel", "type")
    
    # Drop 'parent_id' column from 'message' table if it exists
    if "message" in existing_tables:
        message_columns = [col["name"] for col in inspector.get_columns("message")]
        if "parent_id" in message_columns:
            op.drop_column("message", "parent_id")
    
    # Drop tables if they exist
    if "message_reaction" in existing_tables:
        op.drop_table("message_reaction")
    
    if "channel_member" in existing_tables:
        op.drop_table("channel_member")
