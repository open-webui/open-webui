"""
Organization Usage Tracking - Backward Compatibility Module
Redirects imports to the new Clean Architecture package structure

This file maintains 100% backward compatibility for existing code while 
the actual implementation has been refactored into a Clean Architecture package.

Original file: 1196 lines (exceeded 700-line project limit)
New structure: 6 modules, all under 700 lines each

All existing imports and API contracts are preserved exactly.
"""

# Import everything from the new package to maintain backward compatibility
from open_webui.models.organization_usage import *

# Preserve the exact same public API
__all__ = [
    # Database Models
    'GlobalSettings',
    'ClientOrganization', 'UserClientMapping', 'ClientDailyUsage',
    'ClientUserDailyUsage', 'ClientModelDailyUsage',
    
    # Domain Models (Pydantic)
    'GlobalSettingsModel', 'ClientOrganizationModel', 'UserClientMappingModel',
    'ClientDailyUsageModel', 'ClientUserDailyUsageModel', 'ClientModelDailyUsageModel',
    
    # Forms and Responses
    'GlobalSettingsForm', 'ClientOrganizationForm', 'UserClientMappingForm',
    'ClientUsageStatsResponse', 'ClientBillingResponse',
    
    # Database Operations (Table Classes)
    'GlobalSettingsTable', 'ClientOrganizationTable', 'UserClientMappingTable',
    'ClientUsageTable', 'ProcessedGenerationTable',
    
    # Singleton Instances (CRITICAL for existing code)
    'GlobalSettingsDB', 'ClientOrganizationDB', 'UserClientMappingDB',
    'ClientUsageDB', 'ProcessedGenerationDB'
]