"""
Configuration settings for GoDaddy-specific integrations.
"""

import os
from typing import Dict, Any

# Active Directory API Settings
ACTIVE_DIRECTORY_BASE_URL = os.environ.get("ACTIVE_DIRECTORY_BASE_URL", "https://active-directory.gdcorp.tools")
ACTIVE_DIRECTORY_SSO_HOST = os.environ.get("ACTIVE_DIRECTORY_SSO_HOST", "sso.gdcorp.tools")
ACTIVE_DIRECTORY_TOKEN_REFRESH_MINUTES = float(os.environ.get("ACTIVE_DIRECTORY_TOKEN_REFRESH_MINUTES", "45.0"))
ACTIVE_DIRECTORY_DOMAIN = os.environ.get("ACTIVE_DIRECTORY_DOMAIN", "jomax")

# Feature flags
USE_ACTIVE_DIRECTORY_GROUPS = os.environ.get("USE_ACTIVE_DIRECTORY_GROUPS", "true").lower() == "true"

# Export all settings as a dictionary for easy access
def get_config() -> Dict[str, Any]:
    """Return all configuration settings as a dictionary."""
    return {
        "active_directory": {
            "base_url": ACTIVE_DIRECTORY_BASE_URL,
            "sso_host": ACTIVE_DIRECTORY_SSO_HOST,
            "token_refresh_minutes": ACTIVE_DIRECTORY_TOKEN_REFRESH_MINUTES,
            "domain": ACTIVE_DIRECTORY_DOMAIN,
            "use_groups": USE_ACTIVE_DIRECTORY_GROUPS,
        }
    }