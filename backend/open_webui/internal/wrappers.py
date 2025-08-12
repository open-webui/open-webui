import logging
from contextvars import ContextVar

from open_webui.env import (
    SRC_LOG_LEVELS,
    ENABLE_AWS_RDS_IAM,
    AWS_REGION,
    PG_SSLMODE,
    PG_SSLROOTCERT,
)
from peewee import *
from peewee import InterfaceError as PeeWeeInterfaceError
from peewee import PostgresqlDatabase
from playhouse.db_url import connect, parse
from playhouse.shortcuts import ReconnectMixin

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["DB"])

db_state_default = {"closed": None, "conn": None, "ctx": None, "transactions": None}
db_state = ContextVar("db_state", default=db_state_default.copy())


class PeeweeConnectionState(object):
    def __init__(self, **kwargs):
        super().__setattr__("_state", db_state)
        super().__init__(**kwargs)

    def __setattr__(self, name, value):
        self._state.get()[name] = value

    def __getattr__(self, name):
        value = self._state.get()[name]
        return value


class CustomReconnectMixin(ReconnectMixin):
    reconnect_errors = (
        # psycopg2
        (OperationalError, "termin"),
        (InterfaceError, "closed"),
        # peewee
        (PeeWeeInterfaceError, "closed"),
    )


class ReconnectingPostgresqlDatabase(CustomReconnectMixin, PostgresqlDatabase):
    pass


def _augment_postgres_url_with_iam_and_ssl(db_url: str) -> str:
    if not db_url.startswith("postgres://") and not db_url.startswith("postgresql://"):
        return db_url
    final_url = db_url

    # Debug SSL environment variables
    log.info(
        f"🔍 DEBUG SSL ENV: PG_SSLMODE={PG_SSLMODE}, PG_SSLROOTCERT={PG_SSLROOTCERT}"
    )
    log.info(
        f"🔍 DEBUG SSL ENV: ENABLE_AWS_RDS_IAM={ENABLE_AWS_RDS_IAM}, AWS_REGION={AWS_REGION}"
    )

    try:
        from urllib.parse import urlparse, quote

        if ENABLE_AWS_RDS_IAM:
            import boto3

            parsed = urlparse(final_url)
            username = parsed.username or ""
            host = parsed.hostname
            port = parsed.port or 5432
            if not AWS_REGION:
                raise ValueError(
                    "AWS_REGION must be set when ENABLE_AWS_RDS_IAM is true"
                )
            rds = boto3.client("rds", region_name=AWS_REGION)
            token = rds.generate_db_auth_token(
                DBHostname=host, Port=port, DBUsername=username
            )
            safe_user = quote(username) if username else ""
            new_netloc = f"{safe_user}:{quote(token)}@{host}:{port}"
            final_url = parsed._replace(netloc=new_netloc).geturl()
        # add ssl query params
        if PG_SSLMODE and "sslmode=" not in final_url:
            sep = "&" if "?" in final_url else "?"
            final_url = f"{final_url}{sep}sslmode={PG_SSLMODE}"
            log.info(f"🔍 DEBUG: Added sslmode={PG_SSLMODE} to URL")
        if PG_SSLROOTCERT and "sslrootcert=" not in final_url:
            sep = "&" if "?" in final_url else "?"
            final_url = f"{final_url}{sep}sslrootcert={PG_SSLROOTCERT}"
            log.info(f"🔍 DEBUG: Added sslrootcert={PG_SSLROOTCERT} to URL")
    except Exception as e:
        log.exception(f"Failed to augment PostgreSQL URL for IAM/SSL: {e}")
        raise
    return final_url


def register_connection(db_url):
    print(f"🔌 DB_CONNECT: Starting register_connection with URL: {db_url[:50]}...")
    log.info(f"🔍 DEBUG: Original DB URL: {db_url[:50]}...")
    
    print("🔌 DB_CONNECT: About to augment URL with IAM/SSL...")
    augmented_url = _augment_postgres_url_with_iam_and_ssl(db_url)
    print(f"🔌 DB_CONNECT: URL augmentation complete: {augmented_url[:50]}...")
    log.info(f"🔍 DEBUG: Augmented DB URL: {augmented_url[:50]}...")
    
    print("🔌 DB_CONNECT: About to call connect()...")
    db = connect(augmented_url, unquote_user=True, unquote_password=True)
    print("🔌 DB_CONNECT: ✅ connect() completed successfully")
    
    if isinstance(db, PostgresqlDatabase):
        print("🔌 DB_CONNECT: Setting up PostgreSQL database...")
        # Enable autoconnect for SQLite databases, managed by Peewee
        db.autoconnect = True
        db.reuse_if_open = True
        log.info("Connected to PostgreSQL database")

        # Get the connection details from the AUGMENTED URL to preserve SSL params
        print("🔌 DB_CONNECT: Parsing connection details...")
        connection = parse(augmented_url, unquote_user=True, unquote_password=True)
        print(f"🔌 DB_CONNECT: Connection details parsed successfully")
        log.info(f"🔍 DEBUG: Parsed connection params: {connection}")

        # Use our custom database class that supports reconnection
        print("🔌 DB_CONNECT: Creating ReconnectingPostgresqlDatabase...")
        db = ReconnectingPostgresqlDatabase(**connection)
        print("🔌 DB_CONNECT: About to call db.connect()...")
        db.connect(reuse_if_open=True)
        print("🔌 DB_CONNECT: ✅ db.connect() completed successfully")
    elif isinstance(db, SqliteDatabase):
        # Enable autoconnect for SQLite databases, managed by Peewee
        db.autoconnect = True
        db.reuse_if_open = True
        log.info("Connected to SQLite database")
    else:
        raise ValueError("Unsupported database connection")
    return db
