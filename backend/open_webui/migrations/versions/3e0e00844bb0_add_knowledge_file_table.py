"""Add knowledge_file table

Revision ID: 3e0e00844bb0
Revises: 90ef40d4714e
Create Date: 2025-12-02 06:54:19.401334

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
import open_webui.internal.db

import time
import json
import uuid

# revision identifiers, used by Alembic.
revision: str = "3e0e00844bb0"
down_revision: Union[str, None] = "90ef40d4714e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_file",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column(
            "knowledge_id",
            sa.Text(),
            sa.ForeignKey("knowledge.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "file_id",
            sa.Text(),
            sa.ForeignKey("file.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        # indexes
        sa.Index("ix_knowledge_file_knowledge_id", "knowledge_id"),
        sa.Index("ix_knowledge_file_file_id", "file_id"),
        sa.Index("ix_knowledge_file_user_id", "user_id"),
        # unique constraints
        sa.UniqueConstraint(
            "knowledge_id", "file_id", name="uq_knowledge_file_knowledge_file"
        ),  # prevent duplicate entries
    )

    connection = op.get_bind()

    # 2. Read existing group with user_ids JSON column
    knowledge_table = sa.Table(
        "knowledge",
        sa.MetaData(),
        sa.Column("id", sa.Text()),
        sa.Column("user_id", sa.Text()),
        sa.Column("data", sa.JSON()),  # JSON stored as text in SQLite + PG
    )

    results = connection.execute(
        sa.select(
            knowledge_table.c.id, knowledge_table.c.user_id, knowledge_table.c.data
        )
    ).fetchall()

    # 3. Insert members into group_member table
    kf_table = sa.Table(
        "knowledge_file",
        sa.MetaData(),
        sa.Column("id", sa.Text()),
        sa.Column("user_id", sa.Text()),
        sa.Column("knowledge_id", sa.Text()),
        sa.Column("file_id", sa.Text()),
        sa.Column("created_at", sa.BigInteger()),
        sa.Column("updated_at", sa.BigInteger()),
    )

    file_table = sa.Table(
        "file",
        sa.MetaData(),
        sa.Column("id", sa.Text()),
    )

    now = int(time.time())
    for knowledge_id, user_id, data in results:
        if not data:
            continue

        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                continue  # skip invalid JSON

        if not isinstance(data, dict):
            continue

        file_ids = data.get("file_ids", [])

        for file_id in file_ids:
            file_exists = connection.execute(
                sa.select(file_table.c.id).where(file_table.c.id == file_id)
            ).fetchone()

            if not file_exists:
                continue  # skip non-existing files

            row = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "knowledge_id": knowledge_id,
                "file_id": file_id,
                "created_at": now,
                "updated_at": now,
            }
            connection.execute(kf_table.insert().values(**row))

    with op.batch_alter_table("knowledge") as batch:
        batch.drop_column("data")


def downgrade() -> None:
    # 1. Add back the old data column
    op.add_column("knowledge", sa.Column("data", sa.JSON(), nullable=True))

    connection = op.get_bind()

    # 2. Read knowledge_file entries and reconstruct data JSON
    knowledge_table = sa.Table(
        "knowledge",
        sa.MetaData(),
        sa.Column("id", sa.Text()),
        sa.Column("data", sa.JSON()),
    )

    kf_table = sa.Table(
        "knowledge_file",
        sa.MetaData(),
        sa.Column("id", sa.Text()),
        sa.Column("knowledge_id", sa.Text()),
        sa.Column("file_id", sa.Text()),
    )

    results = connection.execute(sa.select(knowledge_table.c.id)).fetchall()

    for (knowledge_id,) in results:
        file_ids = connection.execute(
            sa.select(kf_table.c.file_id).where(kf_table.c.knowledge_id == knowledge_id)
        ).fetchall()

        file_ids_list = [fid for (fid,) in file_ids]

        data_json = {"file_ids": file_ids_list}

        connection.execute(
            knowledge_table.update()
            .where(knowledge_table.c.id == knowledge_id)
            .values(data=data_json)
        )

    # 3. Drop the knowledge_file table
    op.drop_table("knowledge_file")
