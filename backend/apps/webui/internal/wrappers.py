from contextvars import ContextVar
from peewee import *
from playhouse.db_url import connect
from playhouse.pool import PooledPostgresqlDatabase
from playhouse.shortcuts import ReconnectMixin

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

class ReconnectingPostgresqlDatabase(ReconnectMixin, PostgresqlDatabase):
    pass

class ReconnectingPooledPostgresqlDatabase(ReconnectMixin, PooledPostgresqlDatabase):
    pass

class ReconnectingSqliteDatabase(ReconnectMixin, SqliteDatabase):
    pass


def register_connection(db_url):
    # Connect using the playhouse.db_url module, which supports multiple 
    # database types, then wrap the connection in a ReconnectMixin to handle dropped connections
    db = connect(db_url)
    if isinstance(db, PostgresqlDatabase):
        db = ReconnectingPostgresqlDatabase(db.database, **db.connect_params)
    elif isinstance(db, PooledPostgresqlDatabase):
        db = ReconnectingPooledPostgresqlDatabase(db.database, **db.connect_params)
    elif isinstance(db, SqliteDatabase):
        db = ReconnectingSqliteDatabase(db.database, **db.connect_params)
    else:
        raise ValueError('Unsupported database connection')
    return db
