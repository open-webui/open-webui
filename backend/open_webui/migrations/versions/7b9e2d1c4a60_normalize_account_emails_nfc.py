"""Normalize account email spellings and enforce canonical uniqueness.

Revision ID: 7b9e2d1c4a60
Revises: e42c8f710a36
"""

import sqlalchemy as sa
from alembic import context, op

revision = '7b9e2d1c4a60'
down_revision = 'e42c8f710a36'
branch_labels = None
depends_on = None

INDEX_NAME = 'uq_user_email_nfc_lower'


def _nfc(expression, dialect):
    if dialect == 'sqlite':
        return f'unicode_nfc({expression})'
    if dialect == 'postgresql':
        return f'normalize({expression}, NFC)'
    raise RuntimeError('NFC email uniqueness requires SQLite or PostgreSQL.')


def upgrade():
    dialect = op.get_bind().dialect.name
    normalized_email = _nfc('email', dialect)
    key = 'unicode_email_key(email)' if dialect == 'sqlite' else _nfc(f'lower({normalized_email})', dialect)
    if not context.is_offline_mode():
        # Report identifiers, not addresses, and never merge or delete accounts.
        # SQLite uses the dedicated Unicode key, since its built-in lower()
        # only folds ASCII and disagrees with Python account lookups.
        rows = (
            op.get_bind()
            .execute(
                sa.text(
                    f'SELECT id FROM "user" WHERE {key} IN '
                    f'(SELECT {key} FROM "user" WHERE email IS NOT NULL '
                    f'GROUP BY {key} HAVING count(*) > 1) ORDER BY id'
                )
            )
            .all()
        )
        if rows:
            ids = ', '.join(str(row.id) for row in rows)
            raise RuntimeError(
                'Cannot normalize account emails: canonically equivalent addresses '
                f'belong to multiple user IDs: {ids}. Resolve these accounts before rerunning migrations; '
                'no account has been changed.'
            )

    # Creating the constraint first also prevents an offline SQL migration from
    # changing any account when pre-existing canonical duplicates are present.
    op.create_index(
        INDEX_NAME,
        'user',
        [sa.text(key)],
        unique=True,
        sqlite_where=sa.text('email IS NOT NULL'),
        postgresql_where=sa.text('email IS NOT NULL'),
    )
    for table in ('user', 'auth'):
        op.execute(sa.text(f'UPDATE "{table}" SET email = {normalized_email} WHERE email IS NOT NULL'))


def downgrade():
    op.drop_index(INDEX_NAME, table_name='user')
    # Canonical composition is intentionally retained; the original Unicode
    # spelling cannot be recovered, and the older case-insensitive index stays.
