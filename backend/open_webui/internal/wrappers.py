import logging
import os
from contextvars import ContextVar

from peewee import *
from peewee import InterfaceError as PeeWeeInterfaceError
from peewee import PostgresqlDatabase
from playhouse.db_url import connect, parse
from playhouse.shortcuts import ReconnectMixin

log = logging.getLogger(__name__)

db_state_default = {"closed": None, "conn": None, "ctx": None, "transactions": None}
db_state = ContextVar("db_state", default=db_state_default.copy())


class PeeweeConnectionState(object):
    def __init__(self, **kwargs):
        super().__setattr__("_state", db_state)
        super().__init__(**kwargs)

    def __setattr__(self, name, value):
        self._state.get()[name] = value

    def __getattr__(self, name):
        value = self._state.get()[name]
        return value


class CustomReconnectMixin(ReconnectMixin):
    reconnect_errors = (
        # psycopg2
        (OperationalError, "termin"),
        (InterfaceError, "closed"),
        # peewee
        (PeeWeeInterfaceError, "closed"),
    )


class ReconnectingPostgresqlDatabase(CustomReconnectMixin, PostgresqlDatabase):
    pass


def register_connection(db_url):
    # Check if using SQLCipher protocol
    if db_url.startswith("sqlite+sqlcipher://"):
        database_password = os.environ.get("DATABASE_PASSWORD")
        if not database_password or database_password.strip() == "":
            raise ValueError(
                "DATABASE_PASSWORD is required when using sqlite+sqlcipher:// URLs"
            )
        from playhouse.sqlcipher_ext import SqlCipherDatabase

        # Parse the database path from SQLCipher URL
        # Convert sqlite+sqlcipher:///path/to/db.sqlite to /path/to/db.sqlite
        db_path = db_url.replace("sqlite+sqlcipher://", "")

        # Use Peewee's native SqlCipherDatabase with encryption
        db = SqlCipherDatabase(db_path, passphrase=database_password)
        db.autoconnect = True
        db.reuse_if_open = True
        log.info("Connected to encrypted SQLite database using SQLCipher")

    else:
        # Standard database connection (existing logic)
        db = connect(db_url, unquote_user=True, unquote_password=True)
        if isinstance(db, PostgresqlDatabase):
            # Enable autoconnect for SQLite databases, managed by Peewee
            db.autoconnect = True
            db.reuse_if_open = True
            log.info("Connected to PostgreSQL database")

            # Get the connection details
            connection = parse(db_url, unquote_user=True, unquote_password=True)

            # Use our custom database class that supports reconnection
            db = ReconnectingPostgresqlDatabase(**connection)
            db.connect(reuse_if_open=True)
        elif isinstance(db, SqliteDatabase):
            # Enable autoconnect for SQLite databases, managed by Peewee
            db.autoconnect = True
            db.reuse_if_open = True
            log.info("Connected to SQLite database")
        else:
            raise ValueError("Unsupported database connection")
    return db
