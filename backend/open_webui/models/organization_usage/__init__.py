"""
Organization Usage Tracking - Clean Architecture Implementation
Main module providing backward-compatible public API
"""

# Import all database models (preserve existing imports)
from .database import (
    GlobalSettings,
    ClientOrganization, UserClientMapping, ClientDailyUsage,
    ClientUserDailyUsage, ClientModelDailyUsage
)

# Import all domain models (preserve existing imports)
from .domain import (
    GlobalSettingsModel, ClientOrganizationModel, UserClientMappingModel,
    ClientDailyUsageModel, ClientUserDailyUsageModel, ClientModelDailyUsageModel,
    GlobalSettingsForm, ClientOrganizationForm, UserClientMappingForm,
    ClientUsageStatsResponse, ClientBillingResponse,
    UsageRecordDTO, CleanupStatsResult
)

# Import repository implementations
from .repositories_impl import (
    GlobalSettingsRepository, ClientOrganizationRepository,
    UserClientMappingRepository
)
from .client_usage_repository import ClientUsageRepository

# Import time for timestamp operations (used by legacy table classes)
import time
from datetime import date


####################
# Legacy Table Classes for Backward Compatibility
####################


class GlobalSettingsTable:
    """Legacy table class - delegates to repository"""
    
    def __init__(self):
        self._repository = GlobalSettingsRepository()
    
    def get_settings(self):
        return self._repository.get_settings()
    
    def create_or_update_settings(self, settings_form):
        return self._repository.create_or_update_settings(settings_form)


class ClientOrganizationTable:
    """Legacy table class - delegates to repository"""
    
    def __init__(self):
        self._repository = ClientOrganizationRepository()
    
    def create_client(self, client_form, api_key, key_hash=None):
        return self._repository.create_client(client_form, api_key, key_hash)
    
    def get_client_by_id(self, client_id):
        return self._repository.get_client_by_id(client_id)
    
    def get_client_by_api_key(self, api_key):
        return self._repository.get_client_by_api_key(api_key)
    
    def get_all_active_clients(self):
        return self._repository.get_all_active_clients()
    
    def update_client(self, client_id, updates):
        return self._repository.update_client(client_id, updates)
    
    def deactivate_client(self, client_id):
        return self._repository.deactivate_client(client_id)


class UserClientMappingTable:
    """Legacy table class - delegates to repository"""
    
    def __init__(self):
        self._repository = UserClientMappingRepository()
    
    def create_mapping(self, mapping_form):
        return self._repository.create_mapping(mapping_form)
    
    def get_mapping_by_user_id(self, user_id):
        return self._repository.get_mapping_by_user_id(user_id)
    
    def get_mappings_by_client_id(self, client_org_id):
        return self._repository.get_mappings_by_client_id(client_org_id)
    
    def deactivate_mapping(self, user_id):
        return self._repository.deactivate_mapping(user_id)
    
    def update_mapping(self, user_id, updates):
        return self._repository.update_mapping(user_id, updates)


class ClientUsageTable:
    """Legacy table class - delegates to repository with signature adaptation"""
    
    def __init__(self):
        self._repository = ClientUsageRepository()
    
    def record_usage(
        self,
        client_org_id: str,
        user_id: str,
        openrouter_user_id: str,
        model_name: str,
        usage_date: date,
        input_tokens: int = 0,
        output_tokens: int = 0,
        raw_cost: float = 0.0,
        markup_cost: float = 0.0,
        provider: str = None,
        request_metadata: dict = None
    ) -> bool:
        """Legacy method signature - converts to DTO and delegates"""
        usage_record = UsageRecordDTO(
            client_org_id=client_org_id,
            user_id=user_id,
            openrouter_user_id=openrouter_user_id,
            model_name=model_name,
            usage_date=usage_date,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            raw_cost=raw_cost,
            markup_cost=markup_cost,
            provider=provider,
            request_metadata=request_metadata
        )
        return self._repository.record_usage(usage_record)
    
    async def get_usage_stats_by_client(self, client_org_id, use_client_timezone=True):
        return await self._repository.get_usage_stats_by_client(client_org_id, use_client_timezone)
    
    def get_usage_by_user(self, client_org_id, start_date=None, end_date=None):
        return self._repository.get_usage_by_user(client_org_id, start_date, end_date)
    
    def get_usage_by_model(self, client_org_id, start_date=None, end_date=None):
        return self._repository.get_usage_by_model(client_org_id, start_date, end_date)
    
    def get_all_clients_usage_stats(self, start_date=None, end_date=None):
        return self._repository.get_all_clients_usage_stats(start_date, end_date)


class ProcessedGenerationTable:
    """Legacy table class - InfluxDB-First architecture stub"""
    
    def __init__(self):
        pass
    
    def is_generation_processed(self, generation_id, client_org_id):
        """Always return False - InfluxDB handles deduplication via request_id tags"""
        return False
    
    def is_duplicate(self, request_id, model, cost):
        """Always return False - InfluxDB handles deduplication via request_id tags"""
        return False
    
    def mark_generation_processed(self, generation_id, client_org_id, generation_date, total_cost, total_tokens):
        """No-op - InfluxDB handles deduplication via request_id tags"""
        return True
    
    def cleanup_old_processed_generations(self, days_to_keep=60):
        """No-op - InfluxDB handles retention via bucket policies"""
        return {
            "success": True,
            "records_deleted": 0,
            "storage_saved_kb": 0,
            "message": "InfluxDB handles retention automatically"
        }
    
    def get_processed_generations_stats(self, client_org_id, start_date=None, end_date=None):
        """No-op - Use InfluxDB queries for statistics"""
        return {}


####################
# Singleton Instances (CRITICAL for backward compatibility)
####################

# These singleton instances MUST be preserved for existing code compatibility
GlobalSettingsDB = GlobalSettingsTable()
ClientOrganizationDB = ClientOrganizationTable()
UserClientMappingDB = UserClientMappingTable()
ClientUsageDB = ClientUsageTable()
ProcessedGenerationDB = ProcessedGenerationTable()  # Stub for InfluxDB-First architecture


####################
# Export all public APIs for backward compatibility
####################

__all__ = [
    # Database Models
    'GlobalSettings',
    'ClientOrganization', 'UserClientMapping', 'ClientDailyUsage',
    'ClientUserDailyUsage', 'ClientModelDailyUsage',
    
    # Domain Models
    'GlobalSettingsModel', 'ClientOrganizationModel', 'UserClientMappingModel',
    'ClientDailyUsageModel', 'ClientUserDailyUsageModel', 'ClientModelDailyUsageModel',
    
    # Forms and Responses
    'GlobalSettingsForm', 'ClientOrganizationForm', 'UserClientMappingForm',
    'ClientUsageStatsResponse', 'ClientBillingResponse',
    
    # Legacy Table Classes
    'GlobalSettingsTable', 'ClientOrganizationTable', 'UserClientMappingTable',
    'ClientUsageTable', 'ProcessedGenerationTable',
    
    # Singleton Instances (CRITICAL)
    'GlobalSettingsDB', 'ClientOrganizationDB', 'UserClientMappingDB',
    'ClientUsageDB', 'ProcessedGenerationDB'
]