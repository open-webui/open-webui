"""Extend group_owned_asset CheckConstraint to include 'skill'

Revision ID: a2b3c4d5e6f7
Revises: fdcb6cc75284
Create Date: 2026-08-21 00:01:00.000000

Phase 3 (skills-only slice): extends the portable type allowlist on
``group_owned_asset`` so that ``resource_type='skill'`` is accepted.

For SQLite this is implemented as batch table recreation (SQLite does not
support ALTER CHECK CONSTRAINT).  For PostgreSQL the old constraint is
dropped and a new one is created.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: str | None = 'fdcb6cc75284'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW_CHECK = "resource_type IN ('knowledge', 'prompt', 'skill')"
_OLD_CHECK_NAME = 'ck_group_owned_asset_type'


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == 'sqlite':
        # SQLite: batch-recreate the table with the new constraint.
        with op.batch_alter_table('group_owned_asset') as batch_op:
            batch_op.drop_constraint(_OLD_CHECK_NAME, type_='check')
            batch_op.create_check_constraint(
                _OLD_CHECK_NAME,
                _NEW_CHECK,
            )
    else:
        # PostgreSQL (and other dialects): drop + create.
        op.drop_constraint(_OLD_CHECK_NAME, 'group_owned_asset', type_='check')
        op.create_check_constraint(
            _OLD_CHECK_NAME,
            'group_owned_asset',
            _NEW_CHECK,
        )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    _OLD_CHECK = "resource_type IN ('knowledge', 'prompt')"
    if dialect == 'sqlite':
        with op.batch_alter_table('group_owned_asset') as batch_op:
            batch_op.drop_constraint(_OLD_CHECK_NAME, type_='check')
            batch_op.create_check_constraint(
                _OLD_CHECK_NAME,
                _OLD_CHECK,
            )
    else:
        op.drop_constraint(_OLD_CHECK_NAME, 'group_owned_asset', type_='check')
        op.create_check_constraint(
            _OLD_CHECK_NAME,
            'group_owned_asset',
            _OLD_CHECK,
        )
