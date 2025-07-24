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
from open_webui.config import DATA_DIR

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
    """Record usage data to mAI database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        today = date.today()
        timestamp = int(datetime.now().timestamp())
        
        # Extract usage details
        model_name = usage_data.get("model", "unknown")
        total_tokens = usage_data.get("total_tokens", 0)
        raw_cost = float(usage_data.get("total_cost", 0.0))
        markup_cost = raw_cost * 1.3  # mAI markup
        
        # Update live counters
        cursor.execute("""
            INSERT OR REPLACE INTO client_live_counters 
            (client_org_id, current_date, today_tokens, today_requests, 
             today_raw_cost, today_markup_cost, last_updated)
            VALUES (
                ?, ?, 
                COALESCE((SELECT today_tokens FROM client_live_counters 
                         WHERE client_org_id = ? AND current_date = ?), 0) + ?,
                COALESCE((SELECT today_requests FROM client_live_counters 
                         WHERE client_org_id = ? AND current_date = ?), 0) + 1,
                COALESCE((SELECT today_raw_cost FROM client_live_counters 
                         WHERE client_org_id = ? AND current_date = ?), 0.0) + ?,
                COALESCE((SELECT today_markup_cost FROM client_live_counters 
                         WHERE client_org_id = ? AND current_date = ?), 0.0) + ?,
                ?
            )
        """, (
            client_org_id, today,
            client_org_id, today, total_tokens,
            client_org_id, today,
            client_org_id, today, raw_cost,
            client_org_id, today, markup_cost,
            timestamp
        ))
        
        # Update daily usage summary
        cursor.execute("""
            INSERT OR REPLACE INTO client_daily_usage
            (id, client_org_id, usage_date, total_tokens, total_requests,
             raw_cost, markup_cost, primary_model, unique_users, created_at, updated_at)
            VALUES (
                COALESCE((SELECT id FROM client_daily_usage 
                         WHERE client_org_id = ? AND usage_date = ?), ?),
                ?, ?,
                COALESCE((SELECT total_tokens FROM client_daily_usage 
                         WHERE client_org_id = ? AND usage_date = ?), 0) + ?,
                COALESCE((SELECT total_requests FROM client_daily_usage 
                         WHERE client_org_id = ? AND usage_date = ?), 0) + 1,
                COALESCE((SELECT raw_cost FROM client_daily_usage 
                         WHERE client_org_id = ? AND usage_date = ?), 0.0) + ?,
                COALESCE((SELECT markup_cost FROM client_daily_usage 
                         WHERE client_org_id = ? AND usage_date = ?), 0.0) + ?,
                ?, 1, ?, ?
            )
        """, (
            client_org_id, today, str(uuid.uuid4()),
            client_org_id, today,
            client_org_id, today, total_tokens,
            client_org_id, today,
            client_org_id, today, raw_cost,
            client_org_id, today, markup_cost,
            model_name, timestamp, timestamp
        ))
        
        # Record per-model usage
        cursor.execute("""
            INSERT OR REPLACE INTO client_model_daily_usage
            (id, client_org_id, model_name, usage_date, total_tokens, total_requests,
             raw_cost, markup_cost, provider, created_at, updated_at)
            VALUES (
                COALESCE((SELECT id FROM client_model_daily_usage 
                         WHERE client_org_id = ? AND model_name = ? AND usage_date = ?), ?),
                ?, ?, ?,
                COALESCE((SELECT total_tokens FROM client_model_daily_usage 
                         WHERE client_org_id = ? AND model_name = ? AND usage_date = ?), 0) + ?,
                COALESCE((SELECT total_requests FROM client_model_daily_usage 
                         WHERE client_org_id = ? AND model_name = ? AND usage_date = ?), 0) + 1,
                COALESCE((SELECT raw_cost FROM client_model_daily_usage 
                         WHERE client_org_id = ? AND model_name = ? AND usage_date = ?), 0.0) + ?,
                COALESCE((SELECT markup_cost FROM client_model_daily_usage 
                         WHERE client_org_id = ? AND model_name = ? AND usage_date = ?), 0.0) + ?,
                'openrouter', ?, ?
            )
        """, (
            client_org_id, model_name, today, str(uuid.uuid4()),
            client_org_id, model_name, today,
            client_org_id, model_name, today, total_tokens,
            client_org_id, model_name, today,
            client_org_id, model_name, today, raw_cost,
            client_org_id, model_name, today, markup_cost,
            timestamp, timestamp
        ))
        
        conn.commit()
        print(f"✅ Recorded {total_tokens} tokens, ${markup_cost:.6f} for {model_name}")
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

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
    """Get real-time usage data for a client organization"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        today = date.today()
        
        cursor.execute("""
            SELECT today_tokens, today_requests, today_markup_cost, last_updated
            FROM client_live_counters
            WHERE client_org_id = ? AND current_date = ?
        """, (client_org_id, today))
        
        result = cursor.fetchone()
        
        if result:
            return {
                "client_org_id": client_org_id,
                "date": today.isoformat(),
                "tokens": result[0],
                "requests": result[1],
                "cost": result[2],
                "last_updated": result[3]
            }
        else:
            return {
                "client_org_id": client_org_id,
                "date": today.isoformat(),
                "tokens": 0,
                "requests": 0,
                "cost": 0.0,
                "last_updated": 0
            }
            
    finally:
        conn.close()

@router.post("/usage/manual-record")
async def manual_record_usage(
    model: str,
    tokens: int,
    cost: float,
    user=Depends(get_admin_user)
):
    """Manually record usage (for testing or corrections)"""
    try:
        # Get the first active organization
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM client_organizations WHERE is_active = 1 LIMIT 1")
        org = cursor.fetchone()
        conn.close()
        
        if not org:
            raise HTTPException(status_code=404, detail="No active organization found")
        
        usage_data = {
            "model": model,
            "total_tokens": tokens,
            "total_cost": cost
        }
        
        record_usage_to_db(org[0], usage_data)
        
        return {
            "status": "success",
            "message": f"Recorded {tokens} tokens, ${cost} for {model}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record usage: {str(e)}")