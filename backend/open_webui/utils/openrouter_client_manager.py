import aiohttp
import logging
import time
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.organization_usage import (
    GlobalSettingsDB, ClientOrganizationDB, UserClientMappingDB, ClientUsageDB,
    ClientOrganizationForm, UserClientMappingForm
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("OPENROUTER_CLIENT", logging.INFO))

OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"

class OpenRouterClientManager:
    """OpenRouter client API key management service for reseller model"""
    
    def __init__(self):
        self.provisioning_key: Optional[str] = None
        self.default_markup_rate: float = 1.3
        self._load_settings()
    
    def _load_settings(self):
        """Load global settings from database"""
        try:
            settings = GlobalSettingsDB.get_settings()
            if settings:
                self.provisioning_key = settings.openrouter_provisioning_key
                self.default_markup_rate = settings.default_markup_rate
        except Exception as e:
            log.error(f"Failed to load global settings: {e}")
    
    def refresh_settings(self):
        """Refresh settings from database"""
        self._load_settings()
    
    def is_configured(self) -> bool:
        """Check if the provisioning key is configured"""
        return self.provisioning_key is not None
    
    async def make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Make authenticated request to OpenRouter Provisioning API"""
        if not self.is_configured():
            log.warning("OpenRouter provisioning key not configured")
            return None
        
        url = f"{OPENROUTER_API_BASE}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.provisioning_key}",
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
    
    async def create_client_api_key(
        self, 
        client_name: str,
        credit_limit: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a new API key for a client organization"""
        try:
            data = {
                "name": f"Client: {client_name}",
                "label": f"client-{client_name.lower().replace(' ', '-').replace('_', '-')}",
            }
            
            if credit_limit:
                data["limit"] = credit_limit
            
            response = await self.make_request("POST", "/keys/", data=data)
            if response and "data" in response:
                return response["data"]
            return None
        except Exception as e:
            log.error(f"Failed to create API key for client {client_name}: {e}")
            return None
    
    async def get_api_key_info(self, key_hash: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific API key"""
        try:
            response = await self.make_request("GET", f"/keys/{key_hash}")
            if response and "data" in response:
                return response["data"]
            return None
        except Exception as e:
            log.error(f"Failed to get API key info for {key_hash}: {e}")
            return None
    
    async def update_api_key(
        self, 
        key_hash: str, 
        name: Optional[str] = None,
        disabled: Optional[bool] = None,
        limit: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """Update an API key"""
        try:
            data = {}
            if name is not None:
                data["name"] = name
            if disabled is not None:
                data["disabled"] = disabled
            if limit is not None:
                data["limit"] = limit
            
            response = await self.make_request("PATCH", f"/keys/{key_hash}", data=data)
            if response and "data" in response:
                return response["data"]
            return None
        except Exception as e:
            log.error(f"Failed to update API key {key_hash}: {e}")
            return None
    
    async def delete_api_key(self, key_hash: str) -> bool:
        """Delete an API key"""
        try:
            response = await self.make_request("DELETE", f"/keys/{key_hash}")
            return response is not None
        except Exception as e:
            log.error(f"Failed to delete API key {key_hash}: {e}")
            return False
    
    async def list_all_keys(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List all API keys"""
        try:
            params = {"limit": limit, "offset": offset}
            response = await self.make_request("GET", "/keys", params=params)
            if response and "data" in response:
                return response["data"]
            return []
        except Exception as e:
            log.error(f"Failed to list API keys: {e}")
            return []
    
    async def create_client_organization(
        self, 
        client_form: ClientOrganizationForm
    ) -> Optional[Dict[str, Any]]:
        """Create a new client organization with dedicated API key"""
        try:
            # Create API key for the client
            key_data = await self.create_client_api_key(
                client_name=client_form.name,
                credit_limit=client_form.monthly_limit
            )
            
            if not key_data:
                return {"success": False, "message": "Failed to create API key"}
            
            # Extract key information
            api_key = key_data.get("key")  # The actual API key string
            key_hash = key_data.get("hash")  # OpenRouter's key identifier
            
            if not api_key:
                return {"success": False, "message": "No API key returned from OpenRouter"}
            
            # Create client organization in database
            client = ClientOrganizationDB.create_client(
                client_form=client_form,
                api_key=api_key,
                key_hash=key_hash
            )
            
            if not client:
                # Clean up the API key if client creation failed
                if key_hash:
                    await self.delete_api_key(key_hash)
                return {"success": False, "message": "Failed to create client organization"}
            
            return {
                "success": True,
                "message": "Client organization created successfully",
                "client": client.model_dump(),
                "api_key_info": {
                    "key_hash": key_hash,
                    "name": key_data.get("name"),
                    "limit": key_data.get("limit"),
                    "usage": key_data.get("usage", 0)
                }
            }
            
        except Exception as e:
            log.error(f"Failed to create client organization: {e}")
            return {"success": False, "message": str(e)}
    
    async def update_client_limits(
        self, 
        client_id: str, 
        new_limit: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """Update credit limits for a client organization"""
        try:
            client = ClientOrganizationDB.get_client_by_id(client_id)
            if not client:
                return {"success": False, "message": "Client not found"}
            
            # Update OpenRouter API key limit
            if client.openrouter_key_hash and new_limit is not None:
                key_data = await self.update_api_key(
                    key_hash=client.openrouter_key_hash,
                    limit=new_limit
                )
                
                if not key_data:
                    return {"success": False, "message": "Failed to update API key limit"}
            
            # Update database
            updates = {}
            if new_limit is not None:
                updates["monthly_limit"] = new_limit
            
            updated_client = ClientOrganizationDB.update_client(client_id, updates)
            if not updated_client:
                return {"success": False, "message": "Failed to update client"}
            
            return {
                "success": True,
                "message": "Client limits updated successfully",
                "client": updated_client.model_dump()
            }
            
        except Exception as e:
            log.error(f"Failed to update client limits: {e}")
            return {"success": False, "message": str(e)}
    
    async def deactivate_client_organization(self, client_id: str) -> Dict[str, Any]:
        """Deactivate a client organization and disable their API key"""
        try:
            client = ClientOrganizationDB.get_client_by_id(client_id)
            if not client:
                return {"success": False, "message": "Client not found"}
            
            # Disable OpenRouter API key
            if client.openrouter_key_hash:
                key_data = await self.update_api_key(
                    key_hash=client.openrouter_key_hash,
                    disabled=True
                )
                
                if not key_data:
                    log.warning(f"Failed to disable API key for client {client_id}")
            
            # Deactivate in database
            success = ClientOrganizationDB.deactivate_client(client_id)
            if not success:
                return {"success": False, "message": "Failed to deactivate client"}
            
            return {
                "success": True,
                "message": "Client organization deactivated successfully"
            }
            
        except Exception as e:
            log.error(f"Failed to deactivate client organization: {e}")
            return {"success": False, "message": str(e)}
    
    def get_user_client_context(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get client organization context for a user"""
        try:
            mapping = UserClientMappingDB.get_mapping_by_user_id(user_id)
            if not mapping:
                return None
            
            client = ClientOrganizationDB.get_client_by_id(mapping.client_org_id)
            if not client:
                return None
            
            return {
                "client_org_id": client.id,
                "client_name": client.name,
                "api_key": client.openrouter_api_key,
                "markup_rate": client.markup_rate,
                "openrouter_user_id": mapping.openrouter_user_id
            }
        except Exception as e:
            log.error(f"Failed to get user client context for {user_id}: {e}")
            return None
    
    async def record_real_time_usage(
        self,
        user_id: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        raw_cost: float,
        provider: Optional[str] = None,
        generation_time: Optional[float] = None
    ) -> bool:
        """Record usage in real-time when API call is made"""
        try:
            # Get user's client context
            context = self.get_user_client_context(user_id)
            if not context:
                log.warning(f"No client context found for user {user_id}")
                return False
            
            # Calculate markup cost
            markup_cost = raw_cost * context["markup_rate"]
            
            # Record usage
            usage = ClientUsageDB.record_usage(
                client_org_id=context["client_org_id"],
                user_id=user_id,
                openrouter_user_id=context["openrouter_user_id"],
                model_name=model_name,
                usage_date=date.today(),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                raw_cost=raw_cost,
                markup_cost=markup_cost,
                provider=provider,
                generation_time=generation_time
            )
            
            return usage is not None
            
        except Exception as e:
            log.error(f"Failed to record real-time usage: {e}")
            return False


# Global service instance
openrouter_client_manager = OpenRouterClientManager()