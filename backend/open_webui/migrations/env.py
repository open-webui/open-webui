from logging.config import fileConfig

from alembic import context
from open_webui.internal.db import Base
from open_webui.env import DATABASE_URL
from sqlalchemy import engine_from_config, pool, text

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
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

DB_URL = DATABASE_URL

if DB_URL:
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

    # Configure for offline mode with proper schema support
    configure_kwargs = {
        "url": url,
        "target_metadata": target_metadata,
        "literal_binds": True,
        "dialect_opts": {"paramstyle": "named"},
    }

    # Add schema configuration if target_metadata.schema is set
    if target_metadata.schema:
        configure_kwargs["version_table_schema"] = target_metadata.schema

    context.configure(**configure_kwargs)

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
        if target_metadata.schema and connection.dialect.name == 'postgresql':
            # Applying schema settings only in PostgreSQL
            connection.execute(
                text(f"SET search_path TO {target_metadata.schema}, public")
            )
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                version_table_schema=target_metadata.schema,
            )
        else:
            # For SQLite, ignore schema and use default behavior
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
            )

        with context.begin_transaction():
            context.run_migrations()
            connection.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
