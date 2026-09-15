"""add Chinese comments to database tables and columns"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op
from open_webui.models.db_comments import COLUMN_COMMENTS, TABLE_COMMENTS

revision: str = '4f7a8c9d0e1b'
down_revision: tuple[str, str] = ('d4c1a8e37b62', 'f0bd01a18a3d')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _comment_postgresql(table_name: str, column_name: str | None, comment: str | None) -> None:
    preparer = op.get_bind().dialect.identifier_preparer
    table = preparer.quote(table_name)
    target = f'{table}.{preparer.quote(column_name)}' if column_name else table
    object_type = 'COLUMN' if column_name else 'TABLE'
    op.execute(sa.text(f'COMMENT ON {object_type} {target} IS {_literal(comment or "")}'))


def _comment_mysql(table_name: str, column_name: str, comment: str, column: dict) -> None:
    op.alter_column(
        table_name,
        column_name,
        comment=comment,
        existing_type=column['type'],
        existing_nullable=column['nullable'],
        existing_server_default=column['default'],
    )


def _comment_table_mysql(table_name: str, comment: str) -> None:
    preparer = op.get_bind().dialect.identifier_preparer
    op.execute(sa.text(f'ALTER TABLE {preparer.quote(table_name)} COMMENT = {_literal(comment)}'))


def _apply_comments(connection: sa.Connection, table_name: str, table_comment: str, dialect: str) -> None:
    inspector = sa.inspect(connection)
    if dialect == 'postgresql':
        _comment_postgresql(table_name, None, table_comment)
        for column in inspector.get_columns(table_name):
            comment = COLUMN_COMMENTS.get(column['name'])
            if comment:
                _comment_postgresql(table_name, column['name'], comment)
    elif dialect in {'mysql', 'mariadb'}:
        _comment_table_mysql(table_name, table_comment)
        for column in inspector.get_columns(table_name):
            comment = COLUMN_COMMENTS.get(column['name'])
            if comment:
                _comment_mysql(table_name, column['name'], comment, column)


def upgrade() -> None:
    if context.is_offline_mode():
        if context.get_context().dialect.name == 'postgresql':
            for table_name, comment in TABLE_COMMENTS.items():
                _comment_postgresql(table_name, None, comment)
        return

    connection = op.get_bind()
    dialect = connection.dialect.name
    if dialect == 'sqlite':
        return

    existing_tables = set(sa.inspect(connection).get_table_names())
    for table_name, table_comment in TABLE_COMMENTS.items():
        if table_name not in existing_tables:
            continue
        _apply_comments(connection, table_name, table_comment, dialect)


def downgrade() -> None:
    if context.is_offline_mode() or op.get_bind().dialect.name == 'sqlite':
        return

    connection = op.get_bind()
    dialect = connection.dialect.name
    inspector = sa.inspect(connection)
    for table_name in TABLE_COMMENTS:
        if table_name not in inspector.get_table_names():
            continue
        if dialect == 'postgresql':
            _comment_postgresql(table_name, None, None)
            for column in inspector.get_columns(table_name):
                if column['name'] in COLUMN_COMMENTS:
                    _comment_postgresql(table_name, column['name'], None)
