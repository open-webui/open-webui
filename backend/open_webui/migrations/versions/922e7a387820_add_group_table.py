"""Add group table

Revision ID: 922e7a387820
Revises: 4ace53fd72c8
Create Date: 2024-11-14 03:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = '922e7a387820'
down_revision = '4ace53fd72c8'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if 'group' not in existing_tables:
        op.create_table(
            'group',
            sa.Column('id', sa.Text(), nullable=False, primary_key=True, unique=True),
            sa.Column('user_id', sa.Text(), nullable=True),
            sa.Column('name', sa.Text(), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('data', sa.JSON(), nullable=True),
            sa.Column('meta', sa.JSON(), nullable=True),
            sa.Column('permissions', sa.JSON(), nullable=True),
            sa.Column('user_ids', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=True),
            sa.Column('updated_at', sa.BigInteger(), nullable=True),
        )

    # Add 'access_control' column to 'model' table
    model_cols = {c['name'] for c in inspector.get_columns('model')}
    if 'access_control' not in model_cols:
        op.add_column('model', sa.Column('access_control', sa.JSON(), nullable=True))
    if 'is_active' not in model_cols:
        op.add_column(
            'model',
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.sql.expression.true()),
        )

    # Add 'access_control' column to 'knowledge' table
    knowledge_cols = {c['name'] for c in inspector.get_columns('knowledge')}
    if 'access_control' not in knowledge_cols:
        op.add_column('knowledge', sa.Column('access_control', sa.JSON(), nullable=True))

    # Add 'access_control' column to 'prompt' table
    prompt_cols = {c['name'] for c in inspector.get_columns('prompt')}
    if 'access_control' not in prompt_cols:
        op.add_column('prompt', sa.Column('access_control', sa.JSON(), nullable=True))

    # Add 'access_control' column to 'tools' table
    tool_cols = {c['name'] for c in inspector.get_columns('tool')}
    if 'access_control' not in tool_cols:
        op.add_column('tool', sa.Column('access_control', sa.JSON(), nullable=True))


def downgrade():
    op.drop_table('group')
    op.drop_column('model', 'access_control')
    op.drop_column('model', 'is_active')
    op.drop_column('knowledge', 'access_control')
    op.drop_column('prompt', 'access_control')
    op.drop_column('tool', 'access_control')
