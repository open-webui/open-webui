"""add unique index on user.email

Revision ID: a7f3c2e9b1d4
Revises: 959eaac8f909
Create Date: 2026-07-26 20:30:00.000000

The ORM has always declared ``User.email`` as ``unique=True``, but the initial
schema was created with a raw ``create_table`` that never emitted a unique
constraint or index, and no later migration added one. As a result the database
did not actually enforce email uniqueness, which allowed concurrent sign-in
requests for the same new email (notably the trusted-header path) to each pass a
non-atomic ``get_user_by_email`` check and create duplicate accounts.

This migration adds the missing DB-level guarantee so duplicate inserts are
rejected and get-or-create becomes atomic across workers and replicas.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision: str = 'a7f3c2e9b1d4'
down_revision: str | None = '959eaac8f909'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = 'user_email_unique_idx'


def upgrade() -> None:
    if context.is_offline_mode():
        op.create_index(INDEX_NAME, 'user', ['email'], unique=True)
        return

    conn = op.get_bind()
    inspector = sa.inspect(conn)

    existing_indexes = {index['name'] for index in inspector.get_indexes('user')}
    if INDEX_NAME in existing_indexes:
        return

    # A unique index can't be created if the table already contains duplicate
    # emails (exactly the corruption this migration prevents going forward).
    # Refuse to run rather than silently leaving uniqueness unenforced, and tell
    # the operator how to inspect the duplicates so they can merge/remove them.
    duplicates = conn.execute(
        sa.text(
            'SELECT lower(email) AS email, COUNT(*) AS c '
            'FROM "user" '
            'WHERE email IS NOT NULL '
            'GROUP BY lower(email) '
            'HAVING COUNT(*) > 1'
        )
    ).fetchall()
    if duplicates:
        details = ', '.join(f'{row.email} (x{row.c})' for row in duplicates)
        raise RuntimeError(
            'Cannot add a unique index on user.email because duplicate email '
            f'addresses already exist: {details}. Resolve the duplicates (merge '
            "or remove the extra accounts) and re-run the migration. Example:\n"
            '  SELECT id, email, role, created_at FROM "user" '
            'WHERE lower(email) IN (SELECT lower(email) FROM "user" '
            'GROUP BY lower(email) HAVING COUNT(*) > 1) ORDER BY lower(email), created_at;'
        )

    op.create_index(INDEX_NAME, 'user', ['email'], unique=True)


def downgrade() -> None:
    if context.is_offline_mode():
        op.drop_index(INDEX_NAME, table_name='user')
        return

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_indexes = {index['name'] for index in inspector.get_indexes('user')}
    if INDEX_NAME in existing_indexes:
        op.drop_index(INDEX_NAME, table_name='user')
