"""Extend group_owned_asset CheckConstraint to include 'skill'.

Revision ID: 10d3d56cee1c
Revises: fdcb6cc75284
Create Date: 2026-08-22 10:33:53.271833

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '10d3d56cee1c'
down_revision: str | None = 'fdcb6cc75284'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW_CHECK = "resource_type IN ('knowledge', 'prompt', 'skill')"
_OLD_CHECK = "resource_type IN ('knowledge', 'prompt')"
_CHECK_NAME = 'ck_group_owned_asset_type'


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == 'sqlite':
        with op.batch_alter_table('group_owned_asset') as batch_op:
            batch_op.drop_constraint(_CHECK_NAME, type_='check')
            batch_op.create_check_constraint(_CHECK_NAME, _NEW_CHECK)
    else:
        op.drop_constraint(_CHECK_NAME, 'group_owned_asset', type_='check')
        op.create_check_constraint(_CHECK_NAME, 'group_owned_asset', _NEW_CHECK)


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == 'sqlite':
        with op.batch_alter_table('group_owned_asset') as batch_op:
            batch_op.drop_constraint(_CHECK_NAME, type_='check')
            batch_op.create_check_constraint(_CHECK_NAME, _OLD_CHECK)
    else:
        op.drop_constraint(_CHECK_NAME, 'group_owned_asset', type_='check')
        op.create_check_constraint(_CHECK_NAME, 'group_owned_asset', _OLD_CHECK)
