"""
Prune Operations - All Helper Functions

This module contains all the helper functions from backend/open_webui/routers/prune.py
that perform the actual pruning operations, counting, and cleanup.
"""

import sys
import os
import logging
import time
from pathlib import Path
from typing import Optional, Set
from sqlalchemy import select, text

log = logging.getLogger(__name__)

# Add parent directory to path to import Open WebUI modules
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

try:
    from backend.open_webui.models.users import Users
    from backend.open_webui.models.chats import Chat, Chats
    from backend.open_webui.models.messages import Message
    from backend.open_webui.models.files import Files
    from backend.open_webui.models.notes import Notes
    from backend.open_webui.models.prompts import Prompts
    from backend.open_webui.models.models import Models
    from backend.open_webui.models.knowledge import Knowledges
    from backend.open_webui.models.functions import Functions
    from backend.open_webui.models.tools import Tools
    from backend.open_webui.models.folders import Folder, Folders
    from backend.open_webui.internal.db import get_db
    from backend.open_webui.config import CACHE_DIR
except ImportError as e:
    log.error(f"Failed to import Open WebUI modules: {e}")
    log.error("This module requires Open WebUI backend modules to be importable")
    raise

from prune_models import PruneDataForm
from prune_core import collect_file_ids_from_dict


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
        all_file_ids = {f.id for f in Files.get_files()}
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
        chat_count = 0
        with get_db() as db:
            stmt = select(Chat.id, Chat.chat)
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

        log.debug(f"Scanned {chat_count} chats for file references")

        # Scan folders for file references
        # Stream folders using Core SELECT to avoid ORM overhead
        try:
            with get_db() as db:
                stmt = select(Folder.id, Folder.items, Folder.data)
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

                stat_info = file_path.stat()
                file_mtime = stat_info.st_mtime
                if file_mtime < cutoff_time:
                    try:
                        file_size = stat_info.st_size
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
