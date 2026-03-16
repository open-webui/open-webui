"""Add knowledge table

Revision ID: 6a39f3d8e55c
Revises: c0fbf31ca0db
Create Date: 2024-10-01 14:02:35.241684

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column, select
import json

revision = "6a39f3d8e55c"
down_revision = "c0fbf31ca0db"
branch_labels = None
depends_on = None


def upgrade():
    # Creating the 'knowledge' table
    print("Creating knowledge table")
    knowledge_table = op.create_table(
        "knowledge",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=True),
    )

    print("Migrating data from document table to knowledge table")
    # Representation of the existing 'document' table
    document_table = table(
        "document",
        column("collection_name", sa.String()),
        column("user_id", sa.String()),
        column("name", sa.String()),
        column("title", sa.Text()),
        column("content", sa.Text()),
        column("timestamp", sa.BigInteger()),
    )

    # Select all from existing document table
    documents = op.get_bind().execute(
        select(
            document_table.c.collection_name,
            document_table.c.user_id,
            document_table.c.name,
            document_table.c.title,
            document_table.c.content,
            document_table.c.timestamp,
        )
    )

    # Insert data into knowledge table from document table
    for doc in documents:
        op.get_bind().execute(
            knowledge_table.insert().values(
                id=doc.collection_name,
                user_id=doc.user_id,
                description=doc.name,
                meta={
                    "legacy": True,
                    "document": True,
                    "tags": json.loads(doc.content or "{}").get("tags", []),
                },
                name=doc.title,
                created_at=doc.timestamp,
                updated_at=doc.timestamp,  # using created_at for both created_at and updated_at in project
            )
        )


def downgrade():
    op.drop_table("knowledge")
