"""
Billing Service - Business logic for billing and user analysis
Handles subscription billing calculations and user usage analytics
"""

from typing import Dict, Any, List
from datetime import datetime, date
import calendar
from ..repositories.usage_repository import UsageRepository
from ..repositories.client_repository import ClientRepository


class BillingService:
    """Service for billing and user analytics business logic"""
    
    def __init__(self):
        self.usage_repo = UsageRepository()
        self.client_repo = ClientRepository()
    
    async def get_user_usage_breakdown(self, client_org_id: str = None) -> Dict[str, Any]:
        """Get usage breakdown by user for organization"""
        try:
            from open_webui.utils.currency_converter import get_current_usd_pln_rate
            from open_webui.models.users import Users
            from open_webui.utils.user_mapping import get_external_user_id, user_mapping_service
            from open_webui.config import ORGANIZATION_NAME
            
            # Get current exchange rate
            usd_pln_rate = await get_current_usd_pln_rate()
            
            # Get client organization ID
            if not client_org_id:
                client_org_id = self.client_repo.get_environment_client_id()
            
            if not client_org_id:
                return {
                    "success": False,
                    "error": "No client organization found",
                    "user_usage": [],
                    "organization_name": ORGANIZATION_NAME or "My Organization",
                    "total_users": 0
                }
            
            # Get actual usage data from database using current month calculation
            usage_data = self.usage_repo.get_usage_by_user(client_org_id)
            
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
                    "cost_pln": round(usage['markup_cost'] * usd_pln_rate, 2),
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
    
    async def get_model_usage_breakdown(self, client_org_id: str = None) -> Dict[str, Any]:
        """Get usage breakdown by model for organization"""
        try:
            from open_webui.utils.currency_converter import get_current_usd_pln_rate
            
            # Get current exchange rate
            usd_pln_rate = await get_current_usd_pln_rate()
            
            # Get client organization ID
            if not client_org_id:
                client_org_id = self.client_repo.get_environment_client_id()
            
            if not client_org_id:
                return {
                    "success": False,
                    "error": "No client organization found",
                    "model_usage": []
                }
            
            # Get actual usage data from database using current month calculation
            usage_data = self.usage_repo.get_usage_by_model(client_org_id)
            
            # Enhance data with PLN conversion
            model_usage_list = []
            for usage in usage_data:
                enhanced_usage = {
                    "model_name": usage['model_name'],
                    "provider": usage.get('provider', 'Unknown'),
                    "total_tokens": usage['total_tokens'],
                    "total_requests": usage['total_requests'],
                    "markup_cost": usage['markup_cost'],
                    "cost_pln": round(usage['markup_cost'] * usd_pln_rate, 2),
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
    
    def get_subscription_billing(self) -> Dict[str, Any]:
        """Get subscription billing data for current organization"""
        try:
            from open_webui.models.users import Users
            
            # In environment-based mode, all users belong to the same organization
            # Get all users from the system
            users_response = Users.get_users()
            all_users = users_response.users if hasattr(users_response, 'users') else []
            
            # Define pricing tiers
            pricing_tiers = [
                {"min": 1, "max": 3, "price": 79},
                {"min": 4, "max": 9, "price": 69},
                {"min": 10, "max": 19, "price": 59},
                {"min": 20, "max": float('inf'), "price": 54}
            ]
            
            # Get current month info
            now = datetime.now()
            current_month = now.month
            current_year = now.year
            # calendar.monthrange correctly handles all month lengths (28, 29, 30, 31 days)
            days_in_month = calendar.monthrange(current_year, current_month)[1]
            
            # Get user details and calculate billing
            user_details = []
            total_users = len(all_users)
            
            # Determine current pricing tier
            current_tier_price = 79  # default (1-3 users)
            for tier in pricing_tiers:
                if tier["min"] <= total_users <= tier["max"]:
                    current_tier_price = tier["price"]
                    break
            
            # Calculate billing for each user
            total_cost = 0.0
            for user_obj in all_users:
                # Calculate proportional billing
                created_date = datetime.fromtimestamp(user_obj.created_at)
                
                # If user was created this month, calculate proportional cost
                if created_date.year == current_year and created_date.month == current_month:
                    days_remaining = days_in_month - created_date.day + 1
                    billing_proportion = days_remaining / days_in_month
                else:
                    # Full month billing
                    days_remaining = days_in_month
                    billing_proportion = 1.0
                
                user_cost = current_tier_price * billing_proportion
                total_cost += user_cost
                
                user_details.append({
                    "user_id": user_obj.id,
                    "user_name": user_obj.name,
                    "user_email": user_obj.email,
                    "created_date": created_date.strftime("%Y-%m-%d"),
                    "days_remaining_when_added": days_remaining,
                    "billing_proportion": billing_proportion,
                    "monthly_cost_pln": round(user_cost, 2)
                })
            
            # Build tier breakdown with current tier marking
            tier_breakdown = []
            for i, tier in enumerate(pricing_tiers):
                max_display = str(tier["max"]) if tier["max"] != float('inf') else "+"
                min_display = str(tier["min"])
                
                if tier["max"] == float('inf'):
                    tier_range = f"{min_display}+ users"
                else:
                    tier_range = f"{min_display}-{max_display} users"
                
                is_current = tier["min"] <= total_users <= tier["max"]
                
                tier_breakdown.append({
                    "tier_range": tier_range,
                    "price_per_user_pln": tier["price"],
                    "is_current_tier": is_current
                })
            
            # Build subscription data
            subscription_data = {
                "current_month": {
                    "month": current_month,
                    "year": current_year,
                    "total_users": total_users,
                    "current_tier_price_pln": current_tier_price,
                    "total_cost_pln": round(total_cost, 2),
                    "tier_breakdown": tier_breakdown,
                    "user_details": user_details
                }
            }
            
            return {
                "success": True,
                "subscription_data": subscription_data
            }
            
        except Exception as e:
            import traceback
            print(f"Error in subscription billing: {e}")
            print(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "subscription_data": None
            }