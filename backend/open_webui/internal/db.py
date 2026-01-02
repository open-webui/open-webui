import os
import json
import logging
from contextlib import contextmanager
from typing import Any, Optional

from open_webui.internal.wrappers import register_connection
from open_webui.env import (
    OPEN_WEBUI_DIR,
    DATABASE_URL,
    DATABASE_SCHEMA,
    SRC_LOG_LEVELS,
    DATABASE_POOL_MAX_OVERFLOW,
    DATABASE_POOL_RECYCLE,
    DATABASE_POOL_SIZE,
    DATABASE_POOL_TIMEOUT,
    DATABASE_ENABLE_SQLITE_WAL,
)
from sqlalchemy import Dialect, create_engine, MetaData, event, types
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.sql.type_api import _T
from typing_extensions import Self

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["DB"])


class JSONField(types.TypeDecorator):
    impl = types.Text
    cache_ok = True

    def process_bind_param(self, value: Optional[_T], dialect: Dialect) -> Any:
        return json.dumps(value)

    def process_result_value(self, value: Optional[_T], dialect: Dialect) -> Any:
        if value is not None:
            # If value is already a dict/list (deserialized), return it as-is
            if isinstance(value, (dict, list)):
                return value
            return json.loads(value)

    def copy(self, **kw: Any) -> Self:
        return JSONField(self.impl.length)

    def db_value(self, value):
        return json.dumps(value)

    def python_value(self, value):
        if value is not None:
            # If value is already a dict/list (deserialized), return it as-is
            if isinstance(value, (dict, list)):
                return value
            return json.loads(value)


def is_alembic_detected(database_url: str) -> bool:
    """
    Check if Alembic migrations have been applied by detecting the alembic_version table.
    
    Returns True if Alembic is detected, False otherwise.
    If detection fails, returns False (safe fallback to run Peewee migrations).
    """
    try:
        import peewee as pw
        
        # Replace postgresql:// with postgres:// for Peewee compatibility
        peewee_url = database_url.replace("postgresql://", "postgres://")
        db = register_connection(peewee_url)
        
        try:
            if isinstance(db, pw.SqliteDatabase):
                # For SQLite, check sqlite_master for alembic_version table
                cursor = db.execute_sql(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"
                )
                result = cursor.fetchone()
                alembic_detected = result is not None
            else:
                # For PostgreSQL and other databases, query information_schema
                cursor = db.execute_sql(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_name = 'alembic_version'"
                )
                result = cursor.fetchone()
                alembic_detected = result is not None
            
            return alembic_detected
        finally:
            if not db.is_closed():
                db.close()
    except Exception as e:
        # If detection fails, assume Alembic is not present (safe fallback)
        log.debug(f"Could not detect Alembic version table: {e}")
        return False


# Peewee migrations are no longer used - we use Alembic exclusively
# This function is kept for backward compatibility but does nothing
def handle_peewee_migration(DATABASE_URL):
    # Alembic is the only migration system now
    log.debug("Skipping Peewee migrations - using Alembic exclusively")
    return


SQLALCHEMY_DATABASE_URL = DATABASE_URL

# Handle SQLCipher URLs
if SQLALCHEMY_DATABASE_URL.startswith("sqlite+sqlcipher://"):
    database_password = os.environ.get("DATABASE_PASSWORD")
    if not database_password or database_password.strip() == "":
        raise ValueError(
            "DATABASE_PASSWORD is required when using sqlite+sqlcipher:// URLs"
        )

    # Extract database path from SQLCipher URL
    db_path = SQLALCHEMY_DATABASE_URL.replace("sqlite+sqlcipher://", "")
    if db_path.startswith("/"):
        db_path = db_path[1:]  # Remove leading slash for relative paths

    # Create a custom creator function that uses sqlcipher3
    def create_sqlcipher_connection():
        import sqlcipher3

        conn = sqlcipher3.connect(db_path, check_same_thread=False)
        conn.execute(f"PRAGMA key = '{database_password}'")
        return conn

    engine = create_engine(
        "sqlite://",  # Dummy URL since we're using creator
        creator=create_sqlcipher_connection,
        echo=False,
    )

    log.info("Connected to encrypted SQLite database using SQLCipher")

elif "sqlite" in SQLALCHEMY_DATABASE_URL:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )

    def on_connect(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        if DATABASE_ENABLE_SQLITE_WAL:
            cursor.execute("PRAGMA journal_mode=WAL")
        else:
            cursor.execute("PRAGMA journal_mode=DELETE")
        cursor.close()

    event.listen(engine, "connect", on_connect)
else:
    if isinstance(DATABASE_POOL_SIZE, int):
        if DATABASE_POOL_SIZE > 0:
            engine = create_engine(
                SQLALCHEMY_DATABASE_URL,
                pool_size=DATABASE_POOL_SIZE,
                max_overflow=DATABASE_POOL_MAX_OVERFLOW,
                pool_timeout=DATABASE_POOL_TIMEOUT,
                pool_recycle=DATABASE_POOL_RECYCLE,
                pool_pre_ping=True,
                poolclass=QueuePool,
            )
        else:
            engine = create_engine(
                SQLALCHEMY_DATABASE_URL, pool_pre_ping=True, poolclass=NullPool
            )
    else:
        engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)


SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
)
metadata_obj = MetaData(schema=DATABASE_SCHEMA)
Base = declarative_base(metadata=metadata_obj)
Session = scoped_session(SessionLocal)


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


get_db = contextmanager(get_session)
