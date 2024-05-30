from contextvars import ContextVar

from peewee import PostgresqlDatabase, InterfaceError as PeeWeeInterfaceError, MySQLDatabase, _ConnectionState
from playhouse.db_url import register_database
from playhouse.pool import PooledPostgresqlDatabase, PooledMySQLDatabase
from playhouse.shortcuts import ReconnectMixin
from psycopg2 import OperationalError
from psycopg2.errors import InterfaceError


db_state_default = {"closed": None, "conn": None, "ctx": None, "transactions": None}
db_state = ContextVar("db_state", default=db_state_default.copy())


class PeeweeConnectionState(_ConnectionState):
    def __init__(self, **kwargs):
        super().__setattr__("_state", db_state)
        super().__init__(**kwargs)

    def __setattr__(self, name, value):
        self._state.get()[name] = value

    def __getattr__(self, name):
        return self._state.get()[name]


class CustomReconnectMixin(ReconnectMixin):
    reconnect_errors = (
        # default ReconnectMixin exceptions (MySQL specific)
        *ReconnectMixin.reconnect_errors,
        # psycopg2
        (OperationalError, 'termin'),
        (InterfaceError, 'closed'),
        # peewee
        (PeeWeeInterfaceError, 'closed'),
    )


class ReconnectingPostgresqlDatabase(CustomReconnectMixin, PostgresqlDatabase):
    pass


class ReconnectingPooledPostgresqlDatabase(CustomReconnectMixin, PooledPostgresqlDatabase):
    pass


class ReconnectingMySQLDatabase(CustomReconnectMixin, MySQLDatabase):
    pass


class ReconnectingPooledMySQLDatabase(CustomReconnectMixin, PooledMySQLDatabase):
    pass


def register_peewee_databases():
    register_database(MySQLDatabase, 'mysql')
    register_database(PooledMySQLDatabase, 'mysql+pool')
    register_database(ReconnectingPostgresqlDatabase, 'postgres', 'postgresql')
    register_database(ReconnectingPooledPostgresqlDatabase, 'postgres+pool', 'postgresql+pool')
