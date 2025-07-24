import logging
from datetime import date, datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.models.users import UserModel
from open_webui.models.organization_usage import (
    OrganizationSettingsDB,
    OrganizationUsageDB,
    OpenRouterUserMappingDB,
    OrganizationSettingsForm,
    UserMappingForm,
    UsageStatsResponse,
    UserUsageResponse,
    ModelUsageResponse,
    DailyUsageResponse,
)
from open_webui.utils.background_sync import organization_usage_sync
from open_webui.utils.openrouter_org import openrouter_usage_service

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("ORGANIZATION", logging.INFO))

router = APIRouter()

####################
# Request/Response Models
####################

class SyncResponse(BaseModel):
    success: bool
    message: str
    stats: Optional[dict] = None

class StatusResponse(BaseModel):
    is_running: bool
    sync_enabled: bool
    sync_interval_hours: int
    last_sync_at: Optional[int] = None
    last_sync_human: Optional[str] = None
    hours_since_last_sync: Optional[float] = None

class DateRangeRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None

####################
# Organization Settings Endpoints
####################

@router.get("/settings")
async def get_organization_settings(user: UserModel = Depends(get_admin_user)):
    """Get organization settings (admin only)"""
    try:
        settings = OrganizationSettingsDB.get_settings()
        if settings:
            # Don't expose the API key in the response
            settings_dict = settings.model_dump()
            if settings_dict.get("openrouter_api_key"):
                settings_dict["openrouter_api_key"] = "***configured***"
            return settings_dict
        else:
            return {
                "id": "default",
                "openrouter_org_id": None,
                "openrouter_api_key": None,
                "sync_enabled": True,
                "sync_interval_hours": 1,
                "last_sync_at": None
            }
    except Exception as e:
        log.error(f"Failed to get organization settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to get organization settings")

@router.post("/settings")
async def update_organization_settings(
    settings_form: OrganizationSettingsForm,
    user: UserModel = Depends(get_admin_user)
):
    """Update organization settings (admin only)"""
    try:
        result = OrganizationSettingsDB.create_or_update_settings(settings_form)
        if result:
            # Refresh the OpenRouter client settings
            openrouter_usage_service.client.refresh_settings()
            
            # Restart background sync if settings changed
            if settings_form.sync_enabled:
                await organization_usage_sync.stop_sync_service()
                await organization_usage_sync.start_sync_service()
            else:
                await organization_usage_sync.stop_sync_service()
            
            # Don't expose the API key in the response
            result_dict = result.model_dump()
            if result_dict.get("openrouter_api_key"):
                result_dict["openrouter_api_key"] = "***configured***"
            return result_dict
        else:
            raise HTTPException(status_code=500, detail="Failed to update settings")
    except Exception as e:
        log.error(f"Failed to update organization settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update organization settings")

####################
# User Mapping Endpoints
####################

@router.get("/user-mappings")
async def get_user_mappings(user: UserModel = Depends(get_admin_user)):
    """Get all user mappings (admin only)"""
    try:
        mappings = OpenRouterUserMappingDB.get_all_active_mappings()
        return {"mappings": [mapping.model_dump() for mapping in mappings]}
    except Exception as e:
        log.error(f"Failed to get user mappings: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user mappings")

@router.post("/user-mappings")
async def create_user_mapping(
    mapping_form: UserMappingForm,
    user: UserModel = Depends(get_admin_user)
):
    """Create a new user mapping (admin only)"""
    try:
        result = OpenRouterUserMappingDB.create_mapping(mapping_form)
        if result:
            return result.model_dump()
        else:
            raise HTTPException(status_code=500, detail="Failed to create user mapping")
    except Exception as e:
        log.error(f"Failed to create user mapping: {e}")
        raise HTTPException(status_code=500, detail="Failed to create user mapping")

@router.delete("/user-mappings/{owui_user_id}")
async def deactivate_user_mapping(
    owui_user_id: str,
    user: UserModel = Depends(get_admin_user)
):
    """Deactivate a user mapping (admin only)"""
    try:
        result = OpenRouterUserMappingDB.deactivate_mapping(owui_user_id)
        if result:
            return {"success": True, "message": "User mapping deactivated"}
        else:
            raise HTTPException(status_code=404, detail="User mapping not found")
    except Exception as e:
        log.error(f"Failed to deactivate user mapping: {e}")
        raise HTTPException(status_code=500, detail="Failed to deactivate user mapping")

####################
# Usage Data Endpoints
####################

@router.post("/usage/stats")
async def get_usage_stats(
    date_range: DateRangeRequest,
    user: UserModel = Depends(get_admin_user)
):
    """Get organization usage statistics (admin only)"""
    try:
        start_date = None
        end_date = None
        
        if date_range.start_date:
            start_date = datetime.fromisoformat(date_range.start_date).date()
        if date_range.end_date:
            end_date = datetime.fromisoformat(date_range.end_date).date()
        
        result = await openrouter_usage_service.get_organization_stats(start_date, end_date)
        return result
    except Exception as e:
        log.error(f"Failed to get usage stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get usage stats")

@router.post("/usage/by-user")
async def get_usage_by_user(
    date_range: DateRangeRequest,
    user: UserModel = Depends(get_admin_user)
):
    """Get usage breakdown by user (admin only)"""
    try:
        start_date = None
        end_date = None
        
        if date_range.start_date:
            start_date = datetime.fromisoformat(date_range.start_date).date()
        if date_range.end_date:
            end_date = datetime.fromisoformat(date_range.end_date).date()
        
        # Get usage records
        usage_records = OrganizationUsageDB.get_usage_by_date_range(
            start_date or (date.today() - timedelta(days=30)),
            end_date or date.today()
        )
        
        # Group by user
        user_usage = {}
        for record in usage_records:
            user_id = record.user_id
            if user_id not in user_usage:
                user_usage[user_id] = {
                    "user_id": user_id,
                    "user_name": user_id,  # TODO: Get actual user name
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "total_requests": 0,
                    "models": {}
                }
            
            user_usage[user_id]["total_tokens"] += record.total_tokens
            user_usage[user_id]["total_cost"] += record.total_cost
            user_usage[user_id]["total_requests"] += record.request_count
            
            model_name = record.model_name
            if model_name not in user_usage[user_id]["models"]:
                user_usage[user_id]["models"][model_name] = {
                    "model_name": model_name,
                    "tokens": 0,
                    "cost": 0.0,
                    "requests": 0
                }
            
            user_usage[user_id]["models"][model_name]["tokens"] += record.total_tokens
            user_usage[user_id]["models"][model_name]["cost"] += record.total_cost
            user_usage[user_id]["models"][model_name]["requests"] += record.request_count
        
        # Convert models dict to list
        for user_data in user_usage.values():
            user_data["models"] = list(user_data["models"].values())
        
        return {"users": list(user_usage.values())}
    except Exception as e:
        log.error(f"Failed to get usage by user: {e}")
        raise HTTPException(status_code=500, detail="Failed to get usage by user")

@router.post("/usage/by-model")
async def get_usage_by_model(
    date_range: DateRangeRequest,
    user: UserModel = Depends(get_admin_user)
):
    """Get usage breakdown by model (admin only)"""
    try:
        start_date = None
        end_date = None
        
        if date_range.start_date:
            start_date = datetime.fromisoformat(date_range.start_date).date()
        if date_range.end_date:
            end_date = datetime.fromisoformat(date_range.end_date).date()
        
        # Get usage records
        usage_records = OrganizationUsageDB.get_usage_by_date_range(
            start_date or (date.today() - timedelta(days=30)),
            end_date or date.today()
        )
        
        # Group by model
        model_usage = {}
        for record in usage_records:
            model_name = record.model_name
            if model_name not in model_usage:
                model_usage[model_name] = {
                    "model_name": model_name,
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "total_requests": 0,
                    "users": {}
                }
            
            model_usage[model_name]["total_tokens"] += record.total_tokens
            model_usage[model_name]["total_cost"] += record.total_cost
            model_usage[model_name]["total_requests"] += record.request_count
            
            user_id = record.user_id
            if user_id not in model_usage[model_name]["users"]:
                model_usage[model_name]["users"][user_id] = {
                    "user_id": user_id,
                    "user_name": user_id,  # TODO: Get actual user name
                    "tokens": 0,
                    "cost": 0.0,
                    "requests": 0
                }
            
            model_usage[model_name]["users"][user_id]["tokens"] += record.total_tokens
            model_usage[model_name]["users"][user_id]["cost"] += record.total_cost
            model_usage[model_name]["users"][user_id]["requests"] += record.request_count
        
        # Convert users dict to list
        for model_data in model_usage.values():
            model_data["users"] = list(model_data["users"].values())
        
        return {"models": list(model_usage.values())}
    except Exception as e:
        log.error(f"Failed to get usage by model: {e}")
        raise HTTPException(status_code=500, detail="Failed to get usage by model")

@router.post("/usage/daily")
async def get_daily_usage(
    date_range: DateRangeRequest,
    user: UserModel = Depends(get_admin_user)
):
    """Get daily usage breakdown (admin only)"""
    try:
        start_date = None
        end_date = None
        
        if date_range.start_date:
            start_date = datetime.fromisoformat(date_range.start_date).date()
        if date_range.end_date:
            end_date = datetime.fromisoformat(date_range.end_date).date()
        
        # Get usage records
        usage_records = OrganizationUsageDB.get_usage_by_date_range(
            start_date or (date.today() - timedelta(days=30)),
            end_date or date.today()
        )
        
        # Group by date
        daily_usage = {}
        for record in usage_records:
            date_str = record.usage_date.isoformat()
            if date_str not in daily_usage:
                daily_usage[date_str] = {
                    "date": date_str,
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "total_requests": 0,
                    "breakdown": {}
                }
            
            daily_usage[date_str]["total_tokens"] += record.total_tokens
            daily_usage[date_str]["total_cost"] += record.total_cost
            daily_usage[date_str]["total_requests"] += record.request_count
            
            # Add model breakdown
            model_name = record.model_name
            if model_name not in daily_usage[date_str]["breakdown"]:
                daily_usage[date_str]["breakdown"][model_name] = {
                    "model_name": model_name,
                    "tokens": 0,
                    "cost": 0.0,
                    "requests": 0
                }
            
            daily_usage[date_str]["breakdown"][model_name]["tokens"] += record.total_tokens
            daily_usage[date_str]["breakdown"][model_name]["cost"] += record.total_cost
            daily_usage[date_str]["breakdown"][model_name]["requests"] += record.request_count
        
        # Convert breakdown dict to list and sort by date
        for daily_data in daily_usage.values():
            daily_data["breakdown"] = list(daily_data["breakdown"].values())
        
        daily_list = list(daily_usage.values())
        daily_list.sort(key=lambda x: x["date"])
        
        return {"daily_usage": daily_list}
    except Exception as e:
        log.error(f"Failed to get daily usage: {e}")
        raise HTTPException(status_code=500, detail="Failed to get daily usage")

####################
# Sync Control Endpoints
####################

@router.get("/sync/status")
async def get_sync_status(user: UserModel = Depends(get_admin_user)):
    """Get background sync service status (admin only)"""
    try:
        status = organization_usage_sync.get_status()
        return status
    except Exception as e:
        log.error(f"Failed to get sync status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get sync status")

@router.post("/sync/manual")
async def manual_sync(user: UserModel = Depends(get_admin_user)):
    """Trigger manual sync (admin only)"""
    try:
        result = await organization_usage_sync.force_sync()
        return result
    except Exception as e:
        log.error(f"Failed to trigger manual sync: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger manual sync")

@router.post("/sync/start")
async def start_sync_service(user: UserModel = Depends(get_admin_user)):
    """Start background sync service (admin only)"""
    try:
        await organization_usage_sync.start_sync_service()
        return {"success": True, "message": "Background sync service started"}
    except Exception as e:
        log.error(f"Failed to start sync service: {e}")
        raise HTTPException(status_code=500, detail="Failed to start sync service")

@router.post("/sync/stop")
async def stop_sync_service(user: UserModel = Depends(get_admin_user)):
    """Stop background sync service (admin only)"""
    try:
        await organization_usage_sync.stop_sync_service()
        return {"success": True, "message": "Background sync service stopped"}
    except Exception as e:
        log.error(f"Failed to stop sync service: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop sync service")