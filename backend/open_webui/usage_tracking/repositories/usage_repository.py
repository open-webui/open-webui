"""
Usage Repository - Data access for usage tracking
Handles all database operations related to usage data
"""

from typing import Dict, Any, List
from datetime import date
from ..models.entities import UsageRecord


class UsageRepository:
    """Repository for usage data operations"""
    
    @staticmethod
    def record_usage(usage_record: UsageRecord) -> bool:
        """Record usage data using consolidated ORM approach"""
        try:
            from open_webui.models.organization_usage import ClientUsageDB
            
            success = ClientUsageDB.record_usage(
                client_org_id=usage_record.client_org_id,
                user_id=usage_record.user_id,
                openrouter_user_id=usage_record.openrouter_user_id,
                model_name=usage_record.model_name,
                usage_date=usage_record.usage_date,
                input_tokens=usage_record.input_tokens,
                output_tokens=usage_record.output_tokens,
                raw_cost=usage_record.raw_cost,
                markup_cost=usage_record.markup_cost,
                provider=usage_record.provider,
                request_metadata=usage_record.request_metadata
            )
            
            if success:
                total_tokens = usage_record.input_tokens + usage_record.output_tokens
                print(f"✅ Recorded {total_tokens} tokens, ${usage_record.markup_cost:.6f} for {usage_record.model_name}")
            else:
                print(f"❌ Failed to record usage for {usage_record.model_name}")
            
            return success
            
        except Exception as e:
            print(f"❌ Database error: {e}")
            raise
    
    @staticmethod
    def get_usage_stats_by_client(client_org_id: str) -> Any:
        """Get usage statistics for a client organization"""
        try:
            from open_webui.models.organization_usage import ClientUsageDB
            return ClientUsageDB.get_usage_stats_by_client(client_org_id)
        except Exception:
            # Return minimal stats on error
            return type('Stats', (), {
                'today': {
                    'tokens': 0,
                    'requests': 0, 
                    'cost': 0.0,
                    'last_updated': 'No data'
                }
            })()
    
    @staticmethod
    async def get_usage_stats_by_client_async(client_org_id: str) -> Any:
        """Get usage statistics for a client organization (async)"""
        try:
            from open_webui.models.organization_usage import ClientUsageDB
            return await ClientUsageDB.get_usage_stats_by_client(client_org_id)
        except Exception:
            # Return fallback stats structure
            return type('Stats', (), {
                'current_month': {},
                'daily_breakdown': [],
                'monthly_summary': {},
                'client_org_name': 'Unknown'
            })()
    
    @staticmethod
    def get_usage_by_user(client_org_id: str) -> List[Dict[str, Any]]:
        """Get usage breakdown by user"""
        try:
            from open_webui.models.organization_usage import ClientUsageDB
            return ClientUsageDB.get_usage_by_user(client_org_id)
        except Exception:
            return []
    
    @staticmethod
    def get_usage_by_model(client_org_id: str) -> List[Dict[str, Any]]:
        """Get usage breakdown by model"""
        try:
            from open_webui.models.organization_usage import ClientUsageDB
            return ClientUsageDB.get_usage_by_model(client_org_id)
        except Exception:
            return []