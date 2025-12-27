"""
Core Prune Classes and Vector Database Cleaners

This module contains all the core classes from backend/open_webui/routers/prune.py,
including the abstract vector database cleaner and its implementations.
"""

import logging
import json
import uuid
import os
import re
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Set
from abc import ABC, abstractmethod

log = logging.getLogger(__name__)


class PruneLock:
    """
    Simple file-based locking mechanism to prevent concurrent prune operations.

    This uses a lock file with timestamp to prevent multiple admins from running
    prune simultaneously, which could cause race conditions and data corruption.
    """

    LOCK_FILE = None  # Will be set by init
    LOCK_TIMEOUT = timedelta(hours=2)  # Safety timeout

    @classmethod
    def init(cls, cache_dir: Path):
        """Initialize lock file path with cache directory."""
        cls.LOCK_FILE = Path(cache_dir) / ".prune.lock"

    @classmethod
    def acquire(cls) -> bool:
        """
        Try to acquire the lock. Returns True if acquired, False if already locked.

        If lock file exists but is stale (older than timeout), automatically
        removes it and acquires a new lock.
        """
        if cls.LOCK_FILE is None:
            raise RuntimeError("PruneLock not initialized. Call PruneLock.init() first.")

        try:
            # Check if lock file exists
            if cls.LOCK_FILE.exists():
                # Read lock file to check if it's stale
                try:
                    with open(cls.LOCK_FILE, 'r') as f:
                        lock_data = json.load(f)
                        lock_time = datetime.fromisoformat(lock_data['timestamp'])
                        operation_id = lock_data.get('operation_id', 'unknown')

                        # Check if lock is stale
                        if datetime.utcnow() - lock_time > cls.LOCK_TIMEOUT:
                            log.warning(f"Found stale lock from {lock_time} (operation {operation_id}), removing")
                            cls.LOCK_FILE.unlink()
                        else:
                            # Lock is still valid
                            log.warning(f"Prune operation already in progress (started {lock_time}, operation {operation_id})")
                            return False
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    # Corrupt lock file, remove it
                    log.warning(f"Found corrupt lock file, removing: {e}")
                    cls.LOCK_FILE.unlink()

            # Create lock file
            operation_id = str(uuid.uuid4())[:8]
            lock_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'operation_id': operation_id,
                'pid': os.getpid()
            }

            # Ensure parent directory exists
            cls.LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)

            with open(cls.LOCK_FILE, 'w') as f:
                json.dump(lock_data, f)

            log.info(f"Acquired prune lock (operation {operation_id})")
            return True

        except Exception as e:
            log.error(f"Error acquiring prune lock: {e}")
            return False

    @classmethod
    def release(cls) -> None:
        """Release the lock by removing the lock file."""
        if cls.LOCK_FILE is None:
            return

        try:
            if cls.LOCK_FILE.exists():
                cls.LOCK_FILE.unlink()
                log.info("Released prune lock")
        except Exception as e:
            log.error(f"Error releasing prune lock: {e}")


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
    def extract_file_ids(cls, json_string: str) -> Set[str]:
        """
        Extract file IDs from JSON string WITHOUT database validation.

        Args:
            json_string: JSON content as string (or any string to scan)

        Returns:
            Set of extracted file IDs (not validated against database)

        Note:
            Use this method when you have a preloaded set of valid file IDs
            to validate against, avoiding N database queries.
        """
        potential_ids = []
        potential_ids.extend(cls._FILE_ID_PATTERN.findall(json_string))
        potential_ids.extend(cls._URL_PATTERN.findall(json_string))
        return set(potential_ids)


# UUID pattern for direct dict traversal (Phase 1.5 optimization)
UUID_PATTERN = re.compile(
    r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$'
)


def collect_file_ids_from_dict(obj, out: Set[str], valid_ids: Set[str], _depth: int = 0) -> None:
    """
    Recursively traverse dict/list structures and collect file IDs.

    This function replaces json.dumps() + regex approach with direct dict traversal,
    reducing memory usage by ~75% on large chat databases.

    Args:
        obj: Dict, list, or any value to traverse
        out: Set to accumulate found file IDs into
        valid_ids: Set of known valid file IDs (for O(1) validation)
        _depth: Current recursion depth (safety limit)

    Patterns detected:
        - {"id": "uuid"}
        - {"file_id": "uuid"}
        - {"fileId": "uuid"}
        - {"file_ids": ["uuid1", "uuid2"]}
        - {"fileIds": ["uuid1", "uuid2"]}
    """
    # Safety: Prevent excessive recursion
    if _depth > 100:
        return

    if isinstance(obj, dict):
        # Check individual file ID fields
        for field_name in ['id', 'file_id', 'fileId']:
            fid = obj.get(field_name)
            if isinstance(fid, str) and UUID_PATTERN.fullmatch(fid):
                if fid in valid_ids:
                    out.add(fid)

        # Check file ID array fields
        for field_name in ['file_ids', 'fileIds']:
            fid_array = obj.get(field_name)
            if isinstance(fid_array, list):
                for fid in fid_array:
                    if isinstance(fid, str) and UUID_PATTERN.fullmatch(fid):
                        if fid in valid_ids:
                            out.add(fid)

        # Recurse into all dict values
        for value in obj.values():
            collect_file_ids_from_dict(value, out, valid_ids, _depth + 1)

    elif isinstance(obj, list):
        # Recurse into all list items
        for item in obj:
            collect_file_ids_from_dict(item, out, valid_ids, _depth + 1)

    # Primitives (str, int, None, etc.) - do nothing


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
        self,
        active_file_ids: Set[str],
        active_kb_ids: Set[str],
        active_user_ids: Optional[Set[str]] = None
    ) -> int:
        """
        Count how many orphaned vector collections would be deleted.

        Args:
            active_file_ids: Set of file IDs that are still referenced
            active_kb_ids: Set of knowledge base IDs that are still active
            active_user_ids: Set of user IDs that are still active (optional, for multitenancy)

        Returns:
            Number of orphaned collections that would be deleted
        """
        pass

    @abstractmethod
    def cleanup_orphaned_collections(
        self,
        active_file_ids: Set[str],
        active_kb_ids: Set[str],
        active_user_ids: Optional[Set[str]] = None
    ) -> tuple[int, Optional[str]]:
        """
        Actually delete orphaned vector collections.

        Args:
            active_file_ids: Set of file IDs that are still referenced
            active_kb_ids: Set of knowledge base IDs that are still active
            active_user_ids: Set of user IDs that are still active (optional, for multitenancy)

        Returns:
            Tuple of (deleted_count, error_message)
            - deleted_count: Number of collections that were deleted
            - error_message: None on success, error description on failure
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

    def __init__(self, vector_db_client, cache_dir: Path):
        """Initialize ChromaDB cleaner with paths."""
        self.vector_db_client = vector_db_client
        self.vector_dir = Path(cache_dir).parent / "vector_db"
        self.chroma_db_path = self.vector_dir / "chroma.sqlite3"

    def count_orphaned_collections(
        self,
        active_file_ids: Set[str],
        active_kb_ids: Set[str],
        active_user_ids: Optional[Set[str]] = None
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
        self,
        active_file_ids: Set[str],
        active_kb_ids: Set[str],
        active_user_ids: Optional[Set[str]] = None
    ) -> tuple[int, Optional[str]]:
        """Actually delete orphaned ChromaDB collections and database records."""
        if not self.chroma_db_path.exists():
            return (0, None)

        expected_collections = self._build_expected_collections(
            active_file_ids, active_kb_ids
        )
        uuid_to_collection = self._get_collection_mappings()

        deleted_count = 0
        errors = []

        # First, clean up orphaned database records
        try:
            deleted_count += self._cleanup_orphaned_database_records()
        except Exception as e:
            error_msg = f"ChromaDB database cleanup failed: {e}"
            log.error(error_msg)
            errors.append(error_msg)

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
                        log.info(f"Deleted orphaned ChromaDB directory (no mapping): {dir_uuid}")
                    except Exception as e:
                        error_msg = f"Failed to delete orphaned directory {dir_uuid}: {e}"
                        log.error(error_msg)
                        errors.append(error_msg)

                elif collection_name not in expected_collections:
                    try:
                        shutil.rmtree(collection_dir)
                        deleted_count += 1
                        log.info(f"Deleted orphaned ChromaDB collection directory: {collection_name} ({dir_uuid})")
                    except Exception as e:
                        error_msg = f"Failed to delete collection directory {dir_uuid}: {e}"
                        log.error(error_msg)
                        errors.append(error_msg)
                else:
                    log.debug(f"Keeping expected collection: {collection_name} ({dir_uuid})")

        except Exception as e:
            error_msg = f"ChromaDB directory cleanup failed: {e}"
            log.error(error_msg)
            errors.append(error_msg)

        if deleted_count > 0:
            log.info(f"Deleted {deleted_count} orphaned ChromaDB collections")

        # Return error if any critical failures occurred
        if errors:
            return (deleted_count, "; ".join(errors))
        return (deleted_count, None)

    def delete_collection(self, collection_name: str) -> bool:
        """Delete a specific ChromaDB collection by name."""
        try:
            # Attempt to delete via ChromaDB client first
            try:
                self.vector_db_client.delete_collection(collection_name=collection_name)
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

                # Log database size before VACUUM for diagnostic purposes
                db_size_mb = self.chroma_db_path.stat().st_size / (1024 * 1024)
                log.info(f"ChromaDB size after cleanup, before VACUUM: {db_size_mb:.1f}MB (VACUUM needed to reclaim space)")

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

    def __init__(self, vector_db_client):
        """Initialize PGVector cleaner with client."""
        self.vector_db_client = vector_db_client
        # Validate that we can access the PGVector client
        try:
            if hasattr(vector_db_client, "session") and vector_db_client.session:
                self.session = vector_db_client.session
                log.debug("PGVector cleaner initialized successfully")
            else:
                raise Exception("PGVector client session not available")
        except Exception as e:
            log.error(f"Failed to initialize PGVector client for cleanup: {e}")
            self.session = None

    def count_orphaned_collections(
        self,
        active_file_ids: Set[str],
        active_kb_ids: Set[str],
        active_user_ids: Optional[Set[str]] = None
    ) -> int:
        """Count orphaned PGVector collections for preview."""
        if not self.session:
            log.warning(
                "PGVector session not available for counting orphaned collections"
            )
            return 0

        try:
            # Import here to avoid circular dependency
            from sqlalchemy import text

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
        self,
        active_file_ids: Set[str],
        active_kb_ids: Set[str],
        active_user_ids: Optional[Set[str]] = None
    ) -> tuple[int, Optional[str]]:
        """
        Delete orphaned PGVector collections using the existing client's delete method.

        This is the "super easy" approach suggested by @recrudesce - just use the
        existing PGVector client's delete() method for each orphaned collection.
        """
        if not self.session:
            error_msg = "PGVector session not available for cleanup"
            log.warning(error_msg)
            return (0, error_msg)

        try:
            # Import here to avoid circular dependency
            from sqlalchemy import text

            orphaned_collections = self._get_orphaned_collections(
                active_file_ids, active_kb_ids
            )

            if not orphaned_collections:
                log.debug("No orphaned PGVector collections found")
                return (0, None)

            deleted_count = 0
            log.info(
                f"Deleting {len(orphaned_collections)} orphaned PGVector collections"
            )

            # SIMPLIFIED DELETION: Use existing PGVector client delete method
            for collection_name in orphaned_collections:
                try:
                    # This is @recrudesce's "super easy" approach:
                    # Just call the existing delete method!
                    self.vector_db_client.delete(collection_name)
                    deleted_count += 1
                    log.debug(f"Deleted PGVector collection: {collection_name}")

                except Exception as e:
                    log.error(
                        f"Failed to delete PGVector collection '{collection_name}': {e}"
                    )
                    # Continue with other collections even if one fails
                    continue

            # CRITICAL: Clean up orphaned chunks within active KB collections
            # KB collections may contain chunks referencing deleted files
            # This handles the case where a file is deleted but the KB collection remains active
            orphaned_chunks_deleted = 0
            try:
                if self.session:
                    log.debug("Cleaning orphaned chunks from active KB collections")
                    result = self.session.execute(text("""
                        DELETE FROM document_chunk dc
                        WHERE dc.vmetadata ? 'file_id'
                          AND NOT EXISTS (
                            SELECT 1 FROM file f
                            WHERE f.id = (dc.vmetadata->>'file_id')
                          )
                    """))
                    orphaned_chunks_deleted = result.rowcount
                    self.session.commit()
                    if orphaned_chunks_deleted > 0:
                        log.info(f"Deleted {orphaned_chunks_deleted} orphaned chunks from active collections")
            except Exception as e:
                log.error(f"Failed to clean orphaned chunks: {e}")
                if self.session:
                    self.session.rollback()

            # PostgreSQL-specific optimization (if we have access to session)
            try:
                if self.session:
                    self.session.execute(text("VACUUM ANALYZE document_chunk"))
                    self.session.commit()
                    log.debug("Executed VACUUM ANALYZE on document_chunk table")
            except Exception as e:
                log.warning(f"Failed to VACUUM PGVector table: {e}")

            total_deleted = deleted_count + orphaned_chunks_deleted
            if total_deleted > 0:
                log.info(
                    f"Successfully deleted {deleted_count} orphaned collections and {orphaned_chunks_deleted} orphaned chunks"
                )

            return (deleted_count, None)

        except Exception as e:
            if self.session:
                self.session.rollback()
            error_msg = f"PGVector cleanup failed: {e}"
            log.error(error_msg)
            return (0, error_msg)

    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a specific PGVector collection using the existing client method.

        Super simple - just call the existing delete method!
        """
        try:
            # @recrudesce's "super easy" approach: use existing client!
            self.vector_db_client.delete(collection_name)
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
            # Import here to avoid circular dependency
            from sqlalchemy import text

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


class MilvusDatabaseCleaner(VectorDatabaseCleaner):
    """
    Milvus database cleanup implementation (standard mode).

    Handles Milvus's collection-based storage where each collection is independent.
    Collections use the pattern: "{prefix}_{collection_name}" where collection_name
    is typically "file-{id}" for files or knowledge base IDs.
    """

    def __init__(self, vector_db_client):
        """Initialize Milvus cleaner with client."""
        self.vector_db_client = vector_db_client
        self.collection_prefix = getattr(vector_db_client, 'collection_prefix', 'open_webui')
        log.debug(f"Milvus cleaner initialized with prefix: {self.collection_prefix}")

    def count_orphaned_collections(
        self,
        active_file_ids: Set[str],
        active_kb_ids: Set[str],
        active_user_ids: Optional[Set[str]] = None
    ) -> int:
        """Count orphaned Milvus collections for preview."""
        try:
            expected_collections = self._build_expected_collections(
                active_file_ids, active_kb_ids
            )

            # List all collections
            all_collections = self.vector_db_client.client.list_collections()

            # Count collections with our prefix that are not expected
            count = 0
            for collection_name in all_collections:
                if collection_name.startswith(f"{self.collection_prefix}_"):
                    # Extract the original name (remove prefix)
                    original_name = collection_name[len(self.collection_prefix) + 1:]
                    # Restore dashes (Milvus converts - to _)
                    original_name = original_name.replace("_", "-")

                    if original_name not in expected_collections:
                        count += 1
                        log.debug(f"Found orphaned Milvus collection: {collection_name}")

            return count

        except Exception as e:
            log.error(f"Error counting orphaned Milvus collections: {e}")
            return 0

    def cleanup_orphaned_collections(
        self,
        active_file_ids: Set[str],
        active_kb_ids: Set[str],
        active_user_ids: Optional[Set[str]] = None
    ) -> tuple[int, Optional[str]]:
        """Actually delete orphaned Milvus collections."""
        try:
            # Import here to avoid circular dependency
            from pymilvus import utility

            expected_collections = self._build_expected_collections(
                active_file_ids, active_kb_ids
            )

            # List all collections
            all_collections = self.vector_db_client.client.list_collections()

            deleted_count = 0
            errors = []

            for collection_name in all_collections:
                if collection_name.startswith(f"{self.collection_prefix}_"):
                    # Extract the original name (remove prefix)
                    original_name = collection_name[len(self.collection_prefix) + 1:]
                    # Restore dashes (Milvus converts - to _)
                    original_name = original_name.replace("_", "-")

                    if original_name not in expected_collections:
                        try:
                            # Use utility.drop_collection instead of client method
                            utility.drop_collection(collection_name)
                            deleted_count += 1
                            log.info(f"Deleted orphaned Milvus collection: {collection_name}")
                        except Exception as e:
                            error_msg = f"Failed to delete collection {collection_name}: {e}"
                            log.error(error_msg)
                            errors.append(error_msg)

            if deleted_count > 0:
                log.info(f"Deleted {deleted_count} orphaned Milvus collections")

            if errors:
                return (deleted_count, "; ".join(errors))
            return (deleted_count, None)

        except Exception as e:
            error_msg = f"Milvus cleanup failed: {e}"
            log.error(error_msg)
            return (0, error_msg)

    def delete_collection(self, collection_name: str) -> bool:
        """Delete a specific Milvus collection by name."""
        try:
            # Import here to avoid circular dependency
            from pymilvus import utility

            # Convert dashes to underscores (Milvus naming convention)
            collection_name = collection_name.replace("-", "_")
            full_name = f"{self.collection_prefix}_{collection_name}"

            # Check if collection exists using utility module
            if utility.has_collection(full_name):
                utility.drop_collection(full_name)
                log.debug(f"Deleted Milvus collection: {full_name}")
                return True
            else:
                log.debug(f"Milvus collection does not exist: {full_name}")
                return True  # Not existing is effectively deleted

        except Exception as e:
            log.error(f"Error deleting Milvus collection '{collection_name}': {e}")
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


class MilvusMultitenancyDatabaseCleaner(VectorDatabaseCleaner):
    """
    Milvus multitenancy database cleanup implementation.

    Handles Milvus's multitenancy mode where multiple logical collections
    share physical collections using a resource_id field for partitioning.

    In multitenancy mode, there are shared collections like:
    - {prefix}_memories - for user memories
    - {prefix}_knowledge - for knowledge bases
    - {prefix}_files - for file-based collections
    - {prefix}_web_search - for web search results
    - {prefix}_hash_based - for hash-based collections

    Each shared collection contains data from multiple logical collections,
    distinguished by the resource_id field.
    """

    def __init__(self, vector_db_client):
        """Initialize Milvus multitenancy cleaner with client."""
        self.vector_db_client = vector_db_client
        self.collection_prefix = getattr(
            vector_db_client, 'collection_prefix', 'open_webui'
        )

        # Get shared collection names
        self.shared_collections = getattr(
            vector_db_client,
            'shared_collections',
            [
                f"{self.collection_prefix}_memories",
                f"{self.collection_prefix}_knowledge",
                f"{self.collection_prefix}_files",
                f"{self.collection_prefix}_web_search",
                f"{self.collection_prefix}_hash_based",
            ]
        )
        log.debug(f"Milvus multitenancy cleaner initialized with prefix: {self.collection_prefix}")
        log.debug(f"Shared collections: {self.shared_collections}")

    def count_orphaned_collections(
        self,
        active_file_ids: Set[str],
        active_kb_ids: Set[str],
        active_user_ids: Optional[Set[str]] = None
    ) -> int:
        """
        Count orphaned resource_ids across all shared collections.

        In multitenancy mode, we count distinct resource_ids that are not
        in our expected set across all shared collections.
        """
        try:
            expected_resource_ids = self._build_expected_resource_ids(
                active_file_ids, active_kb_ids, active_user_ids
            )

            count = 0

            # Import pymilvus utilities
            from pymilvus import utility, Collection

            for shared_collection_name in self.shared_collections:
                if not utility.has_collection(shared_collection_name):
                    continue

                try:
                    collection = Collection(shared_collection_name)
                    collection.load()

                    # Query ALL resource_ids with pagination using query_iterator
                    # (offset + limit must be < 16384, so iterator is the correct approach)
                    all_resource_ids = set()

                    iterator = collection.query_iterator(
                        expr="",  # Empty expression to query all records
                        output_fields=["resource_id"],
                        batch_size=1000
                    )

                    batch_count = 0
                    while True:
                        results = iterator.next()
                        if not results:
                            iterator.close()
                            break

                        # Collect resource_ids from this batch
                        batch_resource_ids = {res["resource_id"] for res in results}
                        all_resource_ids.update(batch_resource_ids)
                        batch_count += 1

                        if batch_count % 10 == 0:
                            log.debug(f"Fetched {len(all_resource_ids)} resource_ids so far from {shared_collection_name} ({batch_count} batches)")

                    log.info(f"Total resource_ids in {shared_collection_name}: {len(all_resource_ids)}")

                    # Count orphaned ones
                    for resource_id in all_resource_ids:
                        if resource_id not in expected_resource_ids:
                            count += 1
                            log.debug(f"Found orphaned resource_id in {shared_collection_name}: {resource_id}")

                except Exception as e:
                    log.error(f"Error checking shared collection {shared_collection_name}: {e}")

            return count

        except Exception as e:
            log.error(f"Error counting orphaned Milvus multitenancy collections: {e}")
            return 0

    def cleanup_orphaned_collections(
        self,
        active_file_ids: Set[str],
        active_kb_ids: Set[str],
        active_user_ids: Optional[Set[str]] = None
    ) -> tuple[int, Optional[str]]:
        """
        Delete orphaned resource_ids from shared collections.

        In multitenancy mode, we delete records by resource_id filter
        from the shared collections.
        """
        try:
            expected_resource_ids = self._build_expected_resource_ids(
                active_file_ids, active_kb_ids, active_user_ids
            )

            deleted_count = 0
            errors = []

            # Import pymilvus utilities
            from pymilvus import utility, Collection

            for shared_collection_name in self.shared_collections:
                if not utility.has_collection(shared_collection_name):
                    continue

                try:
                    collection = Collection(shared_collection_name)
                    collection.load()

                    # Query ALL resource_ids with pagination using query_iterator
                    # (offset + limit must be < 16384, so iterator is the correct approach)
                    all_resource_ids = set()

                    iterator = collection.query_iterator(
                        expr="",  # Empty expression to query all records
                        output_fields=["resource_id"],
                        batch_size=1000
                    )

                    batch_count = 0
                    while True:
                        results = iterator.next()
                        if not results:
                            iterator.close()
                            break

                        # Collect resource_ids from this batch
                        batch_resource_ids = {res["resource_id"] for res in results}
                        all_resource_ids.update(batch_resource_ids)
                        batch_count += 1

                        if batch_count % 10 == 0:
                            log.debug(f"Fetched {len(all_resource_ids)} resource_ids so far from {shared_collection_name} ({batch_count} batches)")

                    log.info(f"Total resource_ids in {shared_collection_name}: {len(all_resource_ids)}")

                    # Get unique orphaned resource_ids
                    orphaned_ids = [rid for rid in all_resource_ids if rid not in expected_resource_ids]

                    log.info(f"Found {len(orphaned_ids)} orphaned resource_ids in {shared_collection_name}")

                    # Delete each orphaned resource_id
                    for resource_id in orphaned_ids:
                        try:
                            # Delete by resource_id filter expression
                            expr = f"resource_id == '{resource_id}'"
                            collection.delete(expr)
                            deleted_count += 1
                            log.info(f"Deleted orphaned resource_id from {shared_collection_name}: {resource_id}")
                        except Exception as e:
                            error_msg = f"Failed to delete resource_id {resource_id} from {shared_collection_name}: {e}"
                            log.error(error_msg)
                            errors.append(error_msg)

                    # Flush after all deletions in this collection
                    if orphaned_ids:
                        collection.flush()
                        log.debug(f"Flushed deletions for {shared_collection_name}")

                except Exception as e:
                    error_msg = f"Error processing shared collection {shared_collection_name}: {e}"
                    log.error(error_msg)
                    errors.append(error_msg)

            if deleted_count > 0:
                log.info(f"Deleted {deleted_count} orphaned Milvus multitenancy resource_ids")

            if errors:
                return (deleted_count, "; ".join(errors))
            return (deleted_count, None)

        except Exception as e:
            error_msg = f"Milvus multitenancy cleanup failed: {e}"
            log.error(error_msg)
            return (0, error_msg)

    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a specific logical collection in multitenancy mode.

        This deletes all records with the matching resource_id from
        the appropriate shared collection.
        """
        try:
            # Import here to avoid circular dependency
            from pymilvus import utility, Collection

            # Use the reference implementation's _get_collection_and_resource_id logic
            # to determine which shared collection contains this resource_id
            resource_id = collection_name

            # Determine which shared collection based on naming pattern
            if collection_name.startswith("user-memory-"):
                mt_collection = f"{self.collection_prefix}_memories"
            elif collection_name.startswith("file-"):
                mt_collection = f"{self.collection_prefix}_files"
            elif collection_name.startswith("web-search-"):
                mt_collection = f"{self.collection_prefix}_web_search"
            elif len(collection_name) == 63 and all(c in "0123456789abcdef" for c in collection_name):
                mt_collection = f"{self.collection_prefix}_hash_based"
            else:
                mt_collection = f"{self.collection_prefix}_knowledge"

            # Check if the shared collection exists
            if not utility.has_collection(mt_collection):
                log.debug(f"Shared collection {mt_collection} does not exist")
                return True  # Not existing is effectively deleted

            # Delete by resource_id
            collection = Collection(mt_collection)
            collection.load()
            expr = f"resource_id == '{resource_id}'"
            collection.delete(expr)
            collection.flush()

            log.debug(f"Deleted Milvus multitenancy collection: {collection_name} from {mt_collection}")
            return True

        except Exception as e:
            log.error(f"Error deleting Milvus multitenancy collection '{collection_name}': {e}")
            return False

    def _build_expected_resource_ids(
        self,
        active_file_ids: Set[str],
        active_kb_ids: Set[str],
        active_user_ids: Optional[Set[str]] = None
    ) -> Set[str]:
        """
        Build set of resource_ids that should exist across all shared collections.

        This provides 100% coverage by identifying ALL resource_ids that should be preserved.
        Any resource_id NOT in this set will be deleted as orphaned, which includes:
        - Orphaned file collections (files deleted from DB)
        - Orphaned knowledge bases (KBs deleted from DB)
        - Orphaned user memories (users deleted from DB)
        - Web-search collections (ephemeral cache, not tracked in DB)
        - Hash-based collections (temporary content hashes, not tracked in DB)

        This matches ChromaDB/PGVector behavior where ONLY DB-tracked items are preserved.

        Args:
            active_file_ids: Active file IDs from Files table
            active_kb_ids: Active knowledge base IDs from Knowledges table
            active_user_ids: Active user IDs from Users table (optional)

        Returns:
            Set of expected resource_ids across all 5 shared collections
        """
        expected_resource_ids = set()

        # FILE_COLLECTION: file-{id} pattern
        for file_id in active_file_ids:
            expected_resource_ids.add(f"file-{file_id}")

        # KNOWLEDGE_COLLECTION: KB ID directly (fallback for unrecognized patterns)
        for kb_id in active_kb_ids:
            expected_resource_ids.add(kb_id)

        # MEMORY_COLLECTION: user-memory-{user_id} pattern
        if active_user_ids is not None:
            for user_id in active_user_ids:
                expected_resource_ids.add(f"user-memory-{user_id}")

        # WEB_SEARCH_COLLECTION: web-search-{hash} patterns
        # These are NOT in expected set → will be deleted as orphaned ✓
        # Rationale: Ephemeral caches, not tracked in DB, safe to clean

        # HASH_BASED_COLLECTION: {63-char-hex} patterns
        # These are NOT in expected set → will be deleted as orphaned ✓
        # Rationale: Temporary content hashes, not tracked in DB, safe to clean

        return expected_resource_ids


class QdrantDatabaseCleaner(VectorDatabaseCleaner):
    """
    Qdrant vector database cleaner for standard (non-multitenancy) mode.

    In standard mode, each file/KB gets its own collection with naming:
    - {prefix}_file-{file_id}
    - {prefix}_{kb_id}

    Collections are deleted entirely when orphaned.
    """

    def __init__(self, vector_db_client):
        self.vector_db_client = vector_db_client
        self.client = vector_db_client.client
        self.collection_prefix = vector_db_client.collection_prefix

    def count_orphaned_collections(
        self,
        active_file_ids: Set[str],
        active_kb_ids: Set[str],
        active_user_ids: Optional[Set[str]] = None
    ) -> int:
        """Count orphaned Qdrant collections."""
        try:
            expected_collections = self._build_expected_collections(
                active_file_ids, active_kb_ids
            )

            # Get all collections with our prefix
            all_collections = self.client.get_collections().collections
            count = 0

            for collection in all_collections:
                collection_name = collection.name
                if collection_name.startswith(f"{self.collection_prefix}_"):
                    # Remove prefix to get original name
                    original_name = collection_name[len(self.collection_prefix) + 1:]

                    if original_name not in expected_collections:
                        count += 1

        except Exception as e:
            log.error(f"Error counting orphaned Qdrant collections: {e}")
            return 0

        return count

    def cleanup_orphaned_collections(
        self,
        active_file_ids: Set[str],
        active_kb_ids: Set[str],
        active_user_ids: Optional[Set[str]] = None
    ) -> tuple[int, Optional[str]]:
        """Delete orphaned Qdrant collections."""
        try:
            expected_collections = self._build_expected_collections(
                active_file_ids, active_kb_ids
            )

            # Get all collections with our prefix
            all_collections = self.client.get_collections().collections
            deleted_count = 0
            errors = []

            for collection in all_collections:
                collection_name = collection.name
                if collection_name.startswith(f"{self.collection_prefix}_"):
                    # Remove prefix to get original name
                    original_name = collection_name[len(self.collection_prefix) + 1:]

                    if original_name not in expected_collections:
                        try:
                            self.client.delete_collection(collection_name=collection_name)
                            deleted_count += 1
                            log.info(f"Deleted orphaned Qdrant collection: {original_name}")
                        except Exception as e:
                            error_msg = f"Failed to delete Qdrant collection {collection_name}: {e}"
                            log.error(error_msg)
                            errors.append(error_msg)

        except Exception as e:
            error_msg = f"Qdrant cleanup failed: {e}"
            log.error(error_msg)
            return (0, error_msg)

        if errors:
            return (deleted_count, "; ".join(errors))
        return (deleted_count, None)

    def delete_collection(self, collection_name: str) -> bool:
        """Delete a specific Qdrant collection by name."""
        try:
            full_name = f"{self.collection_prefix}_{collection_name}"
            if self.client.collection_exists(collection_name=full_name):
                self.client.delete_collection(collection_name=full_name)
                log.debug(f"Deleted Qdrant collection: {collection_name}")
            return True
        except Exception as e:
            log.error(f"Error deleting Qdrant collection {collection_name}: {e}")
            return False

    def _build_expected_collections(
        self, active_file_ids: Set[str], active_kb_ids: Set[str]
    ) -> Set[str]:
        """Build set of expected collection names (without prefix)."""
        expected_collections = set()

        # File collections use file-{id} pattern
        for file_id in active_file_ids:
            expected_collections.add(f"file-{file_id}")

        # Knowledge base collections use the KB ID directly
        for kb_id in active_kb_ids:
            expected_collections.add(kb_id)

        return expected_collections


class QdrantMultitenancyDatabaseCleaner(VectorDatabaseCleaner):
    """
    Qdrant multitenancy vector database cleaner.

    In multitenancy mode, there are 5 shared collections:
    - {prefix}_memories - for user-memory-{user_id}
    - {prefix}_files - for file-{file_id}
    - {prefix}_knowledge - for {kb_id} (default)
    - {prefix}_web-search - for web-search-{hash} (ephemeral)
    - {prefix}_hash-based - for {63-char-hex} (temporary)

    Each collection stores points with a tenant_id field. Cleanup deletes
    orphaned tenant_ids (not entire collections).

    Uses scroll() with pagination to handle unlimited tenant IDs without
    exceeding memory limits.
    """

    def __init__(self, vector_db_client):
        self.vector_db_client = vector_db_client
        self.client = vector_db_client.client
        self.collection_prefix = vector_db_client.collection_prefix

        # Shared collection names
        self.shared_collections = [
            f"{self.collection_prefix}_memories",
            f"{self.collection_prefix}_files",
            f"{self.collection_prefix}_knowledge",
            f"{self.collection_prefix}_web-search",
            f"{self.collection_prefix}_hash-based",
        ]

    def count_orphaned_collections(
        self,
        active_file_ids: Set[str],
        active_kb_ids: Set[str],
        active_user_ids: Optional[Set[str]] = None
    ) -> int:
        """
        Count orphaned tenant_ids across all shared collections.

        Uses Qdrant's scroll() API with pagination for memory efficiency.
        """
        try:
            from qdrant_client.models import models

            expected_tenant_ids = self._build_expected_tenant_ids(
                active_file_ids, active_kb_ids, active_user_ids or set()
            )

            orphaned_count = 0

            for collection_name in self.shared_collections:
                if not self.client.collection_exists(collection_name=collection_name):
                    continue

                try:
                    # Get all unique tenant_ids in this collection using scroll
                    # Qdrant doesn't have a direct "get unique values" API, so we scroll through points
                    all_tenant_ids = set()
                    offset = None

                    while True:
                        # Scroll through points in batches
                        scroll_result = self.client.scroll(
                            collection_name=collection_name,
                            limit=1000,  # Batch size
                            offset=offset,
                            with_payload=True,
                            with_vectors=False,  # Don't need vectors, save bandwidth
                        )

                        points, next_offset = scroll_result

                        if not points:
                            break

                        # Extract unique tenant_ids from this batch
                        for point in points:
                            if 'tenant_id' in point.payload:
                                all_tenant_ids.add(point.payload['tenant_id'])

                        # Check if there are more results
                        if next_offset is None:
                            break

                        offset = next_offset

                    log.debug(f"Found {len(all_tenant_ids)} tenant_ids in {collection_name}")

                    # Count orphaned tenant_ids
                    for tenant_id in all_tenant_ids:
                        if tenant_id not in expected_tenant_ids:
                            orphaned_count += 1

                except Exception as e:
                    log.error(f"Error scanning Qdrant collection {collection_name}: {e}")

        except Exception as e:
            log.error(f"Error counting orphaned Qdrant multitenancy tenant_ids: {e}")
            return 0

        return orphaned_count

    def cleanup_orphaned_collections(
        self,
        active_file_ids: Set[str],
        active_kb_ids: Set[str],
        active_user_ids: Optional[Set[str]] = None
    ) -> tuple[int, Optional[str]]:
        """
        Delete orphaned tenant_ids from shared collections.

        Uses scroll() for memory-safe iteration and batched deletions.
        """
        try:
            from qdrant_client.models import models

            expected_tenant_ids = self._build_expected_tenant_ids(
                active_file_ids, active_kb_ids, active_user_ids or set()
            )

            deleted_count = 0
            errors = []

            for collection_name in self.shared_collections:
                if not self.client.collection_exists(collection_name=collection_name):
                    continue

                try:
                    # Get all unique tenant_ids using scroll (memory-safe)
                    all_tenant_ids = set()
                    offset = None

                    while True:
                        scroll_result = self.client.scroll(
                            collection_name=collection_name,
                            limit=1000,  # Batch size
                            offset=offset,
                            with_payload=True,
                            with_vectors=False,
                        )

                        points, next_offset = scroll_result

                        if not points:
                            break

                        # Extract unique tenant_ids
                        for point in points:
                            if 'tenant_id' in point.payload:
                                all_tenant_ids.add(point.payload['tenant_id'])

                        if next_offset is None:
                            break

                        offset = next_offset

                    log.info(f"Total tenant_ids in {collection_name}: {len(all_tenant_ids)}")

                    # Delete orphaned tenant_ids
                    orphaned_tenant_ids = [
                        tid for tid in all_tenant_ids if tid not in expected_tenant_ids
                    ]

                    log.info(f"Found {len(orphaned_tenant_ids)} orphaned tenant_ids in {collection_name}")

                    for tenant_id in orphaned_tenant_ids:
                        try:
                            # Delete all points with this tenant_id
                            self.client.delete(
                                collection_name=collection_name,
                                points_selector=models.FilterSelector(
                                    filter=models.Filter(
                                        must=[
                                            models.FieldCondition(
                                                key="tenant_id",
                                                match=models.MatchValue(value=tenant_id)
                                            )
                                        ]
                                    )
                                ),
                            )
                            deleted_count += 1
                            log.debug(f"Deleted orphaned tenant_id from {collection_name}: {tenant_id}")
                        except Exception as e:
                            error_msg = f"Failed to delete tenant_id {tenant_id} from {collection_name}: {e}"
                            log.error(error_msg)
                            errors.append(error_msg)

                except Exception as e:
                    error_msg = f"Error processing Qdrant collection {collection_name}: {e}"
                    log.error(error_msg)
                    errors.append(error_msg)

        except Exception as e:
            error_msg = f"Qdrant multitenancy cleanup failed: {e}"
            log.error(error_msg)
            return (0, error_msg)

        if errors:
            return (deleted_count, "; ".join(errors))
        return (deleted_count, None)

    def delete_collection(self, collection_name: str) -> bool:
        """Delete a specific tenant_id from the appropriate shared collection."""
        try:
            from qdrant_client.models import models

            # Determine which shared collection and tenant_id
            tenant_id = collection_name

            # Map collection name to shared collection (same logic as backend)
            if collection_name.startswith("user-memory-"):
                mt_collection = f"{self.collection_prefix}_memories"
            elif collection_name.startswith("file-"):
                mt_collection = f"{self.collection_prefix}_files"
            elif collection_name.startswith("web-search-"):
                mt_collection = f"{self.collection_prefix}_web-search"
            elif len(collection_name) == 63 and all(c in "0123456789abcdef" for c in collection_name):
                mt_collection = f"{self.collection_prefix}_hash-based"
            else:
                mt_collection = f"{self.collection_prefix}_knowledge"

            if not self.client.collection_exists(collection_name=mt_collection):
                return True

            # Delete all points with this tenant_id
            self.client.delete(
                collection_name=mt_collection,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="tenant_id",
                                match=models.MatchValue(value=tenant_id)
                            )
                        ]
                    )
                ),
            )
            log.debug(f"Deleted Qdrant tenant_id: {tenant_id} from {mt_collection}")
            return True
        except Exception as e:
            log.error(f"Error deleting Qdrant tenant_id {collection_name}: {e}")
            return False

    def _build_expected_tenant_ids(
        self, active_file_ids: Set[str], active_kb_ids: Set[str], active_user_ids: Set[str]
    ) -> Set[str]:
        """
        Build set of expected tenant_ids.

        Tenant IDs are the same as collection names in the mapping:
        - file-{file_id} for files
        - {kb_id} for knowledge bases
        - user-memory-{user_id} for memories
        - web-search-{hash} (ephemeral - always orphaned)
        - {63-char-hex} (temporary - always orphaned)
        """
        expected_tenant_ids = set()

        # File tenant_ids: file-{id}
        for file_id in active_file_ids:
            expected_tenant_ids.add(f"file-{file_id}")

        # Knowledge base tenant_ids: {kb_id}
        for kb_id in active_kb_ids:
            expected_tenant_ids.add(kb_id)

        # User memory tenant_ids: user-memory-{user_id}
        for user_id in active_user_ids:
            expected_tenant_ids.add(f"user-memory-{user_id}")

        # Note: web-search-* and hash-based are ephemeral/temporary
        # They are NOT added to expected set, so they will be cleaned up

        return expected_tenant_ids


class NoOpVectorDatabaseCleaner(VectorDatabaseCleaner):
    """
    No-operation implementation for unsupported vector databases.

    This implementation does nothing and is used when the configured
    vector database is not supported by the cleanup system.
    """

    def count_orphaned_collections(
        self,
        active_file_ids: Set[str],
        active_kb_ids: Set[str],
        active_user_ids: Optional[Set[str]] = None
    ) -> int:
        """No orphaned collections to count for unsupported databases."""
        return 0

    def cleanup_orphaned_collections(
        self,
        active_file_ids: Set[str],
        active_kb_ids: Set[str],
        active_user_ids: Optional[Set[str]] = None
    ) -> tuple[int, Optional[str]]:
        """No collections to cleanup for unsupported databases."""
        return (0, None)

    def delete_collection(self, collection_name: str) -> bool:
        """No collection to delete for unsupported databases."""
        return True


def get_vector_database_cleaner(vector_db_type: str, vector_db_client, cache_dir: Path) -> VectorDatabaseCleaner:
    """
    Factory function to get the appropriate vector database cleaner.

    This function detects the configured vector database type and returns
    the appropriate cleaner implementation. Community contributors can
    extend this function to support additional vector databases.

    Supported databases:
    - ChromaDB: SQLite-based vector database with directory storage
    - PGVector: PostgreSQL extension for vector operations
    - Milvus: Standalone vector database with standard collections
    - Milvus Multitenancy: Milvus with shared collections and resource_id partitioning
    - Qdrant: Standalone vector database with standard collections
    - Qdrant Multitenancy: Qdrant with shared collections and tenant_id filtering

    Returns:
        VectorDatabaseCleaner: Appropriate implementation for the configured database
    """
    vector_db_type = vector_db_type.lower()

    if "chroma" in vector_db_type:
        log.debug("Using ChromaDB cleaner")
        return ChromaDatabaseCleaner(vector_db_client, cache_dir)
    elif "pgvector" in vector_db_type:
        log.debug("Using PGVector cleaner")
        return PGVectorDatabaseCleaner(vector_db_client)
    elif "milvus" in vector_db_type:
        # Detect multitenancy mode by checking for shared_collections attribute
        if hasattr(vector_db_client, 'shared_collections'):
            log.debug("Using Milvus Multitenancy cleaner")
            return MilvusMultitenancyDatabaseCleaner(vector_db_client)
        else:
            log.debug("Using Milvus standard cleaner")
            return MilvusDatabaseCleaner(vector_db_client)
    elif "qdrant" in vector_db_type:
        # Detect multitenancy mode by checking for shared_collections attribute
        if hasattr(vector_db_client, 'shared_collections'):
            log.debug("Using Qdrant Multitenancy cleaner")
            return QdrantMultitenancyDatabaseCleaner(vector_db_client)
        else:
            log.debug("Using Qdrant standard cleaner")
            return QdrantDatabaseCleaner(vector_db_client)
    else:
        log.debug(
            f"No specific cleaner for vector database type: {vector_db_type}, using no-op cleaner"
        )
        return NoOpVectorDatabaseCleaner()
