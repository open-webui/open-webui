import logging
import time
import os
import shutil
import json
import re
from typing import Optional, Set
from pathlib import Path

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
                
                # Extract file IDs using regex patterns
                file_id_pattern = re.compile(r'"id":\s*"([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})"')
                url_pattern = re.compile(r'/api/v1/files/([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})')
                
                potential_file_ids = file_id_pattern.findall(chat_json_str)
                url_file_ids = url_pattern.findall(chat_json_str)
                
                all_potential_ids = set(potential_file_ids + url_file_ids)
                for file_id in all_potential_ids:
                    if Files.get_file_by_id(file_id):
                        active_file_ids.add(file_id)
                        
            except Exception as e:
                log.debug(f"Error processing chat {chat.id} for file references: {e}")

        # Scan folders for file references
        try:
            folders = Folders.get_all_folders()
            
            for folder in folders:
                if folder.items:
                    try:
                        items_str = json.dumps(folder.items)
                        file_id_pattern = re.compile(r'"id":\s*"([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})"')
                        url_pattern = re.compile(r'/api/v1/files/([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})')
                        
                        potential_ids = file_id_pattern.findall(items_str) + url_pattern.findall(items_str)
                        for file_id in potential_ids:
                            if Files.get_file_by_id(file_id):
                                active_file_ids.add(file_id)
                    except Exception as e:
                        log.debug(f"Error processing folder {folder.id} items: {e}")
                
                if hasattr(folder, 'data') and folder.data:
                    try:
                        data_str = json.dumps(folder.data)
                        file_id_pattern = re.compile(r'"id":\s*"([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})"')
                        url_pattern = re.compile(r'/api/v1/files/([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})')
                        
                        potential_ids = file_id_pattern.findall(data_str) + url_pattern.findall(data_str)
                        for file_id in potential_ids:
                            if Files.get_file_by_id(file_id):
                                active_file_ids.add(file_id)
                    except Exception as e:
                        log.debug(f"Error processing folder {folder.id} data: {e}")
                        
        except Exception as e:
            log.debug(f"Error scanning folders for file references: {e}")

        # Scan standalone messages for file references
        try:
            with get_db() as db:
                message_results = db.execute(text("SELECT id, data FROM message WHERE data IS NOT NULL")).fetchall()
                
                for message_id, message_data_json in message_results:
                    if message_data_json:
                        try:
                            data_str = json.dumps(message_data_json) if isinstance(message_data_json, dict) else str(message_data_json)
                            
                            file_id_pattern = re.compile(r'"id":\s*"([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})"')
                            url_pattern = re.compile(r'/api/v1/files/([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})')
                            
                            potential_ids = file_id_pattern.findall(data_str) + url_pattern.findall(data_str)
                            for file_id in potential_ids:
                                if Files.get_file_by_id(file_id):
                                    active_file_ids.add(file_id)
                        except Exception as e:
                            log.debug(f"Error processing message {message_id} data: {e}")
        except Exception as e:
            log.debug(f"Error scanning messages for file references: {e}")
    
    except Exception as e:
        log.error(f"Error determining active file IDs: {e}")
        return set()
    
    log.info(f"Found {len(active_file_ids)} active file IDs")
    return active_file_ids


def safe_delete_vector_collection(collection_name: str) -> bool:
    """
    Safely delete a vector collection, handling both logical and physical cleanup.
    """
    try:
        try:
            VECTOR_DB_CLIENT.delete_collection(collection_name=collection_name)
        except Exception as e:
            log.debug(f"Collection {collection_name} may not exist in DB: {e}")
        
        if "chroma" in VECTOR_DB.lower():
            vector_dir = Path(CACHE_DIR).parent / "vector_db" / collection_name
            if vector_dir.exists() and vector_dir.is_dir():
                shutil.rmtree(vector_dir)
                return True
        
        return True
        
    except Exception as e:
        log.error(f"Error deleting vector collection {collection_name}: {e}")
        return False


def safe_delete_file_by_id(file_id: str) -> bool:
    """
    Safely delete a file record and its associated vector collection.
    """
    try:
        file_record = Files.get_file_by_id(file_id)
        if not file_record:
            return True
        
        collection_name = f"file-{file_id}"
        safe_delete_vector_collection(collection_name)
        
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
                if potential_id.count('-') == 4:
                    file_id = potential_id
            
            if not file_id and filename.count('-') == 4 and len(filename) == 36:
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


def cleanup_orphaned_vector_collections(active_file_ids: Set[str], active_kb_ids: Set[str]) -> None:
    """
    Clean up orphaned vector collections by querying ChromaDB metadata.
    """
    if "chroma" not in VECTOR_DB.lower():
        return
    
    vector_dir = Path(CACHE_DIR).parent / "vector_db"
    if not vector_dir.exists():
        return
    
    chroma_db_path = vector_dir / "chroma.sqlite3"
    if not chroma_db_path.exists():
        return
    
    expected_collections = set()
    
    for file_id in active_file_ids:
        expected_collections.add(f"file-{file_id}")
    
    for kb_id in active_kb_ids:
        expected_collections.add(kb_id)
    
    uuid_to_collection = {}
    try:
        import sqlite3
        
        with sqlite3.connect(str(chroma_db_path)) as conn:
            collection_id_to_name = {}
            cursor = conn.execute("SELECT id, name FROM collections")
            rows = cursor.fetchall()
            
            for row in rows:
                collection_id, collection_name = row
                collection_id_to_name[collection_id] = collection_name
            
            cursor = conn.execute("SELECT id, collection FROM segments WHERE scope = 'VECTOR'")
            segment_rows = cursor.fetchall()
            
            for row in segment_rows:
                segment_id, collection_id = row
                if collection_id in collection_id_to_name:
                    collection_name = collection_id_to_name[collection_id]
                    uuid_to_collection[segment_id] = collection_name
        
        log.info(f"Found {len(uuid_to_collection)} vector segments in ChromaDB metadata")
        
    except Exception as e:
        log.error(f"Error reading ChromaDB metadata: {e}")
        return
    
    deleted_count = 0
    
    try:
        for collection_dir in vector_dir.iterdir():
            if not collection_dir.is_dir():
                continue
                
            dir_uuid = collection_dir.name
            
            if dir_uuid.startswith('.'):
                continue
            
            collection_name = uuid_to_collection.get(dir_uuid)
            
            if collection_name is None:
                try:
                    shutil.rmtree(collection_dir)
                    deleted_count += 1
                except Exception as e:
                    log.error(f"Failed to delete orphaned directory {dir_uuid}: {e}")
            
            elif collection_name not in expected_collections:
                try:
                    shutil.rmtree(collection_dir)
                    deleted_count += 1
                except Exception as e:
                    log.error(f"Failed to delete collection directory {dir_uuid}: {e}")
    
    except Exception as e:
        log.error(f"Error cleaning vector collections: {e}")
    
    if deleted_count > 0:
        log.info(f"Deleted {deleted_count} orphaned vector collections")


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
        Path(CACHE_DIR) / "audio" / "transcriptions"
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
        log.info(f"Deleted {deleted_count} audio cache files ({size_mb:.1f} MB), older than {max_age_days} days")


@router.post("/", response_model=bool)
async def prune_data(form_data: PruneDataForm, user=Depends(get_admin_user)):
    """
    Prunes old and orphaned data using a safe, multi-stage process.
    
    Parameters:
    - days: Optional[int] = None
      - If None: Skip chat deletion entirely
      - If 0: Delete all chats (older than 0 days = all chats)
      - If >= 1: Delete chats older than specified number of days
    - exempt_archived_chats: bool = False
      - If True: Exempt archived chats from deletion (only applies when days is not None)
    - exempt_chats_in_folders: bool = False
      - If True: Exempt chats that are in folders OR pinned chats from deletion (only applies when days is not None)
        Note: Pinned chats behave the same as chats in folders
    - delete_orphaned_chats: bool = True
      - If True: Delete chats from deleted users
    - delete_orphaned_tools: bool = True
      - If True: Delete tools from deleted users
    - delete_orphaned_functions: bool = True
      - If True: Delete functions from deleted users
    - delete_orphaned_prompts: bool = True
      - If True: Delete prompts from deleted users
    - delete_orphaned_knowledge_bases: bool = True
      - If True: Delete knowledge bases from deleted users
    - delete_orphaned_models: bool = True
      - If True: Delete models from deleted users
    - delete_orphaned_notes: bool = True
      - If True: Delete notes from deleted users
    - delete_orphaned_folders: bool = True
      - If True: Delete folders from deleted users
    - audio_cache_max_age_days: Optional[int] = 30
      - If None: Skip audio cache cleanup
      - If >= 0: Delete audio cache files (TTS, STT) older than specified days
    """
    try:
        log.info("Starting data pruning process")
        
        # Stage 1: Delete old chats based on user criteria
        if form_data.days is not None:
            cutoff_time = int(time.time()) - (form_data.days * 86400)
            chats_to_delete = []
            
            for chat in Chats.get_chats():
                if chat.updated_at < cutoff_time:
                    if form_data.exempt_archived_chats and chat.archived:
                        continue
                    if form_data.exempt_chats_in_folders and (getattr(chat, 'folder_id', None) is not None or getattr(chat, 'pinned', False)):
                        continue
                    chats_to_delete.append(chat)
            
            if chats_to_delete:
                log.info(f"Deleting {len(chats_to_delete)} old chats (older than {form_data.days} days)")
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
                file_record.id not in active_file_ids or 
                file_record.user_id not in active_user_ids
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
                    if safe_delete_vector_collection(kb.id):
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
                    Folders.delete_folder_by_id_and_user_id(folder.id, folder.user_id, delete_chats=False)
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
        cleanup_orphaned_vector_collections(final_active_file_ids, final_active_kb_ids)
        
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
        
        if "chroma" in VECTOR_DB.lower():
            chroma_db_path = Path(CACHE_DIR).parent / "vector_db" / "chroma.sqlite3"
            if chroma_db_path.exists():
                try:
                    import sqlite3
                    with sqlite3.connect(str(chroma_db_path)) as conn:
                        conn.execute("VACUUM")
                except Exception as e:
                    log.error(f"Failed to vacuum ChromaDB database: {e}")
        
        log.info("Data pruning completed successfully")
        return True
        
    except Exception as e:
        log.exception(f"Error during data pruning: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT("Data pruning failed"),
        )
