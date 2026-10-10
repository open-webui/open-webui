"""Add model configuration history and initialize Production versions."""

import json
import uuid

import sqlalchemy as sa
from alembic import op

revision = 'e7b9d4a023bc'
down_revision = 'd6a8c3f912ab'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('model', sa.Column('version_id', sa.Text(), nullable=True))
    history = op.create_table(
        'model_history',
        sa.Column('id', sa.Text(), primary_key=True),
        sa.Column('model_id', sa.Text(), nullable=False),
        sa.Column('parent_id', sa.Text(), nullable=True),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.Column('user_id', sa.Text(), nullable=False),
        sa.Column('commit_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
    )
    op.create_index('ix_model_history_model_id', 'model_history', ['model_id'])
    connection = op.get_bind()
    model = sa.Table('model', sa.MetaData(), autoload_with=connection)
    for row in connection.execute(sa.select(model)).mappings():
        snapshot = {key: row[key] for key in ('name', 'base_model_id', 'params', 'meta')}
        for key in ('params', 'meta'):
            value = snapshot[key]
            snapshot[key] = json.loads(value) if isinstance(value, str) else dict(value or {})
        meta = snapshot['meta']
        meta.pop('hidden', None)
        meta.pop('chat_variables_schema', None)
        version_id = str(uuid.uuid4())
        connection.execute(
            history.insert().values(
                id=version_id,
                model_id=row['id'],
                parent_id=None,
                snapshot=snapshot,
                user_id=row['user_id'] or '',
                commit_message=None,
                created_at=row['updated_at'] or row['created_at'] or 0,
            )
        )
        connection.execute(model.update().where(model.c.id == row['id']).values(version_id=version_id))


def downgrade():
    op.drop_index('ix_model_history_model_id', table_name='model_history')
    op.drop_table('model_history')
    with op.batch_alter_table('model') as batch:
        batch.drop_column('version_id')
