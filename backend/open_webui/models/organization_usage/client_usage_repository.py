"""
Client Usage Repository Implementation
Contains complex business logic for usage tracking and statistics
"""
import time
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

from open_webui.internal.db import get_db

from .database import ClientDailyUsage, ClientUserDailyUsage, ClientModelDailyUsage
from .domain import ClientUsageStatsResponse, ClientBillingResponse, UsageRecordDTO
from .repositories import IClientUsageRepository

log = logging.getLogger(__name__)


class ClientUsageRepository(IClientUsageRepository):
    """
    Implementation of client usage repository with complex business logic
    Handles usage recording, statistics, and billing calculations
    """
    
    def record_usage(self, usage_record: UsageRecordDTO) -> bool:
        """
        Record API usage with per-user and per-model tracking
        Updates daily summaries directly (no live counters)
        """
        try:
            with get_db() as db:
                current_time = int(time.time())
                
                # 1. Update client daily usage
                client_usage_id = f"{usage_record.client_org_id}:{usage_record.usage_date}"
                client_usage = db.query(ClientDailyUsage).filter_by(id=client_usage_id).first()
                
                if client_usage:
                    client_usage.total_tokens += usage_record.total_tokens
                    client_usage.total_requests += 1
                    client_usage.raw_cost += usage_record.raw_cost
                    client_usage.markup_cost += usage_record.markup_cost
                    client_usage.updated_at = current_time
                else:
                    client_usage = ClientDailyUsage(
                        id=client_usage_id,
                        client_org_id=usage_record.client_org_id,
                        usage_date=usage_record.usage_date,
                        total_tokens=usage_record.total_tokens,
                        total_requests=1,
                        raw_cost=usage_record.raw_cost,
                        markup_cost=usage_record.markup_cost,
                        primary_model=usage_record.model_name,
                        unique_users=1,
                        created_at=current_time,
                        updated_at=current_time
                    )
                    db.add(client_usage)
                
                # 2. Update per-user daily usage
                user_usage_id = f"{usage_record.client_org_id}:{usage_record.user_id}:{usage_record.usage_date}"
                user_usage = db.query(ClientUserDailyUsage).filter_by(id=user_usage_id).first()
                
                if user_usage:
                    user_usage.total_tokens += usage_record.total_tokens
                    user_usage.total_requests += 1
                    user_usage.raw_cost += usage_record.raw_cost
                    user_usage.markup_cost += usage_record.markup_cost
                    user_usage.updated_at = current_time
                else:
                    user_usage = ClientUserDailyUsage(
                        id=user_usage_id,
                        client_org_id=usage_record.client_org_id,
                        user_id=usage_record.user_id,
                        openrouter_user_id=usage_record.openrouter_user_id,
                        usage_date=usage_record.usage_date,
                        total_tokens=usage_record.total_tokens,
                        total_requests=1,
                        raw_cost=usage_record.raw_cost,
                        markup_cost=usage_record.markup_cost,
                        created_at=current_time,
                        updated_at=current_time
                    )
                    db.add(user_usage)
                
                # 3. Update per-model daily usage
                model_usage_id = f"{usage_record.client_org_id}:{usage_record.model_name}:{usage_record.usage_date}"
                model_usage = db.query(ClientModelDailyUsage).filter_by(id=model_usage_id).first()
                
                if model_usage:
                    model_usage.total_tokens += usage_record.total_tokens
                    model_usage.total_requests += 1
                    model_usage.raw_cost += usage_record.raw_cost
                    model_usage.markup_cost += usage_record.markup_cost
                    model_usage.updated_at = current_time
                else:
                    model_usage = ClientModelDailyUsage(
                        id=model_usage_id,
                        client_org_id=usage_record.client_org_id,
                        model_name=usage_record.model_name,
                        usage_date=usage_record.usage_date,
                        total_tokens=usage_record.total_tokens,
                        total_requests=1,
                        raw_cost=usage_record.raw_cost,
                        markup_cost=usage_record.markup_cost,
                        provider=usage_record.provider,
                        created_at=current_time,
                        updated_at=current_time
                    )
                    db.add(model_usage)
                
                db.commit()
                return True
                
        except Exception as e:
            log.error(f"Failed to record usage for {usage_record.client_org_id}: {e}")
            return False
    
    async def get_usage_stats_by_client(
        self, client_org_id: str, use_client_timezone: bool = True
    ) -> ClientUsageStatsResponse:
        """Get admin-focused daily breakdown stats (no real-time features)"""
        try:
            # Get current exchange rate information with timeout and fallback
            from open_webui.utils.currency_converter import get_exchange_rate_info
            import asyncio
            
            try:
                # Add 5-second timeout to prevent hanging
                exchange_info = await asyncio.wait_for(get_exchange_rate_info(), timeout=5.0)
                usd_pln_rate = exchange_info['usd_pln']
            except (asyncio.TimeoutError, Exception) as e:
                # Fallback to default rate if NBP API is slow/unavailable
                print(f"NBP API timeout/error, using fallback rate: {e}")
                exchange_info = {
                    'usd_pln': 4.0,  # Fallback exchange rate
                    'effective_date': date.today().isoformat(),
                    'rate_source': 'fallback',
                    'error': 'NBP API unavailable'
                }
                usd_pln_rate = 4.0
            
            with get_db() as db:
                # Get current month boundaries
                today = date.today()
                current_month_start = today.replace(day=1)
                
                # Get all daily records for current month (1st to last day)
                month_records = db.query(ClientDailyUsage).filter(
                    ClientDailyUsage.client_org_id == client_org_id,
                    ClientDailyUsage.usage_date >= current_month_start,
                    ClientDailyUsage.usage_date <= today
                ).order_by(ClientDailyUsage.usage_date).all()
                
                # Build daily breakdown for current month
                daily_breakdown = []
                for record in month_records:
                    daily_breakdown.append({
                        'date': record.usage_date.isoformat(),
                        'day_name': record.usage_date.strftime('%A'),
                        'day_number': record.usage_date.day,
                        'tokens': record.total_tokens,
                        'cost': record.markup_cost,
                        'cost_pln': round(record.markup_cost * usd_pln_rate, 2),
                        'requests': record.total_requests,
                        'primary_model': record.primary_model,
                        'unique_users': record.unique_users,
                        'last_activity': datetime.fromtimestamp(record.updated_at).strftime('%H:%M'),
                        'exchange_rate_used': usd_pln_rate
                    })
                
                # Calculate current month totals and averages
                total_tokens = sum(r.total_tokens for r in month_records)
                total_cost = sum(r.markup_cost for r in month_records)
                total_requests = sum(r.total_requests for r in month_records)
                days_with_usage = len(month_records)
                
                # Calculate averages (business insights)
                avg_daily_tokens = total_tokens / max(today.day, 1)
                avg_daily_cost = total_cost / max(today.day, 1)
                avg_usage_day_tokens = total_tokens / max(days_with_usage, 1) if days_with_usage > 0 else 0
                
                current_month = {
                    'month': today.strftime('%B %Y'),
                    'total_tokens': total_tokens,
                    'total_cost': total_cost,
                    'total_cost_pln': round(total_cost * usd_pln_rate, 2),
                    'total_requests': total_requests,
                    'days_with_usage': days_with_usage,
                    'days_in_month': today.day,  # Days elapsed so far
                    'usage_percentage': (days_with_usage / today.day * 100) if today.day > 0 else 0,
                    'exchange_rate_info': exchange_info
                }
                
                # Monthly summary with business insights
                monthly_summary = {
                    'average_daily_tokens': round(avg_daily_tokens),
                    'average_daily_cost': round(avg_daily_cost, 4),
                    'average_usage_day_tokens': round(avg_usage_day_tokens),
                    'busiest_day': max(month_records, key=lambda x: x.total_tokens).usage_date.isoformat() if month_records else None,
                    'highest_cost_day': max(month_records, key=lambda x: x.markup_cost).usage_date.isoformat() if month_records else None,
                    'total_unique_users': len(set(r.unique_users for r in month_records)) if month_records else 0,
                    'most_used_model': max(month_records, key=lambda x: x.total_tokens).primary_model if month_records else None
                }
                
                # Get client name (forward reference resolution)
                client_name = "Unknown"
                try:
                    # Import here to avoid circular imports
                    from . import ClientOrganizationDB
                    client = ClientOrganizationDB.get_client_by_id(client_org_id)
                    if client:
                        client_name = client.name
                except:
                    pass
                
                return ClientUsageStatsResponse(
                    current_month=current_month,
                    daily_breakdown=daily_breakdown,
                    monthly_summary=monthly_summary,
                    client_org_name=client_name
                )
        except Exception as e:
            print(f"Error getting usage stats: {e}")
            return ClientUsageStatsResponse(
                current_month={'month': 'Error', 'total_tokens': 0, 'total_cost': 0.0, 'total_requests': 0, 'days_with_usage': 0, 'days_in_month': 0, 'usage_percentage': 0},
                daily_breakdown=[],
                monthly_summary={'average_daily_tokens': 0, 'average_daily_cost': 0, 'average_usage_day_tokens': 0, 'busiest_day': None, 'highest_cost_day': None, 'total_unique_users': 0, 'most_used_model': None},
                client_org_name="Error"
            )
    
    def get_usage_by_user(
        self, client_org_id: str, start_date: date = None, end_date: date = None
    ) -> List[Dict[str, Any]]:
        """Get usage breakdown by user for a client organization"""
        try:
            with get_db() as db:
                # Default to current month (from 1st day until now) if no dates provided
                if not end_date:
                    end_date = date.today()
                if not start_date:
                    start_date = end_date.replace(day=1)  # First day of current month
                
                # Query per-user daily usage
                user_records = db.query(ClientUserDailyUsage).filter(
                    ClientUserDailyUsage.client_org_id == client_org_id,
                    ClientUserDailyUsage.usage_date >= start_date,
                    ClientUserDailyUsage.usage_date <= end_date
                ).all()
                
                # Aggregate by user
                user_totals = {}
                for record in user_records:
                    if record.user_id not in user_totals:
                        user_totals[record.user_id] = {
                            'user_id': record.user_id,
                            'openrouter_user_id': record.openrouter_user_id,
                            'total_tokens': 0,
                            'total_requests': 0,
                            'raw_cost': 0.0,
                            'markup_cost': 0.0,
                            'days_active': set()
                        }
                    
                    user_totals[record.user_id]['total_tokens'] += record.total_tokens
                    user_totals[record.user_id]['total_requests'] += record.total_requests
                    user_totals[record.user_id]['raw_cost'] += record.raw_cost
                    user_totals[record.user_id]['markup_cost'] += record.markup_cost
                    user_totals[record.user_id]['days_active'].add(record.usage_date)
                
                # Convert to list and add days active count
                result = []
                for user_data in user_totals.values():
                    user_data['days_active'] = len(user_data['days_active'])
                    result.append(user_data)
                
                # Sort by markup cost descending
                result.sort(key=lambda x: x['markup_cost'], reverse=True)
                
                return result
        except Exception as e:
            print(f"Error getting user usage: {e}")
            return []
    
    def get_usage_by_model(
        self, client_org_id: str, start_date: date = None, end_date: date = None
    ) -> List[Dict[str, Any]]:
        """Get usage breakdown by model for a client organization - shows ALL 12 available models"""
        try:
            with get_db() as db:
                # Default to current month (from 1st day until now) if no dates provided
                if not end_date:
                    end_date = date.today()
                if not start_date:
                    start_date = end_date.replace(day=1)  # First day of current month
                
                # Query per-model daily usage
                model_records = db.query(ClientModelDailyUsage).filter(
                    ClientModelDailyUsage.client_org_id == client_org_id,
                    ClientModelDailyUsage.usage_date >= start_date,
                    ClientModelDailyUsage.usage_date <= end_date
                ).all()
                
                # Aggregate by model (only models with usage)
                usage_by_model = {}
                for record in model_records:
                    if record.model_name not in usage_by_model:
                        usage_by_model[record.model_name] = {
                            'total_tokens': 0,
                            'total_requests': 0,
                            'raw_cost': 0.0,
                            'markup_cost': 0.0,
                            'days_used': set(),
                            'provider': record.provider
                        }
                    
                    usage_by_model[record.model_name]['total_tokens'] += record.total_tokens
                    usage_by_model[record.model_name]['total_requests'] += record.total_requests
                    usage_by_model[record.model_name]['raw_cost'] += record.raw_cost
                    usage_by_model[record.model_name]['markup_cost'] += record.markup_cost
                    usage_by_model[record.model_name]['days_used'].add(record.usage_date)
                
                # Define ALL 12 available models (matching frontend fallbackPricingData)
                all_models = [
                    {'id': 'anthropic/claude-sonnet-4', 'name': 'Claude Sonnet 4', 'provider': 'Anthropic'},
                    {'id': 'google/gemini-2.5-flash', 'name': 'Gemini 2.5 Flash', 'provider': 'Google'},
                    {'id': 'google/gemini-2.5-pro', 'name': 'Gemini 2.5 Pro', 'provider': 'Google'},
                    {'id': 'deepseek/deepseek-chat-v3-0324', 'name': 'DeepSeek Chat v3', 'provider': 'DeepSeek'},
                    {'id': 'anthropic/claude-3.7-sonnet', 'name': 'Claude 3.7 Sonnet', 'provider': 'Anthropic'},
                    {'id': 'google/gemini-2.5-flash-lite-preview-06-17', 'name': 'Gemini 2.5 Flash Lite', 'provider': 'Google'},
                    {'id': 'openai/gpt-4.1', 'name': 'GPT-4.1', 'provider': 'OpenAI'},
                    {'id': 'x-ai/grok-4', 'name': 'Grok 4', 'provider': 'xAI'},
                    {'id': 'openai/gpt-4o-mini', 'name': 'GPT-4o Mini', 'provider': 'OpenAI'},
                    {'id': 'openai/o4-mini-high', 'name': 'O4 Mini High', 'provider': 'OpenAI'},
                    {'id': 'openai/o3', 'name': 'O3', 'provider': 'OpenAI'},
                    {'id': 'openai/chatgpt-4o-latest', 'name': 'ChatGPT-4o Latest', 'provider': 'OpenAI'}
                ]
                
                # Create result with ALL 12 models, merging usage data where available
                result = []
                for model in all_models:
                    model_id = model['id']
                    usage = usage_by_model.get(model_id, {
                        'total_tokens': 0,
                        'total_requests': 0,
                        'raw_cost': 0.0,
                        'markup_cost': 0.0,  # This is the key field - 1.3x markup cost
                        'days_used': set(),
                        'provider': model['provider']
                    })
                    
                    result.append({
                        'model_name': model_id,
                        'provider': usage['provider'],
                        'total_tokens': usage['total_tokens'],
                        'total_requests': usage['total_requests'],
                        'raw_cost': usage['raw_cost'],
                        'markup_cost': usage['markup_cost'],  # 1.3x markup rate applied
                        'days_used': len(usage['days_used'])  # Convert set to count
                    })
                
                # Sort by markup cost descending (models with usage first)
                result.sort(key=lambda x: x['markup_cost'], reverse=True)
                
                return result
        except Exception as e:
            print(f"Error getting model usage: {e}")
            return []

    def get_all_clients_usage_stats(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> List[ClientBillingResponse]:
        """Get usage statistics for all clients for billing purposes"""
        try:
            with get_db() as db:
                # Import here to avoid circular imports
                from . import ClientOrganizationDB
                
                # Get all active clients
                clients = ClientOrganizationDB.get_all_active_clients()
                billing_data = []
                
                for client in clients:
                    # This is a simplified version - in real implementation we'd need async handling
                    # For now, return empty list to avoid breaking existing API
                    pass
                
                return billing_data
        except Exception:
            return []