"""add knowledge_directory table

Revision ID: 3c9b0ca343fd
Revises: a0b1c2d3e4f5
Create Date: 2026-05-13 21:58:40.832482

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '3c9b0ca343fd'
down_revision: Union[str, None] = 'a0b1c2d3e4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if 'knowledge_directory' not in existing_tables:
        # Create knowledge_directory table
        op.create_table(
            'knowledge_directory',
            sa.Column('id', sa.Text(), nullable=False),
            sa.Column('knowledge_id', sa.Text(), nullable=False),
            sa.Column('parent_id', sa.Text(), nullable=True),
            sa.Column('name', sa.Text(), nullable=False),
            sa.Column('user_id', sa.Text(), nullable=False),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
            sa.ForeignKeyConstraint(['knowledge_id'], ['knowledge.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['parent_id'], ['knowledge_directory.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint(
                'knowledge_id', 'parent_id', 'name', name='uq_knowledge_directory_knowledge_parent_name'
            ),
        )
        op.create_index('ix_knowledge_directory_knowledge_id', 'knowledge_directory', ['knowledge_id'])
        op.create_index('ix_knowledge_directory_parent_id', 'knowledge_directory', ['parent_id'])

    # Add directory_id column to knowledge_file
    kf_cols = {c['name'] for c in inspector.get_columns('knowledge_file')}
    if 'directory_id' not in kf_cols:
        with op.batch_alter_table('knowledge_file') as batch:
            batch.add_column(sa.Column('directory_id', sa.Text(), nullable=True))
            batch.create_foreign_key(
                'fk_knowledge_file_directory_id',
                'knowledge_directory',
                ['directory_id'],
                ['id'],
                ondelete='SET NULL',
            )
            batch.create_index('ix_knowledge_file_directory_id', ['directory_id'])


def downgrade() -> None:
    # Remove directory_id from knowledge_file
    with op.batch_alter_table('knowledge_file') as batch:
        batch.drop_index('ix_knowledge_file_directory_id')
        batch.drop_constraint('fk_knowledge_file_directory_id', type_='foreignkey')
        batch.drop_column('directory_id')

    # Drop knowledge_directory table
    op.drop_index('ix_knowledge_directory_parent_id', table_name='knowledge_directory')
    op.drop_index('ix_knowledge_directory_knowledge_id', table_name='knowledge_directory')
    op.drop_table('knowledge_directory')
