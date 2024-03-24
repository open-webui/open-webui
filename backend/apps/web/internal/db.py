from peewee import *
from config import SRC_LOG_LEVELS, DATA_DIR
import os
import logging

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["DB"])

# Check if the file exists
if os.path.exists(f"{DATA_DIR}/ollama.db"):
    # Rename the file
    os.rename(f"{DATA_DIR}/ollama.db", f"{DATA_DIR}/webui.db")
    log.info("File renamed successfully.")
else:
    pass


DB = SqliteDatabase(f"{DATA_DIR}/webui.db")
DB.connect()
