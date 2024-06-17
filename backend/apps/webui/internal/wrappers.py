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
        db = PooledPostgresqlExtDatabase(
            db.database,
            max_connections=8,
            stale_timeout=300,
            timeout=None,
            autoconnect=True,
            **db.connect_params
        )
    elif isinstance(db, SqliteDatabase):
        db = PooledSqliteDatabase(
            db.database,
            max_connections=8,
            stale_timeout=300,
            timeout=None,
            autoconnect=True,
            **db.connect_params
        )
    else:
        raise ValueError('Unsupported database connection')
    return db