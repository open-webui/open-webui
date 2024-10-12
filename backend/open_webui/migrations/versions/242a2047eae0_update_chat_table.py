"""Update chat table

Revision ID: 242a2047eae0
Revises: 6a39f3d8e55c
Create Date: 2024-10-09 21:02:35.241684

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, select, update

import json

revision = "242a2047eae0"
down_revision = "6a39f3d8e55c"
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Rename current 'chat' column to 'old_chat'
    op.alter_column("chat", "chat", new_column_name="old_chat", existing_type=sa.Text)

    # Step 2: Add new 'chat' column of type JSON
    op.add_column("chat", sa.Column("chat", sa.JSON(), nullable=True))

    # Step 3: Migrate data from 'old_chat' to 'chat'
    chat_table = table(
        "chat",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("old_chat", sa.Text),
        sa.Column("chat", sa.JSON()),
    )

    # - Selecting all data from the table
    connection = op.get_bind()
    results = connection.execute(select(chat_table.c.id, chat_table.c.old_chat))
    for row in results:
        try:
            # Convert text JSON to actual JSON object, assuming the text is in JSON format
            json_data = json.loads(row.old_chat)
        except json.JSONDecodeError:
            json_data = None  # Handle cases where the text cannot be converted to JSON

        connection.execute(
            sa.update(chat_table)
            .where(chat_table.c.id == row.id)
            .values(chat=json_data)
        )

    # Step 4: Drop 'old_chat' column
    op.drop_column("chat", "old_chat")


def downgrade():
    # Step 1: Add 'old_chat' column back as Text
    op.add_column("chat", sa.Column("old_chat", sa.Text(), nullable=True))

    # Step 2: Convert 'chat' JSON data back to text and store in 'old_chat'
    chat_table = table(
        "chat",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("chat", sa.JSON()),
        sa.Column("old_chat", sa.Text()),
    )

    connection = op.get_bind()
    results = connection.execute(select(chat_table.c.id, chat_table.c.chat))
    for row in results:
        text_data = json.dumps(row.chat) if row.chat is not None else None
        connection.execute(
            sa.update(chat_table)
            .where(chat_table.c.id == row.id)
            .values(old_chat=text_data)
        )

    # Step 3: Remove the new 'chat' JSON column
    op.drop_column("chat", "chat")

    # Step 4: Rename 'old_chat' back to 'chat'
    op.alter_column("chat", "old_chat", new_column_name="chat", existing_type=sa.Text)
