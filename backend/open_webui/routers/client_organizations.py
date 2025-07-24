from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from typing import Optional, List
from datetime import date, datetime, timedelta

from open_webui.models.organization_usage import (
    GlobalSettingsDB, ClientOrganizationDB, UserClientMappingDB, ClientUsageDB,
    GlobalSettingsForm, ClientOrganizationForm, UserClientMappingForm,
    GlobalSettingsModel, ClientOrganizationModel, UserClientMappingModel,
    ClientUsageStatsResponse, ClientBillingResponse
)
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.openrouter_client_manager import openrouter_client_manager

router = APIRouter()

####################
# Global Settings Endpoints
####################

@router.get("/settings", response_model=GlobalSettingsModel)
async def get_global_settings(user=Depends(get_admin_user)):
    """Get global settings for OpenRouter provisioning"""
    settings = GlobalSettingsDB.get_settings()
    if not settings:
        # Return default settings if none exist
        return GlobalSettingsModel(
            id="global",
            openrouter_provisioning_key=None,
            default_markup_rate=1.3,
            billing_currency="USD",
            created_at=0,
            updated_at=0
        )
    return settings

@router.post("/settings")
async def update_global_settings(
    settings_form: GlobalSettingsForm,
    user=Depends(get_admin_user)
):
    """Update global settings"""
    settings = GlobalSettingsDB.create_or_update_settings(settings_form)
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update global settings"
        )
    
    # Refresh the client manager settings
    openrouter_client_manager.refresh_settings()
    
    return {"success": True, "settings": settings.model_dump()}

####################
# Client Organization Endpoints
####################

@router.get("/clients", response_model=List[ClientOrganizationModel])
async def get_all_clients(user=Depends(get_admin_user)):
    """Get all active client organizations"""
    clients = ClientOrganizationDB.get_all_active_clients()
    return clients

@router.get("/clients/{client_id}", response_model=ClientOrganizationModel)
async def get_client_by_id(client_id: str, user=Depends(get_admin_user)):
    """Get a specific client organization by ID"""
    client = ClientOrganizationDB.get_client_by_id(client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client organization not found"
        )
    return client

@router.post("/clients")
async def create_client_organization(
    client_form: ClientOrganizationForm,
    user=Depends(get_admin_user)
):
    """Create a new client organization with dedicated OpenRouter API key"""
    try:
        result = await openrouter_client_manager.create_client_organization(client_form)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create client organization: {str(e)}"
        )

@router.patch("/clients/{client_id}")
async def update_client_organization(
    client_id: str,
    updates: dict,
    user=Depends(get_admin_user)
):
    """Update a client organization"""
    # Handle special case for monthly limit updates
    if "monthly_limit" in updates:
        result = await openrouter_client_manager.update_client_limits(
            client_id=client_id,
            new_limit=updates["monthly_limit"]
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return result
    
    # Handle other updates
    updated_client = ClientOrganizationDB.update_client(client_id, updates)
    if not updated_client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client organization not found or update failed"
        )
    
    return {
        "success": True,
        "message": "Client organization updated successfully",
        "client": updated_client.model_dump()
    }

@router.delete("/clients/{client_id}")
async def deactivate_client_organization(
    client_id: str,
    user=Depends(get_admin_user)
):
    """Deactivate a client organization and disable their API key"""
    result = await openrouter_client_manager.deactivate_client_organization(client_id)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return result

####################
# User-Client Mapping Endpoints
####################

@router.get("/user-mappings", response_model=List[UserClientMappingModel])
async def get_all_user_mappings(user=Depends(get_admin_user)):
    """Get all active user-client mappings"""
    mappings = UserClientMappingDB.get_all_active_mappings()
    return mappings

@router.get("/user-mappings/{user_id}")
async def get_user_mapping(user_id: str, user=Depends(get_admin_user)):
    """Get user-client mapping by user ID"""
    mapping = UserClientMappingDB.get_mapping_by_user_id(user_id)
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User mapping not found"
        )
    return mapping

@router.post("/user-mappings")
async def create_user_mapping(
    mapping_form: UserClientMappingForm,
    user=Depends(get_admin_user)
):
    """Create a new user-client mapping"""
    # Verify client exists
    client = ClientOrganizationDB.get_client_by_id(mapping_form.client_org_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client organization not found"
        )
    
    mapping = UserClientMappingDB.create_mapping(mapping_form)
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user mapping"
        )
    
    return {
        "success": True,
        "message": "User mapping created successfully",
        "mapping": mapping.model_dump()
    }

@router.delete("/user-mappings/{user_id}")
async def deactivate_user_mapping(
    user_id: str,
    user=Depends(get_admin_user)
):
    """Deactivate a user-client mapping"""
    success = UserClientMappingDB.deactivate_mapping(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User mapping not found or deactivation failed"
        )
    
    return {
        "success": True,
        "message": "User mapping deactivated successfully"
    }

####################
# Usage and Billing Endpoints
####################

@router.get("/usage/my-organization")
async def get_my_organization_usage(
    request: Request,
    user=Depends(get_verified_user)
):
    """Get usage summary for the current user's organization"""
    try:
        # First, get the user's organization mapping
        mapping = UserClientMappingDB.get_mapping_by_user_id(user.id)
        
        if not mapping:
            # Auto-create default organization for testing/demo purposes
            # In production, this should be done through proper admin setup
            default_org = None
            all_orgs = ClientOrganizationDB.get_all_active_clients()
            
            # Check if there's a default organization
            for org in all_orgs:
                if org.name == "Default Organization" or org.name == "Test Organization":
                    default_org = org
                    break
            
            # If no default org exists, create one
            if not default_org:
                from open_webui.models.organization_usage import ClientOrganizationForm
                org_form = ClientOrganizationForm(
                    name="Default Organization",
                    markup_rate=1.3,
                    monthly_limit=1000.0,
                    billing_email="admin@example.com"
                )
                default_org = ClientOrganizationDB.create_client(
                    client_form=org_form,
                    api_key=request.app.state.config.OPENAI_API_KEYS[0] if hasattr(request.app.state.config, 'OPENAI_API_KEYS') and request.app.state.config.OPENAI_API_KEYS else "sk-default-test-key",
                    key_hash="default_org_hash"
                )
            
            # Create user mapping to default organization
            if default_org:
                from open_webui.models.organization_usage import UserClientMappingForm
                mapping_form = UserClientMappingForm(
                    user_id=user.id,
                    client_org_id=default_org.id,
                    openrouter_user_id=f"openrouter_{user.id}"
                )
                mapping = UserClientMappingDB.create_mapping(mapping_form)
        
        if not mapping:
            # If no mapping exists, return empty stats
            return {
                "success": True,
                "stats": {
                    "today": {
                        "tokens": 0,
                        "cost": 0.0,
                        "requests": 0,
                        "last_updated": "No organization assigned"
                    },
                    "this_month": {
                        "tokens": 0,
                        "cost": 0.0,
                        "requests": 0,
                        "days_active": 0
                    },
                    "daily_history": [],
                    "client_org_name": "No Organization"
                }
            }
        
        # Get the usage stats for the user's organization
        stats = ClientUsageDB.get_usage_stats_by_client(mapping.client_org_id)
        return {
            "success": True, 
            "stats": stats.model_dump(),
            "client_id": mapping.client_org_id
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get organization usage: {str(e)}"
        )

@router.get("/usage/my-organization/today")
async def get_my_organization_today_usage(
    user=Depends(get_verified_user)
):
    """Get today's usage for the current user's organization"""
    try:
        # First, get the user's organization mapping
        mapping = UserClientMappingDB.get_mapping_by_user_id(user.id)
        
        if not mapping:
            return {
                "success": True,
                "today": {
                    "tokens": 0,
                    "cost": 0.0,
                    "requests": 0,
                    "last_updated": "No organization assigned"
                }
            }
        
        # Get today's usage for the organization
        stats = ClientUsageDB.get_usage_stats_by_client(mapping.client_org_id)
        return {
            "success": True,
            "today": stats.today,
            "last_updated": stats.today.get('last_updated', 'No data')
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get today's usage: {str(e)}"
        )

@router.get("/usage/summary")
async def get_client_usage_summary(
    client_id: Optional[str] = None,
    user=Depends(get_admin_user)
):
    """Get Option 1 hybrid usage summary - real-time today + daily history"""
    try:
        if client_id:
            # Get stats for specific client (Option 1 format)
            stats = ClientUsageDB.get_usage_stats_by_client(client_id)
            return {"success": True, "stats": stats.model_dump()}
        else:
            # Get billing data for all clients
            billing_data = ClientUsageDB.get_all_clients_usage_stats()
            return {
                "success": True,
                "billing_data": [client.model_dump() for client in billing_data]
            }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage statistics: {str(e)}"
        )

@router.get("/usage/today")
async def get_today_usage(
    client_id: str,
    user=Depends(get_admin_user)
):
    """Get real-time usage for today only (for live updates)"""
    try:
        stats = ClientUsageDB.get_usage_stats_by_client(client_id)
        return {
            "success": True,
            "today": stats.today,
            "last_updated": stats.today.get('last_updated', 'No data')
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get today's usage: {str(e)}"
        )

@router.get("/usage/billing")
async def get_billing_summary(
    days_back: int = 30,
    user=Depends(get_admin_user)
):
    """Get billing summary for all clients"""
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        billing_data = ClientUsageDB.get_all_clients_usage_stats(start_date, end_date)
        
        # Calculate totals
        total_raw_cost = sum(client.raw_cost for client in billing_data)
        total_markup_cost = sum(client.markup_cost for client in billing_data)
        total_profit = total_markup_cost - total_raw_cost
        total_tokens = sum(client.total_tokens for client in billing_data)
        total_requests = sum(client.total_requests for client in billing_data)
        
        return {
            "success": True,
            "period": f"{start_date} to {end_date}",
            "summary": {
                "total_raw_cost": total_raw_cost,
                "total_markup_cost": total_markup_cost,
                "total_profit": total_profit,
                "total_tokens": total_tokens,
                "total_requests": total_requests,
                "profit_margin_percent": (total_profit / total_raw_cost * 100) if total_raw_cost > 0 else 0,
                "active_clients": len(billing_data)
            },
            "clients": [client.model_dump() for client in billing_data]
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate billing summary: {str(e)}"
        )

@router.get("/usage/by-user/{client_id}")
async def get_usage_by_user(
    client_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    user=Depends(get_admin_user)
):
    """Get usage breakdown by user for a client organization"""
    try:
        user_usage = ClientUsageDB.get_usage_by_user(client_id, start_date, end_date)
        return {
            "success": True,
            "client_id": client_id,
            "user_usage": user_usage,
            "period": {
                "start": start_date.isoformat() if start_date else "last 30 days",
                "end": end_date.isoformat() if end_date else date.today().isoformat()
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )


@router.get("/usage/by-model/{client_id}")
async def get_usage_by_model(
    client_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    user=Depends(get_admin_user)
):
    """Get usage breakdown by AI model for a client organization"""
    try:
        model_usage = ClientUsageDB.get_usage_by_model(client_id, start_date, end_date)
        return {
            "success": True,
            "client_id": client_id,
            "model_usage": model_usage,
            "period": {
                "start": start_date.isoformat() if start_date else "last 30 days",
                "end": end_date.isoformat() if end_date else date.today().isoformat()
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )


@router.get("/usage/export")
async def export_usage_data(
    client_id: Optional[str] = None,
    format: str = "json",
    user=Depends(get_admin_user)
):
    """Export usage data for billing purposes (Option 1: Daily summaries)"""
    try:
        if client_id:
            # Export daily summaries for specific client
            stats = ClientUsageDB.get_usage_stats_by_client(client_id)
            data = {
                "client_name": stats.client_org_name,
                "export_date": datetime.now().isoformat(),
                "today_usage": stats.today,
                "month_totals": stats.this_month,
                "daily_history": stats.daily_history
            }
        else:
            # Export billing summary for all clients
            billing_data = ClientUsageDB.get_all_clients_usage_stats()
            data = {
                "export_date": datetime.now().isoformat(),
                "clients": [client.model_dump() for client in billing_data],
                "total_clients": len(billing_data),
                "summary": {
                    "total_markup_cost": sum(c.markup_cost for c in billing_data),
                    "total_raw_cost": sum(c.raw_cost for c in billing_data),
                    "total_profit": sum(c.profit_margin for c in billing_data),
                    "total_tokens": sum(c.total_tokens for c in billing_data)
                }
            }
        
        if format.lower() == "csv":
            # TODO: Implement CSV export for daily summaries
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="CSV export not yet implemented for Option 1"
            )
        
        return {
            "success": True,
            "data": data,
            "export_date": datetime.now().isoformat(),
            "format": "Option 1 - Daily summaries"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export usage data: {str(e)}"
        )