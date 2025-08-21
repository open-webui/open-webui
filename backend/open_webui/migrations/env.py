from logging.config import fileConfig

from alembic import context
from open_webui.models.auths import Auth
from open_webui.env import DATABASE_URL, DATABASE_PASSWORD
from sqlalchemy import engine_from_config, pool, create_engine

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
    # Handle SQLCipher URLs
    if DB_URL and DB_URL.startswith("sqlite+sqlcipher://"):
        if not DATABASE_PASSWORD or DATABASE_PASSWORD.strip() == "":
            raise ValueError(
                "DATABASE_PASSWORD is required when using sqlite+sqlcipher:// URLs"
            )

        # Extract database path from SQLCipher URL
        db_path = DB_URL.replace("sqlite+sqlcipher://", "")
        if db_path.startswith("/"):
            db_path = db_path[1:]  # Remove leading slash for relative paths

        # Create a custom creator function that uses sqlcipher3
        def create_sqlcipher_connection():
            import sqlcipher3

            conn = sqlcipher3.connect(db_path, check_same_thread=False)
            conn.execute(f"PRAGMA key = '{DATABASE_PASSWORD}'")
            return conn

        connectable = create_engine(
            "sqlite://",  # Dummy URL since we're using creator
            creator=create_sqlcipher_connection,
            echo=False,
        )
    else:
        # Standard database connection (existing logic)
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
