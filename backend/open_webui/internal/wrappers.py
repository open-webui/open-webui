import logging
from contextvars import ContextVar

from open_webui.env import SRC_LOG_LEVELS, DATABASE_SCHEMA
from peewee import *
from peewee import InterfaceError as PeeWeeInterfaceError
from peewee import PostgresqlDatabase
from playhouse.db_url import connect, parse
from playhouse.shortcuts import ReconnectMixin

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["DB"])

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
    db = connect(db_url, unquote_user=True, unquote_password=True)
    if isinstance(db, PostgresqlDatabase):
        # Enable autoconnect for SQLite databases, managed by Peewee
        db.autoconnect = True
        db.reuse_if_open = True
        log.info("Connected to PostgreSQL database")

        # Get the connection details
        connection = parse(db_url, unquote_user=True, unquote_password=True)
        
        if DATABASE_SCHEMA:
            # Create schema if it doesn't exist
            try:
                cursor = db.cursor()
                log.info(f"Creating schema '{DATABASE_SCHEMA}' if it doesn't exist...")
                cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {DATABASE_SCHEMA}")
                db.commit()
                cursor.close()
                log.info(f"Schema '{DATABASE_SCHEMA}' is ready")
            except Exception as e:
                log.error(f"Error creating schema '{DATABASE_SCHEMA}': {e}")
                # Continue with the connection even if schema creation fails
            
            log.info(f"Setting search path to {DATABASE_SCHEMA},public")
            # Add schema to search path options
            if "options" not in connection:
                connection["options"] = f"-c search_path={DATABASE_SCHEMA},public"
            else:
                connection["options"] += f" -c search_path={DATABASE_SCHEMA},public"
            
            # Close the temporary connection
            db.close()

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
