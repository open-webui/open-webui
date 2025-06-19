"""Add performance indexes to chat, tag, and function tables

---
Database Indexing & Migration Instructions
------------------------------------------
Open-WebUI now automatically creates indexes on key columns in the `chat`, `tag`, and `function` tables for improved performance with SQLite and PostgreSQL.

**For existing installations:**
Apply this migration to add the new indexes to your database:

    alembic upgrade head

This will significantly speed up filtering, sorting, and joining operations as your data grows.
---

Revision ID: 20250619_add_indexes
Revises:
Create Date: 2025-06-19

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250619_add_indexes'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Chat table indexes
    op.create_index('folder_id_idx', 'chat', ['folder_id'])
    op.create_index('user_id_pinned_idx', 'chat', ['user_id', 'pinned'])
    op.create_index('user_id_archived_idx', 'chat', ['user_id', 'archived'])
    op.create_index('updated_at_user_id_idx', 'chat', ['updated_at', 'user_id'])
    op.create_index('folder_id_user_id_idx', 'chat', ['folder_id', 'user_id'])

    # Tag table index
    op.create_index('user_id_idx', 'tag', ['user_id'])

    # Function table index
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