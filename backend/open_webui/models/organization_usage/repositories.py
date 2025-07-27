"""
Repository Interfaces for Organization Usage Tracking
Abstract base classes defining contracts for data access (Clean Architecture Application Layer)
"""
from abc import ABC, abstractmethod
from datetime import date
from typing import Optional, List, Dict, Any

from .domain import (
    GlobalSettingsModel, GlobalSettingsForm,
    ClientOrganizationModel, ClientOrganizationForm,
    UserClientMappingModel, UserClientMappingForm,
    ClientUsageStatsResponse, ClientBillingResponse,
    UsageRecordDTO, ProcessedGenerationInfo, CleanupStatsResult
)


####################
# Repository Interfaces (Abstract Base Classes)
####################


class IGlobalSettingsRepository(ABC):
    """Interface for global settings data access"""
    
    @abstractmethod
    def get_settings(self) -> Optional[GlobalSettingsModel]:
        """Get global settings (singleton)"""
        pass
    
    @abstractmethod
    def create_or_update_settings(
        self, settings_form: GlobalSettingsForm
    ) -> Optional[GlobalSettingsModel]:
        """Create or update global settings"""
        pass


class IClientOrganizationRepository(ABC):
    """Interface for client organization data access"""
    
    @abstractmethod
    def create_client(
        self, client_form: ClientOrganizationForm, api_key: str, key_hash: str = None
    ) -> Optional[ClientOrganizationModel]:
        """Create a new client organization"""
        pass
    
    @abstractmethod
    def get_client_by_id(self, client_id: str) -> Optional[ClientOrganizationModel]:
        """Get client organization by ID"""
        pass
    
    @abstractmethod
    def get_client_by_api_key(self, api_key: str) -> Optional[ClientOrganizationModel]:
        """Get client organization by API key"""
        pass
    
    @abstractmethod
    def get_all_active_clients(self) -> List[ClientOrganizationModel]:
        """Get all active client organizations"""
        pass
    
    @abstractmethod
    def update_client(
        self, client_id: str, updates: dict
    ) -> Optional[ClientOrganizationModel]:
        """Update client organization"""
        pass
    
    @abstractmethod
    def deactivate_client(self, client_id: str) -> bool:
        """Deactivate a client organization"""
        pass


class IUserClientMappingRepository(ABC):
    """Interface for user-client mapping data access"""
    
    @abstractmethod
    def create_mapping(
        self, mapping_form: UserClientMappingForm
    ) -> Optional[UserClientMappingModel]:
        """Create a new user-client mapping"""
        pass
    
    @abstractmethod
    def get_mapping_by_user_id(
        self, user_id: str
    ) -> Optional[UserClientMappingModel]:
        """Get mapping by user ID"""
        pass
    
    @abstractmethod
    def get_mappings_by_client_id(
        self, client_org_id: str
    ) -> List[UserClientMappingModel]:
        """Get all mappings for a client organization"""
        pass
    
    @abstractmethod
    def deactivate_mapping(self, user_id: str) -> bool:
        """Deactivate a user-client mapping"""
        pass
    
    @abstractmethod
    def update_mapping(self, user_id: str, updates: dict) -> bool:
        """Update a user-client mapping"""
        pass


class IClientUsageRepository(ABC):
    """Interface for client usage data access"""
    
    @abstractmethod
    def record_usage(self, usage_record: UsageRecordDTO) -> bool:
        """Record API usage with per-user and per-model tracking"""
        pass
    
    @abstractmethod
    async def get_usage_stats_by_client(
        self, client_org_id: str, use_client_timezone: bool = True
    ) -> ClientUsageStatsResponse:
        """Get admin-focused daily breakdown stats (no real-time features)"""
        pass
    
    @abstractmethod
    def get_usage_by_user(
        self, client_org_id: str, start_date: date = None, end_date: date = None
    ) -> List[Dict[str, Any]]:
        """Get usage breakdown by user for a client organization"""
        pass
    
    @abstractmethod
    def get_usage_by_model(
        self, client_org_id: str, start_date: date = None, end_date: date = None
    ) -> List[Dict[str, Any]]:
        """Get usage breakdown by model for a client organization"""
        pass
    
    @abstractmethod
    def get_all_clients_usage_stats(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> List[ClientBillingResponse]:
        """Get usage statistics for all clients for billing purposes"""
        pass


class IProcessedGenerationRepository(ABC):
    """Interface for processed generation data access"""
    
    @abstractmethod
    def is_generation_processed(self, generation_id: str, client_org_id: str) -> bool:
        """Check if a generation has already been processed"""
        pass
    
    @abstractmethod
    def mark_generation_processed(
        self, generation_info: ProcessedGenerationInfo
    ) -> bool:
        """Mark a generation as processed"""
        pass
    
    @abstractmethod
    def cleanup_old_processed_generations(self, days_to_keep: int = 60) -> CleanupStatsResult:
        """Clean up old processed generation records to prevent table bloat"""
        pass
    
    @abstractmethod
    def get_processed_generations_stats(
        self, client_org_id: str, start_date: date = None, end_date: date = None
    ) -> Dict[str, Any]:
        """Get statistics about processed generations for debugging"""
        pass