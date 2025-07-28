"""
Usage Service - Core business logic for usage tracking
Handles usage recording, statistics, and reporting
"""

from typing import Dict, Any, List, Optional
from datetime import date
from ..models.entities import UsageRecord, ClientInfo
from ..repositories.usage_repository import UsageRepository
from ..repositories.client_repository import ClientRepository


class UsageService:
    """Service for usage tracking business logic"""
    
    def __init__(self):
        self.usage_repo = UsageRepository()
        self.client_repo = ClientRepository()
    
    def record_usage_from_webhook(
        self, 
        client_org_id: str,
        usage_data: Dict[str, Any],
        external_user: Optional[str] = None
    ) -> bool:
        """Process and record usage data from webhook"""
        try:
            # Get client markup rate for accurate cost calculations
            client = self.client_repo.get_client_info(client_org_id)
            if not client:
                raise Exception(f"Client organization not found: {client_org_id}")
            
            # Validate markup rate
            if client.markup_rate <= 0:
                raise Exception(f"Invalid markup rate for client {client.name}: {client.markup_rate}")
            
            # Extract and validate usage details
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
            markup_cost = calculate_markup_cost(raw_cost, client.markup_rate)
            
            # Parse model to get input/output tokens (simplified assumption)
            # In real usage, these should be separate fields from OpenRouter
            input_tokens = int(total_tokens * 0.7)  # Rough estimate
            output_tokens = total_tokens - input_tokens
            
            # Create usage record
            user_id = external_user or "manual_webhook"
            openrouter_user_id = f"webhook_{external_user or 'system'}"
            provider = model_name.split("/")[0] if "/" in model_name else "openrouter"
            
            usage_record = UsageRecord(
                client_org_id=client_org_id,
                user_id=user_id,
                openrouter_user_id=openrouter_user_id,
                model_name=model_name,
                usage_date=date.today(),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                raw_cost=raw_cost,
                markup_cost=markup_cost,
                provider=provider,
                request_metadata={"source": "webhook", "external_user": external_user}
            )
            
            return self.usage_repo.record_usage(usage_record)
            
        except Exception as e:
            print(f"❌ Usage recording error: {e}")
            raise
    
    def get_real_time_usage(self, client_org_id: str) -> Dict[str, Any]:
        """Get real-time usage data for a client organization"""
        try:
            stats = self.usage_repo.get_usage_stats_by_client(client_org_id)
            
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
    
    async def get_organization_usage_summary(self, client_org_id: str = None) -> Dict[str, Any]:
        """Get admin-focused daily breakdown for organization"""
        try:
            from open_webui.config import ORGANIZATION_NAME
            
            # Get client organization ID if not provided
            if not client_org_id:
                client_org_id = self.client_repo.get_environment_client_id()
            
            org_name = ORGANIZATION_NAME or "My Organization"
            
            if client_org_id:
                # Get actual usage data using the new admin-focused method
                stats = await self.usage_repo.get_usage_stats_by_client_async(client_org_id)
                
                return {
                    "success": True,
                    "stats": {
                        "current_month": stats.current_month,
                        "daily_breakdown": stats.daily_breakdown,
                        "monthly_summary": stats.monthly_summary,
                        "client_org_name": stats.client_org_name,
                        "pln_conversion_available": True
                    },
                    "client_id": client_org_id
                }
            else:
                # Fallback for environments without proper client setup
                from open_webui.utils.currency_converter import get_exchange_rate_info
                exchange_info = await get_exchange_rate_info()
                
                return {
                    "success": True,
                    "stats": {
                        "current_month": {
                            "month": date.today().strftime('%B %Y'),
                            "total_tokens": 0,
                            "total_cost": 0.0,
                            "total_cost_pln": 0.0,
                            "total_requests": 0,
                            "days_with_usage": 0,
                            "days_in_month": date.today().day,
                            "usage_percentage": 0,
                            "exchange_rate_info": exchange_info
                        },
                        "daily_breakdown": [],
                        "monthly_summary": {
                            "average_daily_tokens": 0,
                            "average_daily_cost": 0,
                            "average_usage_day_tokens": 0,
                            "busiest_day": None,
                            "highest_cost_day": None,
                            "total_unique_users": 0,
                            "top_models": []
                        },
                        "client_org_name": org_name,
                        "pln_conversion_available": True
                    },
                    "client_id": "env_fallback"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "stats": {
                    "current_month": {
                        "month": "Error", "total_tokens": 0, "total_cost": 0, 
                        "total_requests": 0, "days_with_usage": 0, "days_in_month": 0, 
                        "usage_percentage": 0
                    },
                    "daily_breakdown": [],
                    "monthly_summary": {
                        "average_daily_tokens": 0, "average_daily_cost": 0,
                        "average_usage_day_tokens": 0, "busiest_day": None,
                        "highest_cost_day": None, "total_unique_users": 0, 
                        "top_models": []
                    },
                    "client_org_name": ORGANIZATION_NAME or "My Organization"
                },
                "client_id": "error"
            }