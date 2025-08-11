import logging
from contextvars import ContextVar

from open_webui.env import SRC_LOG_LEVELS, ENABLE_AWS_RDS_IAM, AWS_REGION, PG_SSLMODE, PG_SSLROOTCERT
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
    try:
        from urllib.parse import urlparse, quote
        if ENABLE_AWS_RDS_IAM:
            import boto3
            parsed = urlparse(final_url)
            username = parsed.username or ""
            host = parsed.hostname
            port = parsed.port or 5432
            if not AWS_REGION:
                raise ValueError("AWS_REGION must be set when ENABLE_AWS_RDS_IAM is true")
            rds = boto3.client("rds", region_name=AWS_REGION)
            token = rds.generate_db_auth_token(DBHostname=host, Port=port, DBUsername=username)
            safe_user = quote(username) if username else ""
            new_netloc = f"{safe_user}:{quote(token)}@{host}:{port}"
            final_url = parsed._replace(netloc=new_netloc).geturl()
        # add ssl query params
        if PG_SSLMODE and "sslmode=" not in final_url:
            sep = "&" if "?" in final_url else "?"
            final_url = f"{final_url}{sep}sslmode={PG_SSLMODE}"
        if PG_SSLROOTCERT and "sslrootcert=" not in final_url:
            sep = "&" if "?" in final_url else "?"
            final_url = f"{final_url}{sep}sslrootcert={PG_SSLROOTCERT}"
    except Exception as e:
        log.exception(f"Failed to augment PostgreSQL URL for IAM/SSL: {e}")
        raise
    return final_url


def register_connection(db_url):
    db_url = _augment_postgres_url_with_iam_and_ssl(db_url)
    db = connect(db_url, unquote_user=True, unquote_password=True)
    if isinstance(db, PostgresqlDatabase):
        # Enable autoconnect for SQLite databases, managed by Peewee
        db.autoconnect = True
        db.reuse_if_open = True
        log.info("Connected to PostgreSQL database")

        # Get the connection details
        connection = parse(db_url, unquote_user=True, unquote_password=True)

        # Use our custom database class that supports reconnection
        db = ReconnectingPostgresqlDatabase(**connection)
        db.connect(reuse_if_open=True)
    elif isinstance(db, SqliteDatabase):
        # Enable autoconnect for SQLite databases, managed by Peewee
        db.autoconnect = True
        db.reuse_if_open = True
        log.info("Connected to SQLite database")
    else:
        raise ValueError("Unsupported database connection")
    return db
