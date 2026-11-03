"""Add indexes for channel message and reaction lookups and channel message search."""

import logging

import sqlalchemy as sa
from alembic import op

revision = 'c4d7a9e215b8'
down_revision = 'e42c8f710a36'
branch_labels = None
depends_on = None

INDEXES = [
    ('ix_message_channel_parent_created', 'message', ['channel_id', 'parent_id', 'created_at']),
    ('ix_message_parent_id', 'message', ['parent_id']),
    ('ix_message_reaction_message_id', 'message_reaction', ['message_id']),
]
TRIGRAM_INDEX_NAME = 'message_content_trgm_idx'
FTS_TABLE = 'message_fts'
FTS_TRIGGERS = ('message_fts_insert', 'message_fts_delete', 'message_fts_update')


def upgrade() -> None:
    for name, table, columns in INDEXES:
        op.create_index(name, table, columns, if_not_exists=True)

    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        upgrade_postgresql(conn)
    elif conn.dialect.name == 'sqlite':
        upgrade_sqlite(conn)


def upgrade_postgresql(conn: sa.Connection) -> None:
    try:
        with conn.begin_nested():
            op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
            op.create_index(
                TRIGRAM_INDEX_NAME,
                'message',
                ['content'],
                postgresql_using='gin',
                postgresql_ops={'content': 'gin_trgm_ops'},
                if_not_exists=True,
            )
    except sa.exc.DBAPIError as exc:
        if exc.connection_invalidated:
            raise
        # Alembic records a skipped attempt too; it will not retry on every startup.
        logging.getLogger(__name__).warning('Skipped PostgreSQL index %s: %s', TRIGRAM_INDEX_NAME, exc)


def upgrade_sqlite(conn: sa.Connection) -> None:
    try:
        with conn.begin_nested():
            op.execute(
                f'CREATE VIRTUAL TABLE IF NOT EXISTS {FTS_TABLE} USING fts5('
                "content, content='message', content_rowid='rowid', tokenize='trigram')"
            )
            op.execute(
                f'CREATE TRIGGER IF NOT EXISTS {FTS_TRIGGERS[0]} AFTER INSERT ON message BEGIN '
                f'INSERT INTO {FTS_TABLE}(rowid, content) VALUES (new.rowid, new.content); END'
            )
            op.execute(
                f'CREATE TRIGGER IF NOT EXISTS {FTS_TRIGGERS[1]} AFTER DELETE ON message BEGIN '
                f"INSERT INTO {FTS_TABLE}({FTS_TABLE}, rowid, content) VALUES ('delete', old.rowid, old.content); END"
            )
            op.execute(
                f'CREATE TRIGGER IF NOT EXISTS {FTS_TRIGGERS[2]} AFTER UPDATE OF content ON message BEGIN '
                f"INSERT INTO {FTS_TABLE}({FTS_TABLE}, rowid, content) VALUES ('delete', old.rowid, old.content); "
                f'INSERT INTO {FTS_TABLE}(rowid, content) VALUES (new.rowid, new.content); END'
            )
            op.execute(f"INSERT INTO {FTS_TABLE}({FTS_TABLE}) VALUES ('rebuild')")
    except sa.exc.DBAPIError as exc:
        if exc.connection_invalidated:
            raise
        logging.getLogger(__name__).warning('Skipped SQLite full-text index %s: %s', FTS_TABLE, exc)


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        op.drop_index(TRIGRAM_INDEX_NAME, table_name='message', if_exists=True)
    elif conn.dialect.name == 'sqlite':
        for trigger in FTS_TRIGGERS:
            op.execute(f'DROP TRIGGER IF EXISTS {trigger}')
        op.execute(f'DROP TABLE IF EXISTS {FTS_TABLE}')

    for name, table, _ in INDEXES:
        op.drop_index(name, table_name=table, if_exists=True)
