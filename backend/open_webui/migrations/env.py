"""Alembic environment configuration.

Configures the migration context for both offline (SQL script generation)
and online (live database connection) modes. Handles SQLCipher URLs,
SSL parameter normalisation, and JSON log formatting.
"""

import logging
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, engine_from_config, pool

from open_webui.env import DATABASE_PASSWORD, DATABASE_URL, LOG_FORMAT
from open_webui.internal.db import extract_ssl_params_from_url, reattach_ssl_params_to_url
from open_webui.models.auths import Auth
from open_webui.models.calendar import Calendar, CalendarEvent, CalendarEventAttendee  # noqa: F401

# ── Alembic config & logging ─────────────────────────────────────────────────

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# Re-apply JSON formatter after fileConfig replaces handlers.
if LOG_FORMAT == "json":
    from open_webui.env import JSONFormatter

    for handler in logging.root.handlers:
        handler.setFormatter(JSONFormatter())

# ── Database URL ─────────────────────────────────────────────────────────────

target_metadata = Auth.metadata

DB_URL = DATABASE_URL

# Normalise SSL query params for psycopg2 (Alembic uses psycopg2 for sync).
_url_no_ssl, _ssl_params = extract_ssl_params_from_url(DB_URL)
if _ssl_params:
    DB_URL = reattach_ssl_params_to_url(_url_no_ssl, _ssl_params)

if DB_URL:
    config.set_main_option("sqlalchemy.url", DB_URL.replace("%", "%%"))


# ── Migration runners ────────────────────────────────────────────────────────


def run_migrations_offline() -> None:
    """Generate SQL script without a live database connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _build_connectable():
    """Create the appropriate SQLAlchemy engine for the configured DB URL."""
    if DB_URL and DB_URL.startswith("sqlite+sqlcipher://"):
        if not DATABASE_PASSWORD or DATABASE_PASSWORD.strip() == "":
            raise ValueError(
                "DATABASE_PASSWORD is required when using sqlite+sqlcipher:// URLs"
            )

        db_path = DB_URL.replace("sqlite+sqlcipher://", "")
        if db_path.startswith("/"):
            db_path = db_path[1:]

        def _sqlcipher_creator():
            import sqlcipher3

            conn = sqlcipher3.connect(db_path, check_same_thread=False)
            conn.execute(f"PRAGMA key = '{DATABASE_PASSWORD}'")
            return conn

        return create_engine("sqlite://", creator=_sqlcipher_creator, echo=False)

    return engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    connectable = _build_connectable()
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


# ── Entrypoint ───────────────────────────────────────────────────────────────

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
