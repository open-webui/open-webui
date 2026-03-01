import os
import json
import logging
import time
from contextlib import contextmanager
from typing import Any, Optional

from open_webui.internal.wrappers import register_connection
from open_webui.env import (
    OPEN_WEBUI_DIR,
    DATABASE_URL,
    DATABASE_SCHEMA,
    DATABASE_POOL_MAX_OVERFLOW,
    DATABASE_POOL_RECYCLE,
    DATABASE_POOL_SIZE,
    DATABASE_POOL_TIMEOUT,
    DATABASE_ENABLE_SQLITE_WAL,
    DATABASE_ENABLE_SESSION_SHARING,
    ENABLE_DB_MIGRATIONS,
    REDIS_URL,
    REDIS_KEY_PREFIX,
    REDIS_SENTINEL_HOSTS,
    REDIS_SENTINEL_PORT,
    REDIS_CLUSTER,
    MIGRATION_LOCK_TIMEOUT_SECS,
    MIGRATION_LOCK_RETRY_SLEEP_SECS,
    MIGRATION_LOCK_MAX_WAIT_SECS,
)
from peewee_migrate import Router
from sqlalchemy import Dialect, create_engine, MetaData, event, types
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker, Session
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.sql.type_api import _T
from typing_extensions import Self

log = logging.getLogger(__name__)


class JSONField(types.TypeDecorator):
    impl = types.Text
    cache_ok = True

    def process_bind_param(self, value: Optional[_T], dialect: Dialect) -> Any:
        return json.dumps(value)

    def process_result_value(self, value: Optional[_T], dialect: Dialect) -> Any:
        if value is not None:
            return json.loads(value)

    def copy(self, **kw: Any) -> Self:
        return JSONField(self.impl.length)

    def db_value(self, value):
        return json.dumps(value)

    def python_value(self, value):
        if value is not None:
            return json.loads(value)


# Redis key used for coordinating DB migrations
_MIGRATION_LOCK_KEY = f"{REDIS_KEY_PREFIX}:db_migration_lock"

_migration_lock_holder = None


def _get_redis_client_for_migration_lock():
    """Return a Redis client configured for migration lock coordination."""
    from open_webui.utils.redis import get_redis_connection, get_sentinels_from_env

    redis_sentinels = get_sentinels_from_env(REDIS_SENTINEL_HOSTS, REDIS_SENTINEL_PORT)
    return get_redis_connection(
        REDIS_URL,
        redis_sentinels,
        redis_cluster=REDIS_CLUSTER,
        async_mode=False,
        decode_responses=True,
    )


def _redis_available_for_migration_lock():
    """Return True only if REDIS_URL is set and we can connect (ping) to Redis. Used to decide whether to use the migration lock."""
    if not REDIS_URL:
        return False
    try:
        client = _get_redis_client_for_migration_lock()
        client.ping()
        return True
    except Exception as e:
        log.warning("Redis not reachable for migration lock (REDIS_URL is set): %s", e)
        return False


def _try_acquire_migration_lock():
    """Acquire Redis migration lock with retries. Returns lock holder or None if no Redis."""
    global _migration_lock_holder

    # If Redis is not configured or reachable, fall back to previous behavior:
    # every pod runs migrations without distributed coordination.
    if not _redis_available_for_migration_lock():
        return None

    try:
        from open_webui.socket.utils import RedisLock
        from open_webui.utils.redis import get_sentinels_from_env

        redis_sentinels = get_sentinels_from_env(
            REDIS_SENTINEL_HOSTS, REDIS_SENTINEL_PORT
        )

        lock = RedisLock(
            redis_url=REDIS_URL,
            lock_name=_MIGRATION_LOCK_KEY,
            timeout_secs=MIGRATION_LOCK_TIMEOUT_SECS,
            redis_sentinels=redis_sentinels,
            redis_cluster=REDIS_CLUSTER,
        )

        deadline = time.monotonic() + MIGRATION_LOCK_MAX_WAIT_SECS
        while time.monotonic() < deadline:
            if lock.aquire_lock():
                _migration_lock_holder = lock
                log.info("Acquired DB migration lock; this pod will run migrations.")
                return lock

            log.debug(
                "Another pod is running DB migrations; waiting %ss before retry...",
                MIGRATION_LOCK_RETRY_SLEEP_SECS,
            )
            time.sleep(MIGRATION_LOCK_RETRY_SLEEP_SECS)

        log.error(
            "Could not acquire DB migration lock within %s seconds. Failing startup to avoid race.",
            MIGRATION_LOCK_MAX_WAIT_SECS,
        )
        raise RuntimeError(
            "DB migration lock not acquired in time. Another pod may be migrating; retry later."
        )
    except Exception as e:
        # Fall back to running migrations without distributed coordination.
        log.warning(
            "Redis migration lock unavailable (%s); running migrations without lock.", e
        )
        return None


def release_migration_lock_if_held() -> None:
    """Release the Redis migration lock if this process currently holds it."""
    global _migration_lock_holder
    if _migration_lock_holder is None:
        return

    try:
        _migration_lock_holder.release_lock()
        log.info("Released DB migration lock.")
    except Exception as e:
        log.warning("Failed to release DB migration lock: %s", e)
    finally:
        _migration_lock_holder = None


# Workaround to handle the peewee migration
# This is required to ensure the peewee migration is handled before the alembic migration
def handle_peewee_migration(DATABASE_URL):
    # db = None
    try:
        # Replace the postgresql:// with postgres:// to handle the peewee migration
        db = register_connection(DATABASE_URL.replace("postgresql://", "postgres://"))
        migrate_dir = OPEN_WEBUI_DIR / "internal" / "migrations"
        router = Router(db, logger=log, migrate_dir=migrate_dir)
        router.run()
        db.close()

    except Exception as e:
        log.error(f"Failed to initialize the database connection: {e}")
        log.warning(
            "Hint: If your database password contains special characters, you may need to URL-encode it."
        )
        raise
    finally:
        # Properly closing the database connection
        if db and not db.is_closed():
            db.close()

        # Assert if db connection has been closed
        assert db.is_closed(), "Database connection is still open."


if ENABLE_DB_MIGRATIONS:
    _try_acquire_migration_lock()
    handle_peewee_migration(DATABASE_URL)


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
ScopedSession = scoped_session(SessionLocal)


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


get_db = contextmanager(get_session)


@contextmanager
def get_db_context(db: Optional[Session] = None):
    if isinstance(db, Session) and DATABASE_ENABLE_SESSION_SHARING:
        yield db
    else:
        with get_db() as session:
            yield session
