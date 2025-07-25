"""
Organization models package - refactored from organization_usage.py

This package maintains backward compatibility by re-exporting all classes
that were previously in organization_usage.py
"""

# Import all classes from submodules
from .global_settings import (
    GlobalSettings,
    GlobalSettingsModel,
    GlobalSettingsForm,
    GlobalSettingsTable
)

from .generation_processing import (
    ProcessedGeneration,
    ProcessedGenerationCleanupLog,
    ProcessedGenerationTable
)

from .client_organization import (
    ClientOrganization,
    UserClientMapping,
    ClientOrganizationModel,
    UserClientMappingModel,
    ClientOrganizationForm,
    UserClientMappingForm,
    ClientOrganizationTable,
    UserClientMappingTable
)

from .usage_tracking import (
    ClientDailyUsage,
    ClientUserDailyUsage,
    ClientModelDailyUsage,
    ClientLiveCounters,
    ClientDailyUsageModel,
    ClientUserDailyUsageModel,
    ClientModelDailyUsageModel,
    ClientLiveCountersModel,
    ClientUsageStatsResponse,
    ClientBillingResponse,
    ClientUsageTable
)

# Import database utilities
from open_webui.internal.db import get_db

# Create singleton instances (as in original file)
GlobalSettingsDB = GlobalSettingsTable()
ClientOrganizationDB = ClientOrganizationTable()
UserClientMappingDB = UserClientMappingTable()
ClientUsageDB = ClientUsageTable()
ProcessedGenerationDB = ProcessedGenerationTable()

# Export all classes and instances for backward compatibility
__all__ = [
    # Database models
    'GlobalSettings',
    'ProcessedGeneration',
    'ProcessedGenerationCleanupLog',
    'ClientOrganization',
    'UserClientMapping',
    'ClientDailyUsage',
    'ClientUserDailyUsage',
    'ClientModelDailyUsage',
    'ClientLiveCounters',
    
    # Pydantic models
    'GlobalSettingsModel',
    'ClientOrganizationModel',
    'UserClientMappingModel',
    'ClientDailyUsageModel',
    'ClientUserDailyUsageModel',
    'ClientModelDailyUsageModel',
    'ClientLiveCountersModel',
    
    # Forms
    'GlobalSettingsForm',
    'ClientOrganizationForm',
    'UserClientMappingForm',
    
    # Response models
    'ClientUsageStatsResponse',
    'ClientBillingResponse',
    
    # Table/Service classes
    'GlobalSettingsTable',
    'ClientOrganizationTable',
    'UserClientMappingTable',
    'ClientUsageTable',
    'ProcessedGenerationTable',
    
    # Singleton instances
    'GlobalSettingsDB',
    'ClientOrganizationDB',
    'UserClientMappingDB',
    'ClientUsageDB',
    'ProcessedGenerationDB',
    
    # Database utility
    'get_db'
]