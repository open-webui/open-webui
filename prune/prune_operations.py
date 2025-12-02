"""
Prune Operations - All Helper Functions

This module contains all the helper functions from backend/open_webui/routers/prune.py
that perform the actual pruning operations, counting, and cleanup.
"""

import logging
import time
from pathlib import Path
from typing import Optional, Set, Callable, Any
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError

log = logging.getLogger(__name__)


def retry_on_db_lock(func: Callable, max_retries: int = 3, base_delay: float = 0.5) -> Any:
    """
    Retry a database operation if it fails due to database lock.
    Uses exponential backoff: 0.5s, 1s, 2s

    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds (doubles each retry)

    Returns:
        Result from the function

    Raises:
        Last exception if all retries fail
    """
    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            return func()
        except OperationalError as e:
            last_exception = e
            if 'database is locked' in str(e).lower() and attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                log.warning(f"Database locked, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                raise

    # This should never be reached, but just in case
    raise last_exception

# Import Open WebUI modules using compatibility layer (handles pip/docker/git installs)
try:
    from prune_imports import (
        Users, Chat, Chats, Message, Files, Notes, Prompts, Models,
        Knowledges, Functions, Tools, Folder, Folders, get_db, CACHE_DIR
    )
except ImportError as e:
    log.error(f"Failed to import Open WebUI modules: {e}")
    log.error("This module requires Open WebUI backend modules to be importable")
    raise

from prune_models import PruneDataForm
from prune_core import collect_file_ids_from_dict


# API Compatibility Helpers
def get_all_folders():
    """
    Get all folders from database.
    Compatibility helper for newer Folders API that doesn't have get_all_folders().
    """
    try:
        from prune_imports import Folder as FolderORM, FolderModel, get_db, Folders

        # Try new API first - if get_all_folders exists, use it
        if hasattr(Folders, 'get_all_folders'):
            return Folders.get_all_folders()

        # Otherwise query directly from database
        with get_db() as db:
            folders = db.query(FolderORM).all()
            # Convert to FolderModel instances
            return [FolderModel.model_validate(f) for f in folders]
    except Exception as e:
        log.error(f"Error getting all folders: {e}")
        return []


def count_inactive_users(
    inactive_days: Optional[int], exempt_admin: bool, exempt_pending: bool, all_users=None
) -> int:
    """Count users that would be deleted for inactivity.

    Args:
        inactive_days: Number of days of inactivity before deletion
        exempt_admin: Whether to exempt admin users
        exempt_pending: Whether to exempt pending users
        all_users: Optional pre-fetched list of users to avoid duplicate queries
    """
    if inactive_days is None:
        return 0

    cutoff_time = int(time.time()) - (inactive_days * 86400)
    count = 0

    try:
        if all_users is None:
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


def count_orphaned_records(
    form_data: PruneDataForm,
    active_file_ids: Set[str],
    active_user_ids: Set[str]
) -> dict:
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
            for folder in get_all_folders():
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


def get_active_file_ids(knowledge_bases=None) -> Set[str]:
    """
    Get all file IDs that are actively referenced by knowledge bases, chats, folders, and messages.

    Args:
        knowledge_bases: Optional pre-fetched list of knowledge bases to avoid duplicate queries
    """
    active_file_ids = set()

    try:
        # Preload all valid file IDs to avoid N database queries during validation
        # This is O(1) set lookup instead of O(n) DB queries
        # Use retry logic in case database is locked
        all_file_ids = retry_on_db_lock(lambda: {f.id for f in Files.get_files()})
        log.debug(f"Preloaded {len(all_file_ids)} file IDs for validation")

        # Scan knowledge bases for file references
        if knowledge_bases is None:
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
                    stripped_id = file_id.strip()
                    # Validate against preloaded set (O(1) lookup)
                    if stripped_id in all_file_ids:
                        active_file_ids.add(stripped_id)

        # Scan chats for file references
        # Stream chats using Core SELECT to avoid ORM overhead
        # Wrap in retry logic in case of database lock
        def scan_chats():
            chat_count = 0
            with get_db() as db:
                stmt = select(Chat.id, Chat.chat)
                # SQLAlchemy 2.0+ compatibility: execution_options moved to statement
                try:
                    result = db.execute(stmt.execution_options(stream_results=True))
                except AttributeError:
                    # Fallback for older SQLAlchemy versions
                    result = db.execution_options(stream_results=True).execute(stmt)

                while True:
                    rows = result.fetchmany(1000)
                    if not rows:
                        break

                    for chat_id, chat_dict in rows:
                        chat_count += 1

                        # Skip if no chat data or not a dict
                        if not chat_dict or not isinstance(chat_dict, dict):
                            continue

                        try:
                            # Direct dict traversal (no json.dumps needed)
                            collect_file_ids_from_dict(chat_dict, active_file_ids, all_file_ids)
                        except Exception as e:
                            log.debug(f"Error processing chat {chat_id} for file references: {e}")

            return chat_count

        chat_count = retry_on_db_lock(scan_chats)
        log.debug(f"Scanned {chat_count} chats for file references")

        # Scan folders for file references
        # Stream folders using Core SELECT to avoid ORM overhead
        try:
            with get_db() as db:
                stmt = select(Folder.id, Folder.items, Folder.data)
                # SQLAlchemy 2.0+ compatibility: execution_options moved to statement
                try:
                    result = db.execute(stmt.execution_options(stream_results=True))
                except AttributeError:
                    # Fallback for older SQLAlchemy versions
                    result = db.execution_options(stream_results=True).execute(stmt)

                while True:
                    rows = result.fetchmany(100)
                    if not rows:
                        break

                    for folder_id, items_dict, data_dict in rows:
                        # Process folder.items
                        if items_dict:
                            try:
                                # Direct dict traversal (no json.dumps needed)
                                collect_file_ids_from_dict(items_dict, active_file_ids, all_file_ids)
                            except Exception as e:
                                log.debug(f"Error processing folder {folder_id} items: {e}")

                        # Process folder.data
                        if data_dict:
                            try:
                                # Direct dict traversal (no json.dumps needed)
                                collect_file_ids_from_dict(data_dict, active_file_ids, all_file_ids)
                            except Exception as e:
                                log.debug(f"Error processing folder {folder_id} data: {e}")

        except Exception as e:
            log.debug(f"Error scanning folders for file references: {e}")

        # Scan standalone messages for file references
        # Stream messages using Core SELECT to avoid text() and yield_per issues
        try:
            with get_db() as db:
                stmt = select(Message.id, Message.data).where(Message.data.isnot(None))
                # SQLAlchemy 2.0+ compatibility: execution_options moved to statement
                try:
                    result = db.execute(stmt.execution_options(stream_results=True))
                except AttributeError:
                    # Fallback for older SQLAlchemy versions
                    result = db.execution_options(stream_results=True).execute(stmt)

                while True:
                    rows = result.fetchmany(1000)
                    if not rows:
                        break

                    for message_id, message_data_dict in rows:
                        if message_data_dict:
                            try:
                                # Direct dict traversal (no json.dumps needed)
                                collect_file_ids_from_dict(message_data_dict, active_file_ids, all_file_ids)
                            except Exception as e:
                                log.debug(f"Error processing message {message_id} data: {e}")

        except Exception as e:
            log.debug(f"Error scanning messages for file references: {e}")

    except Exception as e:
        log.error(f"Error determining active file IDs: {e}")
        return set()

    log.info(f"Found {len(active_file_ids)} active file IDs")
    return active_file_ids


def safe_delete_file_by_id(file_id: str, vector_cleaner) -> bool:
    """
    Safely delete a file record and its associated vector collection.
    """
    try:
        file_record = Files.get_file_by_id(file_id)
        if not file_record:
            return True

        # Use modular vector database cleaner
        collection_name = f"file-{file_id}"
        vector_cleaner.delete_collection(collection_name)

        Files.delete_file_by_id(file_id)
        return True

    except Exception as e:
        log.error(f"Error deleting file {file_id}: {e}")
        return False


def cleanup_orphaned_uploads(active_file_ids: Set[str]) -> int:
    """
    Clean up orphaned files in the uploads directory.

    Returns the number of files deleted.
    """
    upload_dir = Path(CACHE_DIR).parent / "uploads"
    if not upload_dir.exists():
        return 0

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

    return deleted_count


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


def cleanup_audio_cache(max_age_days: Optional[int] = 30) -> int:
    """
    Clean up audio cache files older than specified days.

    Returns:
        Number of files deleted
    """
    if max_age_days is None:
        log.info("Skipping audio cache cleanup (max_age_days is None)")
        return 0

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

                stat_info = file_path.stat()
                file_mtime = stat_info.st_mtime
                if file_mtime < cutoff_time:
                    try:
                        file_size = stat_info.st_size
                        file_path.unlink()
                        deleted_count += 1
                        total_size_deleted += file_size
                        log.debug(f"Deleted audio cache file: {file_path} ({file_size} bytes)")
                    except Exception as e:
                        log.error(f"Failed to delete audio file {file_path}: {e}")

        except Exception as e:
            log.error(f"Error cleaning audio directory {audio_dir}: {e}")

    log.info(f"Audio cache cleanup: deleted {deleted_count} files, freed {total_size_deleted} bytes")
    return deleted_count
