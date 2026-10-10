"""Add Tool and Function history without executing or rewriting plugin source."""

import json
import uuid

import sqlalchemy as sa
from alembic import op

revision = 'f8c0e5b134cd'
down_revision = 'e7b9d4a023bc'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    for kind in ('tool', 'function'):
        op.add_column(kind, sa.Column('version_id', sa.Text(), nullable=True))
        history = op.create_table(
            f'{kind}_history',
            sa.Column('id', sa.Text(), primary_key=True),
            sa.Column(f'{kind}_id', sa.Text(), nullable=False),
            sa.Column('parent_id', sa.Text(), nullable=True),
            sa.Column('snapshot', sa.JSON(), nullable=False),
            sa.Column('user_id', sa.Text(), nullable=False),
            sa.Column('commit_message', sa.Text(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
        )
        op.create_index(f'ix_{kind}_history_{kind}_id', f'{kind}_history', [f'{kind}_id'])
        table = sa.Table(kind, sa.MetaData(), autoload_with=connection)
        for row in connection.execute(sa.select(table)).mappings():
            meta = row['meta'] or {}
            meta = json.loads(meta) if isinstance(meta, str) else dict(meta)
            for key in (
                ('manifest', 'has_user_valves', 'toggle') if kind == 'function' else ('manifest', 'has_user_valves')
            ):
                meta.pop(key, None)
            meta.setdefault('description', None)
            if not meta.get('i18n'):
                meta.pop('i18n', None)
            snapshot = {'name': row['name'], 'content': row['content'] or '', 'meta': meta}
            version_id = str(uuid.uuid4())
            connection.execute(
                history.insert().values(
                    **{
                        'id': version_id,
                        f'{kind}_id': row['id'],
                        'parent_id': None,
                        'snapshot': snapshot,
                        'user_id': row['user_id'] or '',
                        'commit_message': None,
                        'created_at': row['updated_at'] or row['created_at'] or 0,
                    }
                )
            )
            connection.execute(table.update().where(table.c.id == row['id']).values(version_id=version_id))


def downgrade():
    for kind in ('function', 'tool'):
        op.drop_index(f'ix_{kind}_history_{kind}_id', table_name=f'{kind}_history')
        op.drop_table(f'{kind}_history')
        with op.batch_alter_table(kind) as batch:
            batch.drop_column('version_id')
