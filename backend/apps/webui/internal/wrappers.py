from contextvars import ContextVar
from peewee import *
from playhouse.db_url import connect
from playhouse.pool import PooledPostgresqlExtDatabase
from playhouse.pool import PooledSqliteDatabase

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

def register_connection(db_url):
    db = connect(db_url)
    if isinstance(db, PostgresqlDatabase):
        # Directly use PostgresqlDatabase without pooling
        db.autoconnect = True
    elif isinstance(db, SqliteDatabase):
        # Directly use SqliteDatabase without pooling
        db.autoconnect = True
    else:
        raise ValueError('Unsupported database connection')
    return db