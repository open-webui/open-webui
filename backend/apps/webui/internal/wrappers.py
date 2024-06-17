from contextvars import ContextVar
from peewee import *
import logging
from playhouse.db_url import connect

from config import SRC_LOG_LEVELS

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

def register_connection(db_url):
    db = connect(db_url)
    if isinstance(db, PostgresqlDatabase):
        # Enable autoconnect for SQLite databases, managed by Peewee
        db.autoconnect = True
        log.info("Connected to PostgreSQL database")
    elif isinstance(db, SqliteDatabase):
        # Enable autoconnect for SQLite databases, managed by Peewee
        db.autoconnect = True
        log.info("Connected to SQLite database")
    else:
        raise ValueError('Unsupported database connection')
    return db