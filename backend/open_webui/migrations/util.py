import sqlalchemy as sa
from alembic import context, op
from sqlalchemy import Inspector


def _dialect_name(conn=None) -> str:
    """
    Return current dialect name.
    Prefer a live Alembic bind when available; fall back to Alembic context
    during offline (`--sql`) runs. If no dialect can be determined, return
    an empty string so callers can choose a safe default.
    """
    if conn is not None:
        return (conn.dialect.name or '').lower()

    try:
        conn = op.get_bind()
    except Exception:
        conn = None

    if conn is not None:
        return (conn.dialect.name or '').lower()

    try:
        return (context.get_context().dialect.name or '').lower()
    except Exception:
        return ''


def key_text(conn=None, length: int = 255):
    """
    Dialect-aware TEXT for identifiers/keys.
    - MySQL/MariaDB: TEXT cannot be indexed/PK'd without prefix length => use VARCHAR(length).
    - PostgreSQL/SQLite: keep TEXT (historical behavior).
    """
    d = _dialect_name(conn)
    if d in ('mysql', 'mariadb'):
        return sa.String(length=length)
    return sa.Text()


def get_existing_tables():
    con = op.get_bind()
    inspector = Inspector.from_engine(con)
    tables = set(inspector.get_table_names())
    return tables


def get_revision_id():
    import uuid

    return str(uuid.uuid4()).replace('-', '')[:12]
