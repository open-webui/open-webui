"""
OpenRouter Client Manager for mAI
Handles usage tracking and client organization management
"""

import os
import logging
from datetime import datetime, date
from typing import Optional, Dict, Any

from open_webui.config import (
    OPENROUTER_API_KEY,
    OPENROUTER_EXTERNAL_USER,
    ORGANIZATION_NAME,
    DATA_DIR
)
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.organization_usage import ClientOrganizationDB
from open_webui.usage_tracking.services.influxdb_first_service import influxdb_first_service

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


class OpenRouterClientManager:
    """Manages OpenRouter client organizations and usage tracking"""
    
    def __init__(self):
        self.is_env_based = bool(OPENROUTER_API_KEY and OPENROUTER_EXTERNAL_USER)
        
    def get_user_client_context(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get client context for a user
        In environment-based mode, returns the environment configuration
        """
        if self.is_env_based:
            # Environment-based mode - all users belong to same organization
            return {
                "client_org_id": OPENROUTER_EXTERNAL_USER,
                "api_key": OPENROUTER_API_KEY,
                "organization_name": ORGANIZATION_NAME,
                "is_env_based": True,
                "user_mapping_enabled": True
            }
        
        # Database-based mode (legacy support)
        # This would query user_client_mappings table
        # For now, return None as we're using environment-based mode
        return None
    
    def sync_ui_key_to_organization(self, user_id: str, api_key: str) -> Dict[str, Any]:
        """
        Sync API key to organization (legacy support)
        In environment-based mode, this is a no-op
        """
        if self.is_env_based:
            return {
                "success": True,
                "message": "Environment-based configuration in use",
                "organization_updated": ORGANIZATION_NAME
            }
        
        # Legacy database-based sync would go here
        return {
            "success": False,
            "message": "Database-based sync not implemented"
        }
    
    async def record_real_time_usage(
        self,
        user_id: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        raw_cost: float,
        generation_id: Optional[str] = None,
        provider: Optional[str] = None,
        generation_time: Optional[float] = None,
        external_user: Optional[str] = None,
        client_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Record usage data in real-time from OpenRouter API responses
        """
        try:
            # Determine client organization ID first (needed for duplicate check)
            if self.is_env_based:
                client_org_id = OPENROUTER_EXTERNAL_USER
                if not client_org_id:
                    log.error("No OPENROUTER_EXTERNAL_USER configured")
                    return False
            else:
                # Legacy: get from client context
                if not client_context or "client_org_id" not in client_context:
                    log.error(f"No client context for user {user_id}")
                    return False
                client_org_id = client_context["client_org_id"]
            
            # Deduplication is now handled by InfluxDB-First service using request_id tags
            # No need for SQLite-based duplicate checking
            
            # Get client organization for markup rate
            client = ClientOrganizationDB.get_client_by_id(client_org_id)
            if not client:
                log.error(f"Client organization not found: {client_org_id}")
                return False
            
            # Calculate markup cost
            markup_rate = client.markup_rate or 1.3
            markup_cost = raw_cost * markup_rate
            
            # Parse provider from model name if not provided
            if not provider and "/" in model_name:
                provider = model_name.split("/")[0]
            elif not provider:
                provider = "openrouter"
            
            # Use external_user if provided, otherwise use user_id
            openrouter_user_id = external_user or f"{client_org_id}_user_{user_id[:8]}"
            
            # Prepare usage data for InfluxDB-First service
            usage_data = {
                "client_org_id": client_org_id,
                "model": model_name,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost_usd": markup_cost,
                "timestamp": datetime.now().isoformat(),
                "external_user": openrouter_user_id,
                "request_id": generation_id,
                "provider": provider,
                "source": "real_time",
                "generation_time": generation_time
            }
            
            # Write directly to InfluxDB (no SQLite fallback)
            success = await influxdb_first_service.write_usage_record(usage_data)
            
            if success:
                total_tokens = input_tokens + output_tokens
                log.info(f"✅ Recorded usage: {total_tokens} tokens, ${markup_cost:.6f} for {model_name} (InfluxDB-First)")
            else:
                log.error(f"Failed to record usage for {model_name} in InfluxDB")
                # Log fallback info but don't write to SQLite
                log.warning(f"Usage data not recorded: {total_tokens} tokens, ${markup_cost:.6f} for {model_name}")
            
            return success
            
        except Exception as e:
            log.error(f"Error recording usage: {e}")
            return False


# Singleton instance
openrouter_client_manager = OpenRouterClientManager()