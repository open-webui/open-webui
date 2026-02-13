"""add_group_member_table

Revision ID: 37f288994c47
Revises: a5c220713937
Create Date: 2025-11-17 03:45:25.123939

"""

import uuid
import time
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "37f288994c47"
down_revision: Union[str, None] = "a5c220713937"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create new table
    op.create_table(
        "group_member",
        sa.Column("id", sa.Text(), primary_key=True, unique=True, nullable=False),
        sa.Column(
            "group_id",
            sa.Text(),
            sa.ForeignKey("group.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Text(),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.BigInteger(), nullable=True),
        sa.UniqueConstraint("group_id", "user_id", name="uq_group_member_group_user"),
    )

    connection = op.get_bind()

    # 2. Read existing group with user_ids JSON column
    group_table = sa.Table(
        "group",
        sa.MetaData(),
        sa.Column("id", sa.Text()),
        sa.Column("user_ids", sa.JSON()),  # JSON stored as text in SQLite + PG
    )

    results = connection.execute(
        sa.select(group_table.c.id, group_table.c.user_ids)
    ).fetchall()

    print(results)

    # 3. Insert members into group_member table
    gm_table = sa.Table(
        "group_member",
        sa.MetaData(),
        sa.Column("id", sa.Text()),
        sa.Column("group_id", sa.Text()),
        sa.Column("user_id", sa.Text()),
        sa.Column("created_at", sa.BigInteger()),
        sa.Column("updated_at", sa.BigInteger()),
    )

    now = int(time.time())
    for group_id, user_ids in results:
        if not user_ids:
            continue

        if isinstance(user_ids, str):
            try:
                user_ids = json.loads(user_ids)
            except Exception:
                continue  # skip invalid JSON

        if not isinstance(user_ids, list):
            continue

        rows = [
            {
                "id": str(uuid.uuid4()),
                "group_id": group_id,
                "user_id": uid,
                "created_at": now,
                "updated_at": now,
            }
            for uid in user_ids
        ]

        if rows:
            connection.execute(gm_table.insert(), rows)

    # 4. Optionally drop the old column
    with op.batch_alter_table("group") as batch:
        batch.drop_column("user_ids")


def downgrade():
    # Reverse: restore user_ids column
    with op.batch_alter_table("group") as batch:
        batch.add_column(sa.Column("user_ids", sa.JSON()))

    connection = op.get_bind()
    gm_table = sa.Table(
        "group_member",
        sa.MetaData(),
        sa.Column("group_id", sa.Text()),
        sa.Column("user_id", sa.Text()),
        sa.Column("created_at", sa.BigInteger()),
        sa.Column("updated_at", sa.BigInteger()),
    )

    group_table = sa.Table(
        "group",
        sa.MetaData(),
        sa.Column("id", sa.Text()),
        sa.Column("user_ids", sa.JSON()),
    )

    # Build JSON arrays again
    results = connection.execute(sa.select(group_table.c.id)).fetchall()

    for (group_id,) in results:
        members = connection.execute(
            sa.select(gm_table.c.user_id).where(gm_table.c.group_id == group_id)
        ).fetchall()

        member_ids = [m[0] for m in members]

        connection.execute(
            group_table.update()
            .where(group_table.c.id == group_id)
            .values(user_ids=member_ids)
        )

    # Drop the new table
    op.drop_table("group_member")
