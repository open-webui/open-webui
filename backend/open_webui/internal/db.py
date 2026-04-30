import os
import json
import logging
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


# ── SSL URL normalization (used by sync engine & Alembic migrations) ─
#
# psycopg2 (sync) needs ``sslmode=`` in the connection string (it does
# not recognise the bare ``ssl=`` key that some ORMs emit).  The helpers
# below strip all SSL-related query params, normalise them, and
# reattach them in the canonical libpq form.
#
# The **async** engine now uses psycopg (v3), which speaks libpq
# natively, so it needs no translation at all — the DATABASE_URL is
# passed through as-is.
# ─────────────────────────────────────────────────────────────────────


def _pop_first(params: dict[str, list[str]], key: str) -> str | None:
    """Pop a single-valued query param, returning ``None`` if absent."""
    values = params.pop(key, None)
    return values[0] if values else None


def _is_postgres_url(url: str) -> bool:
    """Return True if *url* looks like a PostgreSQL connection string."""
    return bool(url) and any(url.startswith(p) for p in ('postgresql://', 'postgresql+', 'postgres://'))


def extract_ssl_params_from_url(url: str) -> tuple[str, dict[str, str]]:
    """Strip SSL query-string parameters from a PostgreSQL URL.

    Returns ``(url_without_ssl, ssl_dict)`` where *ssl_dict* maps
    canonical libpq key names (``sslmode``, ``sslrootcert``, …) to
    their values.  Non-PostgreSQL URLs are returned unchanged with an
    empty dict.
    """
    if not _is_postgres_url(url):
        return url, {}

    parsed = urlparse(url)
    qp = parse_qs(parsed.query, keep_blank_values=True)

    # Prefer sslmode (libpq canonical) over the bare ``ssl`` key.
    sslmode_val = _pop_first(qp, 'sslmode')
    ssl_val = _pop_first(qp, 'ssl')
    ssl_mode = sslmode_val or ssl_val

    ssl_dict: dict[str, str] = {}
    if ssl_mode:
        ssl_dict['sslmode'] = ssl_mode
    for key in ('sslrootcert', 'sslcert', 'sslkey', 'sslcrl'):
        val = _pop_first(qp, key)
        if val:
            ssl_dict[key] = val

    if not ssl_dict:
        return url, ssl_dict

    cleaned_query = urlencode(qp, doseq=True)
    return urlunparse(parsed._replace(query=cleaned_query)), ssl_dict


def reattach_ssl_params_to_url(url_without_ssl: str, ssl_dict: dict[str, str]) -> str:
    """Re-append SSL query-string parameters to a cleaned PostgreSQL URL.

    Used for psycopg2/libpq consumers that expect ``sslmode`` and the
    certificate-file keys in the connection string.
    """
    if not ssl_dict:
        return url_without_ssl

    parts = [f'{k}={v}' for k, v in ssl_dict.items() if v]
    if not parts:
        return url_without_ssl

    sep = '&' if '?' in url_without_ssl else '?'
    return f'{url_without_ssl}{sep}{"&".join(parts)}'


# Backwards-compatible aliases for external callers.
extract_ssl_mode_from_url = extract_ssl_params_from_url
reattach_ssl_mode_to_url = reattach_ssl_params_to_url


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
        # Normalize SSL params so psycopg2 always sees `sslmode=` (never `ssl=`)
        # and cert-file params are preserved in the connection string.
        url_without_ssl, ssl_params = extract_ssl_params_from_url(DATABASE_URL)
        normalized_url = reattach_ssl_params_to_url(url_without_ssl, ssl_params)

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


# Normalize SSL params from the URL once; the sync engine needs them
# reattached in canonical libpq form for psycopg2.
_url_without_ssl, _ssl_dict = extract_ssl_params_from_url(DATABASE_URL)

# For psycopg2 (sync engine), re-append sslmode + cert-file params.
SQLALCHEMY_DATABASE_URL = reattach_ssl_params_to_url(_url_without_ssl, _ssl_dict) if _ssl_dict else DATABASE_URL


def _make_async_url(url: str) -> str:
    """Convert a sync database URL to its async driver equivalent.

    The async engine uses psycopg (v3) which speaks libpq natively,
    so all standard connection-string parameters (``sslmode``,
    ``options``, ``target_session_attrs``, etc.) are passed through
    without any translation.
    """
    if url.startswith('sqlite+sqlcipher://'):
        raise ValueError(
            'sqlite+sqlcipher:// URLs are not supported with async engine. '
            'Use standard sqlite:// or postgresql:// instead.'
        )
    if url.startswith('sqlite:///') or url.startswith('sqlite://'):
        return url.replace('sqlite://', 'sqlite+aiosqlite://', 1)
    # psycopg v3 — auto-selects async mode with create_async_engine
    if url.startswith('postgresql+psycopg2://'):
        return url.replace('postgresql+psycopg2://', 'postgresql+psycopg://', 1)
    if url.startswith('postgresql://'):
        return url.replace('postgresql://', 'postgresql+psycopg://', 1)
    if url.startswith('postgres://'):
        return url.replace('postgres://', 'postgresql+psycopg://', 1)
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

# psycopg (v3) speaks libpq natively — the full DATABASE_URL is passed
# through as-is.  SSL params, ``options``, ``target_session_attrs``, etc.
# all work without any stripping or translation.
ASYNC_SQLALCHEMY_DATABASE_URL = _make_async_url(SQLALCHEMY_DATABASE_URL)

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
    if isinstance(DATABASE_POOL_SIZE, int):
        if DATABASE_POOL_SIZE > 0:
            async_engine = create_async_engine(
                ASYNC_SQLALCHEMY_DATABASE_URL,
                pool_size=DATABASE_POOL_SIZE,
                max_overflow=DATABASE_POOL_MAX_OVERFLOW,
                pool_timeout=DATABASE_POOL_TIMEOUT,
                pool_recycle=DATABASE_POOL_RECYCLE,
                pool_pre_ping=True,
            )
        else:
            async_engine = create_async_engine(
                ASYNC_SQLALCHEMY_DATABASE_URL,
                pool_pre_ping=True,
                poolclass=NullPool,
            )
    else:
        async_engine = create_async_engine(
            ASYNC_SQLALCHEMY_DATABASE_URL,
            pool_pre_ping=True,
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
