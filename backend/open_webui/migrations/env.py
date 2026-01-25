import logging
from logging.config import fileConfig

from alembic import context
from open_webui.models.auths import Auth
from open_webui.env import DATABASE_URL, DATABASE_PASSWORD, LOG_FORMAT
import sqlalchemy as sa
from sqlalchemy.ext.compiler import compiles
from sqlalchemy import engine_from_config, pool, create_engine

log = logging.getLogger(__name__)


# --- MySQL/MariaDB compatibility shims ---------------------------------------
# Goal:
#   Keep existing historical Alembic revisions unchanged while making them
#   executable on MySQL/MariaDB.
#
# Why this is needed:
#   Open-WebUI has older migrations that were originally written with
#   SQLite/PostgreSQL-friendly assumptions. In particular:
#     - some revisions use sa.String() without an explicit length
#     - some revisions use sa.Text() for identifier-like columns such as ids,
#       unique keys, indexed columns, or foreign-key columns
#
# On MySQL/MariaDB, these patterns can fail during DDL generation because:
#   - VARCHAR requires a length
#   - TEXT/BLOB columns cannot be used safely for PRIMARY KEY / UNIQUE / indexed
#     columns without a key length
#   - foreign-key columns must be type-compatible with the referenced key
#
# Scope:
#   These shims affect Alembic migration DDL compilation only. They do not change
#   SQLAlchemy model definitions or runtime query behavior outside migrations.
#
# Design note:
#   sa.String() can be fixed globally because the issue is type-only (missing length).
#   sa.Text() cannot: TEXT is valid in general, but invalid/problematic only when used
#   for PK/UNIQUE/index/FK columns, so we must inspect column context during DDL compilation.
#
#   This shim is a safety net for historical revisions during CREATE TABLE DDL generation.
#   New migrations should still use MariaDB-safe types explicitly (for example key_text()),
#   especially for columns that may later participate in op.create_index(...) or other
#   for PK/UNIQUE/index/FK columns, so we must inspect column context during DDL compilation.
#
# 1) sa.String() without a length:
#    Triggered when a historical migration emits sa.String() and Alembic compiles
#    it for the mysql/mariadb dialect. In that case, rewrite it to VARCHAR(255)
#    so the migration remains valid without editing the historical revision.
@compiles(sa.String, 'mysql')
@compiles(sa.String, 'mariadb')
def _compile_string_mysql(type_, compiler, **kw):
    if type_.length is None:
        type_ = sa.String(length=255)
    return compiler.visit_VARCHAR(type_, **kw)


#
#
# 2) sa.Text() used for key-like columns:
#    Triggered when a historical migration defines a TEXT column that is also:
#      - a PRIMARY KEY
#      - UNIQUE
#      - indexed
#      - or used as a FOREIGN KEY
#
#    During MySQL/MariaDB migration DDL compilation only, rewrite those columns
#    from TEXT to VARCHAR(255). This preserves the intent of the old migration
#    while satisfying MySQL/MariaDB key and FK requirements.
#
#    How it works:
#      - patch MySQLDDLCompiler.get_column_specification()
#      - inspect each column as Alembic renders CREATE/ALTER TABLE DDL
#      - if the column type is sa.Text and it participates in a PK/UNIQUE/index/FK,
#        make a shallow column copy and replace its type with sa.String(255)
#      - delegate back to SQLAlchemy's original compiler method
#
#    This keeps the compatibility logic centralized in env.py instead of
#    modifying many already-released migration files.
try:
    from sqlalchemy.dialects.mysql.base import MySQLDDLCompiler

    def _is_mysql_key_text_column(column) -> bool:
        """
        Return True when a TEXT column participates in a key-like path that is
        unsafe on MySQL/MariaDB and should be rewritten to VARCHAR(255) during
        CREATE TABLE DDL compilation.

        This covers both:
        - column-level flags (primary_key / unique / index / foreign_keys)
        - table-level constraints/indexes attached before CREATE TABLE compilation
        """
        is_fk_col = bool(getattr(column, 'foreign_keys', None))
        if column.primary_key or column.unique or column.index or is_fk_col:
            return True

        table = getattr(column, 'table', None)
        if table is None:
            return False

        for constraint in getattr(table, 'constraints', ()):
            if isinstance(constraint, (sa.PrimaryKeyConstraint, sa.UniqueConstraint)):
                try:
                    if column in constraint.columns:
                        return True
                except Exception:
                    pass

        for index in getattr(table, 'indexes', ()):
            try:
                if column in index.columns:
                    return True
            except Exception:
                pass

        return False

    _orig_get_colspec = MySQLDDLCompiler.get_column_specification

    def _patched_get_column_specification(self, column, **kw):
        # NOTE: For mysql/mariadb, FK columns must be type-compatible with the referenced key.
        # If historical migrations used TEXT for FK columns, MySQL/MariaDB will reject the FK.
        if isinstance(column.type, sa.Text) and _is_mysql_key_text_column(column):
            column = column.copy()
            column.type = sa.String(length=255)
        return _orig_get_colspec(self, column, **kw)

    MySQLDDLCompiler.get_column_specification = _patched_get_column_specification
except Exception:
    if DATABASE_URL.startswith(('mysql', 'mariadb')):
        log.exception('Failed to install MySQL/MariaDB compatibility shims')
        raise
    # If MySQL/MariaDB is not the active dialect, continue without installing the shim.

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# Re-apply JSON formatter after fileConfig replaces handlers.
if LOG_FORMAT == 'json':
    from open_webui.env import JSONFormatter

    for handler in logging.root.handlers:
        handler.setFormatter(JSONFormatter())

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Auth.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

DB_URL = DATABASE_URL

if DB_URL:
    config.set_main_option('sqlalchemy.url', DB_URL.replace('%', '%%'))


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option('sqlalchemy.url')
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Handle SQLCipher URLs
    if DB_URL and DB_URL.startswith('sqlite+sqlcipher://'):
        if not DATABASE_PASSWORD or DATABASE_PASSWORD.strip() == '':
            raise ValueError('DATABASE_PASSWORD is required when using sqlite+sqlcipher:// URLs')

        # Extract database path from SQLCipher URL
        db_path = DB_URL.replace('sqlite+sqlcipher://', '')
        if db_path.startswith('/'):
            db_path = db_path[1:]  # Remove leading slash for relative paths

        # Create a custom creator function that uses sqlcipher3
        def create_sqlcipher_connection():
            import sqlcipher3

            conn = sqlcipher3.connect(db_path, check_same_thread=False)
            conn.execute(f"PRAGMA key = '{DATABASE_PASSWORD}'")
            return conn

        connectable = create_engine(
            'sqlite://',  # Dummy URL since we're using creator
            creator=create_sqlcipher_connection,
            echo=False,
        )
    else:
        # Standard database connection (existing logic)
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix='sqlalchemy.',
            poolclass=pool.NullPool,
        )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
