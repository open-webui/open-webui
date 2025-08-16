"""
Content Source Factory

Factory for creating content source provider instances.
"""

from typing import Dict, Type, Optional
import logging

from .base import ContentSourceProvider
from .providers.google_drive import GoogleDriveProvider

logger = logging.getLogger(__name__)


class ContentSourceFactory:
    """
    Factory for creating content source provider instances.
    
    Follows the pattern established by storage providers in the codebase.
    """
    
    # Registry of available providers
    _providers: Dict[str, Type[ContentSourceProvider]] = {
        'google_drive': GoogleDriveProvider,
        # Future providers can be added here:
        # 'onedrive': OneDriveContentSource,
        # 'dropbox': DropboxContentSource,
        # 'sharepoint': SharePointContentSource,
    }
    
    @classmethod
    def get_provider(cls, provider_type: str) -> ContentSourceProvider:
        """
        Get a content source provider instance.
        
        Args:
            provider_type: The type of provider to create
            
        Returns:
            ContentSourceProvider instance
            
        Raises:
            ValueError: If provider type is not supported
        """
        if provider_type not in cls._providers:
            available = ', '.join(cls._providers.keys())
            raise ValueError(
                f"Unknown content source provider type: {provider_type}. "
                f"Available providers: {available}"
            )
            
        provider_class = cls._providers[provider_type]
        logger.info(f"Creating content source provider: {provider_type}")
        
        return provider_class()
        
    @classmethod
    def register_provider(cls, provider_type: str, provider_class: Type[ContentSourceProvider]) -> None:
        """
        Register a new content source provider.
        
        This allows for dynamic registration of custom providers.
        
        Args:
            provider_type: The identifier for the provider
            provider_class: The provider class to register
        """
        cls._providers[provider_type] = provider_class
        logger.info(f"Registered content source provider: {provider_type}")
        
    @classmethod
    def get_available_providers(cls) -> Dict[str, Type[ContentSourceProvider]]:
        """
        Get all available content source providers.
        
        Returns:
            Dictionary of provider types to their classes
        """
        return cls._providers.copy()


# Create a singleton instance for easy import
content_source_factory = ContentSourceFactory()