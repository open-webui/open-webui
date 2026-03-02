"""Update user table

Revision ID: b10670c03dd5
Revises: 2f1211949ecc
Create Date: 2025-11-28 04:55:31.737538

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


import open_webui.internal.db
import json
import time

# revision identifiers, used by Alembic.
revision: str = "b10670c03dd5"
down_revision: Union[str, None] = "2f1211949ecc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_sqlite_indexes_for_column(table_name, column_name, conn):
    """
    SQLite requires manual removal of any indexes referencing a column
    before ALTER TABLE ... DROP COLUMN can succeed.
    """
    indexes = conn.execute(sa.text(f"PRAGMA index_list('{table_name}')")).fetchall()

    for idx in indexes:
        index_name = idx[1]  # index name
        # Get indexed columns
        idx_info = conn.execute(
            sa.text(f"PRAGMA index_info('{index_name}')")
        ).fetchall()

        indexed_cols = [row[2] for row in idx_info]  # col names
        if column_name in indexed_cols:
            conn.execute(sa.text(f"DROP INDEX IF EXISTS {index_name}"))


def _convert_column_to_json(table: str, column: str):
    conn = op.get_bind()
    dialect = conn.dialect.name

    # SQLite cannot ALTER COLUMN → must recreate column
    if dialect == "sqlite":
        # 1. Add temporary column
        op.add_column(table, sa.Column(f"{column}_json", sa.JSON(), nullable=True))

        # 2. Load old data
        rows = conn.execute(sa.text(f'SELECT id, {column} FROM "{table}"')).fetchall()

        for row in rows:
            uid, raw = row
            if raw is None:
                parsed = None
            else:
                try:
                    parsed = json.loads(raw)
                except Exception:
                    parsed = None  # fallback safe behavior

            conn.execute(
                sa.text(f'UPDATE "{table}" SET {column}_json = :val WHERE id = :id'),
                {"val": json.dumps(parsed) if parsed else None, "id": uid},
            )

        # 3. Drop old TEXT column
        op.drop_column(table, column)

        # 4. Rename new JSON column → original name
        op.alter_column(table, f"{column}_json", new_column_name=column)

    else:
        # PostgreSQL supports direct CAST
        op.alter_column(
            table,
            column,
            type_=sa.JSON(),
            postgresql_using=f"{column}::json",
        )


def _convert_column_to_text(table: str, column: str):
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == "sqlite":
        op.add_column(table, sa.Column(f"{column}_text", sa.Text(), nullable=True))

        rows = conn.execute(sa.text(f'SELECT id, {column} FROM "{table}"')).fetchall()

        for uid, raw in rows:
            conn.execute(
                sa.text(f'UPDATE "{table}" SET {column}_text = :val WHERE id = :id'),
                {"val": json.dumps(raw) if raw else None, "id": uid},
            )

        op.drop_column(table, column)
        op.alter_column(table, f"{column}_text", new_column_name=column)

    else:
        op.alter_column(
            table,
            column,
            type_=sa.Text(),
            postgresql_using=f"to_json({column})::text",
        )


def upgrade() -> None:
    op.add_column(
        "user", sa.Column("profile_banner_image_url", sa.Text(), nullable=True)
    )
    op.add_column("user", sa.Column("timezone", sa.String(), nullable=True))

    op.add_column("user", sa.Column("presence_state", sa.String(), nullable=True))
    op.add_column("user", sa.Column("status_emoji", sa.String(), nullable=True))
    op.add_column("user", sa.Column("status_message", sa.Text(), nullable=True))
    op.add_column(
        "user", sa.Column("status_expires_at", sa.BigInteger(), nullable=True)
    )

    op.add_column("user", sa.Column("oauth", sa.JSON(), nullable=True))

    # Convert info (TEXT/JSONField) → JSON
    _convert_column_to_json("user", "info")
    # Convert settings (TEXT/JSONField) → JSON
    _convert_column_to_json("user", "settings")

    op.create_table(
        "api_key",
        sa.Column("id", sa.Text(), primary_key=True, unique=True),
        sa.Column("user_id", sa.Text(), sa.ForeignKey("user.id", ondelete="CASCADE")),
        sa.Column("key", sa.Text(), unique=True, nullable=False),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("expires_at", sa.BigInteger(), nullable=True),
        sa.Column("last_used_at", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )

    conn = op.get_bind()
    users = conn.execute(
        sa.text('SELECT id, oauth_sub FROM "user" WHERE oauth_sub IS NOT NULL')
    ).fetchall()

    for uid, oauth_sub in users:
        if oauth_sub:
            # Example formats supported:
            #   provider@sub
            #   plain sub (stored as {"oidc": {"sub": sub}})
            if "@" in oauth_sub:
                provider, sub = oauth_sub.split("@", 1)
            else:
                provider, sub = "oidc", oauth_sub

            oauth_json = json.dumps({provider: {"sub": sub}})
            conn.execute(
                sa.text('UPDATE "user" SET oauth = :oauth WHERE id = :id'),
                {"oauth": oauth_json, "id": uid},
            )

    users_with_keys = conn.execute(
        sa.text('SELECT id, api_key FROM "user" WHERE api_key IS NOT NULL')
    ).fetchall()
    now = int(time.time())

    for uid, api_key in users_with_keys:
        if api_key:
            conn.execute(
                sa.text("""
                    INSERT INTO api_key (id, user_id, key, created_at, updated_at)
                    VALUES (:id, :user_id, :key, :created_at, :updated_at)
                """),
                {
                    "id": f"key_{uid}",
                    "user_id": uid,
                    "key": api_key,
                    "created_at": now,
                    "updated_at": now,
                },
            )

    if conn.dialect.name == "sqlite":
        _drop_sqlite_indexes_for_column("user", "api_key", conn)
        _drop_sqlite_indexes_for_column("user", "oauth_sub", conn)

    with op.batch_alter_table("user") as batch_op:
        batch_op.drop_column("api_key")
        batch_op.drop_column("oauth_sub")


def downgrade() -> None:
    # --- 1. Restore old oauth_sub column ---
    op.add_column("user", sa.Column("oauth_sub", sa.Text(), nullable=True))

    conn = op.get_bind()
    users = conn.execute(
        sa.text('SELECT id, oauth FROM "user" WHERE oauth IS NOT NULL')
    ).fetchall()

    for uid, oauth in users:
        try:
            data = json.loads(oauth)
            provider = list(data.keys())[0]
            sub = data[provider].get("sub")
            oauth_sub = f"{provider}@{sub}"
        except Exception:
            oauth_sub = None

        conn.execute(
            sa.text('UPDATE "user" SET oauth_sub = :oauth_sub WHERE id = :id'),
            {"oauth_sub": oauth_sub, "id": uid},
        )

    op.drop_column("user", "oauth")

    # --- 2. Restore api_key field ---
    op.add_column("user", sa.Column("api_key", sa.String(), nullable=True))

    # Restore values from api_key
    keys = conn.execute(sa.text("SELECT user_id, key FROM api_key")).fetchall()
    for uid, key in keys:
        conn.execute(
            sa.text('UPDATE "user" SET api_key = :key WHERE id = :id'),
            {"key": key, "id": uid},
        )

    # Drop new table
    op.drop_table("api_key")

    with op.batch_alter_table("user") as batch_op:
        batch_op.drop_column("profile_banner_image_url")
        batch_op.drop_column("timezone")

        batch_op.drop_column("presence_state")
        batch_op.drop_column("status_emoji")
        batch_op.drop_column("status_message")
        batch_op.drop_column("status_expires_at")

    # Convert info (JSON) → TEXT
    _convert_column_to_text("user", "info")
    # Convert settings (JSON) → TEXT
    _convert_column_to_text("user", "settings")
