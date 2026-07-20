"""add knowledge management tables

Revision ID: a7b8c9d0e1f2
Revises: 42e2978c7933
Create Date: 2026-07-20 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, None] = '42e2978c7933'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # -- knowledge_chunk table --
    if 'knowledge_chunk' not in existing_tables:
        op.create_table(
            'knowledge_chunk',
            sa.Column('id', sa.Text(), nullable=False),
            sa.Column('knowledge_id', sa.Text(), nullable=False),
            sa.Column('file_id', sa.Text(), nullable=False),
            sa.Column('chunk_index', sa.BigInteger(), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('token_count', sa.BigInteger(), nullable=True),
            sa.Column('meta', sa.JSON(), nullable=True),
            sa.Column('content_hash', sa.Text(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('file_id', 'chunk_index', name='uq_knowledge_chunk_file_index'),
            sa.ForeignKeyConstraint(['knowledge_id'], ['knowledge.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['file_id'], ['file.id'], ondelete='CASCADE'),
        )
        op.create_index('ix_knowledge_chunk_knowledge_id', 'knowledge_chunk', ['knowledge_id'])
        op.create_index('ix_knowledge_chunk_file_id', 'knowledge_chunk', ['file_id'])

    # -- knowledge_processing_task table --
    if 'knowledge_processing_task' not in existing_tables:
        op.create_table(
            'knowledge_processing_task',
            sa.Column('id', sa.Text(), nullable=False),
            sa.Column('knowledge_id', sa.Text(), nullable=False),
            sa.Column('file_id', sa.Text(), nullable=True),
            sa.Column('task_type', sa.Text(), nullable=False),
            sa.Column('status', sa.Text(), nullable=False),
            sa.Column('progress_pct', sa.BigInteger(), nullable=False, server_default='0'),
            sa.Column('chunks_total', sa.BigInteger(), nullable=True),
            sa.Column('chunks_processed', sa.BigInteger(), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['knowledge_id'], ['knowledge.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['file_id'], ['file.id'], ondelete='CASCADE'),
        )
        op.create_index('ix_knowledge_processing_knowledge_id', 'knowledge_processing_task', ['knowledge_id'])
        op.create_index('ix_knowledge_processing_file_id', 'knowledge_processing_task', ['file_id'])

    # -- knowledge_batch_task table --
    if 'knowledge_batch_task' not in existing_tables:
        op.create_table(
            'knowledge_batch_task',
            sa.Column('id', sa.Text(), nullable=False),
            sa.Column('knowledge_id', sa.Text(), nullable=False),
            sa.Column('total_files', sa.BigInteger(), nullable=False),
            sa.Column('files_processed', sa.BigInteger(), nullable=False, server_default='0'),
            sa.Column('total_chunks', sa.BigInteger(), nullable=True),
            sa.Column('chunks_embedded', sa.BigInteger(), nullable=True, server_default='0'),
            sa.Column('status', sa.Text(), nullable=False),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['knowledge_id'], ['knowledge.id'], ondelete='CASCADE'),
        )
        op.create_index('ix_knowledge_batch_knowledge_id', 'knowledge_batch_task', ['knowledge_id'])

    # -- knowledge_relevance_judgment table --
    if 'knowledge_relevance_judgment' not in existing_tables:
        op.create_table(
            'knowledge_relevance_judgment',
            sa.Column('id', sa.Text(), nullable=False),
            sa.Column('knowledge_id', sa.Text(), nullable=False),
            sa.Column('query_text', sa.Text(), nullable=False),
            sa.Column('chunk_id', sa.Text(), nullable=True),
            sa.Column('document_text', sa.Text(), nullable=False),
            sa.Column('rank_position', sa.BigInteger(), nullable=True),
            sa.Column('relevance', sa.BigInteger(), nullable=False),
            sa.Column('user_id', sa.Text(), nullable=False),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['knowledge_id'], ['knowledge.id'], ondelete='CASCADE'),
        )
        op.create_index('ix_knowledge_judgment_knowledge_id', 'knowledge_relevance_judgment', ['knowledge_id'])
        op.create_index('ix_knowledge_judgment_query', 'knowledge_relevance_judgment', ['knowledge_id', 'query_text'])

    # -- knowledge_snapshot table --
    if 'knowledge_snapshot' not in existing_tables:
        op.create_table(
            'knowledge_snapshot',
            sa.Column('id', sa.Text(), nullable=False),
            sa.Column('knowledge_id', sa.Text(), nullable=False),
            sa.Column('label', sa.Text(), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('file_count', sa.BigInteger(), nullable=False),
            sa.Column('chunk_count', sa.BigInteger(), nullable=True),
            sa.Column('snapshot_data', sa.JSON(), nullable=False),
            sa.Column('collection_snapshot_path', sa.Text(), nullable=True),
            sa.Column('created_by', sa.Text(), nullable=False),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['knowledge_id'], ['knowledge.id'], ondelete='CASCADE'),
        )
        op.create_index('ix_knowledge_snapshot_knowledge_id', 'knowledge_snapshot', ['knowledge_id'])


def downgrade() -> None:
    op.drop_index('ix_knowledge_snapshot_knowledge_id', table_name='knowledge_snapshot')
    op.drop_table('knowledge_snapshot')

    op.drop_index('ix_knowledge_judgment_query', table_name='knowledge_relevance_judgment')
    op.drop_index('ix_knowledge_judgment_knowledge_id', table_name='knowledge_relevance_judgment')
    op.drop_table('knowledge_relevance_judgment')

    op.drop_index('ix_knowledge_batch_knowledge_id', table_name='knowledge_batch_task')
    op.drop_table('knowledge_batch_task')

    op.drop_index('ix_knowledge_processing_file_id', table_name='knowledge_processing_task')
    op.drop_index('ix_knowledge_processing_knowledge_id', table_name='knowledge_processing_task')
    op.drop_table('knowledge_processing_task')

    op.drop_index('ix_knowledge_chunk_file_id', table_name='knowledge_chunk')
    op.drop_index('ix_knowledge_chunk_knowledge_id', table_name='knowledge_chunk')
    op.drop_table('knowledge_chunk')
