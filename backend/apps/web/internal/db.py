from peewee import *
from peewee_migrate import Router
from playhouse.db_url import connect
from config import SRC_LOG_LEVELS, DATABASE_URL
import os
import logging

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["DB"])

# Raw strings for Windows file paths
file_path_ollama = r"C:\Users\mfran\Documents\Projects\next-webui\backend\data\ollama.db"
file_path_webui = r"C:\Users\mfran\Documents\Projects\next-webui\backend\data\webui.db"

# Check if the file exists
if os.path.exists(file_path_ollama):
    try:
        # Rename the file
        os.rename(file_path_ollama, file_path_webui)
        log.info("File renamed successfully.")
    except Exception as e:
        log.error(f"Error renaming file: {e}")
else:
    log.error("File does not exist.")

try:
    # Initialize SQLite database connection
    DB = SqliteDatabase(file_path_webui)
    router = Router(DB, migrate_dir="apps/web/internal/migrations", logger=log)
    router.run()
    DB.connect(reuse_if_open=True)
    log.info("Database connection established.")
except Exception as e:
    log.error(f"Error initializing database connection: {e}")

# temp_file_path = None  # Initialize temporary file path

# # Check if the file exists
# response = requests.head(f"{DATA_DIR}/ollama.db", auth=(NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD), headers=HEADERS)
# if response.status_code == 200:
#     # Rename the file on Nextcloud
#     rename_response = requests.request("MOVE", f"{DATA_DIR}/ollama.db", f"{DATA_DIR}/webui.db", auth=(NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD), headers=HEADERS)
#     if rename_response.status_code == 200:
#         log.info("File renamed successfully on Nextcloud.")
#         # Now try to download the renamed file
#         webui = requests.get(f"{DATA_DIR}/webui.db", auth=(NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD), headers=HEADERS)
#         if webui.status_code == 200:
#             with tempfile.NamedTemporaryFile(delete=False) as temp_file:
#                 temp_file.write(webui.content)
#                 temp_file_path = temp_file.name
#                 log.info("Webui.db successfully downloaded to temporary file:", temp_file_path)
#         else:
#             log.error("Webui.db not downloaded.")
#     else:
#         log.error(f"Failed to rename file on Nextcloud. Status code: {rename_response.status_code}")
# else:
#     log.error(f"File does not exist on Nextcloud. Status code: {response.status_code}")

# # Connect to the temporary database file
# if temp_file_path:
#     DB = SqliteDatabase(temp_file_path)
#     router = Router(DB, migrate_dir="apps/web/internal/migrations", logger=log)
#     router.run()
#     DB.connect(reuse_if_open=True)
# else:
#     log.error("Temporary file path not defined.")