"""Update user table

Revision ID: b10670c03dd5
Revises: 2f1211949ecc
Create Date: 2025-11-28 04:55:31.737538

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


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
    Note: Auto-indexes created for UNIQUE/PRIMARY KEY constraints cannot be dropped.
    """
    indexes = conn.execute(sa.text(f"PRAGMA index_list('{table_name}')")).fetchall()

    for idx in indexes:
        index_name = idx[1]  # index name
        is_auto_index = idx[
            2
        ]  # origin: 'c' = constraint, 'u' = unique, 'pk' = primary key, 'c' = auto

        # Skip auto-indexes created for UNIQUE/PRIMARY KEY constraints
        # These are automatically dropped when the constraint is removed
        if is_auto_index == 1 or index_name.startswith("sqlite_autoindex_"):
            continue

        # Get indexed columns
        idx_info = conn.execute(
            sa.text(f"PRAGMA index_info('{index_name}')")
        ).fetchall()

        indexed_cols = [row[2] for row in idx_info]  # col names
        if column_name in indexed_cols:
            try:
                conn.execute(sa.text(f"DROP INDEX IF EXISTS {index_name}"))
            except Exception:
                # If it fails (e.g., constraint index), skip it
                pass


def _convert_column_to_json(table: str, column: str):
    conn = op.get_bind()
    dialect = conn.dialect.name
    inspector = Inspector.from_engine(conn)

    # Check existing columns for idempotency
    existing_columns = [col["name"] for col in inspector.get_columns(table)]
    has_original = column in existing_columns
    has_temp = f"{column}_json" in existing_columns

    # SQLite cannot ALTER COLUMN → must recreate column
    if dialect == "sqlite":
        # If column is already JSON (no original text column, no temp column), skip
        if has_original and not has_temp:
            # Check if it's already JSON type by inspecting column type
            col_info = next(
                (c for c in inspector.get_columns(table) if c["name"] == column), None
            )
            if col_info and "JSON" in str(col_info.get("type", "")).upper():
                return  # Already converted

        # 1. Add temporary column if it doesn't exist
        if not has_temp:
            op.add_column(table, sa.Column(f"{column}_json", sa.JSON(), nullable=True))

        # 2. Load old data and migrate (only if original column still exists)
        if has_original:
            rows = conn.execute(
                sa.text(f'SELECT id, {column} FROM "{table}"')
            ).fetchall()

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
                    sa.text(
                        f'UPDATE "{table}" SET {column}_json = :val WHERE id = :id'
                    ),
                    {"val": json.dumps(parsed) if parsed else None, "id": uid},
                )

            # 3. Drop old TEXT column
            op.drop_column(table, column)

        # 4. Rename new JSON column → original name (refresh columns list)
        # Use raw SQL on SQLite so RENAME COLUMN completes (op.alter_column can fail on some SQLite builds)
        existing_columns = [col["name"] for col in inspector.get_columns(table)]
        if f"{column}_json" in existing_columns and column not in existing_columns:
            op.execute(
                sa.text(
                    f'ALTER TABLE "{table}" RENAME COLUMN {column}_json TO {column}'
                )
            )

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
    # Check if columns already exist (idempotent migration)
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "user" in existing_tables:
        user_columns = [col["name"] for col in inspector.get_columns("user")]

        if "profile_banner_image_url" not in user_columns:
            op.add_column(
                "user", sa.Column("profile_banner_image_url", sa.Text(), nullable=True)
            )
        if "timezone" not in user_columns:
            op.add_column("user", sa.Column("timezone", sa.String(), nullable=True))
        if "presence_state" not in user_columns:
            op.add_column(
                "user", sa.Column("presence_state", sa.String(), nullable=True)
            )
        if "status_emoji" not in user_columns:
            op.add_column("user", sa.Column("status_emoji", sa.String(), nullable=True))
        if "status_message" not in user_columns:
            op.add_column("user", sa.Column("status_message", sa.Text(), nullable=True))
        if "status_expires_at" not in user_columns:
            op.add_column(
                "user", sa.Column("status_expires_at", sa.BigInteger(), nullable=True)
            )
        if "oauth" not in user_columns:
            op.add_column("user", sa.Column("oauth", sa.JSON(), nullable=True))
    else:
        # Table doesn't exist yet, add columns normally
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

    # Re-check existing tables after column conversions
    existing_tables = inspector.get_table_names()

    if "api_key" not in existing_tables:
        op.create_table(
            "api_key",
            sa.Column("id", sa.Text(), primary_key=True, unique=True),
            sa.Column(
                "user_id", sa.Text(), sa.ForeignKey("user.id", ondelete="CASCADE")
            ),
            sa.Column("key", sa.Text(), unique=True, nullable=False),
            sa.Column("data", sa.JSON(), nullable=True),
            sa.Column("expires_at", sa.BigInteger(), nullable=True),
            sa.Column("last_used_at", sa.BigInteger(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        )

    conn = op.get_bind()

    # Re-check user columns for idempotency
    user_columns = [col["name"] for col in inspector.get_columns("user")]

    # Migrate oauth_sub to oauth JSON (only if oauth_sub still exists)
    if "oauth_sub" in user_columns:
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

    # Migrate api_key to api_key table (only if api_key column still exists)
    if "api_key" in user_columns:
        users_with_keys = conn.execute(
            sa.text('SELECT id, api_key FROM "user" WHERE api_key IS NOT NULL')
        ).fetchall()
        now = int(time.time())

        for uid, api_key in users_with_keys:
            if api_key:
                # Check if key already exists to avoid duplicates
                existing = conn.execute(
                    sa.text("SELECT id FROM api_key WHERE user_id = :user_id"),
                    {"user_id": uid},
                ).fetchone()
                if not existing:
                    conn.execute(
                        sa.text(
                            """
                            INSERT INTO api_key (id, user_id, key, created_at, updated_at)
                            VALUES (:id, :user_id, :key, :created_at, :updated_at)
                        """
                        ),
                        {
                            "id": f"key_{uid}",
                            "user_id": uid,
                            "key": api_key,
                            "created_at": now,
                            "updated_at": now,
                        },
                    )

    # Drop old columns (only if they still exist)
    columns_to_drop = []
    if "api_key" in user_columns:
        columns_to_drop.append("api_key")
    if "oauth_sub" in user_columns:
        columns_to_drop.append("oauth_sub")

    if columns_to_drop:
        if conn.dialect.name == "sqlite":
            for col in columns_to_drop:
                _drop_sqlite_indexes_for_column("user", col, conn)

        with op.batch_alter_table("user") as batch_op:
            for col in columns_to_drop:
                batch_op.drop_column(col)


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
