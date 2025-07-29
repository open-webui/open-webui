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


def _calculate_top_models_by_tokens(client_org_id: str, current_month_start: date, today: date, db) -> List[Dict[str, Any]]:
    """
    Calculate top 3 models by token count for the current month.
    Returns array with model name and token count for each model.
    Handles edge cases: empty records, fewer than 3 models.
    """
    try:
        # Query model usage for current month
        model_records = db.query(ClientModelDailyUsage).filter(
            ClientModelDailyUsage.client_org_id == client_org_id,
            ClientModelDailyUsage.usage_date >= current_month_start,
            ClientModelDailyUsage.usage_date <= today
        ).all()
        
        if not model_records:
            return []
        
        # Aggregate by model name
        model_totals = {}
        for record in model_records:
            if record.model_name not in model_totals:
                model_totals[record.model_name] = {
                    'model_name': record.model_name,
                    'total_tokens': 0
                }
            model_totals[record.model_name]['total_tokens'] += record.total_tokens
        
        # Sort by total tokens descending and take top 3
        sorted_models = sorted(
            model_totals.values(),
            key=lambda x: x['total_tokens'],
            reverse=True
        )
        
        return sorted_models[:3]  # Return top 3 models
        
    except Exception as e:
        log.error(f"Error calculating top models for client {client_org_id}: {e}")
        return []


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
                
                # Calculate current month totals
                total_tokens = sum(r.total_tokens for r in month_records)
                total_cost = sum(r.markup_cost for r in month_records)
                total_requests = sum(r.total_requests for r in month_records)
                days_with_usage = len(month_records)
                
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
                
                # Calculate top 3 models by token count
                top_models = _calculate_top_models_by_tokens(
                    client_org_id, current_month_start, today, db
                )
                
                # Debug: Log the top models calculation
                print(f"🔍 DEBUG REPO - Client: {client_org_id}")
                print(f"🔍 DEBUG REPO - Top models calculated: {top_models}")
                print(f"🔍 DEBUG REPO - Top models length: {len(top_models)}")
                
                # Calculate unique users from ClientUserDailyUsage (correct implementation)
                user_records = db.query(ClientUserDailyUsage.user_id).filter(
                    ClientUserDailyUsage.client_org_id == client_org_id,
                    ClientUserDailyUsage.usage_date >= current_month_start,
                    ClientUserDailyUsage.usage_date <= today
                ).distinct().all()
                total_unique_users = len(user_records)
                
                # Monthly summary with only used fields
                monthly_summary = {
                    'total_unique_users': total_unique_users,
                    'top_models': top_models
                }
                
                # Debug: Log the complete monthly summary
                print(f"🔍 DEBUG REPO - Monthly summary: {monthly_summary}")
                print(f"🔍 DEBUG REPO - Unique users: {total_unique_users}")
                
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
                monthly_summary={'total_unique_users': 0, 'top_models': []},
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
                
                print(f"🔍 [DEBUG] ClientUsageRepository.get_usage_by_user: client_org_id={client_org_id}, date_range={start_date} to {end_date}")
                
                # Query per-user daily usage
                user_records = db.query(ClientUserDailyUsage).filter(
                    ClientUserDailyUsage.client_org_id == client_org_id,
                    ClientUserDailyUsage.usage_date >= start_date,
                    ClientUserDailyUsage.usage_date <= end_date
                ).all()
                
                print(f"🔍 [DEBUG] Found {len(user_records)} user usage records in DB")
                
                # Let's also check if there are ANY records for this client
                all_client_records = db.query(ClientUserDailyUsage).filter(
                    ClientUserDailyUsage.client_org_id == client_org_id
                ).all()
                print(f"🔍 [DEBUG] Total records for client {client_org_id}: {len(all_client_records)}")
                
                # Check if there are any records at all in the table
                total_records = db.query(ClientUserDailyUsage).count()
                print(f"🔍 [DEBUG] Total records in ClientUserDailyUsage table: {total_records}")
                
                # Show sample of existing data
                if total_records > 0:
                    sample_records = db.query(ClientUserDailyUsage).limit(3).all()
                    for rec in sample_records:
                        print(f"🔍 [DEBUG] Sample record: client_id={rec.client_org_id}, user_id={rec.user_id}, date={rec.usage_date}, tokens={rec.total_tokens}")
                
                
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
    
