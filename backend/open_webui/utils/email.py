"""NFC normalization shared by account writes and database email comparisons."""

import unicodedata

from sqlalchemy import String, event
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.functions import FunctionElement
from sqlalchemy.types import TypeDecorator


def normalize_email(email: str) -> str:
    """Compose equivalent Unicode spellings without changing syntax or case."""
    return unicodedata.normalize('NFC', email)


class NFCEmail(TypeDecorator):
    """Store account email values in NFC, including ORM and bulk writes."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return normalize_email(value) if value is not None else None


class email_nfc(FunctionElement):
    """Canonical Unicode normalization in database email expressions."""

    type = String()
    inherit_cache = True


@compiles(email_nfc, 'sqlite')
def _sqlite_email_nfc(element, compiler, **kwargs):
    return f'unicode_nfc({compiler.process(element.clauses, **kwargs)})'


@compiles(email_nfc, 'postgresql')
def _postgresql_email_nfc(element, compiler, **kwargs):
    return f'normalize({compiler.process(element.clauses, **kwargs)}, NFC)'


class email_key(FunctionElement):
    """Case-insensitive canonical account key, including Unicode on SQLite."""

    type = String()
    inherit_cache = True


@compiles(email_key, 'sqlite')
def _sqlite_email_key(element, compiler, **kwargs):
    return f'unicode_email_key({compiler.process(element.clauses, **kwargs)})'


@compiles(email_key, 'postgresql')
def _postgresql_email_key(element, compiler, **kwargs):
    return f'normalize(lower(normalize({compiler.process(element.clauses, **kwargs)}, NFC)), NFC)'


def _register_sqlite_email_normalization(dbapi_connection, connection_record):
    dbapi_connection.create_function(
        'unicode_nfc', 1, lambda value: normalize_email(value) if value is not None else None, deterministic=True
    )
    # SQLite's built-in lower() folds only ASCII. Use the same Unicode lower()
    # as account inputs, without changing SQL lower() for unrelated queries.
    dbapi_connection.create_function(
        'unicode_email_key',
        1,
        lambda value: normalize_email(normalize_email(value).lower()) if value is not None else None,
        deterministic=True,
    )


def register_sqlite_email_normalization(engine):
    """Install the deterministic index function on every SQLite connection."""
    engine = getattr(engine, 'sync_engine', engine)
    if engine.dialect.name == 'sqlite' and not event.contains(engine, 'connect', _register_sqlite_email_normalization):
        event.listen(engine, 'connect', _register_sqlite_email_normalization)
