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
    ENABLE_AWS_RDS_IAM,
    AWS_REGION,
    PG_SSLMODE,
    PG_SSLROOTCERT,
)
from peewee_migrate import Router
from sqlalchemy import Dialect, create_engine, MetaData, types
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
        # Replace the postgresql:// with postgres:// to handle the peewee migration
        db = register_connection(DATABASE_URL.replace("postgresql://", "postgres://"))
        migrate_dir = OPEN_WEBUI_DIR / "internal" / "migrations"
        router = Router(db, logger=log, migrate_dir=migrate_dir)
        router.run()
        db.close()

    except Exception as e:
        log.error(f"Failed to initialize the database connection: {e}")
        raise
    finally:
        # Properly closing the database connection
        if db and not db.is_closed():
            db.close()

        # Assert if db connection has been closed
        if db:
            assert db.is_closed(), "Database connection is still open."


handle_peewee_migration(DATABASE_URL)


# Build SQLAlchemy connect args for SSL and IAM token if enabled
sqlalchemy_connect_args = {}

# Force SSL parameters if provided to avoid libpq trying default ~/.postgresql
if PG_SSLMODE:
    sqlalchemy_connect_args.setdefault("connect_args", {})
    sqlalchemy_connect_args["connect_args"]["sslmode"] = PG_SSLMODE
if PG_SSLROOTCERT:
    sqlalchemy_connect_args.setdefault("connect_args", {})
    sqlalchemy_connect_args["connect_args"]["sslrootcert"] = PG_SSLROOTCERT

# IAM auth: generate token as password when enabled
sqlalchemy_url = DATABASE_URL
if ENABLE_AWS_RDS_IAM and sqlalchemy_url.startswith("postgresql://"):
    try:
        import boto3
        from urllib.parse import urlparse, quote

        parsed = urlparse(sqlalchemy_url)
        username = parsed.username or ""
        host = parsed.hostname
        port = parsed.port or 5432
        if not AWS_REGION:
            raise ValueError("AWS_REGION must be set when ENABLE_AWS_RDS_IAM is true")
        rds = boto3.client("rds", region_name=AWS_REGION)
        token = rds.generate_db_auth_token(DBHostname=host, Port=port, DBUsername=username)
        # Reconstruct URL with token as password and ensure empty password is ok
        safe_user = quote(username) if username else ""
        safe_host = host
        new_netloc = f"{safe_user}:{quote(token)}@{safe_host}:{port}"
        sqlalchemy_url = parsed._replace(netloc=new_netloc).geturl()
        log.info("Using AWS RDS IAM token for PostgreSQL authentication")
    except Exception as e:
        log.exception(f"Failed to generate AWS RDS IAM token: {e}")
        raise

SQLALCHEMY_DATABASE_URL = sqlalchemy_url
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    if DATABASE_POOL_SIZE > 0:
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            pool_size=DATABASE_POOL_SIZE,
            max_overflow=DATABASE_POOL_MAX_OVERFLOW,
            pool_timeout=DATABASE_POOL_TIMEOUT,
            pool_recycle=DATABASE_POOL_RECYCLE,
            pool_pre_ping=True,
            poolclass=QueuePool,
            **sqlalchemy_connect_args,
        )
    else:
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL, pool_pre_ping=True, poolclass=NullPool, **sqlalchemy_connect_args
        )


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
