"""add automation folder id

Revision ID: 959eaac8f909
Revises: 55f1302ac17c
Create Date: 2026-07-26 19:19:31.345756

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision: str = '959eaac8f909'
down_revision: str | None = '55f1302ac17c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if context.is_offline_mode():
        op.add_column('automation', sa.Column('folder_id', sa.Text(), nullable=True))
        op.create_index('ix_automation_user_folder', 'automation', ['user_id', 'folder_id'])
        return

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {col['name'] for col in inspector.get_columns('automation')}
    indexes = {index['name'] for index in inspector.get_indexes('automation')}

    if 'folder_id' not in columns:
        op.add_column('automation', sa.Column('folder_id', sa.Text(), nullable=True))

    if 'ix_automation_user_folder' not in indexes:
        op.create_index('ix_automation_user_folder', 'automation', ['user_id', 'folder_id'])


def downgrade() -> None:
    if context.is_offline_mode():
        op.drop_index('ix_automation_user_folder', table_name='automation')
        op.drop_column('automation', 'folder_id')
        return

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {col['name'] for col in inspector.get_columns('automation')}
    indexes = {index['name'] for index in inspector.get_indexes('automation')}

    if 'ix_automation_user_folder' in indexes:
        op.drop_index('ix_automation_user_folder', table_name='automation')

    if 'folder_id' in columns:
        op.drop_column('automation', 'folder_id')
