"""
Webhook Service - Business logic for webhook processing
Handles OpenRouter webhook validation and processing
"""

from typing import Dict, Any, List
from datetime import datetime, date, timedelta
from ..models.requests import UsageWebhookPayload, UsageSyncRequest
from ..repositories.client_repository import ClientRepository
from ..repositories.webhook_repository import WebhookRepository
from .usage_service import UsageService
from .openrouter_service import OpenRouterService


class WebhookService:
    """Service for webhook processing business logic"""
    
    def __init__(self):
        self.client_repo = ClientRepository()
        self.webhook_repo = WebhookRepository()
        self.usage_service = UsageService()
        self.openrouter_service = OpenRouterService()
    
    async def process_webhook(self, payload: UsageWebhookPayload) -> Dict[str, str]:
        """Process OpenRouter usage webhook payload"""
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
            
            # Process usage data
            usage_data = {
                "model": payload.model,
                "total_tokens": payload.tokens_used,
                "total_cost": payload.cost
            }
            
            success = self.usage_service.record_usage_from_webhook(
                client_org_id, usage_data, payload.external_user
            )
            
            # Mark as processed if successful and request_id provided
            if success and payload.request_id:
                self.webhook_repo.mark_generation_processed(
                    payload.request_id, payload.model, payload.cost,
                    client_org_id, {"external_user": payload.external_user}
                )
            
            if success:
                return {"status": "success", "message": "Usage recorded"}
            else:
                raise Exception("Failed to record usage")
            
        except Exception as e:
            raise Exception(f"Failed to process webhook: {str(e)}")
    
    async def sync_openrouter_usage(self, request: UsageSyncRequest) -> Dict[str, Any]:
        """Manually sync usage data from OpenRouter API"""
        try:
            # Get all active client organizations
            orgs = self.client_repo.get_all_active_clients()
            
            if not orgs:
                raise Exception("No active organizations found")
            
            sync_results = []
            
            for org_id, org_name, api_key in orgs:
                try:
                    # Fetch recent generations from OpenRouter
                    generations_data = await self.openrouter_service.get_generations(
                        api_key, limit=50
                    )
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
                                
                                self.usage_service.record_usage_from_webhook(
                                    org_id, usage_data, generation.get("user")
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
            raise Exception(f"Sync failed: {str(e)}")
    
    def manual_record_usage(self, model: str, tokens: int, cost: float) -> Dict[str, str]:
        """Manually record usage for testing or corrections"""
        try:
            from open_webui.models.organization_usage import ClientOrganizationDB
            
            # Get the first active organization using ORM
            orgs = ClientOrganizationDB.get_all_active_clients()
            
            if not orgs:
                raise Exception("No active organization found")
            
            org = orgs[0]  # Use first active organization
            
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
                    "message": f"Recorded {tokens} tokens, ${cost} for {model} in organization {org.name}"
                }
            else:
                raise Exception("Failed to record usage")
            
        except Exception as e:
            raise Exception(f"Failed to record usage: {str(e)}")