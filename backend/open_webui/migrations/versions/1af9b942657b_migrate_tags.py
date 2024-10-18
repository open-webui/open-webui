"""Migrate tags

Revision ID: 1af9b942657b
Revises: 242a2047eae0
Create Date: 2024-10-09 21:02:35.241684

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, select, update, column
from sqlalchemy.engine.reflection import Inspector

import json

revision = "1af9b942657b"
down_revision = "242a2047eae0"
branch_labels = None
depends_on = None


def upgrade():
    # Setup an inspection on the existing table to avoid issues
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    # Clean up potential leftover temp table from previous failures
    conn.execute(sa.text("DROP TABLE IF EXISTS _alembic_tmp_tag"))

    # Check if the 'tag' table exists
    tables = inspector.get_table_names()

    # Step 1: Modify Tag table using batch mode for SQLite support
    if "tag" in tables:
        # Get the current columns in the 'tag' table
        columns = [col["name"] for col in inspector.get_columns("tag")]

        # Get any existing unique constraints on the 'tag' table
        current_constraints = inspector.get_unique_constraints("tag")

        with op.batch_alter_table("tag", schema=None) as batch_op:
            # Check if the unique constraint already exists
            if not any(
                constraint["name"] == "uq_id_user_id"
                for constraint in current_constraints
            ):
                # Create unique constraint if it doesn't exist
                batch_op.create_unique_constraint("uq_id_user_id", ["id", "user_id"])

            # Check if the 'data' column exists before trying to drop it
            if "data" in columns:
                batch_op.drop_column("data")

            # Check if the 'meta' column needs to be created
            if "meta" not in columns:
                # Add the 'meta' column if it doesn't already exist
                batch_op.add_column(sa.Column("meta", sa.JSON(), nullable=True))

    tag = table(
        "tag",
        column("id", sa.String()),
        column("name", sa.String()),
        column("user_id", sa.String()),
        column("meta", sa.JSON()),
    )

    # Step 2: Migrate tags
    conn = op.get_bind()
    result = conn.execute(sa.select(tag.c.id, tag.c.name, tag.c.user_id))

    tag_updates = {}
    for row in result:
        new_id = row.name.replace(" ", "_").lower()
        tag_updates[row.id] = new_id

    for tag_id, new_tag_id in tag_updates.items():
        print(f"Updating tag {tag_id} to {new_tag_id}")
        if new_tag_id == "pinned":
            # delete tag
            delete_stmt = sa.delete(tag).where(tag.c.id == tag_id)
            conn.execute(delete_stmt)
        else:
            # Check if the new_tag_id already exists in the database
            existing_tag_query = sa.select(tag.c.id).where(tag.c.id == new_tag_id)
            existing_tag_result = conn.execute(existing_tag_query).fetchone()

            if existing_tag_result:
                # Handle duplicate case: the new_tag_id already exists
                print(
                    f"Tag {new_tag_id} already exists. Removing current tag with ID {tag_id} to avoid duplicates."
                )
                # Option 1: Delete the current tag if an update to new_tag_id would cause duplication
                delete_stmt = sa.delete(tag).where(tag.c.id == tag_id)
                conn.execute(delete_stmt)
            else:
                update_stmt = sa.update(tag).where(tag.c.id == tag_id)
                update_stmt = update_stmt.values(id=new_tag_id)
                conn.execute(update_stmt)

    # Add columns `pinned` and `meta` to 'chat'
    op.add_column("chat", sa.Column("pinned", sa.Boolean(), nullable=True))
    op.add_column(
        "chat", sa.Column("meta", sa.JSON(), nullable=False, server_default="{}")
    )

    chatidtag = table(
        "chatidtag", column("chat_id", sa.String()), column("tag_name", sa.String())
    )
    chat = table(
        "chat",
        column("id", sa.String()),
        column("pinned", sa.Boolean()),
        column("meta", sa.JSON()),
    )

    # Fetch existing tags
    conn = op.get_bind()
    result = conn.execute(sa.select(chatidtag.c.chat_id, chatidtag.c.tag_name))

    chat_updates = {}
    for row in result:
        chat_id = row.chat_id
        tag_name = row.tag_name.replace(" ", "_").lower()

        if tag_name == "pinned":
            # Specifically handle 'pinned' tag
            if chat_id not in chat_updates:
                chat_updates[chat_id] = {"pinned": True, "meta": {}}
            else:
                chat_updates[chat_id]["pinned"] = True
        else:
            if chat_id not in chat_updates:
                chat_updates[chat_id] = {"pinned": False, "meta": {"tags": [tag_name]}}
            else:
                tags = chat_updates[chat_id]["meta"].get("tags", [])
                tags.append(tag_name)

                chat_updates[chat_id]["meta"]["tags"] = list(set(tags))

    # Update chats based on accumulated changes
    for chat_id, updates in chat_updates.items():
        update_stmt = sa.update(chat).where(chat.c.id == chat_id)
        update_stmt = update_stmt.values(
            meta=updates.get("meta", {}), pinned=updates.get("pinned", False)
        )
        conn.execute(update_stmt)
    pass


def downgrade():
    pass
