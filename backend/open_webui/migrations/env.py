from logging.config import fileConfig

from alembic import context
from open_webui.models.auths import Auth
from open_webui.env import (
    DATABASE_URL,
    ENABLE_AWS_RDS_IAM,
    AWS_REGION,
    PG_SSLMODE,
    PG_SSLROOTCERT,
)
from sqlalchemy import engine_from_config, pool

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Auth.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# Build URL with optional IAM token
DB_URL = DATABASE_URL
if ENABLE_AWS_RDS_IAM and DB_URL and DB_URL.startswith("postgresql://"):
    try:
        import boto3
        from urllib.parse import urlparse, quote

        parsed = urlparse(DB_URL)
        username = parsed.username or ""
        host = parsed.hostname
        port = parsed.port or 5432
        if not AWS_REGION:
            raise ValueError("AWS_REGION must be set when ENABLE_AWS_RDS_IAM is true")
        rds = boto3.client("rds", region_name=AWS_REGION)
        token = rds.generate_db_auth_token(
            DBHostname=host, Port=port, DBUsername=username
        )
        safe_user = quote(username) if username else ""
        new_netloc = f"{safe_user}:{quote(token)}@{host}:{port}"
        DB_URL = parsed._replace(netloc=new_netloc).geturl()
    except Exception as e:
        import logging

        logging.getLogger(__name__).exception(
            f"Failed to generate AWS RDS IAM token: {e}"
        )
        raise

if DB_URL:
    # Include SSL params inline to avoid ~/.postgresql lookups
    if PG_SSLMODE and "sslmode=" not in DB_URL:
        sep = "&" if "?" in DB_URL else "?"
        DB_URL = f"{DB_URL}{sep}sslmode={PG_SSLMODE}"
    if PG_SSLROOTCERT and "sslrootcert=" not in DB_URL:
        sep = "&" if "?" in DB_URL else "?"
        DB_URL = f"{DB_URL}{sep}sslrootcert={PG_SSLROOTCERT}"

    config.set_main_option("sqlalchemy.url", DB_URL.replace("%", "%%"))


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
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
