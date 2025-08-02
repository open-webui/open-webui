"""
Repository Implementations for Organization Usage Tracking
Concrete implementations of data access interfaces (Clean Architecture Infrastructure Layer)
"""
import time
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

from open_webui.internal.db import get_db
from sqlalchemy import func

from .database import (
    GlobalSettings,
    ClientOrganization, UserClientMapping, ClientDailyUsage,
    ClientUserDailyUsage, ClientModelDailyUsage
)
from .domain import (
    GlobalSettingsModel, GlobalSettingsForm,
    ClientOrganizationModel, ClientOrganizationForm,
    UserClientMappingModel, UserClientMappingForm,
    ClientUsageStatsResponse, ClientBillingResponse,
    UsageRecordDTO, CleanupStatsResult
)
from .repositories import (
    IGlobalSettingsRepository, IClientOrganizationRepository,
    IUserClientMappingRepository, IClientUsageRepository
)

log = logging.getLogger(__name__)


####################
# Repository Implementations
####################


class GlobalSettingsRepository(IGlobalSettingsRepository):
    """Implementation of global settings repository"""

    def get_settings(self) -> Optional[GlobalSettingsModel]:
        """Get global settings (singleton)"""
        try:
            with get_db() as db:
                settings = db.query(GlobalSettings).first()
                if settings:
                    return GlobalSettingsModel.model_validate(settings)
                return None
        except Exception:
            return None

    def create_or_update_settings(
        self, settings_form: GlobalSettingsForm
    ) -> Optional[GlobalSettingsModel]:
        """Create or update global settings"""
        try:
            with get_db() as db:
                existing = db.query(GlobalSettings).first()
                current_time = int(time.time())
                
                if existing:
                    # Update existing
                    for key, value in settings_form.model_dump().items():
                        setattr(existing, key, value)
                    existing.updated_at = current_time
                    db.commit()
                    db.refresh(existing)
                    return GlobalSettingsModel.model_validate(existing)
                else:
                    # Create new
                    settings_data = settings_form.model_dump()
                    settings_data.update({
                        "id": "global",
                        "created_at": current_time,
                        "updated_at": current_time
                    })
                    new_settings = GlobalSettings(**settings_data)
                    db.add(new_settings)
                    db.commit()
                    db.refresh(new_settings)
                    return GlobalSettingsModel.model_validate(new_settings)
        except Exception:
            return None


class ClientOrganizationRepository(IClientOrganizationRepository):
    """Implementation of client organization repository"""

    def create_client(
        self, client_form: ClientOrganizationForm, api_key: str, key_hash: str = None
    ) -> Optional[ClientOrganizationModel]:
        """Create a new client organization"""
        try:
            with get_db() as db:
                current_time = int(time.time())
                client_data = client_form.model_dump()
                client_data.update({
                    "id": f"client_{client_form.name.lower().replace(' ', '_')}_{current_time}",
                    "openrouter_api_key": api_key,
                    "openrouter_key_hash": key_hash,
                    "is_active": 1,  # Ensure is_active is set
                    "created_at": current_time,
                    "updated_at": current_time
                })
                
                new_client = ClientOrganization(**client_data)
                db.add(new_client)
                db.commit()
                db.refresh(new_client)
                return ClientOrganizationModel.model_validate(new_client)
        except Exception:
            return None

    def get_client_by_id(self, client_id: str) -> Optional[ClientOrganizationModel]:
        """Get client organization by ID"""
        try:
            with get_db() as db:
                client = db.query(ClientOrganization).filter_by(id=client_id, is_active=1).first()
                if client:
                    return ClientOrganizationModel.model_validate(client)
                return None
        except Exception:
            return None
    
    def get_client_by_api_key(self, api_key: str) -> Optional[ClientOrganizationModel]:
        """Get client organization by API key"""
        try:
            with get_db() as db:
                client = db.query(ClientOrganization).filter_by(
                    openrouter_api_key=api_key,
                    is_active=1
                ).first()
                if client:
                    return ClientOrganizationModel.model_validate(client)
                return None
        except Exception:
            return None

    def get_all_active_clients(self) -> List[ClientOrganizationModel]:
        """Get all active client organizations"""
        try:
            with get_db() as db:
                clients = db.query(ClientOrganization).filter_by(is_active=1).all()
                return [ClientOrganizationModel.model_validate(c) for c in clients]
        except Exception:
            return []

    def update_client(
        self, client_id: str, updates: dict
    ) -> Optional[ClientOrganizationModel]:
        """Update client organization"""
        try:
            with get_db() as db:
                client = db.query(ClientOrganization).filter_by(id=client_id).first()
                if client:
                    for key, value in updates.items():
                        setattr(client, key, value)
                    client.updated_at = int(time.time())
                    db.commit()
                    db.refresh(client)
                    return ClientOrganizationModel.model_validate(client)
                return None
        except Exception:
            return None

    def deactivate_client(self, client_id: str) -> bool:
        """Deactivate a client organization"""
        try:
            with get_db() as db:
                client = db.query(ClientOrganization).filter_by(id=client_id).first()
                if client:
                    client.is_active = 0
                    client.updated_at = int(time.time())
                    db.commit()
                    return True
                return False
        except Exception:
            return False


class UserClientMappingRepository(IUserClientMappingRepository):
    """Implementation of user-client mapping repository"""

    def create_mapping(
        self, mapping_form: UserClientMappingForm
    ) -> Optional[UserClientMappingModel]:
        """Create a new user-client mapping"""
        try:
            with get_db() as db:
                current_time = int(time.time())
                mapping_data = mapping_form.model_dump()
                mapping_data.update({
                    "id": f"{mapping_form.user_id}_{mapping_form.client_org_id}",
                    "is_active": 1,  # Ensure is_active is set
                    "created_at": current_time,
                    "updated_at": current_time
                })
                
                new_mapping = UserClientMapping(**mapping_data)
                db.add(new_mapping)
                db.commit()
                db.refresh(new_mapping)
                return UserClientMappingModel.model_validate(new_mapping)
        except Exception:
            return None

    def get_mapping_by_user_id(
        self, user_id: str
    ) -> Optional[UserClientMappingModel]:
        """Get mapping by user ID"""
        try:
            with get_db() as db:
                mapping = db.query(UserClientMapping).filter_by(
                    user_id=user_id, is_active=1
                ).first()
                if mapping:
                    return UserClientMappingModel.model_validate(mapping)
                return None
        except Exception:
            return None

    def get_mappings_by_client_id(
        self, client_org_id: str
    ) -> List[UserClientMappingModel]:
        """Get all mappings for a client organization"""
        try:
            with get_db() as db:
                mappings = db.query(UserClientMapping).filter_by(
                    client_org_id=client_org_id, is_active=1
                ).all()
                return [UserClientMappingModel.model_validate(m) for m in mappings]
        except Exception:
            return []

    def deactivate_mapping(self, user_id: str) -> bool:
        """Deactivate a user-client mapping"""
        try:
            with get_db() as db:
                mapping = db.query(UserClientMapping).filter_by(
                    user_id=user_id
                ).first()
                if mapping:
                    mapping.is_active = 0
                    mapping.updated_at = int(time.time())
                    db.commit()
                    return True
                return False
        except Exception:
            return False
    
    def update_mapping(self, user_id: str, updates: dict) -> bool:
        """Update a user-client mapping"""
        try:
            with get_db() as db:
                mapping = db.query(UserClientMapping).filter_by(
                    user_id=user_id, is_active=1
                ).first()
                if mapping:
                    for key, value in updates.items():
                        setattr(mapping, key, value)
                    mapping.updated_at = int(time.time())
                    db.commit()
                    return True
                return False
        except Exception as e:
            log.error(f"Failed to update mapping for user {user_id}: {e}")
            return False


# ProcessedGenerationRepository removed - InfluxDB-First architecture
# handles deduplication via request_id tags, no longer needed