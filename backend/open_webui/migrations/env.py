from __future__ import annotations

# Alembic environment configuration runner.
# Coordinates database migrations in both offline and online execution modes.
import logging.config
import logging
import alembic.context
from open_webui.env import DATABASE_PASSWORD, DATABASE_URL, LOG_FORMAT
from open_webui.internal.db import enable_iam_token_auth, extract_ssl_params_from_url, reattach_ssl_params_to_url
from open_webui.models.auths import Auth
from open_webui.models.calendar import Calendar, CalendarEvent, CalendarEventAttendee  # noqa: F401
from sqlalchemy import create_engine, engine_from_config, pool

alembic_config = alembic.context.config
if alembic_config.config_file_name:
    logging.config.fileConfig(alembic_config.config_file_name, disable_existing_loggers=False)
if LOG_FORMAT == 'json':
    from open_webui.env import JSONFormatter

    for log_handler in logging.root.handlers:
        log_handler.setFormatter(JSONFormatter())
migration_metadata = Auth.metadata
target_db_url = DATABASE_URL
base_url, ssl_query_params = extract_ssl_params_from_url(target_db_url)
if ssl_query_params:
    target_db_url = reattach_ssl_params_to_url(base_url, ssl_query_params)
if target_db_url:
    alembic_config.set_main_option('sqlalchemy.url', target_db_url.replace('%', '%%'))


def run_migrations_offline() -> None:
    """Execute Alembic migrations in offline mode (outputs raw SQL DDL)."""
    db_connection_url = alembic_config.get_main_option('sqlalchemy.url')
    alembic.context.configure(
        url=db_connection_url,
        target_metadata=migration_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
    )
    with alembic.context.begin_transaction():
        alembic.context.run_migrations()


def _get_engine_connectable():
    """Build the database engine based on target URL and authentication credentials."""
    if target_db_url and target_db_url.startswith('sqlite+sqlcipher://'):
        if not DATABASE_PASSWORD or not DATABASE_PASSWORD.strip():
            raise ValueError('DATABASE_PASSWORD is required when using sqlite+sqlcipher:// URLs')
        raw_db_path = target_db_url.replace('sqlite+sqlcipher://', '')
        if raw_db_path.startswith('/'):
            raw_db_path = raw_db_path[1:]

        def _sqlite_cipher_creator():
            import sqlcipher3

            cipher_conn = sqlcipher3.connect(raw_db_path, check_same_thread=False)
            cipher_conn.execute(f"PRAGMA key = '{DATABASE_PASSWORD}'")
            return cipher_conn

        return create_engine('sqlite://', creator=_sqlite_cipher_creator, echo=False)
    return engine_from_config(
        alembic_config.get_section(alembic_config.config_ini_section, {}),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )


def run_migrations_online() -> None:
    """Execute migrations against a live database connection."""
    live_connectable = _get_engine_connectable()
    enable_iam_token_auth(live_connectable)
    with live_connectable.connect() as live_connection:
        alembic.context.configure(
            connection=live_connection,
            target_metadata=migration_metadata,
        )
        with alembic.context.begin_transaction():
            alembic.context.run_migrations()


# Alembic execution entrypoint branch
if alembic.context.is_offline_mode():
    run_migrations_offline()  # run in offline mode
if not alembic.context.is_offline_mode():
    run_migrations_online()  # run in online mode
