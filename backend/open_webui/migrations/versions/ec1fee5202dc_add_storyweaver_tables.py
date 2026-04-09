"""add_storyweaver_tables

Revision ID: ec1fee5202dc
Revises: b2c3d4e5f6a7
Create Date: 2026-04-07 22:15:00.433666

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = 'ec1fee5202dc'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add Tables for StoryWeaver
    op.create_table(
        'sw_novel',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id')
    )

    op.create_table(
        'sw_knowledge_base',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('novel_id', sa.String(), nullable=False),
        sa.Column('universe_docs', sa.JSON(), nullable=True),
        sa.Column('characters', sa.JSON(), nullable=True),
        sa.Column('locations', sa.JSON(), nullable=True),
        sa.Column('objects', sa.JSON(), nullable=True),
        sa.Column('timeline', sa.JSON(), nullable=True),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id'),
        sa.UniqueConstraint('novel_id')
    )

    op.create_table(
        'sw_manuscript',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('novel_id', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('chapter_structure', sa.JSON(), nullable=True),
        sa.Column('word_count', sa.BigInteger(), nullable=True),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id'),
        sa.UniqueConstraint('novel_id')
    )

    op.create_table(
        'sw_version',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('novel_id', sa.String(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('entity_id', sa.String(), nullable=False),
        sa.Column('old_data', sa.JSON(), nullable=True),
        sa.Column('new_data', sa.JSON(), nullable=False),
        sa.Column('change_type', sa.String(), nullable=False),
        sa.Column('version_number', sa.BigInteger(), nullable=False),
        sa.Column('timestamp', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id')
    )

    # Add active session context directly to user
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(sa.Column('current_novel_id', sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_column('current_novel_id')

    op.drop_table('sw_version')
    op.drop_table('sw_manuscript')
    op.drop_table('sw_knowledge_base')
    op.drop_table('sw_novel')
