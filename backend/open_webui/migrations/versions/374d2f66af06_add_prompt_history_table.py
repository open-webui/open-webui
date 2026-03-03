"""Add prompt history table

Revision ID: 374d2f66af06
Revises: c440947495f3
Create Date: 2026-01-23 17:15:00.000000

"""

from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa

revision: str = "374d2f66af06"
down_revision: Union[str, None] = "c440947495f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Step 1: Read existing data from OLD table (schema likely command as PK)
    # We use batch_alter previously, but we want to move to new table.
    # We need to assume the OLD structure.

    old_prompt_table = sa.table(
        "prompt",
        sa.column("command", sa.Text()),
        sa.column("user_id", sa.Text()),
        sa.column("title", sa.Text()),
        sa.column("content", sa.Text()),
        sa.column("timestamp", sa.BigInteger()),
        sa.column("access_control", sa.JSON()),
    )

    # Check if table exists/read data
    try:
        existing_prompts = conn.execute(
            sa.select(
                old_prompt_table.c.command,
                old_prompt_table.c.user_id,
                old_prompt_table.c.title,
                old_prompt_table.c.content,
                old_prompt_table.c.timestamp,
                old_prompt_table.c.access_control,
            )
        ).fetchall()
    except Exception:
        # Fallback if table doesn't exist (new install)
        existing_prompts = []

    # Step 2: Create new prompt table with 'id' as PRIMARY KEY
    op.create_table(
        "prompt_new",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("command", sa.String(), unique=True, index=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("access_control", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("version_id", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )

    # Step 3: Create prompt_history table
    op.create_table(
        "prompt_history",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("prompt_id", sa.Text(), nullable=False, index=True),
        sa.Column("parent_id", sa.Text(), nullable=True),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("commit_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
    )

    # Step 4: Migrate data
    prompt_new_table = sa.table(
        "prompt_new",
        sa.column("id", sa.Text()),
        sa.column("command", sa.String()),
        sa.column("user_id", sa.String()),
        sa.column("name", sa.Text()),
        sa.column("content", sa.Text()),
        sa.column("data", sa.JSON()),
        sa.column("meta", sa.JSON()),
        sa.column("access_control", sa.JSON()),
        sa.column("is_active", sa.Boolean()),
        sa.column("version_id", sa.Text()),
        sa.column("tags", sa.JSON()),
        sa.column("created_at", sa.BigInteger()),
        sa.column("updated_at", sa.BigInteger()),
    )

    prompt_history_table = sa.table(
        "prompt_history",
        sa.column("id", sa.Text()),
        sa.column("prompt_id", sa.Text()),
        sa.column("parent_id", sa.Text()),
        sa.column("snapshot", sa.JSON()),
        sa.column("user_id", sa.Text()),
        sa.column("commit_message", sa.Text()),
        sa.column("created_at", sa.BigInteger()),
    )

    for row in existing_prompts:
        command = row[0]
        user_id = row[1]
        title = row[2]
        content = row[3]
        timestamp = row[4]
        access_control = row[5]

        new_uuid = str(uuid.uuid4())
        history_uuid = str(uuid.uuid4())
        clean_command = command[1:] if command and command.startswith("/") else command

        # Insert into prompt_new
        conn.execute(
            sa.insert(prompt_new_table).values(
                id=new_uuid,
                command=clean_command,
                user_id=user_id,
                name=title,
                content=content,
                data={},
                meta={},
                access_control=access_control,
                is_active=True,
                version_id=history_uuid,
                tags=[],
                created_at=timestamp,
                updated_at=timestamp,
            )
        )

        # Create initial history entry
        conn.execute(
            sa.insert(prompt_history_table).values(
                id=history_uuid,
                prompt_id=new_uuid,
                parent_id=None,
                snapshot={
                    "name": title,
                    "content": content,
                    "command": clean_command,
                    "data": {},
                    "meta": {},
                    "access_control": access_control,
                },
                user_id=user_id,
                commit_message=None,
                created_at=timestamp,
            )
        )

    # Step 5: Replace old table with new one
    op.drop_table("prompt")
    op.rename_table("prompt_new", "prompt")


def downgrade() -> None:
    conn = op.get_bind()

    # Step 1: Read new data
    prompt_table = sa.table(
        "prompt",
        sa.column("command", sa.String()),
        sa.column("name", sa.Text()),
        sa.column("created_at", sa.BigInteger()),
        sa.column("user_id", sa.Text()),
        sa.column("content", sa.Text()),
        sa.column("access_control", sa.JSON()),
    )

    try:
        current_data = conn.execute(
            sa.select(
                prompt_table.c.command,
                prompt_table.c.name,
                prompt_table.c.created_at,
                prompt_table.c.user_id,
                prompt_table.c.content,
                prompt_table.c.access_control,
            )
        ).fetchall()
    except Exception:
        current_data = []

    # Step 2: Drop history and table
    op.drop_table("prompt_history")
    op.drop_table("prompt")

    # Step 3: Recreate old table (command as PK?)
    # Assuming old schema:
    op.create_table(
        "prompt",
        sa.Column("command", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String()),
        sa.Column("title", sa.Text()),
        sa.Column("content", sa.Text()),
        sa.Column("timestamp", sa.BigInteger()),
        sa.Column("access_control", sa.JSON()),
        sa.Column("id", sa.Integer(), nullable=True),
    )

    # Step 4: Restore data
    old_prompt_table = sa.table(
        "prompt",
        sa.column("command", sa.String()),
        sa.column("user_id", sa.String()),
        sa.column("title", sa.Text()),
        sa.column("content", sa.Text()),
        sa.column("timestamp", sa.BigInteger()),
        sa.column("access_control", sa.JSON()),
    )

    for row in current_data:
        command = row[0]
        name = row[1]
        created_at = row[2]
        user_id = row[3]
        content = row[4]
        access_control = row[5]

        # Restore leading /
        old_command = (
            "/" + command if command and not command.startswith("/") else command
        )

        conn.execute(
            sa.insert(old_prompt_table).values(
                command=old_command,
                user_id=user_id,
                title=name,
                content=content,
                timestamp=created_at,
                access_control=access_control,
            )
        )
