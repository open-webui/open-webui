from peewee import *
from peewee_migrate import Router
from playhouse.shortcuts import ReconnectMixin
from playhouse.db_url import PooledPostgresqlDatabase, connect, register_database
from psycopg2 import OperationalError
from psycopg2.errors import InterfaceError
from config import SRC_LOG_LEVELS, DATA_DIR, DATABASE_URL
import os
import logging

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["DB"])

# Check if the file exists
if os.path.exists(f"{DATA_DIR}/ollama.db"):
    # Rename the file
    os.rename(f"{DATA_DIR}/ollama.db", f"{DATA_DIR}/webui.db")
    log.info("Database migrated from Ollama-WebUI successfully.")
else:
    pass


class PGReconnectMixin(ReconnectMixin):
    reconnect_errors = (
        # Postgres error examples:
        (OperationalError, 'termin'),
        (InterfaceError, 'closed'),
    )


class ReconnectingPostgresqlDatabase(PGReconnectMixin, PooledPostgresqlDatabase):
    pass


register_database(ReconnectingPostgresqlDatabase, 'postgres+pool', 'postgresql+pool')

DB = connect(DATABASE_URL)
log.info(f"Connected to a {DB.__class__.__name__} database.")
router = Router(DB, migrate_dir="apps/web/internal/migrations", logger=log)
router.run()
DB.connect(reuse_if_open=True)
