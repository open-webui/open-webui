"""
Base Content Source Provider

Defines the abstract interface for all content source providers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Callable, Optional, AsyncGenerator
import logging

logger = logging.getLogger(__name__)


class ContentSourceProvider(ABC):
    """
    Abstract base class for content source providers.
    
    Providers implement methods to list, download, and sync files from external sources.
    They emit hooks to allow the knowledge system to process files without tight coupling.
    """
    
    def __init__(self):
        self._hooks: Dict[str, List[Callable]] = {}
        
    def register_hook(self, event: str, handler: Callable) -> None:
        """
        Register a hook handler for a specific event.
        
        Args:
            event: The event name (e.g., 'file_ready', 'sync_started')
            handler: Async callable that will be invoked when the event is emitted
        """
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(handler)
        logger.debug(f"Registered hook for event '{event}'")
        
    async def emit_hook(self, event: str, data: Dict[str, Any]) -> None:
        """
        Emit an event to all registered handlers.
        
        Args:
            event: The event name
            data: Data to pass to the handlers
        """
        handlers = self._hooks.get(event, [])
        for handler in handlers:
            try:
                await handler(data)
            except Exception as e:
                logger.error(f"Error in hook handler for event '{event}': {e}")
                
    @abstractmethod
    async def list_files(self, path: str = "", recursive: bool = True) -> List[Dict[str, Any]]:
        """
        List files in the content source.
        
        Args:
            path: The path to list files from (provider-specific format)
            recursive: Whether to list files recursively
            
        Returns:
            List of file metadata dictionaries
        """
        pass
        
    @abstractmethod
    async def download_file(self, file_id: str) -> AsyncGenerator[bytes, None]:
        """
        Download a file from the content source.
        
        Args:
            file_id: Provider-specific file identifier
            
        Yields:
            File content in chunks
        """
        pass
        
    @abstractmethod
    async def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about the content source service.
        
        Returns:
            Dictionary with service information (e.g., account email, quota)
        """
        pass
        
    async def sync_folder(self, folder_id: str, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Sync a folder from the content source.
        
        This is a high-level method that lists files and emits hooks for processing.
        Subclasses can override for provider-specific behavior.
        
        Args:
            folder_id: Provider-specific folder identifier
            context: Optional context to pass through hooks (e.g., kb_id, user_id)
        """
        context = context or {}
        
        # Emit sync started event
        await self.emit_hook('sync_started', {
            'folder_id': folder_id,
            'context': context
        })
        
        try:
            # List files in the folder
            files = await self.list_files(folder_id, recursive=True)
            
            # Process each file
            for file_info in files:
                try:
                    # Download file content
                    content_chunks = []
                    async for chunk in self.download_file(file_info['id']):
                        content_chunks.append(chunk)
                    content = b''.join(content_chunks)
                    
                    # Emit file ready event
                    await self.emit_hook('file_ready', {
                        'file_info': file_info,
                        'content': content,
                        'context': context
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing file {file_info.get('name', 'unknown')}: {e}")
                    await self.emit_hook('file_error', {
                        'file_info': file_info,
                        'error': str(e),
                        'context': context
                    })
                    
            # Emit sync completed event
            await self.emit_hook('sync_completed', {
                'folder_id': folder_id,
                'file_count': len(files),
                'context': context
            })
            
        except Exception as e:
            logger.error(f"Error during sync: {e}")
            await self.emit_hook('sync_error', {
                'folder_id': folder_id,
                'error': str(e),
                'context': context
            })
            raise
            
    async def sync_content(self, source_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generic sync method that handles file synchronization and returns results.
        
        This method provides a unified interface for the knowledge router to sync content.
        It handles both simple sync (download all) and advanced sync (with change detection).
        
        Args:
            source_id: Provider-specific source identifier (folder ID, etc.)
            context: Context including file_ids, user_id, options, etc.
            
        Returns:
            Dictionary with sync results including added, updated, removed files and errors
        """
        context = context or {}
        sync_results = {
            "added_files": [],
            "updated_files": [],
            "removed_files": [],
            "errors": [],
            "changes": False
        }
        
        # Build provider file map from existing files
        provider_file_map = {}
        existing_file_ids = context.get("file_ids", [])
        if existing_file_ids:
            from open_webui.models.files import Files
            existing_files = Files.get_files_by_ids(existing_file_ids)
            for file in existing_files:
                if file.data and file.data.get("provider") == context.get("provider_name"):
                    provider_id = file.data.get("provider_file_id")
                    if provider_id:
                        provider_file_map[provider_id] = {
                            "id": file.id,
                            "name": file.filename,
                            "modified_time": file.data.get("provider_modified_time"),
                            "data": file.data
                        }
        
        # Track sync progress
        async def track_file_processed(data: Dict[str, Any]):
            file_id = data.get("file_id")
            if file_id:
                sync_results["added_files"].append(file_id)
                sync_results["changes"] = True
            
        async def track_file_updated(data: Dict[str, Any]):
            sync_results["updated_files"].append(data.get("file_id", "unknown"))
            sync_results["changes"] = True
            
        async def track_file_removed(data: Dict[str, Any]):
            file_info = data.get("file_info", {})
            file_id = file_info.get("id")
            if file_id:
                sync_results["removed_files"].append(file_id)
                sync_results["changes"] = True
            
        async def track_error(data: Dict[str, Any]):
            sync_results["errors"].append({
                "file": data.get("file_info", {}).get("name", "unknown"),
                "error": data.get("error", "Unknown error")
            })
        
        # Register internal tracking hooks
        self.register_hook("file_processed", track_file_processed)
        self.register_hook("file_updated", track_file_updated)
        self.register_hook("file_removed", track_file_removed)
        self.register_hook("file_error", track_error)
        
        try:
            # Use advanced sync if available, otherwise basic sync
            if hasattr(self, 'sync_folder_with_metadata'):
                await self.sync_folder_with_metadata(
                    folder_id=source_id,
                    existing_files=provider_file_map,
                    context=context
                )
            else:
                await self.sync_folder(source_id, context)
                
        finally:
            # Clean up tracking hooks
            if "file_processed" in self._hooks:
                self._hooks["file_processed"] = [h for h in self._hooks["file_processed"] if h != track_file_processed]
            if "file_updated" in self._hooks:
                self._hooks["file_updated"] = [h for h in self._hooks["file_updated"] if h != track_file_updated]
            if "file_removed" in self._hooks:
                self._hooks["file_removed"] = [h for h in self._hooks["file_removed"] if h != track_file_removed]
            if "file_error" in self._hooks:
                self._hooks["file_error"] = [h for h in self._hooks["file_error"] if h != track_error]
                
        return sync_results