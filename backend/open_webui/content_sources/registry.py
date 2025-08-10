"""
Content Source Registry

Global registry for content source providers with hook support.
"""

from typing import Dict, List, Optional, Any, Callable
import logging
import asyncio

from .base import ContentSourceProvider

logger = logging.getLogger(__name__)


class ContentSourceRegistry:
    """Registry for content source providers with global hook support."""
    
    def __init__(self):
        self._providers: Dict[str, ContentSourceProvider] = {}
        self._global_hooks: Dict[str, List[Callable]] = {}
        
    def register_provider(self, name: str, provider: ContentSourceProvider) -> None:
        """Register a content source provider."""
        self._providers[name] = provider
        logger.info(f"Registered content source provider: {name}")
        
    def unregister_provider(self, name: str) -> None:
        """Unregister a content source provider."""
        if name in self._providers:
            self._providers.pop(name)
            logger.info(f"Unregistered content source provider: {name}")
        
    def get_provider(self, name: str) -> Optional[ContentSourceProvider]:
        """Get a content source provider by name."""
        return self._providers.get(name)
    
    def get_all_providers(self) -> Dict[str, ContentSourceProvider]:
        """Get all registered providers."""
        return self._providers.copy()
        
    def register_global_hook(self, event: str, handler: Callable) -> None:
        """
        Register a global hook that will be called for all providers.
        
        Args:
            event: The event name to listen for
            handler: Async callable that will be invoked when the event is emitted
        """
        if event not in self._global_hooks:
            self._global_hooks[event] = []
        self._global_hooks[event].append(handler)
        logger.debug(f"Registered global hook for event '{event}'")
        
    async def emit_hook(self, event: str, data: Dict[str, Any]) -> None:
        """
        Emit a hook event to all global handlers and registered providers.
        
        Args:
            event: The event name
            data: Data to pass to the handlers
        """
        # Call global hooks first
        for handler in self._global_hooks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Error in global hook handler for event '{event}': {e}")
        
        # Then emit to all registered providers
        for provider_name, provider in self._providers.items():
            try:
                await provider.emit_hook(event, data)
            except Exception as e:
                logger.error(f"Error emitting hook '{event}' to provider '{provider_name}': {e}")


# Global registry instance
content_source_registry = ContentSourceRegistry()

# Define standard hook events
HOOK_EVENTS = {
    # File operations
    'before_file_add': 'Before file is added to knowledge base',
    'after_file_add': 'After file is added to knowledge base',
    'before_file_remove': 'Before file is removed from knowledge base',
    'after_file_remove': 'After file is removed from knowledge base',
    'before_file_update': 'Before file is updated in knowledge base',
    'after_file_update': 'After file is updated in knowledge base',
    
    # Knowledge base operations
    'before_knowledge_create': 'Before knowledge base is created',
    'after_knowledge_create': 'After knowledge base is created',
    'before_knowledge_update': 'Before knowledge base is updated',
    'after_knowledge_update': 'After knowledge base is updated',
    'before_knowledge_delete': 'Before knowledge base is deleted',
    'after_knowledge_delete': 'After knowledge base is deleted',
    'before_knowledge_reset': 'Before knowledge base is reset',
    'after_knowledge_reset': 'After knowledge base is reset',
    
    # Batch operations
    'before_files_batch_add': 'Before multiple files are added',
    'after_files_batch_add': 'After multiple files are added',
    
    # Sync operations (for content sources)
    'sync_started': 'Sync operation started',
    'sync_completed': 'Sync operation completed',
    'sync_error': 'Error during sync operation',
    'file_ready': 'File downloaded and ready for processing',
    'file_error': 'Error processing file',
    
    # Content sync operations
    'before_content_sync': 'Before content sync starts',
    'after_content_sync': 'After content sync completes',
    'content_sync_error': 'Error during content sync',
    'sync_progress': 'Progress update during sync',
    'file_new': 'New file detected during sync',
    'file_updated': 'File updated during sync',
    'file_unchanged': 'File unchanged during sync',
    'file_removed': 'File removed detected during sync',
    'file_skipped': 'File skipped during sync',
}