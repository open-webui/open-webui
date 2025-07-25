"""
Legacy organization_usage.py - maintained for backward compatibility

All classes have been refactored into the organization package:
- organization/global_settings.py
- organization/generation_processing.py  
- organization/client_organization.py
- organization/usage_tracking.py

This file now simply re-exports everything from the organization package
to maintain backward compatibility with existing imports.
"""

# Re-export everything from the organization package
from .organization import *

# Note: This maintains 100% backward compatibility
# All existing imports like:
#   from open_webui.models.organization_usage import ClientOrganization
# will continue to work exactly as before