import logging
from contextvars import ContextVar
import time

from open_webui.env import SRC_LOG_LEVELS
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
    # Initialize connection attempts
    max_retries = 3
    current_retry = 0
    last_exception = None

    while current_retry < max_retries:
        try:
            db = connect(db_url, unquote_password=True)
            if isinstance(db, PostgresqlDatabase):
                # Get the connection details
                connection = parse(db_url, unquote_password=True)
                
                # Add connection pooling settings
                connection.update({
                    'max_connections': 20,  # Maximum number of connections
                    'stale_timeout': 300,   # 5 minutes
                    'timeout': 30           # 30 seconds connection timeout
                })

                # Use our custom database class that supports reconnection
                db = ReconnectingPostgresqlDatabase(**connection)
                
                # Test the connection
                db.connect(reuse_if_open=True)
                with db.connection():
                    db.execute_sql('SELECT 1')
                
                log.info("Successfully connected to PostgreSQL database")
                return db
                
            elif isinstance(db, SqliteDatabase):
                db.autoconnect = True
                db.reuse_if_open = True
                log.info("Connected to SQLite database")
                return db
            else:
                raise ValueError("Unsupported database connection")
                
        except Exception as e:
            last_exception = e
            current_retry += 1
            if current_retry < max_retries:
                log.warning(f"Connection attempt {current_retry} failed: {str(e)}. Retrying...")
                time.sleep(2 ** current_retry)  # Exponential backoff
            else:
                log.error(f"All connection attempts failed: {str(e)}")
                raise
