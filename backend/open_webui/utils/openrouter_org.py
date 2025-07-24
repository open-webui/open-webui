import aiohttp
import logging
import time
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.organization_usage import (
    OrganizationSettingsDB, OrganizationUsageDB, OpenRouterUserMappingDB
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("OPENROUTER_ORG", logging.INFO))

OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"

class OpenRouterOrgClient:
    """OpenRouter Organization API client for usage tracking"""
    
    def __init__(self):
        self.api_key: Optional[str] = None
        self.org_id: Optional[str] = None
        self._load_settings()
    
    def _load_settings(self):
        """Load organization settings from database"""
        try:
            settings = OrganizationSettingsDB.get_settings()
            if settings:
                self.api_key = settings.openrouter_api_key
                self.org_id = settings.openrouter_org_id
        except Exception as e:
            log.error(f"Failed to load organization settings: {e}")
    
    def refresh_settings(self):
        """Refresh settings from database"""
        self._load_settings()
    
    def is_configured(self) -> bool:
        """Check if the client is properly configured"""
        return self.api_key is not None and self.org_id is not None
    
    async def make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Make authenticated request to OpenRouter API"""
        if not self.is_configured():
            log.warning("OpenRouter organization client not configured")
            return None
        
        url = f"{OPENROUTER_API_BASE}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=data,
                    ssl=True
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        log.error(f"OpenRouter API error: {response.status} - {await response.text()}")
                        return None
        except Exception as e:
            log.error(f"OpenRouter API request failed: {e}")
            return None
    
    async def get_generations(
        self, 
        limit: int = 100,
        offset: int = 0,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[List[Dict]]:
        """Get generation history from OpenRouter API"""
        params = {
            "limit": limit,
            "offset": offset
        }
        
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        response = await self.make_request("GET", "/generations", params=params)
        if response and "data" in response:
            return response["data"]
        return []
    
    async def get_usage_stats(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[Dict]:
        """Get usage statistics from OpenRouter API"""
        params = {}
        
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        return await self.make_request("GET", "/usage", params=params)
    
    async def sync_usage_data(self, days_back: int = 1) -> Dict[str, Any]:
        """
        Sync usage data from OpenRouter to local database
        
        Args:
            days_back: Number of days to sync backwards from today
            
        Returns:
            Dictionary with sync results
        """
        if not self.is_configured():
            return {"success": False, "message": "Client not configured"}
        
        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        log.info(f"Syncing OpenRouter usage data from {start_date} to {end_date}")
        
        try:
            # Get user mappings
            mappings = OpenRouterUserMappingDB.get_all_active_mappings()
            if not mappings:
                return {"success": False, "message": "No user mappings found"}
            
            # Create mapping lookup
            openrouter_to_owui = {m.openrouter_user_id: m.owui_user_id for m in mappings}
            
            # Fetch generations data
            all_generations = []
            offset = 0
            limit = 100
            
            while True:
                generations = await self.get_generations(
                    limit=limit,
                    offset=offset,
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat()
                )
                
                if not generations:
                    break
                
                all_generations.extend(generations)
                
                if len(generations) < limit:
                    break
                
                offset += limit
            
            log.info(f"Retrieved {len(all_generations)} generation records")
            
            # Process and store usage data
            processed_count = 0
            error_count = 0
            
            for gen in all_generations:
                try:
                    # Extract user ID from generation record
                    openrouter_user_id = gen.get("user")
                    if not openrouter_user_id or openrouter_user_id not in openrouter_to_owui:
                        continue  # Skip unknown users
                    
                    owui_user_id = openrouter_to_owui[openrouter_user_id]
                    
                    # Extract usage data
                    model_name = gen.get("model", "unknown")
                    created_at = gen.get("created_at")
                    if not created_at:
                        continue
                    
                    # Parse date from ISO timestamp
                    usage_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).date()
                    
                    # Extract token usage
                    usage = gen.get("usage", {})
                    input_tokens = usage.get("prompt_tokens", 0)
                    output_tokens = usage.get("completion_tokens", 0)
                    
                    # Calculate costs (OpenRouter provides cost in response)
                    cost = gen.get("cost", 0.0)
                    
                    # Extract metadata
                    provider = gen.get("provider", {}).get("name")
                    generation_time = gen.get("generation_time")
                    
                    # Record usage in database
                    result = OrganizationUsageDB.record_usage(
                        user_id=owui_user_id,
                        openrouter_user_id=openrouter_user_id,
                        model_name=model_name,
                        usage_date=usage_date,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cost=cost,
                        provider=provider,
                        generation_time=generation_time
                    )
                    
                    if result:
                        processed_count += 1
                    else:
                        error_count += 1
                        
                except Exception as e:
                    log.error(f"Error processing generation record: {e}")
                    error_count += 1
                    continue
            
            # Update last sync timestamp
            OrganizationSettingsDB.update_last_sync()
            
            return {
                "success": True,
                "message": f"Sync completed successfully",
                "stats": {
                    "total_records": len(all_generations),
                    "processed": processed_count,
                    "errors": error_count,
                    "date_range": f"{start_date} to {end_date}"
                }
            }
            
        except Exception as e:
            log.error(f"Failed to sync usage data: {e}")
            return {"success": False, "message": f"Sync failed: {str(e)}"}


class OpenRouterUsageService:
    """Service for managing OpenRouter organization usage tracking"""
    
    def __init__(self):
        self.client = OpenRouterOrgClient()
    
    def get_user_id_for_request(self, user_id: str) -> Optional[str]:
        """
        Get OpenRouter user ID for a given OWUI user ID
        Used when making API calls to include user parameter
        """
        try:
            mapping = OpenRouterUserMappingDB.get_mapping_by_owui_user_id(user_id)
            if mapping and mapping.is_active:
                return mapping.openrouter_user_id
            return None
        except Exception as e:
            log.error(f"Failed to get OpenRouter user ID for {user_id}: {e}")
            return None
    
    async def manual_sync(self, days_back: int = 7) -> Dict[str, Any]:
        """Manually trigger usage data sync"""
        return await self.client.sync_usage_data(days_back)
    
    async def get_organization_stats(
        self, 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get organization usage statistics"""
        try:
            # Get local usage stats
            stats = OrganizationUsageDB.get_usage_stats(start_date, end_date)
            
            # Get fresh data from OpenRouter if needed
            settings = OrganizationSettingsDB.get_settings()
            if settings and settings.last_sync_at:
                last_sync = datetime.fromtimestamp(settings.last_sync_at)
                hours_since_sync = (datetime.now() - last_sync).total_seconds() / 3600
                
                # Auto-sync if more than configured interval has passed
                if hours_since_sync >= settings.sync_interval_hours:
                    log.info("Auto-syncing usage data due to sync interval")
                    await self.client.sync_usage_data(days_back=1)
                    # Refresh stats after sync
                    stats = OrganizationUsageDB.get_usage_stats(start_date, end_date)
            
            return {
                "success": True,
                "stats": stats.model_dump(),
                "last_sync": settings.last_sync_at if settings else None
            }
            
        except Exception as e:
            log.error(f"Failed to get organization stats: {e}")
            return {"success": False, "message": str(e)}


# Global service instance
openrouter_usage_service = OpenRouterUsageService()