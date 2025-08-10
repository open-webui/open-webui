"""
Content Sources Module

This module provides a unified interface for integrating external content sources
(Google Drive, OneDrive, Dropbox, etc.) with Open WebUI's knowledge base system.
"""

from .factory import content_source_factory
from .registry import content_source_registry
from .scheduler import scheduler as content_source_scheduler

# Initialize Google Drive provider in the registry
try:
    gdrive_provider = content_source_factory.get_provider('google_drive')
    content_source_registry.register_provider('google_drive', gdrive_provider)
except Exception as e:
    import logging
    logging.getLogger(__name__).warning(f"Failed to initialize Google Drive provider: {e}")

__all__ = [
    "content_source_factory", 
    "content_source_registry",
    "content_source_scheduler"
]