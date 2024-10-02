import logging
from contextvars import ContextVar

from open_webui.env import SRC_LOG_LEVELS
from peewee import *
from peewee import InterfaceError as PeeWeeInterfaceError
from peewee import PostgresqlDatabase, MySQLDatabase, SqliteDatabase
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
        return self._state.get()[name]


class CustomReconnectMixin(ReconnectMixin):
    reconnect_errors = (
        # psycopg2
        (OperationalError, "termin"),
        (InterfaceError, "closed"),
        # peewee
        (PeeWeeInterfaceError, "closed"),
        # MySQL
        (OperationalError, "MySQL server has gone away"),
        (InterfaceError, "Connection to MySQL server lost"),
    )


class ReconnectingPostgresqlDatabase(CustomReconnectMixin, PostgresqlDatabase):
    pass


class ReconnectingMysqlDatabase(CustomReconnectMixin, MySQLDatabase):
    pass


class ReconnectingSqliteDatabase(CustomReconnectMixin, SqliteDatabase):
    pass


def register_connection(db_url):
    parsed_url = parse(db_url, unquote_password=True)
    scheme = parsed_url['scheme']

    if scheme == 'mysql':
        db = ReconnectingMysqlDatabase(**parsed_url)
        log.info("Connected to MySQL database")
    elif scheme in ['postgresql', 'postgres']:
        db = ReconnectingPostgresqlDatabase(**parsed_url)
        log.info("Connected to PostgreSQL database")
    elif scheme == 'sqlite':
        db = ReconnectingSqliteDatabase(parsed_url['database'])
        log.info("Connected to SQLite database")
    else:
        raise ValueError(f"Unsupported database scheme: {scheme}")

    db.connection_state = PeeweeConnectionState()
    db.autoconnect = True
    db.reuse_if_open = True
    db.connect(reuse_if_open=True)

    return db

