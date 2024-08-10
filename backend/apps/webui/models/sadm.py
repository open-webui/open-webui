# apps/webui/models/sadm.py

import os
import time
import logging
import mimetypes
import json

from pathlib import Path
from threading import Event, Thread
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pydantic import BaseModel
from sqlalchemy import text


from apps.webui.models.documents import (
    Documents,
    Document,
    DocumentForm
)

from apps.webui.internal.db import Base, get_db


from apps.rag.main import (
    store_data_in_vector_db,
    get_loader
)

from utils.misc import (
    calculate_sha256,
    extract_folders_after_data_docs,
    sanitize_filename,
    locate_document_in_filesystem
)

from config import (
    SRC_LOG_LEVELS,
    CONFIG_DATA,
    CONFIG_FILE,
    UPLOAD_DIR,
    UPLOADS_DIR_NAME,
    DOCS_DIR,
    DOCS_DIR_NAME

    
)

# Logging setup
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


# class for dummy userid
class DummyUserIDClass:
    def __init__(self, id: str):
        self.id = id

# Dummy user ID
dummy_userid = '98df4ebb-1f64-487b-8705-9835acf0b407'

# Dummy user ID but with the id attribute for scan_docs_dir in the main script
DummyUserIDForMainScript = DummyUserIDClass(id=dummy_userid)

class SADMStatus(BaseModel):
    status: str

class SADMEventHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            log.debug(f"File created: {event.src_path}")
            self.process(event, "created")

    def on_modified(self, event):
        if not event.is_directory:
            log.debug(f"File modified: {event.src_path}")
            self.process(event, "modified")

    def on_deleted(self, event):
        if not event.is_directory:
            log.debug(f"File deleted: {event.src_path}")
            self.process(event, "deleted")

    def on_moved(self, event):
        if not event.is_directory:
            old_name = os.path.basename(event.src_path)
            new_name = os.path.basename(event.dest_path)
            log.debug(f"File moved from {event.src_path} to {event.dest_path}")
            self.process(event, "deleted", old_name, new_name)
            time.sleep(1)
            self.process(event, "created", old_name, new_name)

    def process(self, event, event_type, old_name=None, new_name=None):
        if event_type == "deleted":
            file_path = event.src_path
            file_name = os.path.basename(file_path)
            file_name_no_symbols = sanitize_filename(file_name)
            new_file_name = f"{file_name_no_symbols}"

            try:
                doc = Documents.get_doc_by_name(new_file_name)
                if doc:
                    db_result = Documents.delete_doc_by_name_only_from_db(new_file_name)
                    log.info(f"Document: '{new_file_name}' has been successfully removed")
                    log.debug(f"Document '{new_file_name}' SQL db removal Result: {db_result}")
                else:
                    log.debug(f"Document '{new_file_name}' not found in the SQL database.")
            except Exception as e:
                log.error(f"Error processing document '{new_file_name}': {e}")

        elif event_type in ["created", "modified"]:
            file_path = event.src_path if old_name is None else event.dest_path
            file_name = os.path.basename(file_path)
            file_name_no_symbols = sanitize_filename(file_name)
            new_file_name = f"{file_name_no_symbols}"

            try:
                with open(file_path, "rb") as f:
                    collection_name = calculate_sha256(f)[:63]
            except Exception as e:
                log.error(f"Error reading file '{file_path}': {e}")
                return

            log.debug(f"Transformed file name: '{new_file_name}'")
            log.debug(f"Generated collection name: '{collection_name}'")

            try:
                doc = Documents.get_doc_by_name(new_file_name)
                if doc:
                    db_result = Documents.delete_doc_by_name_only_from_db(new_file_name)
                    log.debug(f"Document '{new_file_name}' SQL db removal Result: {db_result}")
                else:
                    log.debug(f"Document '{new_file_name}' not found in the SQL database Proceeding to Recreation!")

                tags = extract_folders_after_data_docs(Path(file_path))
                file_content_type = mimetypes.guess_type(file_path)[0]
                loader, _ = get_loader(file_name, file_content_type, file_path)
                file_extension = os.path.splitext(file_name)[1].lstrip('.')

                try:
                    data = loader.load()
                except Exception as e:
                    log.error(f"Error loading file '{file_path}': {e}")
                    return

                try:
                    result = store_data_in_vector_db(data, collection_name)
                    if result:
                        # Added file extension to tags
                        tags.append(f".{file_extension}")

                        doc_form = DocumentForm(
                            collection_name=collection_name,
                            name=new_file_name,
                            title=file_name,
                            filename=file_name,
                            content=json.dumps({"tags": [{"name": name} for name in tags]}) if tags else "{}",
                            timestamp=int(time.time()),
                            location=DOCS_DIR_NAME
                        )
                        result = Documents.insert_new_doc(dummy_userid, doc_form)
                        log.debug(f"Document '{new_file_name}' processed and inserted to the vector db successfully.")
                        log.debug(f"Document insertion result: {result}")
                except Exception as e:
                    log.error(f"Error processing file '{file_name_no_symbols}': {e}")
            except Exception as e:
                log.error(f"Unexpected error during file processing for '{file_name_no_symbols}': {e}")

class SelfAwareDocumentMonitoring:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SelfAwareDocumentMonitoring, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):  # Ensure init only runs once
            self.stop_event = Event()
            self.monitoring_thread = None
            self.observer = None
            self.initialized = True

    def ensure_location_column_exists(self):
        """Ensure the 'location' column exists in the 'document' table and update existing documents."""
        if self.read_from_sadm_config_is_location_exists_in_db():
            log.info("according to the configuration file location column already exists in the database. Skipping redundant operation...")
            return
        
        try:
            with get_db() as db:
                # Check if 'location' column exists
                result = db.execute(text("PRAGMA table_info(document);"))
                columns = [row[1] for row in result.fetchall()]  # row[1] is the column name
                log.debug(f"Columns in 'document' table: {columns}")

                if 'location' not in columns:
                    # Column does not exist, add it
                    db.execute(text("ALTER TABLE document ADD COLUMN location TEXT"))
                    db.commit()
                    log.info("Added 'location' column to 'document' table.")
                else:
                    log.info("'location' column already exists in 'document' table.")
                
                # Update location for existing documents
                documents = db.query(Document).all()
                log.debug(f"Found {len(documents)} documents to process.")
                for document in documents:
                    if document.location:
                        # Skip documents that already have a location
                        continue
                    
                    # Determine the location based on filename 
                    file_path = locate_document_in_filesystem(UPLOAD_DIR, document.filename)
                    if file_path:
                        new_location = UPLOADS_DIR_NAME
                    else:
                        file_path = locate_document_in_filesystem(DOCS_DIR, document.filename)
                        if file_path:
                            new_location = DOCS_DIR_NAME
                        else:
                            new_location = None
                    
                    if new_location:
                        document.location = new_location
                        db.commit()
                        log.info(f"Updated location for document '{document.name}' to '{new_location}'.")
                                
                # Set is_location_exists_in_db to True after processing
                CONFIG_DATA["SADM"]["is_location_exists_in_db"] = True
                try:
                    with CONFIG_FILE.open("w") as file:
                        json.dump(CONFIG_DATA, file, indent=4)
                    log.debug("Set 'is_location_exists_in_db' to 'True' in the configuration.")
                except Exception as e:
                    log.error(f"Error writing to config file: {e}")

        except Exception as e:
            log.error(f"Error while checking or updating 'location' column: {e}")

    def remove_missing_files_from_db(self):
        """Check if files in the 'document' table exist in the filesystem and remove those that do not."""
        try:
            with get_db() as db:
                # Get all documents from the database
                documents = db.query(Document).all()
                log.info(f"Found {len(documents)} documents to check for missing files.")

                for document in documents:
                    filename = document.filename
                    if not filename:
                        log.warning(f"Document ID {document.id} has an empty filename. Skipping.")
                        continue
                    
                    # Search for the file in both directories
                    file_path_upload = locate_document_in_filesystem(UPLOAD_DIR, filename)
                    file_path_docs = locate_document_in_filesystem(DOCS_DIR, filename)
                    
                    # Check if file exists in either directory
                    if not file_path_upload and not file_path_docs:
                        # File does not exist in either directory, remove from database
                        db_result = Documents.delete_doc_by_name_only_from_db(document.name)
                        log.info(f"File '{filename}' not found. Document '{document.name}' removed from SQL database. Result: {db_result}")
                    else:
                        log.info(f"File '{filename}' exists in filesystem. No action needed.")

        except Exception as e:
            log.error(f"Error while checking and removing missing files: {e}")


    def read_sadm_config(self):
        return CONFIG_DATA.get("SADM", {})

    def read_sadm_state(self):
        return CONFIG_DATA.get("SADM", {}).get("state", "disabled")
    
    def read_from_sadm_config_is_location_exists_in_db(self):
        """Check if 'is_location_exists_in_db' property is true or false. Create it with default 'false' if it doesn't exist."""
        if "SADM" not in CONFIG_DATA:
            CONFIG_DATA["SADM"] = {}

        if "is_location_exists_in_db" not in CONFIG_DATA["SADM"]:
            CONFIG_DATA["SADM"]["is_location_exists_in_db"] = False
            try:
                with CONFIG_FILE.open("w") as file:
                    json.dump(CONFIG_DATA, file, indent=4)
                log.debug("Added 'is_location_exists_in_db' with default value 'False' to the configuration.")
            except Exception as e:
                log.error(f"Error writing to config file: {e}")

        return CONFIG_DATA["SADM"]["is_location_exists_in_db"]

    def write_sadm_state(self, state: str):
        if "SADM" not in CONFIG_DATA:
            CONFIG_DATA["SADM"] = {}
        CONFIG_DATA["SADM"]["state"] = state
        try:
            with CONFIG_FILE.open("w") as file:
                json.dump(CONFIG_DATA, file, indent=4)
        except Exception as e:
            log.error(f"Error writing to config file: {e}")

    def start_monitoring_thread(self, path: str):
        if not path:
            log.error("Invalid path for monitoring.")
            return
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            log.info("Self-Aware Document Monitoring thread is already active.")
            return

        self.stop_event.clear()
        self.monitoring_thread = Thread(target=self.start_monitoring, args=(path,))
        self.monitoring_thread.start()
        self.remove_missing_files_from_db()

    def start_monitoring(self, path: str):
        self.observer = Observer()
        event_handler = SADMEventHandler()
        self.observer.schedule(event_handler, path, recursive=True)
        self.observer.start()
        log.info("Self-Aware Document Monitoring Monitoring has been started!")

        try:
            while not self.stop_event.is_set():
                time.sleep(1)
        except Exception as e:
            log.error(f"Self-Aware Document Monitoring Monitoring thread error: {e}")
        finally:
            self.observer.stop()
            self.observer.join()
            log.info("Self-Aware Document Monitoring has been stopped!")

    def stop_monitoring_thread(self):
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            log.info("Stopping Self-Aware Document Monitoring thread...")
            self.stop_event.set()
            self.monitoring_thread.join(timeout=10)
            if self.monitoring_thread.is_alive():
                log.warning("Self-Aware Document Monitoring Monitoring thread did not stop within the timeout period.")
            self.monitoring_thread = None
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None

