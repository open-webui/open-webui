import json
import logging
from contextlib import contextmanager
from typing import Any, Optional
import os

from sqlalchemy import Dialect, create_engine, MetaData, types
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.sql.type_api import _T
from typing_extensions import Self
from sqlalchemy.sql import text
from sqlalchemy import event
from sqlalchemy.schema import Table

# Initialize Base first, before any model imports
metadata_obj = MetaData()
Base = declarative_base(metadata=metadata_obj)

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
)
from peewee_migrate import Router

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


def handle_peewee_migration(DATABASE_URL):
    """Handle Peewee database migrations"""
    try:
        log.info(f"Setting up Peewee connection with URL: {DATABASE_URL}")
        db = register_connection(DATABASE_URL.replace("postgresql://", "postgres://"))
        
        migrate_dir = OPEN_WEBUI_DIR / "internal" / "migrations"
        router = Router(db, logger=log, migrate_dir=migrate_dir)
        
        # Run the migrations
        log.info("Running Peewee migrations...")
        router.run()
        db.close()
    except Exception as e:
        log.error(f"Database connection test failed: {e}")
        # No need to retry with pooler since we now prioritize it from the start
        raise


def initialize_database():
    """Initialize the database and run migrations"""
    # Check if we should skip migrations
    if os.environ.get("SKIP_DB_MIGRATIONS", "").lower() == "true":
        log.info("Skipping database migrations as SKIP_DB_MIGRATIONS is set to true")
        # Override the alembic_version table name for this session
        # This is important since we're using a custom table name
        @event.listens_for(Table, "after_parent_attach")
        def _set_version_table_schema(table, parent):
            if table.name == "alembic_version":
                table.name = "owui_alembic_version"
                
        log.info("Set custom alembic version table name: owui_alembic_version")
        return
        
    try:
        log.info(f"Starting database initialization with URL: {DATABASE_URL}")
        
        # Run Peewee migrations first
        handle_peewee_migration(DATABASE_URL)
        log.info("Peewee migration handler completed")
        
        # Run Alembic migrations
        from alembic import command
        from alembic.config import Config
        from pathlib import Path
        
        # Create Alembic config
        alembic_cfg = Config()
        migrations_dir = Path(__file__).parent.parent / "migrations"
        alembic_cfg.set_main_option("script_location", str(migrations_dir))
        alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
        
        log.info("Running Alembic migrations...")
        command.upgrade(alembic_cfg, "head")
        log.info("Alembic migrations completed successfully")
        
    except Exception as e:
        log.error(f"Error during database initialization: {e}")
        if "sqlite" in DATABASE_URL.lower():
            log.warning("Using SQLite database. If you're seeing migration errors, consider using PostgreSQL instead.")
        else:
            log.warning("Check your database connection settings and ensure your PostgreSQL server is accessible.")
        raise

SQLALCHEMY_DATABASE_URL = DATABASE_URL
log.info(f"Setting up SQLAlchemy with database URL: {SQLALCHEMY_DATABASE_URL}")

if "sqlite" in SQLALCHEMY_DATABASE_URL:
    log.info("Using SQLite database with SQLAlchemy")
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    log.info("Using PostgreSQL database with SQLAlchemy")
    if DATABASE_POOL_SIZE > 0:
        log.info(f"Using database connection pool with size: {DATABASE_POOL_SIZE}")
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
        log.info("Using database connection without pooling")
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL, pool_pre_ping=True, poolclass=NullPool,
        )

# Check if connection is working by executing a simple query
try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        log.info(f"Database connection test successful: {result.scalar()}")
except Exception as e:
    log.error(f"Database connection test failed: {e}")
    
log.info(f"Database engine initialized: {engine.name}")

SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
)
metadata_obj.schema = DATABASE_SCHEMA
Session = scoped_session(SessionLocal)

def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

get_db = contextmanager(get_session)
