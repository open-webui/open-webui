"""Add user_id index to file table

Revision ID: b1f1e9a4c7d2
Revises: fa1c3b27e891
Create Date: 2026-05-20

Adds an index on file.user_id to speed up Files.get_files_by_user_id
and related queries that currently full-scan the table.
"""

from alembic import op
import sqlalchemy as sa

revision = "b1f1e9a4c7d2"
down_revision = "fa1c3b27e891"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name in ("sqlite", "postgresql"):
        bind.execute(
            sa.text("CREATE INDEX IF NOT EXISTS file_user_id_idx ON file (user_id)")
        )
        return
    try:
        op.create_index("file_user_id_idx", "file", ["user_id"])
    except Exception:
        pass


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name in ("sqlite", "postgresql"):
        bind.execute(sa.text("DROP INDEX IF EXISTS file_user_id_idx"))
        return
    try:
        op.drop_index("file_user_id_idx", table_name="file")
    except Exception:
        pass
