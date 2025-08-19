"""Utility functions for content source management."""
import logging
from typing import Optional
from open_webui.content_sources.registry import content_source_registry
from open_webui.content_sources.factory import content_source_factory

logger = logging.getLogger(__name__)


def refresh_provider_configuration(provider_name: str) -> bool:
    """
    Refresh a content source provider's configuration.
    
    This is typically called when configuration settings are updated
    in the admin panel.
    
    Args:
        provider_name: Name of the provider to refresh
        
    Returns:
        True if refresh was successful, False otherwise
    """
    try:
        # Get existing provider instance
        provider = content_source_registry.get_provider(provider_name)
        
        if provider and hasattr(provider, 'refresh_configuration'):
            provider.refresh_configuration()
            logger.info(f"Refreshed configuration for provider: {provider_name}")
            return True
        else:
            # Provider not loaded yet or doesn't support refresh
            logger.debug(f"Provider {provider_name} not loaded or doesn't support refresh")
            return False
            
    except Exception as e:
        logger.error(f"Error refreshing provider {provider_name}: {e}")
        return False