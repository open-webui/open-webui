import sys
from datetime import datetime, timedelta, timezone
import logging
import os
import asyncio

from open_webui.env import GLOBAL_LOG_LEVEL, SRC_LOG_LEVELS
from open_webui.models.chats import Chat
from open_webui.models.messages import Message
from open_webui.models.files import File
from open_webui.config import PersistentConfig
from open_webui.retrieval.vector.connector import VECTOR_DB_CLIENT
from open_webui.storage.provider import Storage
from open_webui.internal.db import get_db

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

# Timeout duration in seconds
TIMEOUT_DURATION = 60 * 60 * 24

# Add data retention settings to config
DATA_RETENTION_DAYS = PersistentConfig(
    "DATA_RETENTION_DAYS",
    "data_retention.days",
    int(os.environ.get("DATA_RETENTION_DAYS", "30")),
)

DATA_RETENTION_ENABLED = PersistentConfig(
    "DATA_RETENTION_ENABLED",
    "data_retention.enabled",
    os.environ.get("DATA_RETENTION_ENABLED", "True").lower() == "true",
)


def _cleanup_old_data():
    try:
        log.info("Running data retention cleanup task")
        retention_days = DATA_RETENTION_DAYS.value
        cutoff_date = int(
            (datetime.now(timezone.utc) - timedelta(days=retention_days)).timestamp()
        )

        with get_db() as db:
            # Get counts before deletion for reporting
            old_chats = db.query(Chat).filter(Chat.created_at < cutoff_date).count()
            old_messages = (
                db.query(Message).filter(Message.created_at < cutoff_date).count()
            )
            old_files = db.query(File).filter(File.created_at < cutoff_date).count()

            # Get file paths before deletion for filesystem cleanup
            old_file_paths = [
                file.path
                for file in db.query(File).filter(File.created_at < cutoff_date).all()
            ]

            # Get collection names for vector DB cleanup
            old_collections = set()
            for file in db.query(File).filter(File.created_at < cutoff_date).all():
                if file.meta and "collection_name" in file.meta:
                    old_collections.add(file.meta["collection_name"])

            # Delete in correct order to maintain referential integrity
            db.query(Message).filter(Message.created_at < cutoff_date).delete()
            db.query(Chat).filter(Chat.created_at < cutoff_date).delete()
            db.query(File).filter(File.created_at < cutoff_date).delete()

            # Clean up vector DB collections
            for collection in old_collections:
                try:
                    VECTOR_DB_CLIENT.delete_collection(collection)
                    log.info(f"Deleted vector collection: {collection}")
                except Exception as e:
                    log.error(f"Error deleting vector collection {collection}: {e}")

            # Clean up files from storage
            for file_path in old_file_paths:
                try:
                    Storage.delete_file(file_path)
                    log.info(f"Deleted file from storage: {file_path}")
                except Exception as e:
                    log.error(f"Error deleting file from storage {file_path}: {e}")

            db.commit()

            results = {
                "deleted_chats": old_chats,
                "deleted_messages": old_messages,
                "deleted_files": old_files,
                "deleted_collections": len(old_collections),
            }
            log.info(f"Data retention completed: {results}")
            return results

        log.info("Data retention task completed")
    except Exception as e:
        log.error(f"Error in data retention task: {e}")
        return None


async def run_data_retention():
    """Run data retention cleanup task"""
    while True:
        _cleanup_old_data()
        # Repeat once a day
        await asyncio.sleep(TIMEOUT_DURATION)
