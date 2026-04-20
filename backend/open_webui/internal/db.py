import os
import json
import logging
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Optional
from pathlib import Path
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, quote_plus, urlsplit
import ssl

import boto3
from open_webui.internal.wrappers import register_connection
from open_webui.env import (
    OPEN_WEBUI_DIR,
    DB_VARS,
    DATABASE_CA_PATH,
    DATABASE_ENABLE_IAM_TOKEN_AUTH,
    DATABASE_URL,
    DATABASE_USER,
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
from pydantic import BaseModel, SecretStr
from sqlalchemy import Dialect, create_engine, MetaData, event, types
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.sql.type_api import _T
from typing_extensions import Self

log = logging.getLogger(__name__)


def _create_engine(url: str | URL, connect_args: dict | None = None) -> Engine:
    if isinstance(DATABASE_POOL_SIZE, int):
        if DATABASE_POOL_SIZE > 0:
            engine = create_engine(
                url,
                pool_size=DATABASE_POOL_SIZE,
                max_overflow=DATABASE_POOL_MAX_OVERFLOW,
                pool_timeout=DATABASE_POOL_TIMEOUT,
                pool_recycle=DATABASE_POOL_RECYCLE,
                pool_pre_ping=True,
                poolclass=QueuePool,
                connect_args=connect_args,
            )
        else:
            engine = create_engine(
                url,
                pool_pre_ping=True,
                poolclass=NullPool,
                connect_args=connect_args,
            )
    else:
        engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
    return engine


def _create_async_engine(url: str | URL, connect_args: dict | None = None) -> AsyncEngine:
    if isinstance(DATABASE_POOL_SIZE, int):
        if DATABASE_POOL_SIZE > 0:
            engine = create_async_engine(
                url,
                pool_size=DATABASE_POOL_SIZE,
                max_overflow=DATABASE_POOL_MAX_OVERFLOW,
                pool_timeout=DATABASE_POOL_TIMEOUT,
                pool_recycle=DATABASE_POOL_RECYCLE,
                pool_pre_ping=True,
                poolclass=QueuePool,
                connect_args=connect_args,
            )
        else:
            engine = create_async_engine(
                url,
                pool_pre_ping=True,
                poolclass=NullPool,
                connect_args=connect_args,
            )
    else:
        engine = create_async_engine(url, pool_pre_ping=True, connect_args=connect_args)
    return engine


class IAMToken(BaseModel):
    token: SecretStr
    expiration: datetime


class RDSIAMConfig:
    def __init__(
        self, db_type: str, db_name: str, db_host: str, db_port: int, db_user: str, ca_path: str | None = None
    ) -> None:

        self.db_type = db_type
        self.db_name = db_name
        self.db_host = db_host
        self.db_port = db_port
        self.db_user = db_user
        self.ca_path = ca_path

        # RDS host format: {db}.{account}.{region}.rds.amazonaws.com
        aws_region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        host_parts = db_host.split(".")
        if len(host_parts) >= 4 and host_parts[-3] == "rds" and host_parts[-2] == "amazonaws":
            if (host_region := host_parts[-4]) != aws_region:
                raise ValueError(
                    f"AWS_DEFAULT_REGION '{aws_region}' does not match the region inferred from "
                    f"DATABASE_HOST '{db_host}' ('{host_region}'). "
                    f"Set AWS_DEFAULT_REGION={host_region} to match your RDS instance."
                )
        self.client = boto3.client("rds", region_name=aws_region)
        self.token = self.get_token()

        self.sync_connect_args = self._get_sync_connect_args()
        self.async_connect_args = self._get_async_connect_args()

    def get_token(self) -> IAMToken:
        """Generate and return an RDS IAM authorization token.

        RDS tokens are presigned URLs; expiration time is calculated from the token's
        query string parameters.
        """
        try:
            token = self.client.generate_db_auth_token(self.db_host, self.db_port, self.db_user)
            expiration = self.set_token_expiration(token)
            log.info(f"AWS RDS token for {self.db_host} expires {expiration} UTC.")
            return IAMToken(token=SecretStr(token), expiration=expiration)
        except Exception as e:
            log.error(f"AWS RDS token error: {e.__class__.__qualname__} {e}")
            raise

    def set_token_expiration(self, token: str) -> datetime:
        """
        Calculate authorization token expiration time from a presigned RDS URL.

        RDS tokens are presigned URLs. The query string contains the time at which the
        token was generated, and the number of seconds until it expires. This function
        converts these values and returns the token expiration as a UTC-aware datetime.
        """
        split_token = urlsplit(token)
        parsed_qs: dict = parse_qs(split_token.query)
        generation_time = datetime.strptime(parsed_qs["X-Amz-Date"][0], "%Y%m%dT%H%M%SZ")
        duration = timedelta(seconds=int(parsed_qs["X-Amz-Expires"][0]))
        expiration = generation_time + duration
        return expiration.replace(tzinfo=timezone.utc)

    def create_engine(self, is_async: bool = False) -> Engine | AsyncEngine:
        return self._create_async_engine() if is_async else self._create_sync_engine()

    def _get_sync_connect_args(self) -> dict:
        connect_args = {"sslmode": "require"}
        if self.ca_path is None:
            log.info("No CA provided; using sslmode=require without certificate verification.")
        else:
            _ca_path = Path(self.ca_path).resolve()
            if _ca_path.exists() and _ca_path.is_file():
                connect_args["sslmode"] = "verify-full"
                connect_args["sslrootcert"] = str(self.ca_path)
            else:
                log.warning(
                    f"CA file not found at {self.ca_path}; using sslmode=require without certificate verification."
                )
        return connect_args

    def _create_sync_engine(self) -> Engine:
        url = URL.create(
            drivername=self.db_type,
            username=self.db_user,
            password=None,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )
        return _create_engine(url=url, connect_args=self.sync_connect_args)

    def _get_async_connect_args(self) -> dict:
        connect_args = {"ssl": True}
        if self.ca_path is None:
            log.info("No CA provided; using ssl=True without certificate verification.")
        else:
            _ca_path = Path(self.ca_path).resolve()
            if _ca_path.exists() and _ca_path.is_file():
                connect_args["ssl"] = ssl.create_default_context(cafile=self.ca_path, purpose=ssl.Purpose.SERVER_AUTH)
            else:
                log.warning(f"CA file not found at {self.ca_path}; using ssl=True without certificate verification.")
        return connect_args

    def _create_async_engine(self) -> AsyncEngine:
        # if dialect can't be inferred here, use default sync url to create async engine
        # and let sqlalchemy handle it
        if self.db_type in ["postgres", "postgresql", "postgresql+psycopg2"]:
            url = URL.create(
                drivername="postgresql+asyncpg",
                username=self.db_user,
                password=None,
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
            )
        else:
            url = URL.create(
                drivername=self.db_type,
                username=self.db_user,
                password=None,
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
            )
        return _create_async_engine(url=url, connect_args=self.async_connect_args)

    def check_token(self, dialect, connection_record, connection_args, connection_kwargs) -> None:
        now = datetime.now(tz=timezone.utc)
        if not self.token or now >= self.token.expiration - timedelta(seconds=60):
            self.token = self.get_token()
        connection_kwargs["password"] = self.token.token.get_secret_value()


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
def handle_peewee_migration(db_url: str = DATABASE_URL, connect_args: dict | None = None):
    db = None
    try:
        # Replace the postgresql:// with postgres:// to handle the peewee migration
        db = register_connection(db_url.replace('postgresql://', 'postgres://'), connect_args=connect_args)
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


if DATABASE_ENABLE_IAM_TOKEN_AUTH:
    rds_iam_config = RDSIAMConfig(
        db_type=DB_VARS["db_type"],
        db_name=DB_VARS["db_name"],
        db_host=DB_VARS["db_host"],
        db_port=DB_VARS["db_port"],
        db_user=DATABASE_USER,
        ca_path=DATABASE_CA_PATH,
    )

if ENABLE_DB_MIGRATIONS:
    if DATABASE_ENABLE_IAM_TOKEN_AUTH:
        _token_val = rds_iam_config.token.token.get_secret_value()
        _migration_url = (
            f'{DB_VARS["db_type"]}://{DATABASE_USER}:{quote_plus(_token_val)}'
            f'@{DB_VARS["db_host"]}:{DB_VARS["db_port"]}/{DB_VARS["db_name"]}'
        )
        handle_peewee_migration(_migration_url, connect_args=rds_iam_config.sync_connect_args)
    else:
        handle_peewee_migration(DATABASE_URL)


SQLALCHEMY_DATABASE_URL = DATABASE_URL


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
elif DATABASE_ENABLE_IAM_TOKEN_AUTH:
    engine = rds_iam_config.create_engine()
    event.listen(engine, 'do_connect', rds_iam_config.check_token)
else:
    engine = _create_engine(url=SQLALCHEMY_DATABASE_URL)


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

ASYNC_SQLALCHEMY_DATABASE_URL = _make_async_url(SQLALCHEMY_DATABASE_URL)

if 'sqlite' in ASYNC_SQLALCHEMY_DATABASE_URL:
    # Generous default — async coroutines + no session sharing = high connection demand.
    _sqlite_pool_size = (
        DATABASE_POOL_SIZE
        if isinstance(DATABASE_POOL_SIZE, int) and DATABASE_POOL_SIZE > 0
        else 512
    )
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
elif DATABASE_ENABLE_IAM_TOKEN_AUTH:
    async_engine = rds_iam_config.create_engine(is_async=True)
    event.listen(async_engine.sync_engine, 'do_connect', rds_iam_config.check_token)
else:
    async_engine = _create_async_engine(url=ASYNC_SQLALCHEMY_DATABASE_URL)


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
