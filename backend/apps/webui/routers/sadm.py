# Unfortunately, an attempt to split the Self-Aware Document Monitoring (SADM) script into two separate files (one for definitions and classes (models),
# and one for the APIRouter (routers)) resulted in issues with starting/stopping and tracking the monitoring thread's status. 
# This restructuring caused problems in determining whether the thread was running correctly. 
# As a result, I made a single-file implementation to maintain reliable thread management. 

import sys
import time
import logging
import os

from threading import Event, Thread
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import mimetypes

from fastapi import FastAPI, HTTPException, Depends, APIRouter
from pydantic import BaseModel

from apps.webui.models.documents import (
    Documents,
    DocumentForm,
)  

from apps.rag.main import (
    store_data_in_vector_db,
    get_loader,
    scan_docs_dir,
) 
from utils.misc import (
    calculate_sha256,
    extract_folders_after_data_docs,
)  

from config import (
    DOCS_DIR,
    SRC_LOG_LEVELS,
    GLOBAL_LOG_LEVEL
)  

from utils.utils import (
    get_admin_user,
)


# Logging setup
logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


# Global stop event and monitoring thread
stop_event = Event()
monitoring_thread = None

# File to persist monitoring state
STATE_FILE = ".monitoring_state"

# class for dummy userid
class DummyUserIDClass:
    def __init__(self, id: str):
        self.id = id

# Dummy user ID
dummy_userid = '98df4ebb-1f64-487b-8705-9835acf0b407'

# Dummy user ID but with the id attribute for scan_docs_dir in the main script
DummyUserIDForMainScript = DummyUserIDClass(id=dummy_userid)

def read_state():
    """Read monitoring state from file."""
    if not os.path.exists(STATE_FILE):
        return "disabled"
    with open(STATE_FILE, "r") as file:
        state = file.read().strip()
    return state

def write_state(state: str):
    """Write monitoring state to file."""
    with open(STATE_FILE, "w") as file:
        file.write(state)

class MonitoringStatus(BaseModel):
    status: str

class DocEventHandler(FileSystemEventHandler):
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
            file_name_with_ext = os.path.basename(file_path)
            file_name_no_ext, file_ext = os.path.splitext(file_name_with_ext)
            file_name_no_symbols = file_name_no_ext.lower().replace(" ", "-").replace(".", "")
            new_file_name = f"{file_name_no_symbols}{file_ext[1:]}"

            try:
                result = Documents.delete_doc_by_name(new_file_name)
                log.info(f"Document '{new_file_name}' removed from the database. Result: {result}")
            except Exception as e:
                log.error(f"Error deleting document '{new_file_name}': {e}")

        elif event_type in ["created", "modified"]:
            file_path = event.src_path if old_name is None else event.dest_path
            file_name_with_ext = os.path.basename(file_path)
            file_name_no_ext, file_ext = os.path.splitext(file_name_with_ext)
            file_name_no_symbols = file_name_no_ext.lower().replace(" ", "-").replace(".", "")
            new_file_name = f"{file_name_no_symbols}{file_ext[1:]}"

            try:
                with open(file_path, "rb") as f:
                    collection_name = calculate_sha256(f)[:63]
            except Exception as e:
                log.error(f"Error reading file '{file_path}': {e}")
                return

            log.debug(f"Transformed file name: '{new_file_name}'")
            log.debug(f"Generated collection name: '{collection_name}'")

            try:
                if Documents.get_doc_by_name(new_file_name):
                    log.info(f"Document '{new_file_name}' exists. Proceeding to delete and recreate.")
                    Documents.delete_doc_by_name(new_file_name)

                tags = extract_folders_after_data_docs(Path(file_path))
                file_content_type = mimetypes.guess_type(file_path)[0]
                loader, _ = get_loader(file_name_with_ext, file_content_type, file_path)

                try:
                    data = loader.load()
                except Exception as e:
                    log.error(f"Error loading file '{file_path}': {e}")
                    return

                try:
                    result = store_data_in_vector_db(data, collection_name)
                    if result:
                        doc_form = DocumentForm(
                            collection_name=collection_name,
                            name=new_file_name,
                            title=file_name_with_ext,
                            filename=file_name_with_ext,
                            timestamp=int(time.time()),
                        )
                        result = Documents.insert_new_doc(dummy_userid, doc_form)
                        log.info(f"Document '{new_file_name}' processed and inserted successfully.")
                        log.debug(f"Document insertion result: {result}")
                except Exception as e:
                    log.error(f"Error processing file '{file_name_no_symbols}': {e}")

            except Exception as e:
                log.error(f"Unexpected error during file processing for '{file_name_no_symbols}': {e}")


def start_monitoring_thread(path: str, stop_event: Event):
    global monitoring_thread

    if not path or not isinstance(stop_event, Event):
        log.error("Invalid arguments: path must be a non-empty string and stop_event must be an instance of Event.")
        return

    if monitoring_thread and monitoring_thread.is_alive():
        log.info("Self-Aware Document Monitoring thread is already active.")
        return

    log.info("Initiating Self-Aware Document Monitoring thread...")
    
    stop_event.clear()
    
    try:
        monitoring_thread = Thread(target=start_monitoring, args=(path, stop_event))
        monitoring_thread.start()
        log.info("Self-Aware Document Monitoring thread started successfully.")
    except Exception as e:
        log.error(f"Failed to start Self-Aware Document Monitoring thread: {e}")

def start_monitoring(path: str, stop_event: Event):
    observer = Observer()
    event_handler = DocEventHandler()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    log.info("Self-Aware Document Monitoring is now active.")

    try:
        while not stop_event.is_set():
            time.sleep(1)
    except Exception as e:
        log.error(f"Self-Aware Document Monitoring thread encountered an issue: {e}")
    finally:
        log.debug("Stopping Self-Aware Document Monitoring...")
        observer.stop()
        observer.join()
        log.debug("Self-Aware Document Monitoring stopped successfully.")
        
# FastAPI Router application setup
router = APIRouter()

@router.post("/enable")
def enable_monitoring_route(user=Depends(get_admin_user)):
    """
    Enable and start the Self-Aware Document Monitoring process.
    """
    if read_state() == "enabled":
        return {"message": "Self-Aware Document Monitoring is already enabled"}

    try:
        write_state("enabled")
        
        log.info("Scanning for new Documents...")

        if DOCS_DIR:
            log.debug(f"Starting scan of directory: {DOCS_DIR}")
            try:
                scan_docs_dir(user=user)
                log.info("Scan completed successfully!")
            except Exception as scan_error:
                log.error(f"Error during scan_docs_dir execution: {scan_error}")
                raise HTTPException(status_code=500, detail=f"Failed to scan documents: {scan_error}")
        else:
            log.warning("DOCS_DIR is not defined. Skipping scan_docs_dir function.")
        
        start_monitoring_thread(DOCS_DIR, stop_event)
        return {"message": "Self-Aware Document Monitoring has been enabled and is now Active"}
    except Exception as e:
        log.error(f"Error enabling Self-Aware Document Monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to enable monitoring: {e}")

@router.post("/disable")
def disable_monitoring_route(user=Depends(get_admin_user)):
    """
    Disable and stop the Self-Aware Document Monitoring process.
    """
    if read_state() == "disabled":
        return {"message": "Self-Aware Document Monitoring is already disabled"}

    global monitoring_thread
    try:
        write_state("disabled")
        if monitoring_thread and monitoring_thread.is_alive():
            stop_event.set()
            log.info("Self-Aware Document Monitoring has been disabled and is now inactive.")
            monitoring_thread.join(timeout=10)
            if monitoring_thread.is_alive():
                log.warning("Self-Aware Document Monitoring thread did not stop within the timeout period.")
        return {"message": "Self-Aware Document Monitoring has been disabled and is now inactive"}
    except Exception as e:
        log.error(f"Error disabling Self-Aware Document Monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to disable monitoring: {e}")
    finally:
        monitoring_thread = None

@router.get("/status", response_model=MonitoringStatus)
def status_route(user=Depends(get_admin_user)):
    """
    Get the status of the Self-Aware Document Monitoring process.
    """
    state = read_state()
    status = "running" if (state == "enabled" and monitoring_thread and monitoring_thread.is_alive()) else "disabled"
    
    log.debug(f"Self-Aware Document Monitoring current status: {status}")
    return {"status": status}
