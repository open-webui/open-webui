"""Add resource_tag, one table linking tags to chats and notes in place of meta.tags, and note.folder_id.

Revision ID: b7d4f1a2c960
Revises: c4e1a7d93b20
"""

import time
import uuid

import sqlalchemy as sa
from alembic import op

revision = 'b7d4f1a2c960'
down_revision = 'c4e1a7d93b20'
branch_labels = None
depends_on = None

BATCH_SIZE = 500
# Postgres can't index much longer values.
MAX_TAG_LENGTH = 500

resource_tag = sa.table(
    'resource_tag',
    sa.column('id', sa.Text),
    sa.column('resource_type', sa.Text),
    sa.column('resource_id', sa.Text),
    sa.column('tag_id', sa.Text),
    sa.column('user_id', sa.Text),
    sa.column('created_at', sa.BigInteger),
)
# Only these columns: chat rows also hold the whole conversation.
RESOURCES = {
    name: sa.table(name, sa.column('id', sa.Text), sa.column('user_id', sa.Text), sa.column('meta', sa.JSON))
    for name in ('chat', 'note')
}


def _batches(conn, resource):
    """Rows of (id, user_id, meta) in id order, a batch at a time."""
    stmt = sa.select(resource.c.id, resource.c.user_id, resource.c.meta).order_by(resource.c.id).limit(BATCH_SIZE)
    if conn.dialect.name == 'sqlite':
        # SQLite accepts text that isn't JSON in a JSON column; such rows have no tags to read.
        stmt = stmt.where(sa.or_(resource.c.meta.is_(None), sa.func.json_valid(resource.c.meta) == 1))
    last_id = ''
    while True:
        rows = conn.execute(stmt.where(resource.c.id > last_id)).all()
        if not rows:
            return
        yield rows
        last_id = rows[-1].id


def _tag_ids(tags):
    """The list's usable tags, without the characters a JSON string can hold but a text column can't."""
    ids = [
        tag.replace('\x00', '').encode('utf-8', 'ignore').decode()
        for tag in (tags if isinstance(tags, list) else [])
        if isinstance(tag, str)
    ]
    return list(dict.fromkeys(tag_id for tag_id in ids if 0 < len(tag_id) <= MAX_TAG_LENGTH))


def _set_meta(conn, resource, metas):
    """Write a batch of {id: meta}."""
    if not metas:
        return
    if conn.dialect.name == 'postgresql':
        # One statement per batch: here an executemany would go to the server row by row.
        new = sa.values(sa.column('id', sa.Text), sa.column('meta', sa.JSON), name='new').data(list(metas.items()))
        conn.execute(sa.update(resource).where(resource.c.id == new.c.id).values(meta=sa.cast(new.c.meta, sa.JSON)))
    else:
        conn.execute(
            sa.update(resource)
            .where(resource.c.id == sa.bindparam('b_id'))
            .values(meta=sa.bindparam('b_meta', type_=sa.JSON)),
            [{'b_id': id, 'b_meta': meta} for id, meta in metas.items()],
        )


def upgrade():
    conn = op.get_bind()
    if 'resource_tag' not in sa.inspect(conn).get_table_names():
        op.create_table(
            'resource_tag',
            sa.Column('id', sa.Text(), nullable=False),
            sa.Column('resource_type', sa.Text(), nullable=False),
            sa.Column('resource_id', sa.Text(), nullable=False),
            sa.Column('tag_id', sa.Text(), nullable=False),
            sa.Column('user_id', sa.Text(), nullable=False),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('resource_type', 'resource_id', 'tag_id', name='uq_resource_tag'),
        )
        op.create_index('ix_resource_tag_user_id_tag_id', 'resource_tag', ['user_id', 'tag_id'])

    inspector = sa.inspect(conn)
    if 'folder_id' not in {column['name'] for column in inspector.get_columns('note')}:
        op.add_column('note', sa.Column('folder_id', sa.Text(), nullable=True))
    if 'ix_note_folder_id' not in {index['name'] for index in inspector.get_indexes('note')}:
        op.create_index('ix_note_folder_id', 'note', ['folder_id'])

    for resource_type, resource in RESOURCES.items():
        for rows in _batches(conn, resource):
            links = []
            stripped = {}
            for row in rows:
                # Without an owner there is nobody for the tags to belong to.
                if row.user_id is None or not isinstance(row.meta, dict) or 'tags' not in row.meta:
                    continue
                # created_at keeps the list's order.
                now = time.time_ns()
                for index, tag_id in enumerate(_tag_ids(row.meta['tags'])):
                    links.append(
                        {
                            'id': str(uuid.uuid4()),
                            'resource_type': resource_type,
                            'resource_id': row.id,
                            'tag_id': tag_id,
                            'user_id': row.user_id,
                            'created_at': now + index,
                        }
                    )
                stripped[row.id] = {key: value for key, value in row.meta.items() if key != 'tags'}
            if links:
                conn.execute(sa.insert(resource_tag), links)
            _set_meta(conn, resource, stripped)


def downgrade():
    conn = op.get_bind()
    for resource_type, resource in RESOURCES.items():
        for rows in _batches(conn, resource):
            tags = {}
            for resource_id, tag_id in conn.execute(
                sa.select(resource_tag.c.resource_id, resource_tag.c.tag_id)
                .where(
                    resource_tag.c.resource_type == resource_type,
                    resource_tag.c.resource_id.in_([row.id for row in rows]),
                )
                .order_by(resource_tag.c.created_at, resource_tag.c.tag_id)
            ):
                tags.setdefault(resource_id, []).append(tag_id)
            _set_meta(
                conn, resource, {row.id: {**(row.meta or {}), 'tags': tags[row.id]} for row in rows if row.id in tags}
            )
    op.drop_index('ix_note_folder_id', table_name='note')
    op.drop_column('note', 'folder_id')
    op.drop_index('ix_resource_tag_user_id_tag_id', table_name='resource_tag')
    op.drop_table('resource_tag')
