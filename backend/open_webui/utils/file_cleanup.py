"""
File cleanup utilities for chat deletion operations.
Handles reference counting and safe file removal.
"""

import os
import logging
from typing import List, Dict, Set
from open_webui.models.files import Files
from open_webui.models.chats import Chats
from open_webui.config import DATA_DIR

log = logging.getLogger(__name__)

class FileCleanupManager:
    """Manages file cleanup operations with reference counting."""
    
    def __init__(self):
        self.files_model = Files
        self.chats_model = Chats
    
    def get_chat_file_references(self, chat_id: str) -> Set[str]:
        """Extract all file IDs referenced in a chat."""
        chat = self.chats_model.get_chat_by_id(chat_id)
        if not chat:
            return set()
        
        file_ids = set()
        
        # Check metadata files
        metadata_files = chat.meta.get('files', []) if chat.meta else []
        for file_ref in metadata_files:
            if isinstance(file_ref, dict) and 'id' in file_ref:
                file_ids.add(file_ref['id'])
        
        # Check message files
        messages = chat.chat.get('messages', {})
        for message in messages.values():
            if message.get('files'):
                for file_ref in message['files']:
                    if isinstance(file_ref, dict) and 'id' in file_ref:
                        file_ids.add(file_ref['id'])
        
        return file_ids
    
    def count_file_references(self, file_id: str) -> int:
        """Count how many chats reference a specific file."""
        all_chats = self.chats_model.get_chats()
        reference_count = 0
        
        for chat in all_chats:
            chat_file_refs = self.get_chat_file_references(chat.id)
            if file_id in chat_file_refs:
                reference_count += 1
        
        return reference_count
    
    def get_orphaned_files(self, file_ids: Set[str]) -> Set[str]:
        """Identify files that are only referenced by the chat being deleted."""
        orphaned_files = set()
        
        for file_id in file_ids:
            if self.count_file_references(file_id) <= 1:
                orphaned_files.add(file_id)
        
        return orphaned_files
    
    def cleanup_file_images(self, file_id: str) -> bool:
        """Remove extracted images for a specific file."""
        try:
            file_model = self.files_model.get_file_by_id(file_id)
            if not file_model or not file_model.image_refs:
                return True
            
            deleted_count = 0
            for image_ref in file_model.image_refs:
                image_path = os.path.join(DATA_DIR, image_ref)
                if os.path.exists(image_path):
                    os.remove(image_path)
                    deleted_count += 1
                    log.info(f"Deleted image: {image_path}")
            
            log.info(f"Cleaned up {deleted_count} images for file {file_id}")
            return True
            
        except Exception as e:
            log.error(f"Failed to cleanup images for file {file_id}: {e}")
            return False
    
    def cleanup_file_data(self, file_id: str) -> bool:
        """Remove file data and database record."""
        try:
            file_model = self.files_model.get_file_by_id(file_id)
            if not file_model:
                return True
            
            # Remove physical file if it exists
            if file_model.path:
                file_path = os.path.join(DATA_DIR, file_model.path)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    log.info(f"Deleted file: {file_path}")
            
            # Remove database record
            success = self.files_model.delete_file_by_id(file_id)
            if success:
                log.info(f"Deleted file record: {file_id}")
            
            return success
            
        except Exception as e:
            log.error(f"Failed to cleanup file data for {file_id}: {e}")
            return False
    
    def cleanup_chat_files(self, chat_id: str) -> Dict[str, bool]:
        """Clean up all files associated with a chat."""
        results = {
            'files_processed': 0,
            'files_deleted': 0,
            'images_cleaned': 0,
            'errors': []
        }
        
        try:
            # Get all file references from the chat
            file_refs = self.get_chat_file_references(chat_id)
            results['files_processed'] = len(file_refs)
            
            if not file_refs:
                log.info(f"No files to cleanup for chat {chat_id}")
                return results
            
            # Identify orphaned files
            orphaned_files = self.get_orphaned_files(file_refs)
            log.info(f"Found {len(orphaned_files)} orphaned files for chat {chat_id}")
            
            # Clean up orphaned files
            for file_id in orphaned_files:
                # Clean up extracted images
                if self.cleanup_file_images(file_id):
                    results['images_cleaned'] += 1
                
                # Clean up file data
                if self.cleanup_file_data(file_id):
                    results['files_deleted'] += 1
                else:
                    results['errors'].append(f"Failed to delete file {file_id}")
            
            log.info(f"Chat {chat_id} cleanup: {results}")
            return results
            
        except Exception as e:
            error_msg = f"Failed to cleanup files for chat {chat_id}: {e}"
            log.error(error_msg)
            results['errors'].append(error_msg)
            return results

# Global instance
file_cleanup_manager = FileCleanupManager()