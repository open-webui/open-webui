"""
Centralized file cleanup utility for complete file deletion.

This module provides functions to cleanly delete files from:
- All knowledge collections (vector DB and metadata)
- File-specific collections in vector DB
- SQL database (works with both SQLite and PostgreSQL)
- Physical file storage

Database Compatibility:
- SQL Database: Works with both SQLite and PostgreSQL via SQLAlchemy ORM
- Vector Database: Works with Chroma (SQLite-based), pgvector (PostgreSQL),
  Milvus, Qdrant, and OpenSearch via VECTOR_DB_CLIENT abstraction
- When using pgvector, it can use the same PostgreSQL database as the main SQL database
"""

import logging
from typing import Optional, Tuple, Dict

from open_webui.models.files import Files
from open_webui.models.knowledge import Knowledges
from open_webui.retrieval.vector.connector import VECTOR_DB_CLIENT
from open_webui.storage.provider import Storage

log = logging.getLogger(__name__)


def cleanup_file_completely(
    file_id: str,
    exclude_knowledge_id: Optional[str] = None,
    delete_physical_file: bool = True,
) -> Tuple[bool, Dict]:
    """
    Completely clean up a file from all systems.
    
    This function performs a complete cleanup of a file:
    1. Removes file from all knowledge collections (vector DB and metadata)
    2. Deletes file-specific collection from vector DB
    3. Deletes file from SQL database
    4. Deletes physical file from storage
    
    Args:
        file_id: The ID of the file to clean up
        exclude_knowledge_id: Optional knowledge base ID to exclude from cleanup
                             (used when removing from a specific knowledge base only)
        delete_physical_file: Whether to delete the physical file (default: True)
        
    Returns:
        Tuple of (success: bool, details: dict)
        details contains:
            - knowledge_bases_updated: list of knowledge base IDs updated
            - vector_db_cleaned: bool
            - file_collection_deleted: bool
            - sql_deleted: bool
            - physical_file_deleted: bool
            - errors: list of error messages
    """
    details = {
        "knowledge_bases_updated": [],
        "vector_db_cleaned": False,
        "file_collection_deleted": False,
        "sql_deleted": False,
        "physical_file_deleted": False,
        "errors": [],
    }
    
    # Get file info first (needed for physical file deletion)
    file = Files.get_file_by_id(file_id)
    if not file:
        details["errors"].append(f"File {file_id} not found in database")
        log.warning(f"File {file_id} not found, cannot perform cleanup")
        return False, details
    
    log.info(f"Starting complete cleanup for file {file_id} (filename: {file.filename})")
    
    # Step 1: Find all knowledge bases using this file
    knowledge_bases = Knowledges.get_knowledge_bases_by_file_id(file_id)
    
    if exclude_knowledge_id:
        # Filter out the excluded knowledge base
        knowledge_bases = [
            kb for kb in knowledge_bases if kb.id != exclude_knowledge_id
        ]
        log.info(
            f"Found {len(knowledge_bases)} knowledge bases using file {file_id} "
            f"(excluding {exclude_knowledge_id})"
        )
    else:
        log.info(f"Found {len(knowledge_bases)} knowledge bases using file {file_id}")
    
    # Step 2: Remove from all knowledge collections in vector DB
    vector_db_success = True
    for knowledge in knowledge_bases:
        try:
            log.info(
                f"Removing file {file_id} from vector DB collection: {knowledge.id}"
            )
            VECTOR_DB_CLIENT.delete(
                collection_name=knowledge.id, filter={"file_id": file_id}
            )
            details["knowledge_bases_updated"].append(knowledge.id)
        except Exception as e:
            error_msg = f"Error deleting from vector DB collection {knowledge.id}: {e}"
            log.exception(error_msg)
            details["errors"].append(error_msg)
            vector_db_success = False
    
    details["vector_db_cleaned"] = vector_db_success
    
    # Step 3: Remove from all knowledge bases' file_ids lists
    if knowledge_bases:
        try:
            log.info(f"Removing file {file_id} from {len(knowledge_bases)} knowledge base metadata")
            for knowledge in knowledge_bases:
                if knowledge.data and isinstance(knowledge.data, dict):
                    file_ids = knowledge.data.get("file_ids", [])
                    if isinstance(file_ids, list) and file_id in file_ids:
                        file_ids.remove(file_id)
                        knowledge.data["file_ids"] = file_ids
                        
                        # Update the knowledge base
                        updated = Knowledges.update_knowledge_data_by_id(
                            knowledge.id, knowledge.data
                        )
                        if not updated:
                            error_msg = (
                                f"Failed to remove file {file_id} from "
                                f"knowledge base {knowledge.id} metadata"
                            )
                            log.error(error_msg)
                            details["errors"].append(error_msg)
        except Exception as e:
            error_msg = f"Error removing file from knowledge base metadata: {e}"
            log.exception(error_msg)
            details["errors"].append(error_msg)
    
    # Step 4: Delete file-specific collection from vector DB
    file_collection = f"file-{file_id}"
    try:
        if VECTOR_DB_CLIENT.has_collection(collection_name=file_collection):
            log.info(f"Deleting file collection: {file_collection}")
            VECTOR_DB_CLIENT.delete_collection(collection_name=file_collection)
            details["file_collection_deleted"] = True
        else:
            log.debug(f"File collection {file_collection} does not exist, skipping")
            details["file_collection_deleted"] = True  # Consider it success if it doesn't exist
    except Exception as e:
        error_msg = f"Error deleting file collection {file_collection}: {e}"
        log.exception(error_msg)
        details["errors"].append(error_msg)
    
    # Step 5: Delete from SQL database
    try:
        log.info(f"Deleting file {file_id} from SQL database")
        sql_result = Files.delete_file_by_id(file_id)
        if sql_result:
            details["sql_deleted"] = True
        else:
            error_msg = f"Failed to delete file {file_id} from SQL database"
            log.error(error_msg)
            details["errors"].append(error_msg)
    except Exception as e:
        error_msg = f"Error deleting file {file_id} from SQL database: {e}"
        log.exception(error_msg)
        details["errors"].append(error_msg)
    
    # Step 6: Delete physical file (only if delete_physical_file is True)
    if delete_physical_file and file.path:
        try:
            log.info(f"Deleting physical file: {file.path}")
            Storage.delete_file(file.path)
            details["physical_file_deleted"] = True
        except Exception as e:
            error_msg = f"Error deleting physical file {file.path}: {e}"
            log.exception(error_msg)
            details["errors"].append(error_msg)
    elif not delete_physical_file:
        log.info(f"Skipping physical file deletion for {file_id} (delete_physical_file=False)")
        details["physical_file_deleted"] = None  # Indicate it was skipped
    elif not file.path:
        log.warning(f"File {file_id} has no path, cannot delete physical file")
        details["errors"].append(f"File {file_id} has no path stored")
    
    # Determine overall success
    # Consider it successful if critical operations succeeded
    # (vector DB cleanup and SQL deletion are critical)
    success = (
        details["sql_deleted"]
        and details["vector_db_cleaned"]
        and (details["file_collection_deleted"] is not False)
    )
    
    if success:
        log.info(
            f"Successfully completed cleanup for file {file_id}. "
            f"Updated {len(details['knowledge_bases_updated'])} knowledge bases"
        )
    else:
        log.warning(
            f"Cleanup for file {file_id} completed with errors: {details['errors']}"
        )
    
    return success, details


def cleanup_file_from_knowledge_only(
    file_id: str, knowledge_id: str
) -> Tuple[bool, Dict]:
    """
    Remove a file from a specific knowledge collection only.
    
    This function removes a file from a single knowledge collection without
    deleting the file itself. Used when a file is in multiple knowledge collections.
    
    Args:
        file_id: The ID of the file to remove
        knowledge_id: The knowledge base ID to remove the file from
        
    Returns:
        Tuple of (success: bool, details: dict)
    """
    details = {
        "vector_db_cleaned": False,
        "knowledge_base_updated": False,
        "errors": [],
    }
    
    log.info(
        f"Removing file {file_id} from knowledge collection {knowledge_id} only"
    )
    
    # Step 1: Remove from vector DB collection
    try:
        log.info(
            f"Removing file {file_id} from vector DB collection: {knowledge_id}"
        )
        VECTOR_DB_CLIENT.delete(
            collection_name=knowledge_id, filter={"file_id": file_id}
        )
        details["vector_db_cleaned"] = True
    except Exception as e:
        error_msg = f"Error deleting from vector DB collection {knowledge_id}: {e}"
        log.exception(error_msg)
        details["errors"].append(error_msg)
    
    # Step 2: Remove from knowledge base's file_ids list
    try:
        knowledge = Knowledges.get_knowledge_by_id(knowledge_id)
        if knowledge and knowledge.data and isinstance(knowledge.data, dict):
            file_ids = knowledge.data.get("file_ids", [])
            if isinstance(file_ids, list) and file_id in file_ids:
                file_ids.remove(file_id)
                knowledge.data["file_ids"] = file_ids
                
                updated = Knowledges.update_knowledge_data_by_id(
                    knowledge_id, knowledge.data
                )
                if updated:
                    details["knowledge_base_updated"] = True
                    log.info(
                        f"Removed file {file_id} from knowledge base {knowledge_id} metadata"
                    )
                else:
                    error_msg = (
                        f"Failed to remove file {file_id} from "
                        f"knowledge base {knowledge_id} metadata"
                    )
                    log.error(error_msg)
                    details["errors"].append(error_msg)
            else:
                log.warning(
                    f"File {file_id} not found in knowledge base {knowledge_id} file_ids list"
                )
                details["knowledge_base_updated"] = True  # Already removed
        else:
            error_msg = f"Knowledge base {knowledge_id} not found"
            log.error(error_msg)
            details["errors"].append(error_msg)
    except Exception as e:
        error_msg = f"Error removing file from knowledge base metadata: {e}"
        log.exception(error_msg)
        details["errors"].append(error_msg)
    
    success = details["vector_db_cleaned"] and details["knowledge_base_updated"]
    
    if success:
        log.info(
            f"Successfully removed file {file_id} from knowledge collection {knowledge_id}"
        )
    else:
        log.warning(
            f"Removal of file {file_id} from knowledge collection {knowledge_id} "
            f"completed with errors: {details['errors']}"
        )
    
    return success, details

