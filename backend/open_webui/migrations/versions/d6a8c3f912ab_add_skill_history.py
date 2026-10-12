"""Add immutable multi-file skill snapshots, preserving existing instruction bytes."""

import uuid

import sqlalchemy as sa
from alembic import op

revision = 'd6a8c3f912ab'
down_revision = 'b8e4f0a3c752'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('skill', sa.Column('version_id', sa.Text(), nullable=True))
    op.add_column('skill', sa.Column('data', sa.JSON(), nullable=True))
    history = op.create_table(
        'skill_history',
        sa.Column('id', sa.Text(), primary_key=True),
        sa.Column('skill_id', sa.Text(), nullable=False),
        sa.Column('parent_id', sa.Text(), nullable=True),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.Column('user_id', sa.Text(), nullable=False),
        sa.Column('commit_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
    )
    op.create_index('ix_skill_history_skill_id', 'skill_history', ['skill_id'])
    connection = op.get_bind()
    skill = sa.Table('skill', sa.MetaData(), autoload_with=connection)
    for row in connection.execute(sa.select(skill)).mappings():
        version_id = str(uuid.uuid4())
        data = {'files': [{'path': 'SKILL.md', 'content': row['content']}]}
        connection.execute(
            history.insert().values(
                id=version_id,
                skill_id=row['id'],
                parent_id=None,
                user_id=row['user_id'],
                commit_message=None,
                created_at=row['updated_at'],
                snapshot={
                    'name': row['name'],
                    'description': row['description'],
                    'meta': row['meta'] or {},
                    'content': row['content'],
                    'data': data,
                },
            )
        )
        connection.execute(skill.update().where(skill.c.id == row['id']).values(version_id=version_id, data=data))


def downgrade():
    op.drop_index('ix_skill_history_skill_id', table_name='skill_history')
    op.drop_table('skill_history')
    with op.batch_alter_table('skill') as batch:
        batch.drop_column('version_id')
        batch.drop_column('data')
