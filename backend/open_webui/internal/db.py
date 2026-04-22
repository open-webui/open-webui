import os
import json
import logging
import ssl as _stdlib_ssl
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

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
    DATABASE_SQLITE_PRAGMA_SYNCHRONOUS,
    DATABASE_SQLITE_PRAGMA_BUSY_TIMEOUT,
    DATABASE_SQLITE_PRAGMA_CACHE_SIZE,
    DATABASE_SQLITE_PRAGMA_TEMP_STORE,
    DATABASE_SQLITE_PRAGMA_MMAP_SIZE,
    DATABASE_SQLITE_PRAGMA_JOURNAL_SIZE_LIMIT,
    ENABLE_DB_MIGRATIONS,
)
from peewee_migrate import Router
from sqlalchemy import Dialect, create_engine, MetaData, event, types
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker, Session
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.sql.type_api import _T
from typing_extensions import Self

log = logging.getLogger(__name__)


def extract_ssl_mode_from_url(url: str) -> tuple[str, str | None]:
    """Strip SSL query-string parameters from a PostgreSQL URL.

    asyncpg and psycopg2 use different query-string keys for SSL
    (``ssl`` vs ``sslmode``).  This helper removes **both** from the
    URL so that each driver can receive the correct parameter through
    its own mechanism (query-string re-injection for psycopg2,
    ``connect_args`` for asyncpg).

    Returns
    -------
    (url_without_ssl, ssl_mode)
        *url_without_ssl* is the original URL with ``ssl`` / ``sslmode``
        query parameters removed.  *ssl_mode* is the extracted mode
        string (e.g. ``'require'``), or ``None`` if neither parameter
        was present.

    Non-PostgreSQL URLs are returned unchanged with ``ssl_mode=None``.
    """
    if not url or not any(url.startswith(prefix) for prefix in ('postgresql://', 'postgresql+', 'postgres://')):
        return url, None

    parsed = urlparse(url)
    query_params = parse_qs(parsed.query, keep_blank_values=True)

    # Prefer sslmode (libpq canonical) over the asyncpg-only ssl key.
    ssl_mode: str | None = None
    for key in ('sslmode', 'ssl'):
        values = query_params.pop(key, None)
        if values and ssl_mode is None:
            ssl_mode = values[0]

    if ssl_mode is None:
        # Nothing to strip — return the URL untouched.
        return url, None

    # Rebuild the query string without the SSL keys.
    remaining_query = urlencode(query_params, doseq=True)
    url_without_ssl = urlunparse(parsed._replace(query=remaining_query))
    return url_without_ssl, ssl_mode


def build_asyncpg_ssl_args(ssl_mode: str | None) -> dict:
    """Convert a libpq-style SSL mode value to asyncpg ``connect_args``.

    Returns a dict suitable for unpacking into
    ``create_async_engine(..., connect_args=...)``.
    """
    if ssl_mode is None:
        return {}

    mode = ssl_mode.lower()
    if mode == 'disable':
        return {'connect_args': {'ssl': False}}
    if mode in ('allow', 'prefer'):
        # asyncpg has no direct equivalent — omit to let it try without.
        return {}
    if mode == 'require':
        # SSL required but no certificate verification (matches libpq).
        ctx = _stdlib_ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = _stdlib_ssl.CERT_NONE
        return {'connect_args': {'ssl': ctx}}
    if mode in ('verify-ca', 'verify-full'):
        # Full verification — use the system trust store.
        ctx = _stdlib_ssl.create_default_context()
        if mode == 'verify-ca':
            ctx.check_hostname = False
        return {'connect_args': {'ssl': ctx}}

    # Unknown value — pass through as-is and let asyncpg decide.
    return {'connect_args': {'ssl': ssl_mode}}


def reattach_ssl_mode_to_url(url_without_ssl: str, ssl_mode: str | None) -> str:
    """Re-append ``sslmode=<value>`` to a cleaned PostgreSQL URL.

    Used for psycopg2 / libpq consumers that expect the canonical
    ``sslmode`` query-string key.
    """
    if ssl_mode is None:
        return url_without_ssl
    separator = '&' if '?' in url_without_ssl else '?'
    return f'{url_without_ssl}{separator}sslmode={ssl_mode}'


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


# Workaround to handle the peewee migration
# This is required to ensure the peewee migration is handled before the alembic migration
def handle_peewee_migration(DATABASE_URL):
    db = None
    try:
        # Normalize SSL params so psycopg2 always sees `sslmode=` (never `ssl=`).
        url_without_ssl, ssl_mode = extract_ssl_mode_from_url(DATABASE_URL)
        normalized_url = reattach_ssl_mode_to_url(url_without_ssl, ssl_mode)

        # Replace the postgresql:// with postgres:// to handle the peewee migration
        db = register_connection(normalized_url.replace('postgresql://', 'postgres://'))
        migrate_dir = OPEN_WEBUI_DIR / 'internal' / 'migrations'
        router = Router(db, logger=log, migrate_dir=migrate_dir)
        router.run()
        db.close()

    except Exception as e:
        log.error(f'Failed to initialize the database connection: {e}')
        log.warning('Hint: If your database password contains special characters, you may need to URL-encode it.')
        raise
    finally:
        # Properly closing the database connection
        if db and not db.is_closed():
            db.close()

        # Assert if db connection has been closed
        if db is not None:
            assert db.is_closed(), 'Database connection is still open.'


if ENABLE_DB_MIGRATIONS:
    handle_peewee_migration(DATABASE_URL)


# Normalize SSL params from the URL once; each engine branch re-injects
# the driver-appropriate form.
DATABASE_URL_WITHOUT_SSL, DATABASE_SSL_MODE = extract_ssl_mode_from_url(DATABASE_URL)

# For psycopg2 (sync engine), re-append sslmode=<value>.
SQLALCHEMY_DATABASE_URL = (
    reattach_ssl_mode_to_url(DATABASE_URL_WITHOUT_SSL, DATABASE_SSL_MODE) if DATABASE_SSL_MODE else DATABASE_URL
)


def _make_async_url(url: str) -> str:
    """Convert a sync database URL to its async driver equivalent."""
    if url.startswith('sqlite+sqlcipher://'):
        # SQLCipher has no async driver — not supported for async
        raise ValueError(
            'sqlite+sqlcipher:// URLs are not supported with async engine. '
            'Use standard sqlite:// or postgresql:// instead.'
        )
    if url.startswith('sqlite:///') or url.startswith('sqlite://'):
        return url.replace('sqlite://', 'sqlite+aiosqlite://', 1)
    if url.startswith('postgresql+psycopg2://'):
        return url.replace('postgresql+psycopg2://', 'postgresql+asyncpg://', 1)
    if url.startswith('postgresql://'):
        return url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    if url.startswith('postgres://'):
        return url.replace('postgres://', 'postgresql+asyncpg://', 1)
    # For other dialects, return as-is and let SQLAlchemy handle it
    return url


# ============================================================
# SYNC ENGINE (used only for: startup migrations, config loading,
#              Alembic, peewee migration, health checks)
# ============================================================

# Handle SQLCipher URLs
if SQLALCHEMY_DATABASE_URL.startswith('sqlite+sqlcipher://'):
    database_password = os.environ.get('DATABASE_PASSWORD')
    if not database_password or database_password.strip() == '':
        raise ValueError('DATABASE_PASSWORD is required when using sqlite+sqlcipher:// URLs')

    # Extract database path from SQLCipher URL
    db_path = SQLALCHEMY_DATABASE_URL.replace('sqlite+sqlcipher://', '')

    # Create a custom creator function that uses sqlcipher3
    def create_sqlcipher_connection():
        import sqlcipher3

        conn = sqlcipher3.connect(db_path, check_same_thread=False)
        conn.execute(f"PRAGMA key = '{database_password}'")
        return conn

    # The dummy "sqlite://" URL would cause SQLAlchemy to auto-select
    # SingletonThreadPool, which non-deterministically closes in-use
    # connections when thread count exceeds pool_size, leading to segfaults
    # in the native sqlcipher3 C library. Use NullPool by default for safety,
    # or QueuePool if DATABASE_POOL_SIZE is explicitly configured.
    if isinstance(DATABASE_POOL_SIZE, int) and DATABASE_POOL_SIZE > 0:
        engine = create_engine(
            'sqlite://',
            creator=create_sqlcipher_connection,
            pool_size=DATABASE_POOL_SIZE,
            max_overflow=DATABASE_POOL_MAX_OVERFLOW,
            pool_timeout=DATABASE_POOL_TIMEOUT,
            pool_recycle=DATABASE_POOL_RECYCLE,
            pool_pre_ping=True,
            poolclass=QueuePool,
            echo=False,
        )
    else:
        engine = create_engine(
            'sqlite://',
            creator=create_sqlcipher_connection,
            poolclass=NullPool,
            echo=False,
        )

    log.info('Connected to encrypted SQLite database using SQLCipher')

elif 'sqlite' in SQLALCHEMY_DATABASE_URL:
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={'check_same_thread': False})

    def _apply_sqlite_pragmas(dbapi_connection):
        """Apply all configured SQLite PRAGMAs to a raw DBAPI connection."""
        cursor = dbapi_connection.cursor()
        if DATABASE_ENABLE_SQLITE_WAL:
            cursor.execute('PRAGMA journal_mode=WAL')
        else:
            cursor.execute('PRAGMA journal_mode=DELETE')

        # Each PRAGMA is skipped when its env var is empty, allowing opt-out.
        if DATABASE_SQLITE_PRAGMA_SYNCHRONOUS:
            cursor.execute(f'PRAGMA synchronous={DATABASE_SQLITE_PRAGMA_SYNCHRONOUS}')
        if DATABASE_SQLITE_PRAGMA_BUSY_TIMEOUT:
            cursor.execute(f'PRAGMA busy_timeout={DATABASE_SQLITE_PRAGMA_BUSY_TIMEOUT}')
        if DATABASE_SQLITE_PRAGMA_CACHE_SIZE:
            cursor.execute(f'PRAGMA cache_size={DATABASE_SQLITE_PRAGMA_CACHE_SIZE}')
        if DATABASE_SQLITE_PRAGMA_TEMP_STORE:
            cursor.execute(f'PRAGMA temp_store={DATABASE_SQLITE_PRAGMA_TEMP_STORE}')
        if DATABASE_SQLITE_PRAGMA_MMAP_SIZE:
            cursor.execute(f'PRAGMA mmap_size={DATABASE_SQLITE_PRAGMA_MMAP_SIZE}')
        if DATABASE_SQLITE_PRAGMA_JOURNAL_SIZE_LIMIT:
            cursor.execute(f'PRAGMA journal_size_limit={DATABASE_SQLITE_PRAGMA_JOURNAL_SIZE_LIMIT}')
        cursor.close()

    def on_connect(dbapi_connection, connection_record):
        _apply_sqlite_pragmas(dbapi_connection)

    event.listen(engine, 'connect', on_connect)
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
            engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True, poolclass=NullPool)
    else:
        engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)


# Sync session — used ONLY for startup config loading (config.py runs at import time)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
metadata_obj = MetaData(schema=DATABASE_SCHEMA)
Base = declarative_base(metadata=metadata_obj)
ScopedSession = scoped_session(SessionLocal)


def get_session():
    """Sync session generator — used ONLY for startup/config operations."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


get_db = contextmanager(get_session)


# ============================================================
# ASYNC ENGINE (used for ALL runtime database operations)
# ============================================================

# Use the SSL-stripped URL for asyncpg — SSL is injected via connect_args.
ASYNC_SQLALCHEMY_DATABASE_URL = _make_async_url(
    DATABASE_URL_WITHOUT_SSL if DATABASE_SSL_MODE else SQLALCHEMY_DATABASE_URL
)

if 'sqlite' in ASYNC_SQLALCHEMY_DATABASE_URL:
    # Generous default — async coroutines + no session sharing = high connection demand.
    _sqlite_pool_size = DATABASE_POOL_SIZE if isinstance(DATABASE_POOL_SIZE, int) and DATABASE_POOL_SIZE > 0 else 512
    async_engine = create_async_engine(
        ASYNC_SQLALCHEMY_DATABASE_URL,
        connect_args={'check_same_thread': False},
        pool_size=_sqlite_pool_size,
        pool_timeout=DATABASE_POOL_TIMEOUT,
        pool_recycle=DATABASE_POOL_RECYCLE,
        pool_pre_ping=True,
    )

    @event.listens_for(async_engine.sync_engine, 'connect')
    def _set_sqlite_pragmas(dbapi_connection, connection_record):
        _apply_sqlite_pragmas(dbapi_connection)
else:
    # Inject asyncpg-compatible SSL connect_args when the user specified
    # sslmode/ssl in DATABASE_URL.
    asyncpg_ssl_args = build_asyncpg_ssl_args(DATABASE_SSL_MODE)

    if isinstance(DATABASE_POOL_SIZE, int):
        if DATABASE_POOL_SIZE > 0:
            async_engine = create_async_engine(
                ASYNC_SQLALCHEMY_DATABASE_URL,
                pool_size=DATABASE_POOL_SIZE,
                max_overflow=DATABASE_POOL_MAX_OVERFLOW,
                pool_timeout=DATABASE_POOL_TIMEOUT,
                pool_recycle=DATABASE_POOL_RECYCLE,
                pool_pre_ping=True,
                **asyncpg_ssl_args,
            )
        else:
            async_engine = create_async_engine(
                ASYNC_SQLALCHEMY_DATABASE_URL,
                pool_pre_ping=True,
                poolclass=NullPool,
                **asyncpg_ssl_args,
            )
    else:
        async_engine = create_async_engine(
            ASYNC_SQLALCHEMY_DATABASE_URL,
            pool_pre_ping=True,
            **asyncpg_ssl_args,
        )


AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_async_session():
    """Async session generator for FastAPI Depends()."""
    async with AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()


@asynccontextmanager
async def get_async_db():
    """Async context manager for use outside of FastAPI dependency injection."""
    async with AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()


@asynccontextmanager
async def get_async_db_context(db: Optional[AsyncSession] = None):
    """Async context manager that reuses an existing session if provided and session sharing is enabled."""
    if isinstance(db, AsyncSession) and DATABASE_ENABLE_SESSION_SHARING:
        yield db
    else:
        async with get_async_db() as session:
            yield session
