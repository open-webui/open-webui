"""Promote subagent_of + model_id_primary to real columns and reorder indexes

Revision ID: bab38fc89261
Revises: fa1c3b27e891
Create Date: 2026-05-20

Adds two denormalized columns so hot queries don't have to json_extract the
(potentially 100+ MB) chat blob just to filter subagents or count facet models:

  subagent_of       - from meta.subagent_of, lets the subagent filter hit an index
  model_id_primary  - from chat.models[0], drives the model facet aggregate

Also reorders the user-scoped sidebar index from (updated_at, user_id) to
(user_id, updated_at) — the sidebar query is
``WHERE user_id = ? ORDER BY updated_at DESC`` and the old order forced
SQLite to sort the full filtered result on every load. Adds a partial
``chat_sidebar_default_idx`` to make the default sidebar view a pure
index-only scan.

Postgres branch is a no-op; columns and indexes there will ship separately.
"""

import sqlalchemy as sa
from alembic import op

revision = "bab38fc89261"
down_revision = "fa1c3b27e891"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Add columns idempotently (some installs may already have them from
    # a prior partial migration / a manual patch).
    inspector = sa.inspect(bind)
    chat_columns = {c["name"] for c in inspector.get_columns("chat")}
    if "subagent_of" not in chat_columns:
        op.add_column("chat", sa.Column("subagent_of", sa.String(), nullable=True))
    if "model_id_primary" not in chat_columns:
        op.add_column("chat", sa.Column("model_id_primary", sa.String(), nullable=True))

    if dialect == "sqlite":
        # Backfill from the JSON blobs. Wrapped in try/except because some
        # legacy rows hold malformed JSON and we'd rather leave them NULL
        # than abort the whole migration.
        try:
            bind.execute(
                sa.text(
                    "UPDATE chat SET "
                    "  subagent_of = json_extract(meta, '$.subagent_of'), "
                    "  model_id_primary = json_extract(chat, '$.models[0]')"
                )
            )
        except Exception:
            pass

        # Drop the misordered legacy index and replace it with the
        # equality-then-sort variant.
        try:
            op.drop_index("updated_at_user_id_idx", table_name="chat")
        except Exception:
            pass
        bind.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS user_id_updated_at_idx "
                "ON chat (user_id, updated_at)"
            )
        )

        bind.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS chat_sidebar_default_idx "
                "ON chat (user_id, updated_at) "
                "WHERE archived = 0 AND folder_id IS NULL AND "
                "(pinned = 0 OR pinned IS NULL) AND subagent_of IS NULL"
            )
        )

        # Refresh planner stats so the new indexes are picked up.
        try:
            bind.execute(sa.text("ANALYZE"))
        except Exception:
            pass


def downgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        bind.execute(sa.text("DROP INDEX IF EXISTS chat_sidebar_default_idx"))
        bind.execute(sa.text("DROP INDEX IF EXISTS user_id_updated_at_idx"))
        bind.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS updated_at_user_id_idx "
                "ON chat (updated_at, user_id)"
            )
        )

    inspector = sa.inspect(bind)
    chat_columns = {c["name"] for c in inspector.get_columns("chat")}
    if "model_id_primary" in chat_columns:
        try:
            op.drop_column("chat", "model_id_primary")
        except Exception:
            pass
    if "subagent_of" in chat_columns:
        try:
            op.drop_column("chat", "subagent_of")
        except Exception:
            pass
