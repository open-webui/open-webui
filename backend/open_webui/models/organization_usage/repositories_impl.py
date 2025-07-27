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
    GlobalSettings, ProcessedGeneration, ProcessedGenerationCleanupLog,
    ClientOrganization, UserClientMapping, ClientDailyUsage,
    ClientUserDailyUsage, ClientModelDailyUsage
)
from .domain import (
    GlobalSettingsModel, GlobalSettingsForm,
    ClientOrganizationModel, ClientOrganizationForm,
    UserClientMappingModel, UserClientMappingForm,
    ClientUsageStatsResponse, ClientBillingResponse,
    UsageRecordDTO, ProcessedGenerationInfo, CleanupStatsResult
)
from .repositories import (
    IGlobalSettingsRepository, IClientOrganizationRepository,
    IUserClientMappingRepository, IClientUsageRepository,
    IProcessedGenerationRepository
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


class ProcessedGenerationRepository(IProcessedGenerationRepository):
    """Implementation of processed generation repository"""

    def is_generation_processed(self, generation_id: str, client_org_id: str) -> bool:
        """Check if a generation has already been processed"""
        try:
            with get_db() as db:
                processed = db.query(ProcessedGeneration).filter_by(
                    id=generation_id,
                    client_org_id=client_org_id
                ).first()
                return processed is not None
        except Exception as e:
            log.error(f"Error checking processed generation {generation_id}: {e}")
            return False

    def mark_generation_processed(
        self, generation_info: ProcessedGenerationInfo
    ) -> bool:
        """Mark a generation as processed"""
        try:
            with get_db() as db:
                processed_gen = ProcessedGeneration(
                    id=generation_info.generation_id,
                    client_org_id=generation_info.client_org_id,
                    generation_date=generation_info.generation_date,
                    processed_at=generation_info.processed_at,
                    total_cost=generation_info.total_cost,
                    total_tokens=generation_info.total_tokens
                )
                db.add(processed_gen)
                db.commit()
                return True
        except Exception as e:
            log.error(f"Error marking generation {generation_info.generation_id} as processed: {e}")
            return False

    def cleanup_old_processed_generations(self, days_to_keep: int = 60) -> CleanupStatsResult:
        """Clean up old processed generation records to prevent table bloat"""
        cleanup_start_time = time.time()
        
        try:
            cutoff_date = date.today() - timedelta(days=days_to_keep)
            cutoff_timestamp = int(time.time()) - (days_to_keep * 24 * 3600)
            
            with get_db() as db:
                # First, get statistics before cleanup for logging
                total_records_query = db.query(ProcessedGeneration).count()
                records_to_delete_query = db.query(ProcessedGeneration).filter(
                    ProcessedGeneration.processed_at < cutoff_timestamp
                ).count()
                
                # Get breakdown by organization for audit trail
                org_breakdown_query = db.query(
                    ProcessedGeneration.client_org_id,
                    func.count(ProcessedGeneration.id).label('count'),
                    func.sum(ProcessedGeneration.total_tokens).label('tokens'),
                    func.sum(ProcessedGeneration.total_cost).label('cost')
                ).filter(
                    ProcessedGeneration.processed_at < cutoff_timestamp
                ).group_by(ProcessedGeneration.client_org_id).all()
                
                org_stats = {}
                total_old_tokens = 0
                total_old_cost = 0.0
                
                for org_id, count, tokens, cost in org_breakdown_query:
                    org_stats[org_id] = {
                        "records": count,
                        "tokens": tokens or 0,
                        "cost": cost or 0.0
                    }
                    total_old_tokens += tokens or 0
                    total_old_cost += cost or 0.0
                
                # Perform the actual cleanup
                deleted_count = db.query(ProcessedGeneration).filter(
                    ProcessedGeneration.processed_at < cutoff_timestamp
                ).delete()
                
                db.commit()
                
                # Calculate cleanup duration and storage estimates
                cleanup_duration = time.time() - cleanup_start_time
                records_remaining = total_records_query - deleted_count
                
                # Estimate storage savings (approximate)
                avg_record_size_bytes = 100  # Rough estimate per record
                storage_saved_kb = (deleted_count * avg_record_size_bytes) / 1024
                
                # Log cleanup operation to audit table
                cleanup_log_entry = ProcessedGenerationCleanupLog(
                    cleanup_date=date.today(),
                    cutoff_date=cutoff_date,
                    days_retained=days_to_keep,
                    records_before=total_records_query,
                    records_deleted=deleted_count,
                    records_remaining=records_remaining,
                    old_tokens_removed=total_old_tokens,
                    old_cost_removed=total_old_cost,
                    storage_saved_kb=storage_saved_kb,
                    cleanup_duration_seconds=cleanup_duration,
                    success=True,
                    created_at=int(time.time())
                )
                db.add(cleanup_log_entry)
                db.commit()
                
                # Enhanced logging for production monitoring
                if deleted_count > 0:
                    log.info(f"🧹 Processed generations cleanup completed: "
                           f"{deleted_count:,} records deleted ({records_remaining:,} remaining), "
                           f"{total_old_tokens:,} tokens, ${total_old_cost:.6f} removed, "
                           f"~{storage_saved_kb:.1f}KB saved in {cleanup_duration:.2f}s")
                    
                    # Log organization breakdown for audit
                    for org_id, stats in org_stats.items():
                        log.debug(f"  • {org_id}: {stats['records']} records, "
                                f"{stats['tokens']:,} tokens, ${stats['cost']:.6f}")
                else:
                    log.debug(f"Processed generations cleanup: No old records found (cutoff: {cutoff_date})")
                
                return CleanupStatsResult(
                    success=True,
                    cutoff_date=cutoff_date.isoformat(),
                    days_to_keep=days_to_keep,
                    records_before=total_records_query,
                    records_deleted=deleted_count,
                    records_remaining=records_remaining,
                    old_tokens_removed=total_old_tokens,
                    old_cost_removed=total_old_cost,
                    storage_saved_kb=round(storage_saved_kb, 2),
                    cleanup_duration_seconds=round(cleanup_duration, 3),
                    organization_breakdown=org_stats,
                    cleanup_timestamp=int(time.time())
                )
                
        except Exception as e:
            cleanup_duration = time.time() - cleanup_start_time
            
            # Log failed cleanup to audit table (if possible)
            try:
                with get_db() as db:
                    cutoff_date = date.today() - timedelta(days=days_to_keep)
                    cleanup_log_entry = ProcessedGenerationCleanupLog(
                        cleanup_date=date.today(),
                        cutoff_date=cutoff_date,
                        days_retained=days_to_keep,
                        records_before=0,
                        records_deleted=0,
                        records_remaining=0,
                        old_tokens_removed=0,
                        old_cost_removed=0.0,
                        storage_saved_kb=0.0,
                        cleanup_duration_seconds=cleanup_duration,
                        success=False,
                        error_message=str(e)[:500],  # Truncate long error messages
                        created_at=int(time.time())
                    )
                    db.add(cleanup_log_entry)
                    db.commit()
            except Exception as log_error:
                log.error(f"Failed to log cleanup error to audit table: {log_error}")
            
            log.error(f"❌ Error cleaning up processed generations: {e}")
            return CleanupStatsResult(
                success=False,
                cutoff_date="",
                days_to_keep=days_to_keep,
                records_before=0,
                records_deleted=0,
                records_remaining=0,
                old_tokens_removed=0,
                old_cost_removed=0.0,
                storage_saved_kb=0.0,
                cleanup_duration_seconds=round(cleanup_duration, 3),
                organization_breakdown={},
                cleanup_timestamp=int(time.time()),
                error=str(e)
            )

    def get_processed_generations_stats(
        self, client_org_id: str, start_date: date = None, end_date: date = None
    ) -> Dict[str, Any]:
        """Get statistics about processed generations for debugging"""
        try:
            with get_db() as db:
                query = db.query(ProcessedGeneration).filter_by(client_org_id=client_org_id)
                
                if start_date:
                    query = query.filter(ProcessedGeneration.generation_date >= start_date)
                if end_date:
                    query = query.filter(ProcessedGeneration.generation_date <= end_date)
                
                generations = query.all()
                
                total_cost = sum(g.total_cost for g in generations)
                total_tokens = sum(g.total_tokens for g in generations)
                
                return {
                    "client_org_id": client_org_id,
                    "total_processed": len(generations),
                    "total_cost": total_cost,
                    "total_tokens": total_tokens,
                    "date_range": {
                        "start": start_date.isoformat() if start_date else None,
                        "end": end_date.isoformat() if end_date else None
                    }
                }
        except Exception as e:
            log.error(f"Error getting processed generation stats: {e}")
            return {}