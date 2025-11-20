"""
Administrative cleanup utilities for maintenance operations.
"""

import logging
from typing import Dict, List
from open_webui.utils.file_cleanup import file_cleanup_manager
from open_webui.models.files import Files
from open_webui.models.chats import Chats

log = logging.getLogger(__name__)

class AdminCleanupManager:
    """Administrative cleanup operations."""
    
    def __init__(self):
        self.files_model = Files()
        self.chats_model = Chats()
    
    def find_orphaned_files(self) -> List[str]:
        """Find all files that are not referenced by any chat."""
        all_files = self.files_model.get_files()
        all_chats = self.chats_model.get_chats()
        
        # Collect all file references from all chats
        referenced_files = set()
        for chat in all_chats:
            chat_file_refs = file_cleanup_manager.get_chat_file_references(chat.id)
            referenced_files.update(chat_file_refs)
        
        # Find orphaned files
        orphaned_files = []
        for file in all_files:
            if file.id not in referenced_files:
                orphaned_files.append(file.id)
        
        return orphaned_files
    
    def cleanup_orphaned_files(self) -> Dict[str, int]:
        """Clean up all orphaned files."""
        orphaned_files = self.find_orphaned_files()
        
        results = {
            'total_orphaned': len(orphaned_files),
            'cleaned_up': 0,
            'errors': 0
        }
        
        for file_id in orphaned_files:
            try:
                # Clean images
                file_cleanup_manager.cleanup_file_images(file_id)
                
                # Clean file data
                if file_cleanup_manager.cleanup_file_data(file_id):
                    results['cleaned_up'] += 1
                else:
                    results['errors'] += 1
                    
            except Exception as e:
                log.error(f"Failed to cleanup orphaned file {file_id}: {e}")
                results['errors'] += 1
        
        log.info(f"Orphaned file cleanup completed: {results}")
        return results
    
    def get_storage_usage(self) -> Dict[str, any]:
        """Get storage usage statistics."""
        all_files = self.files_model.get_files()
        
        total_files = len(all_files)
        total_size = 0
        image_count = 0
        
        for file in all_files:
            if hasattr(file, 'size') and file.size:
                total_size += file.size
            
            if file.image_refs:
                image_count += len(file.image_refs)
        
        orphaned_count = len(self.find_orphaned_files())
        
        return {
            'total_files': total_files,
            'total_size_bytes': total_size,
            'total_images': image_count,
            'orphaned_files': orphaned_count
        }

# Global instance
admin_cleanup_manager = AdminCleanupManager()