import logging
import time
import os
import shutil
import json
import re
import sqlite3
from typing import Optional, Set, Union
from pathlib import Path
from abc import ABC, abstractmethod

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text

from open_webui.utils.auth import get_admin_user
from open_webui.models.users import Users
from open_webui.models.chats import Chats
from open_webui.models.files import Files
from open_webui.models.notes import Notes
from open_webui.models.prompts import Prompts
from open_webui.models.models import Models
from open_webui.models.knowledge import Knowledges
from open_webui.models.functions import Functions
from open_webui.models.tools import Tools
from open_webui.models.folders import Folders
from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT, VECTOR_DB
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.config import CACHE_DIR
from open_webui.internal.db import get_db

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()


class JSONFileIDExtractor:
    """
    Utility for extracting and validating file IDs from JSON content.

    Replaces duplicated regex compilation and validation logic used throughout
    the file scanning functions. Compiles patterns once for better performance.
    """

    # Compile patterns once at class level for performance
    _FILE_ID_PATTERN = re.compile(
        r'"id":\s*"([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})"'
    )
    _URL_PATTERN = re.compile(
        r"/api/v1/files/([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})"
    )

    @classmethod
    def extract_and_validate_file_ids(cls, json_string: str) -> Set[str]:
        """
        Extract file IDs from JSON string and validate they exist in database.

        Args:
            json_string: JSON content as string (or any string to scan)

        Returns:
            Set of validated file IDs that exist in the Files table

        Note:
            This method replaces the repeated pattern of:
            1. Compiling the same regex patterns
            2. Extracting potential IDs
            3. Validating each ID exists via Files.get_file_by_id()
            4. Building a set of validated IDs
        """
        validated_ids = set()

        # Extract potential IDs using both patterns
        potential_ids = []
        potential_ids.extend(cls._FILE_ID_PATTERN.findall(json_string))
        potential_ids.extend(cls._URL_PATTERN.findall(json_string))

        # Validate each ID exists in database
        for file_id in potential_ids:
            if Files.get_file_by_id(file_id):
                validated_ids.add(file_id)

        return validated_ids


class VectorDatabaseCleaner(ABC):
    """
    Abstract base class for vector database cleanup operations.

    This interface defines the contract that all vector database implementations
    must follow. Community contributors can implement support for new vector
    databases by extending this class.

    Supported operations:
    - Count orphaned collections (for dry-run preview)
    - Cleanup orphaned collections (actual deletion)
    - Delete individual collections by name
    """

    @abstractmethod
    def count_orphaned_collections(
        self, active_file_ids: Set[str], active_kb_ids: Set[str]
    ) -> int:
        """
        Count how many orphaned vector collections would be deleted.

        Args:
            active_file_ids: Set of file IDs that are still referenced
            active_kb_ids: Set of knowledge base IDs that are still active

        Returns:
            Number of orphaned collections that would be deleted
        """
        pass

    @abstractmethod
    def cleanup_orphaned_collections(
        self, active_file_ids: Set[str], active_kb_ids: Set[str]
    ) -> int:
        """
        Actually delete orphaned vector collections.

        Args:
            active_file_ids: Set of file IDs that are still referenced
            active_kb_ids: Set of knowledge base IDs that are still active

        Returns:
            Number of collections that were actually deleted
        """
        pass

    @abstractmethod
    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a specific vector collection by name.

        Args:
            collection_name: Name of the collection to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        pass


class ChromaDatabaseCleaner(VectorDatabaseCleaner):
    """
    ChromaDB-specific implementation of vector database cleanup.

    Handles ChromaDB's specific storage structure including:
    - SQLite metadata database (chroma.sqlite3)
    - Physical vector storage directories
    - Collection name to UUID mapping
    - Segment-based storage architecture
    """

    def __init__(self):
        self.vector_dir = Path(CACHE_DIR).parent / "vector_db"
        self.chroma_db_path = self.vector_dir / "chroma.sqlite3"

    def count_orphaned_collections(
        self, active_file_ids: Set[str], active_kb_ids: Set[str]
    ) -> int:
        """Count orphaned ChromaDB collections for preview."""
        if not self.chroma_db_path.exists():
            return 0

        expected_collections = self._build_expected_collections(
            active_file_ids, active_kb_ids
        )
        uuid_to_collection = self._get_collection_mappings()

        count = 0
        try:
            for collection_dir in self.vector_dir.iterdir():
                if not collection_dir.is_dir() or collection_dir.name.startswith("."):
                    continue

                dir_uuid = collection_dir.name
                collection_name = uuid_to_collection.get(dir_uuid)

                if (
                    collection_name is None
                    or collection_name not in expected_collections
                ):
                    count += 1
        except Exception as e:
            log.debug(f"Error counting orphaned ChromaDB collections: {e}")

        return count

    def cleanup_orphaned_collections(
        self, active_file_ids: Set[str], active_kb_ids: Set[str]
    ) -> int:
        """Actually delete orphaned ChromaDB collections and database records."""
        if not self.chroma_db_path.exists():
            return 0

        expected_collections = self._build_expected_collections(
            active_file_ids, active_kb_ids
        )
        uuid_to_collection = self._get_collection_mappings()

        deleted_count = 0

        # First, clean up orphaned database records
        try:
            deleted_count += self._cleanup_orphaned_database_records()
        except Exception as e:
            log.error(f"Error cleaning orphaned database records: {e}")

        # Then clean up physical directories
        try:
            for collection_dir in self.vector_dir.iterdir():
                if not collection_dir.is_dir() or collection_dir.name.startswith("."):
                    continue

                dir_uuid = collection_dir.name
                collection_name = uuid_to_collection.get(dir_uuid)

                # Delete if no corresponding collection name or collection is not expected
                if collection_name is None:
                    try:
                        shutil.rmtree(collection_dir)
                        deleted_count += 1
                        log.debug(f"Deleted orphaned ChromaDB directory: {dir_uuid}")
                    except Exception as e:
                        log.error(
                            f"Failed to delete orphaned directory {dir_uuid}: {e}"
                        )

                elif collection_name not in expected_collections:
                    try:
                        shutil.rmtree(collection_dir)
                        deleted_count += 1
                        log.debug(
                            f"Deleted orphaned ChromaDB collection: {collection_name}"
                        )
                    except Exception as e:
                        log.error(
                            f"Failed to delete collection directory {dir_uuid}: {e}"
                        )

        except Exception as e:
            log.error(f"Error cleaning ChromaDB collections: {e}")

        if deleted_count > 0:
            log.info(f"Deleted {deleted_count} orphaned ChromaDB collections")

        return deleted_count

    def delete_collection(self, collection_name: str) -> bool:
        """Delete a specific ChromaDB collection by name."""
        try:
            # Attempt to delete via ChromaDB client first
            try:
                VECTOR_DB_CLIENT.delete_collection(collection_name=collection_name)
                log.debug(f"Deleted ChromaDB collection via client: {collection_name}")
            except Exception as e:
                log.debug(
                    f"Collection {collection_name} may not exist in ChromaDB: {e}"
                )

            # Also clean up physical directory if it exists
            # Note: ChromaDB uses UUID directories, so we'd need to map collection name to UUID
            # For now, let the cleanup_orphaned_collections method handle physical cleanup
            return True

        except Exception as e:
            log.error(f"Error deleting ChromaDB collection {collection_name}: {e}")
            return False

    def _build_expected_collections(
        self, active_file_ids: Set[str], active_kb_ids: Set[str]
    ) -> Set[str]:
        """Build set of collection names that should exist."""
        expected_collections = set()

        # File collections use "file-{id}" pattern
        for file_id in active_file_ids:
            expected_collections.add(f"file-{file_id}")

        # Knowledge base collections use the KB ID directly
        for kb_id in active_kb_ids:
            expected_collections.add(kb_id)

        return expected_collections

    def _get_collection_mappings(self) -> dict:
        """Get mapping from ChromaDB directory UUID to collection name."""
        uuid_to_collection = {}

        try:
            with sqlite3.connect(str(self.chroma_db_path)) as conn:
                # First, get collection ID to name mapping
                collection_id_to_name = {}
                cursor = conn.execute("SELECT id, name FROM collections")
                for collection_id, collection_name in cursor.fetchall():
                    collection_id_to_name[collection_id] = collection_name

                # Then, get segment ID to collection mapping (segments are the directory UUIDs)
                cursor = conn.execute(
                    "SELECT id, collection FROM segments WHERE scope = 'VECTOR'"
                )
                for segment_id, collection_id in cursor.fetchall():
                    if collection_id in collection_id_to_name:
                        collection_name = collection_id_to_name[collection_id]
                        uuid_to_collection[segment_id] = collection_name

            log.debug(f"Found {len(uuid_to_collection)} ChromaDB vector segments")

        except Exception as e:
            log.error(f"Error reading ChromaDB metadata: {e}")

        return uuid_to_collection

    def _cleanup_orphaned_database_records(self) -> int:
        """
        Clean up orphaned database records that ChromaDB's delete_collection() method leaves behind.

        This is the key fix for the file size issue - ChromaDB doesn't properly cascade
        deletions, leaving orphaned embeddings, metadata, and FTS data that prevent
        VACUUM from reclaiming space.

        Returns:
            Number of orphaned records cleaned up
        """
        cleaned_records = 0

        try:
            with sqlite3.connect(str(self.chroma_db_path)) as conn:
                # Count orphaned records before cleanup
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) FROM embeddings 
                    WHERE segment_id NOT IN (SELECT id FROM segments)
                """
                )
                orphaned_embeddings = cursor.fetchone()[0]

                if orphaned_embeddings == 0:
                    log.debug("No orphaned ChromaDB embeddings found")
                    return 0

                log.info(
                    f"Cleaning up {orphaned_embeddings} orphaned ChromaDB embeddings and related data"
                )

                # Delete orphaned embedding_metadata first (child records)
                cursor = conn.execute(
                    """
                    DELETE FROM embedding_metadata 
                    WHERE id IN (
                        SELECT id FROM embeddings 
                        WHERE segment_id NOT IN (SELECT id FROM segments)
                    )
                """
                )
                metadata_deleted = cursor.rowcount
                cleaned_records += metadata_deleted

                # Delete orphaned embeddings
                cursor = conn.execute(
                    """
                    DELETE FROM embeddings 
                    WHERE segment_id NOT IN (SELECT id FROM segments)
                """
                )
                embeddings_deleted = cursor.rowcount
                cleaned_records += embeddings_deleted

                # Selectively clean FTS while preserving active content
                fts_cleaned = self._cleanup_fts_selectively(conn)
                log.info(f"FTS cleanup: preserved {fts_cleaned} valid text entries")

                # Clean up orphaned collection and segment metadata
                cursor = conn.execute(
                    """
                    DELETE FROM collection_metadata 
                    WHERE collection_id NOT IN (SELECT id FROM collections)
                """
                )
                collection_meta_deleted = cursor.rowcount
                cleaned_records += collection_meta_deleted

                cursor = conn.execute(
                    """
                    DELETE FROM segment_metadata 
                    WHERE segment_id NOT IN (SELECT id FROM segments)
                """
                )
                segment_meta_deleted = cursor.rowcount
                cleaned_records += segment_meta_deleted

                # Clean up orphaned max_seq_id records
                cursor = conn.execute(
                    """
                    DELETE FROM max_seq_id 
                    WHERE segment_id NOT IN (SELECT id FROM segments)
                """
                )
                seq_id_deleted = cursor.rowcount
                cleaned_records += seq_id_deleted

                # Force FTS index rebuild - this is crucial for VACUUM to work properly
                conn.execute(
                    "INSERT INTO embedding_fulltext_search(embedding_fulltext_search) VALUES('rebuild')"
                )

                # Commit changes
                conn.commit()

                log.info(
                    f"ChromaDB cleanup: {embeddings_deleted} embeddings, {metadata_deleted} metadata, "
                    f"{collection_meta_deleted} collection metadata, {segment_meta_deleted} segment metadata, "
                    f"{seq_id_deleted} sequence IDs"
                )

        except Exception as e:
            log.error(f"Error cleaning orphaned ChromaDB database records: {e}")
            raise

        return cleaned_records

    def _cleanup_fts_selectively(self, conn) -> int:
        """
        Selectively clean FTS content with atomic operations, preserving only data from active embeddings.

        This method prevents destroying valid search data by:
        1. Creating and validating temporary table with valid content
        2. Using atomic transactions for DELETE/INSERT operations
        3. Rolling back on failure to preserve existing data
        4. Conservative fallback: skip FTS cleanup if validation fails

        Returns:
            Number of valid FTS entries preserved, or -1 if FTS cleanup was skipped
        """
        try:
            # Step 1: Create temporary table with valid content
            conn.execute(
                """
                CREATE TEMPORARY TABLE temp_valid_fts AS
                SELECT DISTINCT em.string_value 
                FROM embedding_metadata em
                JOIN embeddings e ON em.id = e.id  
                JOIN segments s ON e.segment_id = s.id
                WHERE em.string_value IS NOT NULL 
                  AND em.string_value != ''
            """
            )

            # Step 2: Validate temp table creation and count records
            cursor = conn.execute("SELECT COUNT(*) FROM temp_valid_fts")
            valid_count = cursor.fetchone()[0]

            # Step 3: Validate temp table is accessible
            try:
                conn.execute("SELECT 1 FROM temp_valid_fts LIMIT 1")
                temp_table_ok = True
            except Exception:
                temp_table_ok = False

            # Step 4: Only proceed if validation passed
            if not temp_table_ok:
                log.warning(
                    "FTS temp table validation failed, skipping FTS cleanup for safety"
                )
                conn.execute("DROP TABLE IF EXISTS temp_valid_fts")
                return -1  # Signal FTS cleanup was skipped

            # Step 5: FTS cleanup operation (already in transaction)
            try:
                # Delete all FTS content
                conn.execute("DELETE FROM embedding_fulltext_search")

                # Re-insert only valid content if any exists
                if valid_count > 0:
                    conn.execute(
                        """
                        INSERT INTO embedding_fulltext_search(string_value) 
                        SELECT string_value FROM temp_valid_fts
                    """
                    )
                    log.debug(f"Preserved {valid_count} valid FTS entries")
                else:
                    log.debug("No valid FTS content found, cleared all entries")

                # Rebuild FTS index
                conn.execute(
                    "INSERT INTO embedding_fulltext_search(embedding_fulltext_search) VALUES('rebuild')"
                )

            except Exception as e:
                log.error(f"FTS cleanup failed: {e}")
                conn.execute("DROP TABLE IF EXISTS temp_valid_fts")
                return -1  # Signal FTS cleanup failed

            # Step 6: Clean up temporary table
            conn.execute("DROP TABLE IF EXISTS temp_valid_fts")

            return valid_count

        except Exception as e:
            log.error(f"FTS cleanup validation failed, leaving FTS untouched: {e}")
            # Conservative approach: don't touch FTS if anything goes wrong
            try:
                conn.execute("DROP TABLE IF EXISTS temp_valid_fts")
            except:
                pass
            return -1  # Signal FTS cleanup was skipped


class PGVectorDatabaseCleaner(VectorDatabaseCleaner):
    """
    PGVector database cleanup implementation.

    Leverages the existing PGVector client's delete() method for simple,
    reliable collection cleanup while maintaining comprehensive error handling
    and safety features.
    """

    def __init__(self):
        # Validate that we can access the PGVector client
        try:
            if VECTOR_DB_CLIENT is None:
                raise Exception("VECTOR_DB_CLIENT is not available")
            # Test if we can access the session
            if hasattr(VECTOR_DB_CLIENT, "session") and VECTOR_DB_CLIENT.session:
                self.session = VECTOR_DB_CLIENT.session
                log.debug("PGVector cleaner initialized successfully")
            else:
                raise Exception("PGVector client session not available")
        except Exception as e:
            log.error(f"Failed to initialize PGVector client for cleanup: {e}")
            self.session = None

    def count_orphaned_collections(
        self, active_file_ids: Set[str], active_kb_ids: Set[str]
    ) -> int:
        """Count orphaned PGVector collections for preview."""
        if not self.session:
            log.warning(
                "PGVector session not available for counting orphaned collections"
            )
            return 0

        try:
            orphaned_collections = self._get_orphaned_collections(
                active_file_ids, active_kb_ids
            )
            self.session.rollback()  # Read-only transaction
            return len(orphaned_collections)

        except Exception as e:
            if self.session:
                self.session.rollback()
            log.error(f"Error counting orphaned PGVector collections: {e}")
            return 0

    def cleanup_orphaned_collections(
        self, active_file_ids: Set[str], active_kb_ids: Set[str]
    ) -> int:
        """
        Delete orphaned PGVector collections using the existing client's delete method.

        This is the "super easy" approach suggested by @recrudesce - just use the
        existing PGVector client's delete() method for each orphaned collection.
        """
        if not self.session:
            log.warning("PGVector session not available for cleanup")
            return 0

        try:
            orphaned_collections = self._get_orphaned_collections(
                active_file_ids, active_kb_ids
            )

            if not orphaned_collections:
                log.debug("No orphaned PGVector collections found")
                return 0

            deleted_count = 0
            log.info(
                f"Deleting {len(orphaned_collections)} orphaned PGVector collections"
            )

            # SIMPLIFIED DELETION: Use existing PGVector client delete method
            for collection_name in orphaned_collections:
                try:
                    # This is @recrudesce's "super easy" approach:
                    # Just call the existing delete method!
                    VECTOR_DB_CLIENT.delete(collection_name)
                    deleted_count += 1
                    log.debug(f"Deleted PGVector collection: {collection_name}")

                except Exception as e:
                    log.error(
                        f"Failed to delete PGVector collection '{collection_name}': {e}"
                    )
                    # Continue with other collections even if one fails
                    continue

            # PostgreSQL-specific optimization (if we have access to session)
            try:
                if self.session:
                    self.session.execute(text("VACUUM ANALYZE document_chunk"))
                    self.session.commit()
                    log.debug("Executed VACUUM ANALYZE on document_chunk table")
            except Exception as e:
                log.warning(f"Failed to VACUUM PGVector table: {e}")

            if deleted_count > 0:
                log.info(
                    f"Successfully deleted {deleted_count} orphaned PGVector collections"
                )

            return deleted_count

        except Exception as e:
            if self.session:
                self.session.rollback()
            log.error(f"Error cleaning orphaned PGVector collections: {e}")
            return 0

    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a specific PGVector collection using the existing client method.

        Super simple - just call the existing delete method!
        """
        try:
            # @recrudesce's "super easy" approach: use existing client!
            VECTOR_DB_CLIENT.delete(collection_name)
            log.debug(f"Deleted PGVector collection: {collection_name}")
            return True

        except Exception as e:
            log.error(f"Error deleting PGVector collection '{collection_name}': {e}")
            return False

    def _get_orphaned_collections(
        self, active_file_ids: Set[str], active_kb_ids: Set[str]
    ) -> Set[str]:
        """
        Find collections that exist in PGVector but are no longer referenced.

        This is the only "complex" part - discovery. The actual deletion is simple!
        """
        try:
            expected_collections = self._build_expected_collections(
                active_file_ids, active_kb_ids
            )

            # Query distinct collection names from document_chunk table
            result = self.session.execute(
                text("SELECT DISTINCT collection_name FROM document_chunk")
            ).fetchall()

            existing_collections = {row[0] for row in result}
            orphaned_collections = existing_collections - expected_collections

            log.debug(
                f"Found {len(existing_collections)} existing collections, "
                f"{len(expected_collections)} expected, "
                f"{len(orphaned_collections)} orphaned"
            )

            return orphaned_collections

        except Exception as e:
            log.error(f"Error finding orphaned PGVector collections: {e}")
            return set()

    def _build_expected_collections(
        self, active_file_ids: Set[str], active_kb_ids: Set[str]
    ) -> Set[str]:
        """Build set of collection names that should exist."""
        expected_collections = set()

        # File collections use "file-{id}" pattern (same as ChromaDB)
        for file_id in active_file_ids:
            expected_collections.add(f"file-{file_id}")

        # Knowledge base collections use the KB ID directly (same as ChromaDB)
        for kb_id in active_kb_ids:
            expected_collections.add(kb_id)

        return expected_collections


class NoOpVectorDatabaseCleaner(VectorDatabaseCleaner):
    """
    No-operation implementation for unsupported vector databases.

    This implementation does nothing and is used when the configured
    vector database is not supported by the cleanup system.
    """

    def count_orphaned_collections(
        self, active_file_ids: Set[str], active_kb_ids: Set[str]
    ) -> int:
        """No orphaned collections to count for unsupported databases."""
        return 0

    def cleanup_orphaned_collections(
        self, active_file_ids: Set[str], active_kb_ids: Set[str]
    ) -> int:
        """No collections to cleanup for unsupported databases."""
        return 0

    def delete_collection(self, collection_name: str) -> bool:
        """No collection to delete for unsupported databases."""
        return True


def get_vector_database_cleaner() -> VectorDatabaseCleaner:
    """
    Factory function to get the appropriate vector database cleaner.

    This function detects the configured vector database type and returns
    the appropriate cleaner implementation. Community contributors can
    extend this function to support additional vector databases.

    Returns:
        VectorDatabaseCleaner: Appropriate implementation for the configured database
    """
    vector_db_type = VECTOR_DB.lower()

    if "chroma" in vector_db_type:
        log.debug("Using ChromaDB cleaner")
        return ChromaDatabaseCleaner()
    elif "pgvector" in vector_db_type:
        log.debug("Using PGVector cleaner")
        return PGVectorDatabaseCleaner()
    else:
        log.debug(
            f"No specific cleaner for vector database type: {VECTOR_DB}, using no-op cleaner"
        )
        return NoOpVectorDatabaseCleaner()


class PruneDataForm(BaseModel):
    days: Optional[int] = None
    exempt_archived_chats: bool = False
    exempt_chats_in_folders: bool = False
    delete_orphaned_chats: bool = True
    delete_orphaned_tools: bool = False
    delete_orphaned_functions: bool = False
    delete_orphaned_prompts: bool = True
    delete_orphaned_knowledge_bases: bool = True
    delete_orphaned_models: bool = True
    delete_orphaned_notes: bool = True
    delete_orphaned_folders: bool = True
    audio_cache_max_age_days: Optional[int] = 30
    delete_inactive_users_days: Optional[int] = None
    exempt_admin_users: bool = True
    exempt_pending_users: bool = True
    dry_run: bool = True


class PrunePreviewResult(BaseModel):
    inactive_users: int = 0
    old_chats: int = 0
    orphaned_chats: int = 0
    orphaned_files: int = 0
    orphaned_tools: int = 0
    orphaned_functions: int = 0
    orphaned_prompts: int = 0
    orphaned_knowledge_bases: int = 0
    orphaned_models: int = 0
    orphaned_notes: int = 0
    orphaned_folders: int = 0
    orphaned_uploads: int = 0
    orphaned_vector_collections: int = 0
    audio_cache_files: int = 0


# Counting helper functions for dry-run preview
def count_inactive_users(
    inactive_days: Optional[int], exempt_admin: bool, exempt_pending: bool
) -> int:
    """Count users that would be deleted for inactivity."""
    if inactive_days is None:
        return 0

    cutoff_time = int(time.time()) - (inactive_days * 86400)
    count = 0

    try:
        all_users = Users.get_users()["users"]
        for user in all_users:
            if exempt_admin and user.role == "admin":
                continue
            if exempt_pending and user.role == "pending":
                continue
            if user.last_active_at < cutoff_time:
                count += 1
    except Exception as e:
        log.debug(f"Error counting inactive users: {e}")

    return count


def count_old_chats(
    days: Optional[int], exempt_archived: bool, exempt_in_folders: bool
) -> int:
    """Count chats that would be deleted by age."""
    if days is None:
        return 0

    cutoff_time = int(time.time()) - (days * 86400)
    count = 0

    try:
        for chat in Chats.get_chats():
            if chat.updated_at < cutoff_time:
                if exempt_archived and chat.archived:
                    continue
                if exempt_in_folders and (
                    getattr(chat, "folder_id", None) is not None
                    or getattr(chat, "pinned", False)
                ):
                    continue
                count += 1
    except Exception as e:
        log.debug(f"Error counting old chats: {e}")

    return count


def count_orphaned_records(form_data: PruneDataForm) -> dict:
    """Count orphaned database records that would be deleted."""
    counts = {
        "chats": 0,
        "files": 0,
        "tools": 0,
        "functions": 0,
        "prompts": 0,
        "knowledge_bases": 0,
        "models": 0,
        "notes": 0,
        "folders": 0,
    }

    try:
        # Get active user IDs
        active_user_ids = {user.id for user in Users.get_users()["users"]}

        # Get active file IDs for file orphan detection
        active_file_ids = get_active_file_ids()

        # Count orphaned files
        for file_record in Files.get_files():
            should_delete = (
                file_record.id not in active_file_ids
                or file_record.user_id not in active_user_ids
            )
            if should_delete:
                counts["files"] += 1

        # Count other orphaned records
        if form_data.delete_orphaned_chats:
            for chat in Chats.get_chats():
                if chat.user_id not in active_user_ids:
                    counts["chats"] += 1

        if form_data.delete_orphaned_tools:
            for tool in Tools.get_tools():
                if tool.user_id not in active_user_ids:
                    counts["tools"] += 1

        if form_data.delete_orphaned_functions:
            for function in Functions.get_functions():
                if function.user_id not in active_user_ids:
                    counts["functions"] += 1

        if form_data.delete_orphaned_prompts:
            for prompt in Prompts.get_prompts():
                if prompt.user_id not in active_user_ids:
                    counts["prompts"] += 1

        if form_data.delete_orphaned_knowledge_bases:
            for kb in Knowledges.get_knowledge_bases():
                if kb.user_id not in active_user_ids:
                    counts["knowledge_bases"] += 1

        if form_data.delete_orphaned_models:
            for model in Models.get_all_models():
                if model.user_id not in active_user_ids:
                    counts["models"] += 1

        if form_data.delete_orphaned_notes:
            for note in Notes.get_notes():
                if note.user_id not in active_user_ids:
                    counts["notes"] += 1

        if form_data.delete_orphaned_folders:
            for folder in Folders.get_all_folders():
                if folder.user_id not in active_user_ids:
                    counts["folders"] += 1

    except Exception as e:
        log.debug(f"Error counting orphaned records: {e}")

    return counts


def count_orphaned_uploads(active_file_ids: Set[str]) -> int:
    """Count orphaned files in uploads directory."""
    upload_dir = Path(CACHE_DIR).parent / "uploads"
    if not upload_dir.exists():
        return 0

    count = 0
    try:
        for file_path in upload_dir.iterdir():
            if not file_path.is_file():
                continue

            filename = file_path.name
            file_id = None

            # Extract file ID from filename patterns
            if len(filename) > 36:
                potential_id = filename[:36]
                if potential_id.count("-") == 4:
                    file_id = potential_id

            if not file_id and filename.count("-") == 4 and len(filename) == 36:
                file_id = filename

            if not file_id:
                for active_id in active_file_ids:
                    if active_id in filename:
                        file_id = active_id
                        break

            if file_id and file_id not in active_file_ids:
                count += 1
    except Exception as e:
        log.debug(f"Error counting orphaned uploads: {e}")

    return count


def count_audio_cache_files(max_age_days: Optional[int]) -> int:
    """Count audio cache files that would be deleted."""
    if max_age_days is None:
        return 0

    cutoff_time = time.time() - (max_age_days * 86400)
    count = 0

    audio_dirs = [
        Path(CACHE_DIR) / "audio" / "speech",
        Path(CACHE_DIR) / "audio" / "transcriptions",
    ]

    for audio_dir in audio_dirs:
        if not audio_dir.exists():
            continue

        try:
            for file_path in audio_dir.iterdir():
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    count += 1
        except Exception as e:
            log.debug(f"Error counting audio files in {audio_dir}: {e}")

    return count


def get_active_file_ids() -> Set[str]:
    """
    Get all file IDs that are actively referenced by knowledge bases, chats, folders, and messages.
    """
    active_file_ids = set()

    try:
        # Scan knowledge bases for file references
        knowledge_bases = Knowledges.get_knowledge_bases()
        log.debug(f"Found {len(knowledge_bases)} knowledge bases")

        for kb in knowledge_bases:
            if not kb.data:
                continue

            file_ids = []

            if isinstance(kb.data, dict) and "file_ids" in kb.data:
                if isinstance(kb.data["file_ids"], list):
                    file_ids.extend(kb.data["file_ids"])

            if isinstance(kb.data, dict) and "files" in kb.data:
                if isinstance(kb.data["files"], list):
                    for file_ref in kb.data["files"]:
                        if isinstance(file_ref, dict) and "id" in file_ref:
                            file_ids.append(file_ref["id"])
                        elif isinstance(file_ref, str):
                            file_ids.append(file_ref)

            for file_id in file_ids:
                if isinstance(file_id, str) and file_id.strip():
                    active_file_ids.add(file_id.strip())

        # Scan chats for file references
        chats = Chats.get_chats()
        log.debug(f"Found {len(chats)} chats to scan for file references")

        for chat in chats:
            if not chat.chat or not isinstance(chat.chat, dict):
                continue

            try:
                chat_json_str = json.dumps(chat.chat)
                # Use utility to extract and validate file IDs
                validated_ids = JSONFileIDExtractor.extract_and_validate_file_ids(
                    chat_json_str
                )
                active_file_ids.update(validated_ids)

            except Exception as e:
                log.debug(f"Error processing chat {chat.id} for file references: {e}")

        # Scan folders for file references
        try:
            folders = Folders.get_all_folders()

            for folder in folders:
                if folder.items:
                    try:
                        items_str = json.dumps(folder.items)
                        # Use utility to extract and validate file IDs
                        validated_ids = (
                            JSONFileIDExtractor.extract_and_validate_file_ids(items_str)
                        )
                        active_file_ids.update(validated_ids)
                    except Exception as e:
                        log.debug(f"Error processing folder {folder.id} items: {e}")

                if hasattr(folder, "data") and folder.data:
                    try:
                        data_str = json.dumps(folder.data)
                        # Use utility to extract and validate file IDs
                        validated_ids = (
                            JSONFileIDExtractor.extract_and_validate_file_ids(data_str)
                        )
                        active_file_ids.update(validated_ids)
                    except Exception as e:
                        log.debug(f"Error processing folder {folder.id} data: {e}")

        except Exception as e:
            log.debug(f"Error scanning folders for file references: {e}")

        # Scan standalone messages for file references
        try:
            with get_db() as db:
                message_results = db.execute(
                    text("SELECT id, data FROM message WHERE data IS NOT NULL")
                ).fetchall()

                for message_id, message_data_json in message_results:
                    if message_data_json:
                        try:
                            data_str = (
                                json.dumps(message_data_json)
                                if isinstance(message_data_json, dict)
                                else str(message_data_json)
                            )
                            # Use utility to extract and validate file IDs
                            validated_ids = (
                                JSONFileIDExtractor.extract_and_validate_file_ids(
                                    data_str
                                )
                            )
                            active_file_ids.update(validated_ids)
                        except Exception as e:
                            log.debug(
                                f"Error processing message {message_id} data: {e}"
                            )
        except Exception as e:
            log.debug(f"Error scanning messages for file references: {e}")

    except Exception as e:
        log.error(f"Error determining active file IDs: {e}")
        return set()

    log.info(f"Found {len(active_file_ids)} active file IDs")
    return active_file_ids


def safe_delete_file_by_id(file_id: str) -> bool:
    """
    Safely delete a file record and its associated vector collection.
    """
    try:
        file_record = Files.get_file_by_id(file_id)
        if not file_record:
            return True

        # Use modular vector database cleaner
        vector_cleaner = get_vector_database_cleaner()
        collection_name = f"file-{file_id}"
        vector_cleaner.delete_collection(collection_name)

        Files.delete_file_by_id(file_id)
        return True

    except Exception as e:
        log.error(f"Error deleting file {file_id}: {e}")
        return False


def cleanup_orphaned_uploads(active_file_ids: Set[str]) -> None:
    """
    Clean up orphaned files in the uploads directory.
    """
    upload_dir = Path(CACHE_DIR).parent / "uploads"
    if not upload_dir.exists():
        return

    deleted_count = 0

    try:
        for file_path in upload_dir.iterdir():
            if not file_path.is_file():
                continue

            filename = file_path.name
            file_id = None

            # Extract file ID from filename patterns
            if len(filename) > 36:
                potential_id = filename[:36]
                if potential_id.count("-") == 4:
                    file_id = potential_id

            if not file_id and filename.count("-") == 4 and len(filename) == 36:
                file_id = filename

            if not file_id:
                for active_id in active_file_ids:
                    if active_id in filename:
                        file_id = active_id
                        break

            if file_id and file_id not in active_file_ids:
                try:
                    file_path.unlink()
                    deleted_count += 1
                except Exception as e:
                    log.error(f"Failed to delete upload file {filename}: {e}")

    except Exception as e:
        log.error(f"Error cleaning uploads directory: {e}")

    if deleted_count > 0:
        log.info(f"Deleted {deleted_count} orphaned upload files")


def delete_inactive_users(
    inactive_days: int, exempt_admin: bool = True, exempt_pending: bool = True
) -> int:
    """
    Delete users who have been inactive for the specified number of days.

    Returns the number of users deleted.
    """
    if inactive_days is None:
        return 0

    cutoff_time = int(time.time()) - (inactive_days * 86400)
    deleted_count = 0

    try:
        users_to_delete = []

        # Get all users and check activity
        all_users = Users.get_users()["users"]

        for user in all_users:
            # Skip if user is exempt
            if exempt_admin and user.role == "admin":
                continue
            if exempt_pending and user.role == "pending":
                continue

            # Check if user is inactive based on last_active_at
            if user.last_active_at < cutoff_time:
                users_to_delete.append(user)

        # Delete inactive users
        for user in users_to_delete:
            try:
                # Delete the user - this will cascade to all their data
                Users.delete_user_by_id(user.id)
                deleted_count += 1
                log.info(
                    f"Deleted inactive user: {user.email} (last active: {user.last_active_at})"
                )
            except Exception as e:
                log.error(f"Failed to delete user {user.id}: {e}")

    except Exception as e:
        log.error(f"Error during inactive user deletion: {e}")

    return deleted_count


def cleanup_audio_cache(max_age_days: Optional[int] = 30) -> None:
    """
    Clean up audio cache files older than specified days.
    """
    if max_age_days is None:
        log.info("Skipping audio cache cleanup (max_age_days is None)")
        return

    cutoff_time = time.time() - (max_age_days * 86400)
    deleted_count = 0
    total_size_deleted = 0

    audio_dirs = [
        Path(CACHE_DIR) / "audio" / "speech",
        Path(CACHE_DIR) / "audio" / "transcriptions",
    ]

    for audio_dir in audio_dirs:
        if not audio_dir.exists():
            continue

        try:
            for file_path in audio_dir.iterdir():
                if not file_path.is_file():
                    continue

                file_mtime = file_path.stat().st_mtime
                if file_mtime < cutoff_time:
                    try:
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        deleted_count += 1
                        total_size_deleted += file_size
                    except Exception as e:
                        log.error(f"Failed to delete audio file {file_path}: {e}")

        except Exception as e:
            log.error(f"Error cleaning audio directory {audio_dir}: {e}")

    if deleted_count > 0:
        size_mb = total_size_deleted / (1024 * 1024)
        log.info(
            f"Deleted {deleted_count} audio cache files ({size_mb:.1f} MB), older than {max_age_days} days"
        )


@router.post("/", response_model=Union[bool, PrunePreviewResult])
async def prune_data(form_data: PruneDataForm, user=Depends(get_admin_user)):
    """
    Prunes old and orphaned data using a safe, multi-stage process.

    If dry_run=True (default), returns preview counts without deleting anything.
    If dry_run=False, performs actual deletion and returns True on success.
    """
    try:
        # Get vector database cleaner based on configuration
        vector_cleaner = get_vector_database_cleaner()

        if form_data.dry_run:
            log.info("Starting data pruning preview (dry run)")

            # Get counts for all enabled operations
            active_file_ids = get_active_file_ids()
            active_user_ids = {user.id for user in Users.get_users()["users"]}
            active_kb_ids = {
                kb.id
                for kb in Knowledges.get_knowledge_bases()
                if kb.user_id in active_user_ids
            }

            orphaned_counts = count_orphaned_records(form_data)

            result = PrunePreviewResult(
                inactive_users=count_inactive_users(
                    form_data.delete_inactive_users_days,
                    form_data.exempt_admin_users,
                    form_data.exempt_pending_users,
                ),
                old_chats=count_old_chats(
                    form_data.days,
                    form_data.exempt_archived_chats,
                    form_data.exempt_chats_in_folders,
                ),
                orphaned_chats=orphaned_counts["chats"],
                orphaned_files=orphaned_counts["files"],
                orphaned_tools=orphaned_counts["tools"],
                orphaned_functions=orphaned_counts["functions"],
                orphaned_prompts=orphaned_counts["prompts"],
                orphaned_knowledge_bases=orphaned_counts["knowledge_bases"],
                orphaned_models=orphaned_counts["models"],
                orphaned_notes=orphaned_counts["notes"],
                orphaned_folders=orphaned_counts["folders"],
                orphaned_uploads=count_orphaned_uploads(active_file_ids),
                orphaned_vector_collections=vector_cleaner.count_orphaned_collections(
                    active_file_ids, active_kb_ids
                ),
                audio_cache_files=count_audio_cache_files(
                    form_data.audio_cache_max_age_days
                ),
            )

            log.info("Data pruning preview completed")
            return result

        # Actual deletion logic (dry_run=False)
        log.info("Starting data pruning process")

        # Stage 0: Delete inactive users (if enabled)
        deleted_users = 0
        if form_data.delete_inactive_users_days is not None:
            log.info(
                f"Deleting users inactive for more than {form_data.delete_inactive_users_days} days"
            )
            deleted_users = delete_inactive_users(
                form_data.delete_inactive_users_days,
                form_data.exempt_admin_users,
                form_data.exempt_pending_users,
            )
            if deleted_users > 0:
                log.info(f"Deleted {deleted_users} inactive users")
            else:
                log.info("No inactive users found to delete")
        else:
            log.info("Skipping inactive user deletion (disabled)")

        # Stage 1: Delete old chats based on user criteria
        if form_data.days is not None:
            cutoff_time = int(time.time()) - (form_data.days * 86400)
            chats_to_delete = []

            for chat in Chats.get_chats():
                if chat.updated_at < cutoff_time:
                    if form_data.exempt_archived_chats and chat.archived:
                        continue
                    if form_data.exempt_chats_in_folders and (
                        getattr(chat, "folder_id", None) is not None
                        or getattr(chat, "pinned", False)
                    ):
                        continue
                    chats_to_delete.append(chat)

            if chats_to_delete:
                log.info(
                    f"Deleting {len(chats_to_delete)} old chats (older than {form_data.days} days)"
                )
                for chat in chats_to_delete:
                    Chats.delete_chat_by_id(chat.id)
            else:
                log.info(f"No chats found older than {form_data.days} days")
        else:
            log.info("Skipping chat deletion (days parameter is None)")

        # Stage 2: Build preservation set
        log.info("Building preservation set")

        active_user_ids = {user.id for user in Users.get_users()["users"]}
        log.info(f"Found {len(active_user_ids)} active users")

        active_kb_ids = set()
        knowledge_bases = Knowledges.get_knowledge_bases()

        for kb in knowledge_bases:
            if kb.user_id in active_user_ids:
                active_kb_ids.add(kb.id)

        log.info(f"Found {len(active_kb_ids)} active knowledge bases")

        active_file_ids = get_active_file_ids()

        # Stage 3: Delete orphaned database records
        log.info("Deleting orphaned database records")

        deleted_files = 0
        for file_record in Files.get_files():
            should_delete = (
                file_record.id not in active_file_ids
                or file_record.user_id not in active_user_ids
            )

            if should_delete:
                if safe_delete_file_by_id(file_record.id):
                    deleted_files += 1

        if deleted_files > 0:
            log.info(f"Deleted {deleted_files} orphaned files")

        deleted_kbs = 0
        if form_data.delete_orphaned_knowledge_bases:
            for kb in knowledge_bases:
                if kb.user_id not in active_user_ids:
                    if vector_cleaner.delete_collection(kb.id):
                        Knowledges.delete_knowledge_by_id(kb.id)
                        deleted_kbs += 1

            if deleted_kbs > 0:
                log.info(f"Deleted {deleted_kbs} orphaned knowledge bases")
        else:
            log.info("Skipping knowledge base deletion (disabled)")

        deleted_others = 0

        if form_data.delete_orphaned_chats:
            chats_deleted = 0
            for chat in Chats.get_chats():
                if chat.user_id not in active_user_ids:
                    Chats.delete_chat_by_id(chat.id)
                    chats_deleted += 1
                    deleted_others += 1
            if chats_deleted > 0:
                log.info(f"Deleted {chats_deleted} orphaned chats")
        else:
            log.info("Skipping orphaned chat deletion (disabled)")

        if form_data.delete_orphaned_tools:
            tools_deleted = 0
            for tool in Tools.get_tools():
                if tool.user_id not in active_user_ids:
                    Tools.delete_tool_by_id(tool.id)
                    tools_deleted += 1
                    deleted_others += 1
            if tools_deleted > 0:
                log.info(f"Deleted {tools_deleted} orphaned tools")
        else:
            log.info("Skipping tool deletion (disabled)")

        if form_data.delete_orphaned_functions:
            functions_deleted = 0
            for function in Functions.get_functions():
                if function.user_id not in active_user_ids:
                    Functions.delete_function_by_id(function.id)
                    functions_deleted += 1
                    deleted_others += 1
            if functions_deleted > 0:
                log.info(f"Deleted {functions_deleted} orphaned functions")
        else:
            log.info("Skipping function deletion (disabled)")

        if form_data.delete_orphaned_notes:
            notes_deleted = 0
            for note in Notes.get_notes():
                if note.user_id not in active_user_ids:
                    Notes.delete_note_by_id(note.id)
                    notes_deleted += 1
                    deleted_others += 1
            if notes_deleted > 0:
                log.info(f"Deleted {notes_deleted} orphaned notes")
        else:
            log.info("Skipping note deletion (disabled)")

        if form_data.delete_orphaned_prompts:
            prompts_deleted = 0
            for prompt in Prompts.get_prompts():
                if prompt.user_id not in active_user_ids:
                    Prompts.delete_prompt_by_command(prompt.command)
                    prompts_deleted += 1
                    deleted_others += 1
            if prompts_deleted > 0:
                log.info(f"Deleted {prompts_deleted} orphaned prompts")
        else:
            log.info("Skipping prompt deletion (disabled)")

        if form_data.delete_orphaned_models:
            models_deleted = 0
            for model in Models.get_all_models():
                if model.user_id not in active_user_ids:
                    Models.delete_model_by_id(model.id)
                    models_deleted += 1
                    deleted_others += 1
            if models_deleted > 0:
                log.info(f"Deleted {models_deleted} orphaned models")
        else:
            log.info("Skipping model deletion (disabled)")

        if form_data.delete_orphaned_folders:
            folders_deleted = 0
            for folder in Folders.get_all_folders():
                if folder.user_id not in active_user_ids:
                    Folders.delete_folder_by_id_and_user_id(
                        folder.id, folder.user_id
                    )
                    folders_deleted += 1
                    deleted_others += 1
            if folders_deleted > 0:
                log.info(f"Deleted {folders_deleted} orphaned folders")
        else:
            log.info("Skipping folder deletion (disabled)")

        if deleted_others > 0:
            log.info(f"Total other orphaned records deleted: {deleted_others}")

        # Stage 4: Clean up orphaned physical files
        log.info("Cleaning up orphaned physical files")

        final_active_file_ids = get_active_file_ids()
        final_active_kb_ids = {kb.id for kb in Knowledges.get_knowledge_bases()}

        cleanup_orphaned_uploads(final_active_file_ids)

        # Use modular vector database cleanup
        vector_cleaner.cleanup_orphaned_collections(
            final_active_file_ids, final_active_kb_ids
        )

        # Stage 5: Audio cache cleanup
        log.info("Cleaning audio cache")
        cleanup_audio_cache(form_data.audio_cache_max_age_days)

        # Stage 6: Database optimization
        log.info("Optimizing database")

        try:
            with get_db() as db:
                db.execute(text("VACUUM"))
        except Exception as e:
            log.error(f"Failed to vacuum main database: {e}")

        # Vector database-specific optimization
        if isinstance(vector_cleaner, ChromaDatabaseCleaner):
            try:
                with sqlite3.connect(str(vector_cleaner.chroma_db_path)) as conn:
                    conn.execute("VACUUM")
                    log.info("Vacuumed ChromaDB database")
            except Exception as e:
                log.error(f"Failed to vacuum ChromaDB database: {e}")
        elif (
            isinstance(vector_cleaner, PGVectorDatabaseCleaner)
            and vector_cleaner.session
        ):
            try:
                vector_cleaner.session.execute(text("VACUUM ANALYZE"))
                vector_cleaner.session.commit()
                log.info("Executed VACUUM ANALYZE on PostgreSQL database")
            except Exception as e:
                log.error(f"Failed to vacuum PostgreSQL database: {e}")

        log.info("Data pruning completed successfully")
        return True

    except Exception as e:
        log.exception(f"Error during data pruning: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT("Data pruning failed"),
        )
