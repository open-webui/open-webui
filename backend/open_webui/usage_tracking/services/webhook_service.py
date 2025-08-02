"""
Webhook Service - Business logic for webhook processing
Handles OpenRouter webhook validation and processing
InfluxDB-First architecture (no SQLite fallback)
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from ..models.requests import UsageWebhookPayload, UsageSyncRequest
from ..repositories.client_repository import ClientRepository
from ..repositories.webhook_repository import WebhookRepository
from .usage_service import UsageService
from .openrouter_service import OpenRouterService
from .influxdb_first_service import influxdb_first_service

logger = logging.getLogger(__name__)


class WebhookService:
    """Service for webhook processing business logic"""
    
    def __init__(self):
        self.client_repo = ClientRepository()
        self.webhook_repo = WebhookRepository()
        self.usage_service = UsageService()
        self.openrouter_service = OpenRouterService()
        
        # Initialize InfluxDB-First service
        self.influxdb_first_enabled = os.getenv("INFLUXDB_FIRST_ENABLED", "false").lower() == "true"
        
        if self.influxdb_first_enabled:
            logger.info("InfluxDB-First integration enabled for webhook processing (no SQLite fallback)")
        else:
            logger.info("InfluxDB-First integration disabled - falling back to legacy dual-write mode")
    
    async def process_webhook(self, payload: UsageWebhookPayload) -> Dict[str, str]:
        """Process OpenRouter usage webhook payload with optional InfluxDB integration"""
        try:
            # Verify API key belongs to a client organization
            client_org_id = self.client_repo.get_client_by_api_key(payload.api_key)
            if not client_org_id:
                raise Exception("Client organization not found")
            
            # Check for duplicate processing if request_id is provided
            if payload.request_id:
                is_duplicate = self.webhook_repo.is_duplicate_generation(
                    payload.request_id, payload.model, payload.cost
                )
                if is_duplicate:
                    return {"status": "success", "message": "Duplicate request ignored"}
            
            # Prepare webhook data for InfluxDB
            webhook_data = {
                "api_key": payload.api_key,
                "model": payload.model,
                "tokens_used": payload.tokens_used,
                "cost": payload.cost,
                "timestamp": payload.timestamp,
                "external_user": payload.external_user,
                "request_id": payload.request_id,
                "client_org_id": client_org_id
            }
            
            if self.influxdb_first_enabled:
                # InfluxDB-First mode: single write path with built-in deduplication
                success = await influxdb_first_service.write_usage_record(webhook_data)
                
                if success:
                    logger.debug(f"Written to InfluxDB-First: {payload.model} - {payload.tokens_used} tokens")
                    return {
                        "status": "success", 
                        "message": "Usage recorded (InfluxDB-First)",
                        "storage": "influxdb_first"
                    }
                else:
                    raise Exception("Failed to write to InfluxDB-First service")
            
            else:
                # Legacy fallback mode (dual-write logic preserved for transition)
                logger.warning("Using legacy dual-write mode - consider enabling INFLUXDB_FIRST_ENABLED")
                return await self._process_webhook_legacy(payload, client_org_id, webhook_data)
            
        except Exception as e:
            logger.error(f"Webhook processing error: {str(e)}")
            raise Exception(f"Failed to process webhook: {str(e)}")
    
    async def sync_openrouter_usage(self, request: UsageSyncRequest) -> Dict[str, Any]:
        """
        DEPRECATED: OpenRouter bulk sync is disabled
        
        This method has been disabled because the OpenRouter API does not provide
        a bulk generations endpoint. The previous implementation was causing 404 errors.
        
        Real-time usage tracking via webhooks is the primary method for collecting usage data.
        """
        # Get organization count for response compatibility
        orgs = self.client_repo.get_all_active_clients()
        org_count = len(orgs) if orgs else 0
        
        return {
            "status": "deprecated",
            "message": "Bulk sync functionality has been disabled due to non-existent OpenRouter API endpoint",
            "details": {
                "reason": "The OpenRouter API /api/v1/generations endpoint does not exist and was causing 404 errors",
                "alternative": "Real-time usage tracking via webhooks is the primary method for collecting usage data",
                "impact": "No data loss - real-time tracking continues to work normally"
            },
            "results": [{
                "organization": "All Organizations",
                "status": "skipped",
                "message": "Bulk sync disabled - using real-time tracking instead"
            }],
            "total_organizations": org_count
        }
    
    async def manual_record_usage(self, model: str, tokens: int, cost: float) -> Dict[str, str]:
        """Manually record usage for testing or corrections with InfluxDB support"""
        try:
            from open_webui.models.organization_usage import ClientOrganizationDB
            
            # Get the first active organization using ORM
            orgs = ClientOrganizationDB.get_all_active_clients()
            
            if not orgs:
                raise Exception("No active organization found")
            
            org = orgs[0]  # Use first active organization
            
            if self.influxdb_first_enabled:
                # InfluxDB-First mode
                webhook_data = {
                    "client_org_id": org.id,
                    "api_key": "manual_admin",
                    "model": model,
                    "tokens_used": tokens,
                    "cost_usd": cost,
                    "timestamp": datetime.utcnow().isoformat(),
                    "external_user": "manual_admin",
                    "request_id": f"manual_{datetime.utcnow().timestamp()}"
                }
                
                success = await influxdb_first_service.write_usage_record(webhook_data)
                
                if success:
                    logger.info(f"Manual usage written to InfluxDB-First: {model} - {tokens} tokens")
                    return {
                        "status": "success",
                        "message": f"Recorded {tokens} tokens, ${cost} for {model} in organization {org.name} (InfluxDB-First)"
                    }
                else:
                    raise Exception("Failed to record manual usage in InfluxDB-First")
            
            else:
                # Legacy fallback mode
                logger.warning("Using legacy manual record mode - consider enabling INFLUXDB_FIRST_ENABLED")
                usage_data = {
                    "model": model,
                    "total_tokens": tokens,
                    "total_cost": cost
                }
                
                success = self.usage_service.record_usage_from_webhook(
                    org.id, usage_data, "manual_admin"
                )
                
                if success:
                    return {
                        "status": "success",
                        "message": f"Recorded {tokens} tokens, ${cost} for {model} in organization {org.name} (Legacy SQLite)"
                    }
                else:
                    raise Exception("Failed to record usage")
            
        except Exception as e:
            raise Exception(f"Failed to record usage: {str(e)}")
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get the status of webhook service and its integrations"""
        status = {
            "webhook_service": "operational",
            "influxdb_first_enabled": self.influxdb_first_enabled,
            "storage_backends": []
        }
        
        if self.influxdb_first_enabled:
            # InfluxDB-First mode
            try:
                influxdb_health = await influxdb_first_service.health_check()
                status["storage_backends"].append({
                    "type": "InfluxDB-First",
                    "status": influxdb_health.get("status", "unknown"),
                    "url": influxdb_health.get("url"),
                    "mode": influxdb_health.get("mode"),
                    "primary": True,
                    "circuit_breaker": influxdb_health.get("circuit_breaker")
                })
            except Exception as e:
                status["storage_backends"].append({
                    "type": "InfluxDB-First",
                    "status": "error",
                    "error": str(e),
                    "primary": True
                })
        else:
            # Legacy mode - SQLite primary
            status["storage_backends"].append({
                "type": "SQLite",
                "status": "operational", 
                "primary": True,
                "note": "Legacy mode - consider enabling INFLUXDB_FIRST_ENABLED"
            })
        
        return status
    
    async def _process_webhook_legacy(self, payload, client_org_id: str, webhook_data: Dict[str, Any]) -> Dict[str, str]:
        """Legacy dual-write webhook processing (for backward compatibility)"""
        # Check for duplicate processing if request_id is provided
        if payload.request_id:
            is_duplicate = self.webhook_repo.is_duplicate_generation(
                payload.request_id, payload.model, payload.cost
            )
            if is_duplicate:
                return {"status": "success", "message": "Duplicate request ignored"}
        
        # Process usage data in SQLite
        usage_data = {
            "model": payload.model,
            "total_tokens": payload.tokens_used,
            "total_cost": payload.cost
        }
        
        sqlite_success = self.usage_service.record_usage_from_webhook(
            client_org_id, usage_data, payload.external_user
        )
        
        # Mark as processed if successful and request_id provided
        if sqlite_success and payload.request_id:
            self.webhook_repo.mark_generation_processed(
                payload.request_id, payload.model, payload.cost,
                client_org_id, {"external_user": payload.external_user}
            )
        
        if sqlite_success:
            return {
                "status": "success", 
                "message": "Usage recorded (Legacy SQLite)",
                "storage": "sqlite"
            }
        else:
            raise Exception("Failed to record usage in SQLite")