"""Add knowledge_file table

Revision ID: 06aec582b5b3
Revises: 018012973d35
Create Date: 2025-11-18 22:45:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column, select
import json
import time

revision = "06aec582b5b3"
down_revision = "018012973d35"
branch_labels = None
depends_on = None


def upgrade():
    # Create knowledge_file table
    print("Creating knowledge_file table")
    knowledge_file_table = op.create_table(
        "knowledge_file",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("knowledge_id", sa.Text(), nullable=False),
        sa.Column("file_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )

    # Add indexes for performance
    op.create_index("idx_knowledge_file_knowledge_id", "knowledge_file", ["knowledge_id"])
    op.create_index("idx_knowledge_file_file_id", "knowledge_file", ["file_id"])

    # Add unique constraint to prevent duplicate entries
    op.create_unique_constraint(
        "uq_knowledge_file_knowledge_id_file_id",
        "knowledge_file",
        ["knowledge_id", "file_id"]
    )

    # Add foreign key with CASCADE delete
    op.create_foreign_key(
        "fk_knowledge_file_knowledge_id",
        "knowledge_file",
        "knowledge",
        ["knowledge_id"],
        ["id"],
        ondelete="CASCADE"
    )

    print("Migrating data from knowledge.data.file_ids to knowledge_file table")

    # Representation of the existing knowledge table
    knowledge_table = table(
        "knowledge",
        column("id", sa.Text()),
        column("user_id", sa.Text()),
        column("data", sa.JSON()),
    )

    # Select all knowledge entries
    conn = op.get_bind()
    knowledge_entries = conn.execute(
        select(
            knowledge_table.c.id,
            knowledge_table.c.user_id,
            knowledge_table.c.data,
        )
    )

    # Migrate file_ids from JSON to knowledge_file table
    current_time = int(time.time())
    knowledge_file_entries = []

    for knowledge_entry in knowledge_entries:
        knowledge_id = knowledge_entry.id
        user_id = knowledge_entry.user_id
        data = knowledge_entry.data

        if data and isinstance(data, dict):
            file_ids = data.get("file_ids", [])

            if file_ids and isinstance(file_ids, list):
                for file_id in file_ids:
                    # Generate unique ID for knowledge_file entry
                    import uuid
                    knowledge_file_id = str(uuid.uuid4())

                    knowledge_file_entries.append({
                        "id": knowledge_file_id,
                        "knowledge_id": knowledge_id,
                        "file_id": file_id,
                        "user_id": user_id,
                        "created_at": current_time,
                        "updated_at": current_time,
                    })

    # Bulk insert knowledge_file entries
    # Note: This operation is transactional - if it fails, the entire migration rolls back
    if knowledge_file_entries:
        conn.execute(
            knowledge_file_table.insert(),
            knowledge_file_entries
        )
        print(f"Migrated {len(knowledge_file_entries)} file associations to knowledge_file table")
    else:
        print("No file associations to migrate")

    # Set data field to NULL for all knowledge entries
    # This only persists if the above operations succeed (same transaction)
    print("Setting knowledge.data to NULL")
    conn.execute(
        knowledge_table.update().values(data=None)
    )


def downgrade():
    print("Rolling back: migrating data from knowledge_file table back to knowledge.data")

    # Representation of tables
    knowledge_table = table(
        "knowledge",
        column("id", sa.Text()),
        column("data", sa.JSON()),
    )

    knowledge_file_table = table(
        "knowledge_file",
        column("knowledge_id", sa.Text()),
        column("file_id", sa.Text()),
    )

    conn = op.get_bind()

    # Get all knowledge_file entries grouped by knowledge_id
    knowledge_file_entries = conn.execute(
        select(
            knowledge_file_table.c.knowledge_id,
            knowledge_file_table.c.file_id,
        )
    )

    # Group file_ids by knowledge_id
    knowledge_file_map = {}
    for entry in knowledge_file_entries:
        knowledge_id = entry.knowledge_id
        file_id = entry.file_id

        if knowledge_id not in knowledge_file_map:
            knowledge_file_map[knowledge_id] = []
        knowledge_file_map[knowledge_id].append(file_id)

    # Get all knowledge bases to ensure we restore data structure even for empty ones
    all_knowledge = conn.execute(
        select(knowledge_table.c.id)
    )

    # Restore data for all knowledge bases
    restored_count = 0
    for knowledge_entry in all_knowledge:
        knowledge_id = knowledge_entry.id
        # Restore file_ids array (empty if no files existed)
        file_ids = knowledge_file_map.get(knowledge_id, [])
        conn.execute(
            knowledge_table.update()
            .where(knowledge_table.c.id == knowledge_id)
            .values(data={"file_ids": file_ids})
        )
        restored_count += 1

    print(f"Restored file_ids to {restored_count} knowledge entries ({len(knowledge_file_map)} with files, {restored_count - len(knowledge_file_map)} empty)")

    # Drop foreign key constraint
    op.drop_constraint("fk_knowledge_file_knowledge_id", "knowledge_file", type_="foreignkey")

    # Drop unique constraint
    op.drop_constraint("uq_knowledge_file_knowledge_id_file_id", "knowledge_file", type_="unique")

    # Drop indexes
    op.drop_index("idx_knowledge_file_file_id", table_name="knowledge_file")
    op.drop_index("idx_knowledge_file_knowledge_id", table_name="knowledge_file")

    # Drop knowledge_file table
    op.drop_table("knowledge_file")
    print("knowledge_file table dropped")
