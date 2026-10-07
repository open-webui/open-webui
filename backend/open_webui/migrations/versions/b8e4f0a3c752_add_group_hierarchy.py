"""Add single-parent group hierarchy.

Revision ID: b8e4f0a3c752
Revises: a7d3e9f2b641
"""

from alembic import op
import sqlalchemy as sa

revision = 'b8e4f0a3c752'
down_revision = 'a7d3e9f2b641'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('group') as batch:
        batch.add_column(
            sa.Column(
                'parent_group_id',
                sa.Text(),
                sa.ForeignKey('group.id', name='fk_group_parent', ondelete='SET NULL'),
                nullable=True,
            )
        )
        batch.create_index('ix_group_parent_group_id', ['parent_group_id'])


def downgrade():
    with op.batch_alter_table('group') as batch:
        batch.drop_index('ix_group_parent_group_id')
        batch.drop_constraint('fk_group_parent', type_='foreignkey')
        batch.drop_column('parent_group_id')
