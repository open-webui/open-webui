"""
GoDaddy-specific extensions for Open WebUI.

This module integrates GoDaddy-specific authentication and group management
functionality with Open WebUI.
"""

import logging
from typing import Any, Dict

log = logging.getLogger(__name__)

def init_godaddy_extensions():
    """
    Initialize GoDaddy-specific extensions for Open WebUI.
    
    This should be called during application startup to patch the relevant
    components and enable GoDaddy-specific functionality.
    """
    log.info("Initializing GoDaddy extensions")
    
    # Patch OAuth Manager to use Active Directory for group management
    from godaddy.oauth_extension import patch_oauth_manager
    if not patch_oauth_manager():
        log.error("Failed to initialize GoDaddy OAuth extensions")
    
    # Patch the signin handler to refresh groups on every login
    from godaddy.auth_extension import patch_signin_handler
    if not patch_signin_handler():
        log.error("Failed to initialize group refresh on login")
        
    log.info("GoDaddy extensions initialized")