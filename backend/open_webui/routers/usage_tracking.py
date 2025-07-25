"""
Usage Tracking Router for mAI
Handles OpenRouter usage data collection and webhooks
"""

import asyncio
import hashlib
import hmac
import json
import sqlite3
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
import uuid

import requests
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from pydantic import BaseModel, Field

from open_webui.models.users import Users
from open_webui.utils.auth import get_current_user, get_admin_user
from open_webui.config import DATA_DIR, ORGANIZATION_NAME, OPENROUTER_EXTERNAL_USER
from open_webui.utils.user_mapping import get_external_user_id, user_mapping_service

router = APIRouter()

# Database path
DB_PATH = f"{DATA_DIR}/webui.db"

class UsageWebhookPayload(BaseModel):
    """OpenRouter usage webhook payload structure"""
    api_key: str
    user_id: Optional[str] = None
    model: str
    tokens_used: int
    cost: float
    timestamp: str
    external_user: Optional[str] = None
    request_id: Optional[str] = None

class UsageSyncRequest(BaseModel):
    """Manual usage sync request"""
    days_back: int = Field(default=1, ge=1, le=30)

async def get_openrouter_generations(api_key: str, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Fetch generation data from OpenRouter API"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    url = "https://openrouter.ai/api/v1/generations"
    params = {
        "limit": limit,
        "offset": offset
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"OpenRouter API error: {str(e)}")

def get_client_org_by_api_key(api_key: str) -> Optional[str]:
    """Get client organization ID by API key"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT id FROM client_organizations WHERE openrouter_api_key = ? AND is_active = 1",
            (api_key,)
        )
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        conn.close()

def record_usage_to_db(
    client_org_id: str,
    usage_data: Dict[str, Any],
    external_user: Optional[str] = None
):
    """Record usage data to mAI database using consolidated ORM approach"""
    try:
        from open_webui.models.organization_usage import ClientUsageDB, ClientOrganizationDB
        
        today = date.today()
        
        # Get client markup rate for accurate cost calculations
        client = ClientOrganizationDB.get_client_by_id(client_org_id)
        if not client:
            raise Exception(f"Client organization not found: {client_org_id}")
        
        markup_rate = client.markup_rate
        
        # Validate markup rate
        if markup_rate <= 0:
            raise Exception(f"Invalid markup rate for client {client.name}: {markup_rate}")
        
        # Extract usage details
        model_name = usage_data.get("model", "unknown")
        total_tokens = usage_data.get("total_tokens", 0)
        raw_cost = float(usage_data.get("total_cost", 0.0))
        
        # Validate input data
        if raw_cost < 0:
            raise Exception(f"Negative cost not allowed: ${raw_cost:.6f}")
        
        if total_tokens < 0:
            raise Exception(f"Negative tokens not allowed: {total_tokens}")
        
        # Calculate markup cost using standardized utility
        from open_webui.utils.cost_calculator import calculate_markup_cost
        markup_cost = calculate_markup_cost(raw_cost, markup_rate)
        
        # Parse model to get input/output tokens (simplified assumption)
        # In real usage, these should be separate fields from OpenRouter
        input_tokens = int(total_tokens * 0.7)  # Rough estimate
        output_tokens = total_tokens - input_tokens
        
        # Use the consolidated ORM method from organization_usage.py
        user_id = external_user or "manual_webhook"
        openrouter_user_id = f"webhook_{external_user or 'system'}"
        provider = model_name.split("/")[0] if "/" in model_name else "openrouter"
        
        success = ClientUsageDB.record_usage(
            client_org_id=client_org_id,
            user_id=user_id,
            openrouter_user_id=openrouter_user_id,
            model_name=model_name,
            usage_date=today,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            raw_cost=raw_cost,
            markup_cost=markup_cost,
            provider=provider,
            request_metadata={"source": "webhook", "external_user": external_user}
        )
        
        if success:
            print(f"✅ Recorded {total_tokens} tokens, ${markup_cost:.6f} for {model_name}")
        else:
            print(f"❌ Failed to record usage for {model_name}")
            raise Exception("Database recording failed")
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        raise

@router.post("/webhook/openrouter-usage")
async def openrouter_usage_webhook(
    payload: UsageWebhookPayload,
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Webhook endpoint for OpenRouter usage notifications
    Note: OpenRouter doesn't have native webhooks, but this endpoint
    can receive usage data from other integrations
    """
    try:
        # Verify API key belongs to a client organization
        client_org_id = get_client_org_by_api_key(payload.api_key)
        if not client_org_id:
            raise HTTPException(status_code=404, detail="Client organization not found")
        
        # Process usage data in background
        usage_data = {
            "model": payload.model,
            "total_tokens": payload.tokens_used,
            "total_cost": payload.cost
        }
        
        background_tasks.add_task(
            record_usage_to_db,
            client_org_id,
            usage_data,
            payload.external_user
        )
        
        return {"status": "success", "message": "Usage recorded"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process webhook: {str(e)}")

@router.post("/sync/openrouter-usage")
async def sync_openrouter_usage(
    request: UsageSyncRequest,
    user=Depends(get_admin_user)
):
    """
    Manually sync usage data from OpenRouter API
    This is the primary method since OpenRouter doesn't have webhooks
    """
    try:
        # Get all active client organizations
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, openrouter_api_key 
            FROM client_organizations 
            WHERE is_active = 1 AND openrouter_api_key IS NOT NULL
        """)
        orgs = cursor.fetchall()
        conn.close()
        
        if not orgs:
            raise HTTPException(status_code=404, detail="No active organizations found")
        
        sync_results = []
        
        for org_id, org_name, api_key in orgs:
            try:
                # Fetch recent generations from OpenRouter
                generations_data = await get_openrouter_generations(api_key, limit=50)
                generations = generations_data.get("data", [])
                
                # Process each generation
                synced_count = 0
                for generation in generations:
                    # Check if this generation is from the last N days
                    created_at = generation.get("created_at")
                    if created_at:
                        gen_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        if gen_date.date() >= (date.today() - timedelta(days=request.days_back)):
                            # Record this usage
                            usage_data = {
                                "model": generation.get("model", "unknown"),
                                "total_tokens": generation.get("total_tokens", 0),
                                "total_cost": generation.get("total_cost", 0.0)
                            }
                            
                            record_usage_to_db(
                                org_id,
                                usage_data,
                                generation.get("user")
                            )
                            synced_count += 1
                
                sync_results.append({
                    "organization": org_name,
                    "synced_generations": synced_count,
                    "status": "success"
                })
                
            except Exception as e:
                sync_results.append({
                    "organization": org_name,
                    "error": str(e),
                    "status": "failed"
                })
        
        return {
            "status": "completed",
            "results": sync_results,
            "total_organizations": len(orgs)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

@router.get("/usage/real-time/{client_org_id}")
async def get_real_time_usage(
    client_org_id: str,
    user=Depends(get_current_user)
):
    """Get real-time usage data for a client organization using consolidated ORM approach"""
    try:
        from open_webui.models.organization_usage import ClientUsageDB
        
        # Use the consolidated ORM method
        stats = ClientUsageDB.get_usage_stats_by_client(client_org_id)
        
        return {
            "client_org_id": client_org_id,
            "date": date.today().isoformat(),
            "tokens": stats.today.get("tokens", 0),
            "requests": stats.today.get("requests", 0),
            "cost": stats.today.get("cost", 0.0),
            "last_updated": stats.today.get("last_updated", "No data")
        }
        
    except Exception as e:
        # Fallback to empty data on error
        return {
            "client_org_id": client_org_id,
            "date": date.today().isoformat(),
            "tokens": 0,
            "requests": 0,
            "cost": 0.0,
            "last_updated": 0,
            "error": str(e)
        }

@router.post("/usage/manual-record")
async def manual_record_usage(
    model: str,
    tokens: int,
    cost: float,
    user=Depends(get_admin_user)
):
    """Manually record usage (for testing or corrections) using consolidated ORM approach"""
    try:
        from open_webui.models.organization_usage import ClientOrganizationDB
        
        # Get the first active organization using ORM
        orgs = ClientOrganizationDB.get_all_active_clients()
        
        if not orgs:
            raise HTTPException(status_code=404, detail="No active organization found")
        
        org = orgs[0]  # Use first active organization
        
        usage_data = {
            "model": model,
            "total_tokens": tokens,
            "total_cost": cost
        }
        
        record_usage_to_db(org.id, usage_data, "manual_admin")
        
        return {
            "status": "success",
            "message": f"Recorded {tokens} tokens, ${cost} for {model} in organization {org.name}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record usage: {str(e)}")

# Environment-based Usage Tracking Endpoints
# These endpoints work with the new environment-based configuration

@router.get("/my-organization/usage-summary")
async def get_my_organization_usage_summary(user=Depends(get_current_user)):
    """Get usage summary for the current organization (environment-based)"""
    try:
        # Use environment-based organization name
        org_name = ORGANIZATION_NAME or "My Organization"
        external_user = OPENROUTER_EXTERNAL_USER or f"user_{user.id}"
        
        # For now, return mock data that matches the expected structure
        # TODO: Implement actual usage tracking once OpenRouter integration is complete
        return {
            "success": True,
            "stats": {
                "today": {
                    "tokens": 0,
                    "cost": 0.0,
                    "cost_pln": 0.0,
                    "requests": 0,
                    "last_updated": "No usage today",
                    "exchange_rate": 4.1234,
                    "exchange_rate_date": date.today().isoformat()
                },
                "this_month": {
                    "tokens": 0,
                    "cost": 0.0,
                    "cost_pln": 0.0,
                    "requests": 0,
                    "days_active": 0
                },
                "client_org_name": org_name,
                "exchange_rate_info": {
                    "usd_pln": 4.1234,
                    "effective_date": date.today().isoformat()
                },
                "pln_conversion_available": True
            },
            "client_id": "env_based"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "stats": {
                "today": {"tokens": 0, "cost": 0, "requests": 0, "last_updated": "Error loading data"},
                "this_month": {"tokens": 0, "cost": 0, "requests": 0, "days_active": 0},
                "client_org_name": ORGANIZATION_NAME or "My Organization"
            },
            "client_id": "env_based"
        }

@router.get("/my-organization/today-usage")
async def get_my_organization_today_usage(user=Depends(get_current_user)):
    """Get today's usage for the current organization (environment-based)"""
    try:
        return {
            "success": True,
            "today": {
                "tokens": 0,
                "cost": 0.0,
                "cost_pln": 0.0,
                "requests": 0,
                "last_updated": datetime.now().isoformat(),
                "exchange_rate": 4.1234,
                "exchange_rate_date": date.today().isoformat()
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "today": {
                "tokens": 0,
                "cost": 0,
                "requests": 0,
                "last_updated": "Error loading data"
            }
        }

def get_environment_client_org_id() -> Optional[str]:
    """Get client organization ID for environment-based setup"""
    try:
        from open_webui.models.organization_usage import ClientOrganizationDB
        
        # For environment-based setup, get the first (and should be only) active client
        orgs = ClientOrganizationDB.get_all_active_clients()
        if orgs:
            return orgs[0].id
        
        # Fallback: create a default client org ID based on organization name
        if ORGANIZATION_NAME:
            import hashlib
            org_hash = hashlib.md5(ORGANIZATION_NAME.encode()).hexdigest()[:8]
            return f"env_client_{org_hash}"
        
        return "env_client_default"
    except Exception as e:
        print(f"Warning: Failed to get client org ID: {e}")
        return None

@router.get("/my-organization/usage-by-user")
async def get_my_organization_usage_by_user(user=Depends(get_current_user)):
    """Get usage breakdown by user for the current organization (environment-based)"""
    try:
        from open_webui.models.organization_usage import ClientUsageDB
        
        # Get client organization ID
        client_org_id = get_environment_client_org_id()
        if not client_org_id:
            return {
                "success": False,
                "error": "No client organization found",
                "user_usage": [],
                "organization_name": ORGANIZATION_NAME or "My Organization",
                "total_users": 0
            }
        
        # Get actual usage data from database using current month calculation
        usage_data = ClientUsageDB.get_usage_by_user(client_org_id)
        
        # Get all users to create complete list with user details
        all_users = Users.get_users()
        user_dict = {u.id: u for u in all_users}
        
        # Enhance usage data with user details
        user_usage_list = []
        for usage in usage_data:
            user_obj = user_dict.get(usage['user_id'])
            enhanced_usage = {
                "user_id": usage['user_id'],
                "user_name": user_obj.name if user_obj else usage['user_id'],
                "user_email": user_obj.email if user_obj else "unknown@example.com",
                "external_user_id": usage.get('openrouter_user_id', 'unknown'),
                "total_tokens": usage['total_tokens'],
                "total_requests": usage['total_requests'],
                "markup_cost": usage['markup_cost'],
                "cost_pln": usage['markup_cost'] * 4.1234,  # TODO: Use real exchange rate
                "days_active": usage['days_active'],
                "last_activity": None,  # Could be enhanced with last usage date
                "user_mapping_enabled": True
            }
            user_usage_list.append(enhanced_usage)
        
        # Add users with no usage data
        users_with_usage = {u['user_id'] for u in user_usage_list}
        for user_obj in all_users:
            if user_obj.id not in users_with_usage:
                try:
                    external_user_id = get_external_user_id(user_obj.id, user_obj.name)
                    user_usage_list.append({
                        "user_id": user_obj.id,
                        "user_name": user_obj.name,
                        "user_email": user_obj.email,
                        "external_user_id": external_user_id,
                        "total_tokens": 0,
                        "total_requests": 0,
                        "markup_cost": 0.0,
                        "cost_pln": 0.0,
                        "days_active": 0,
                        "last_activity": None,
                        "user_mapping_enabled": True
                    })
                except Exception as e:
                    user_usage_list.append({
                        "user_id": user_obj.id,
                        "user_name": user_obj.name,
                        "user_email": user_obj.email,
                        "external_user_id": "mapping_error",
                        "total_tokens": 0,
                        "total_requests": 0,
                        "markup_cost": 0.0,
                        "cost_pln": 0.0,
                        "days_active": 0,
                        "last_activity": None,
                        "user_mapping_enabled": False,
                        "error": str(e)
                    })
        
        return {
            "success": True,
            "user_usage": user_usage_list,
            "organization_name": ORGANIZATION_NAME or "My Organization",
            "total_users": len(user_usage_list),
            "user_mapping_info": user_mapping_service.get_mapping_info()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "user_usage": [],
            "organization_name": ORGANIZATION_NAME or "My Organization",
            "total_users": 0
        }

@router.get("/my-organization/usage-by-model")
async def get_my_organization_usage_by_model(user=Depends(get_current_user)):
    """Get usage breakdown by model for the current organization (environment-based)"""
    try:
        from open_webui.models.organization_usage import ClientUsageDB
        
        # Get client organization ID
        client_org_id = get_environment_client_org_id()
        if not client_org_id:
            return {
                "success": False,
                "error": "No client organization found",
                "model_usage": []
            }
        
        # Get actual usage data from database using current month calculation
        usage_data = ClientUsageDB.get_usage_by_model(client_org_id)
        
        # Enhance data with PLN conversion
        model_usage_list = []
        for usage in usage_data:
            enhanced_usage = {
                "model_name": usage['model_name'],
                "provider": usage.get('provider', 'Unknown'),
                "total_tokens": usage['total_tokens'],
                "total_requests": usage['total_requests'],
                "markup_cost": usage['markup_cost'],
                "cost_pln": usage['markup_cost'] * 4.1234,  # TODO: Use real exchange rate
                "days_used": usage.get('days_used', 0)
            }
            model_usage_list.append(enhanced_usage)
        
        return {
            "success": True,
            "model_usage": model_usage_list
        }
    except Exception as e:
        print(f"Error getting model usage: {e}")
        return {
            "success": False,
            "error": str(e),
            "model_usage": []
        }

@router.get("/my-organization/subscription-billing")
async def get_my_organization_subscription_billing(user=Depends(get_current_user)):
    """Get subscription billing data for the current organization (environment-based)"""
    try:
        return {
            "success": True,
            "subscription_data": None  # No subscription billing in environment-based mode
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "subscription_data": None
        }

@router.get("/model-pricing")
async def get_mai_model_pricing():
    """Get mAI model pricing information"""
    try:
        # Return static pricing data for now
        # TODO: Implement real-time pricing fetch from OpenRouter
        models = [
            {
                "id": "anthropic/claude-sonnet-4",
                "name": "Claude Sonnet 4",
                "provider": "Anthropic",
                "price_per_million_input": 8.00,
                "price_per_million_output": 24.00,
                "context_length": 1000000,
                "category": "Premium"
            },
            {
                "id": "google/gemini-2.5-flash",
                "name": "Gemini 2.5 Flash",
                "provider": "Google",
                "price_per_million_input": 1.50,
                "price_per_million_output": 6.00,
                "context_length": 2000000,
                "category": "Fast"
            },
            {
                "id": "openai/gpt-4o-mini",
                "name": "GPT-4o Mini",
                "provider": "OpenAI",
                "price_per_million_input": 0.15,
                "price_per_million_output": 0.60,
                "context_length": 128000,
                "category": "Budget"
            }
        ]
        
        return {
            "success": True,
            "models": models
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "models": []
        }