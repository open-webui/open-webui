"""Add resource comments and reactions.

Revision ID: c41f8d9e2a10
Revises: 0bd252b206fb
"""

import sqlalchemy as sa
from alembic import op

revision = 'c41f8d9e2a10'
down_revision = '0bd252b206fb'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'comment',
        sa.Column('id', sa.Text(), primary_key=True),
        sa.Column('user_id', sa.Text(), nullable=True),
        sa.Column('resource_type', sa.Text(), nullable=False),
        sa.Column('resource_id', sa.Text(), nullable=False),
        sa.Column('parent_id', sa.Text(), nullable=True),
        sa.Column('reply_to_id', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('target_type', sa.Text(), nullable=True),
        sa.Column('target_id', sa.Text(), nullable=True),
        sa.Column('meta', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
        sa.Column('deleted_at', sa.BigInteger(), nullable=True),
    )
    op.create_index('ix_comment_resource', 'comment', ['resource_type', 'resource_id', 'parent_id', 'created_at', 'id'])
    op.create_index('ix_comment_parent', 'comment', ['parent_id', 'created_at', 'id'])
    op.create_index('ix_comment_target', 'comment', ['resource_type', 'resource_id', 'target_type', 'target_id'])
    op.create_table(
        'comment_reaction',
        sa.Column('id', sa.Text(), primary_key=True),
        sa.Column('user_id', sa.Text(), nullable=False),
        sa.Column('comment_id', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.UniqueConstraint('comment_id', 'user_id', 'name', name='uq_comment_reaction'),
    )
    op.create_index('ix_comment_reaction_comment_id', 'comment_reaction', ['comment_id'])


def downgrade():
    op.drop_table('comment_reaction')
    op.drop_table('comment')
