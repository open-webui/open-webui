"""Add indexes

Revision ID: 018012973d35
Revises: d31026856c01
Create Date: 2025-08-13 03:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = '018012973d35'
down_revision = 'd31026856c01'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    def _idx_exists(table, idx_name):
        return any(i['name'] == idx_name for i in inspector.get_indexes(table))

    # Chat table indexes
    if not _idx_exists('chat', 'folder_id_idx'):
        op.create_index('folder_id_idx', 'chat', ['folder_id'])
    if not _idx_exists('chat', 'user_id_pinned_idx'):
        op.create_index('user_id_pinned_idx', 'chat', ['user_id', 'pinned'])
    if not _idx_exists('chat', 'user_id_archived_idx'):
        op.create_index('user_id_archived_idx', 'chat', ['user_id', 'archived'])
    if not _idx_exists('chat', 'updated_at_user_id_idx'):
        op.create_index('updated_at_user_id_idx', 'chat', ['updated_at', 'user_id'])
    if not _idx_exists('chat', 'folder_id_user_id_idx'):
        op.create_index('folder_id_user_id_idx', 'chat', ['folder_id', 'user_id'])

    # Tag table index
    if not _idx_exists('tag', 'user_id_idx'):
        op.create_index('user_id_idx', 'tag', ['user_id'])

    # Function table index (only if is_global column exists — added by a later migration)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    func_cols = {c['name'] for c in inspector.get_columns('function')}
    if 'is_global' in func_cols and not _idx_exists('function', 'is_global_idx'):
        op.create_index('is_global_idx', 'function', ['is_global'])


def downgrade():
    # Chat table indexes
    op.drop_index('folder_id_idx', table_name='chat')
    op.drop_index('user_id_pinned_idx', table_name='chat')
    op.drop_index('user_id_archived_idx', table_name='chat')
    op.drop_index('updated_at_user_id_idx', table_name='chat')
    op.drop_index('folder_id_user_id_idx', table_name='chat')

    # Tag table index
    op.drop_index('user_id_idx', table_name='tag')

    # Function table index

    op.drop_index('is_global_idx', table_name='function')
