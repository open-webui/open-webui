import os
import logging
import json

from peewee import *
from peewee_migrate import Router

from apps.webui.internal.wrappers import register_connection
from config import SRC_LOG_LEVELS, DATA_DIR, DATABASE_URL, BACKEND_DIR

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["DB"])


class JSONField(TextField):
    def db_value(self, value):
        return json.dumps(value)

    def python_value(self, value):
        if value is not None:
            return json.loads(value)


# Check if the file exists
if os.path.exists(f"{DATA_DIR}/ollama.db"):
    # Rename the file
    os.rename(f"{DATA_DIR}/ollama.db", f"{DATA_DIR}/webui.db")
    log.info("Database migrated from Ollama-WebUI successfully.")
else:
    pass


# The `register_connection` function encapsulates the logic for setting up
# the database connection based on the connection string, while `connect`
# is a Peewee-specific method to manage the connection state and avoid errors
# when a connection is already open.
try:
    DB = register_connection(DATABASE_URL)
    log.info(f"Connected to a {DB.__class__.__name__} database.")
except Exception as e:
    log.error(f"Failed to initialize the database connection: {e}")
    raise

router = Router(
    DB,
    migrate_dir=BACKEND_DIR / "apps" / "webui" / "internal" / "migrations",
    logger=log,
)
router.run()
try:
    DB.connect(reuse_if_open=True)
except OperationalError as e:
    log.info(f"Failed to connect to database again due to: {e}")
    pass
