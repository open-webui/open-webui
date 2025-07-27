"""
Enhanced Usage Calculation with Polish Timezone Support and Double Counting Prevention

This module provides enhanced usage calculation methods that solve the critical
issues identified in Month Total calculations:
1. Double counting prevention
2. Polish timezone support
3. Improved rollover timing
4. Monitoring and validation
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, Tuple
import time
from contextlib import contextmanager

from open_webui.models.organization_usage import (
    ClientLiveCounters, ClientDailyUsage, ClientOrganizationDB,
    ClientUsageStatsResponse, get_db
)
from open_webui.utils.timezone_utils import (
    get_client_local_date, get_client_month_start,
    log_timezone_transition, TimezoneCalculationError
)

log = logging.getLogger(__name__)


class MonthTotalCalculationError(Exception):
    """Custom exception for month total calculation errors"""
    pass


@contextmanager
def usage_transaction():
    """Context manager for usage calculations with proper error handling"""
    with get_db() as db:
        try:
            yield db
            db.commit()
        except Exception as e:
            db.rollback()
            log.error(f"Usage transaction rolled back: {e}")
            raise


def validate_no_double_counting(db, client_org_id: str, today: date) -> Dict[str, Any]:
    """
    Validate that today's data doesn't exist in both live counter and daily summary
    
    Returns:
        Dictionary with validation results and recommended action
    """
    daily_summary = db.query(ClientDailyUsage).filter_by(
        client_org_id=client_org_id,
        usage_date=today
    ).first()
    
    live_counter = db.query(ClientLiveCounters).filter_by(
        client_org_id=client_org_id
    ).first()
    
    has_daily_data = daily_summary is not None
    has_live_data = live_counter is not None and live_counter.current_date == today and live_counter.today_tokens > 0
    
    double_counting_risk = has_daily_data and has_live_data
    
    if double_counting_risk:
        log.error(f"DOUBLE COUNTING DETECTED: Client {client_org_id} has today's data in both tables!")
        return {
            "valid": False,
            "issue": "double_counting",
            "daily_tokens": daily_summary.total_tokens if daily_summary else 0,
            "live_tokens": live_counter.today_tokens if live_counter else 0,
            "recommended_action": "use_daily_summary_as_source_of_truth"
        }
    
    return {
        "valid": True,
        "has_daily_data": has_daily_data,
        "has_live_data": has_live_data,
        "recommended_action": "no_action_needed"
    }


def get_enhanced_usage_stats_by_client(
    client_org_id: str, 
    use_client_timezone: bool = True,
    prevent_double_counting: bool = True
) -> ClientUsageStatsResponse:
    """
    Enhanced usage stats calculation with timezone support and double counting prevention
    
    Args:
        client_org_id: Client organization ID
        use_client_timezone: Use client's local timezone for date calculations
        prevent_double_counting: Enable double counting validation and prevention
        
    Returns:
        ClientUsageStatsResponse with accurate month totals
        
    Raises:
        MonthTotalCalculationError: If calculation fails
    """
    try:
        with usage_transaction() as db:
            # Get client information for timezone
            client = ClientOrganizationDB.get_client_by_id(client_org_id)
            client_timezone = "Europe/Warsaw"  # Default to Poland
            client_name = "Unknown"
            
            if client:
                client_name = client.name
                client_timezone = getattr(client, 'timezone', "Europe/Warsaw")
            
            # Calculate dates using client's timezone
            if use_client_timezone:
                try:
                    today = get_client_local_date(client_timezone)
                    current_month_start = get_client_month_start(client_timezone)
                    
                    # Log timezone differences for monitoring
                    server_today = date.today()
                    if today != server_today:
                        log_timezone_transition(
                            "enhanced_usage_stats", client_org_id,
                            server_today, today, client_timezone
                        )
                except TimezoneCalculationError as e:
                    log.warning(f"Timezone calculation failed for client {client_org_id}: {e}")
                    today = date.today()
                    current_month_start = today.replace(day=1)
            else:
                today = date.today()
                current_month_start = today.replace(day=1)
            
            # DOUBLE COUNTING PREVENTION
            if prevent_double_counting:
                validation_result = validate_no_double_counting(db, client_org_id, today)
                
                if not validation_result["valid"]:
                    # Handle double counting
                    if validation_result["recommended_action"] == "use_daily_summary_as_source_of_truth":
                        # Reset live counter and use daily summary
                        live_counter = db.query(ClientLiveCounters).filter_by(
                            client_org_id=client_org_id
                        ).with_for_update().first()
                        
                        if live_counter:
                            live_counter.current_date = today
                            live_counter.today_tokens = 0
                            live_counter.today_requests = 0
                            live_counter.today_raw_cost = 0.0
                            live_counter.today_markup_cost = 0.0
                            live_counter.last_updated = int(time.time())
                            
                            log.info(f"Reset live counter to prevent double counting for client {client_org_id}")
            
            # Get today's data (single source of truth)
            today_data = get_today_usage_data(db, client_org_id, today)
            
            # Get historical data (excluding today to prevent double counting)
            daily_history = get_daily_history(db, client_org_id, today)
            
            # Calculate month totals (excluding today from historical data)
            month_totals = calculate_month_totals(
                db, client_org_id, current_month_start, today, today_data
            )
            
            return ClientUsageStatsResponse(
                today=today_data,
                this_month=month_totals,
                daily_history=daily_history,
                client_org_name=client_name
            )
            
    except Exception as e:
        log.error(f"Enhanced usage stats calculation failed for client {client_org_id}: {e}")
        raise MonthTotalCalculationError(f"Usage stats calculation failed: {str(e)}")


def get_today_usage_data(db, client_org_id: str, today: date) -> Dict[str, Any]:
    """Get today's usage data from single source of truth"""
    
    # Check daily summary first (historical data takes precedence)
    daily_summary = db.query(ClientDailyUsage).filter_by(
        client_org_id=client_org_id,
        usage_date=today
    ).first()
    
    if daily_summary:
        # Today's data exists in daily summary - sync to live counter
        live_counter = db.query(ClientLiveCounters).filter_by(
            client_org_id=client_org_id
        ).with_for_update().first()
        
        if not live_counter:
            live_counter = ClientLiveCounters(
                client_org_id=client_org_id,
                current_date=today,
                today_tokens=daily_summary.total_tokens,
                today_requests=daily_summary.total_requests,
                today_raw_cost=daily_summary.raw_cost,
                today_markup_cost=daily_summary.markup_cost,
                last_updated=int(time.time())
            )
            db.add(live_counter)
        else:
            # Sync live counter with daily summary
            live_counter.current_date = today
            live_counter.today_tokens = daily_summary.total_tokens
            live_counter.today_requests = daily_summary.total_requests
            live_counter.today_raw_cost = daily_summary.raw_cost
            live_counter.today_markup_cost = daily_summary.markup_cost
            live_counter.last_updated = int(time.time())
        
        return {
            'tokens': daily_summary.total_tokens,
            'cost': daily_summary.markup_cost,
            'requests': daily_summary.total_requests,
            'last_updated': 'From daily summary (authoritative)'
        }
    
    # No daily summary - check live counter
    live_counter = db.query(ClientLiveCounters).filter_by(
        client_org_id=client_org_id
    ).first()
    
    if live_counter and live_counter.current_date == today:
        return {
            'tokens': live_counter.today_tokens,
            'cost': live_counter.today_markup_cost,
            'requests': live_counter.today_requests,
            'last_updated': datetime.fromtimestamp(live_counter.last_updated).strftime('%H:%M:%S')
        }
    elif live_counter and live_counter.current_date != today:
        # Stale live counter - perform rollover if needed
        if live_counter.today_tokens > 0:
            from open_webui.models.organization_usage import ClientUsageDB
            usage_db = ClientUsageDB()
            usage_db._rollup_to_daily_summary(db, live_counter)
        
        # Reset for today
        live_counter.current_date = today
        live_counter.today_tokens = 0
        live_counter.today_requests = 0
        live_counter.today_raw_cost = 0.0
        live_counter.today_markup_cost = 0.0
        live_counter.last_updated = int(time.time())
        
        return {
            'tokens': 0,
            'cost': 0.0,
            'requests': 0,
            'last_updated': 'Reset after rollover'
        }
    
    # No data exists
    return {
        'tokens': 0,
        'cost': 0.0,
        'requests': 0,
        'last_updated': 'No usage today'
    }


def get_daily_history(db, client_org_id: str, today: date) -> list:
    """Get daily history excluding today to prevent double counting"""
    daily_records = db.query(ClientDailyUsage).filter(
        ClientDailyUsage.client_org_id == client_org_id,
        ClientDailyUsage.usage_date < today  # Exclude today
    ).order_by(ClientDailyUsage.usage_date.desc()).limit(30).all()
    
    daily_history = []
    for record in daily_records:
        daily_history.append({
            'date': record.usage_date.isoformat(),
            'tokens': record.total_tokens,
            'cost': record.markup_cost,
            'requests': record.total_requests
        })
    
    return daily_history


def calculate_month_totals(
    db, client_org_id: str, current_month_start: date, today: date, today_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Calculate month totals excluding today from historical data"""
    
    # Get historical month data (excluding today)
    month_records = db.query(ClientDailyUsage).filter(
        ClientDailyUsage.client_org_id == client_org_id,
        ClientDailyUsage.usage_date >= current_month_start,
        ClientDailyUsage.usage_date < today  # Exclude today
    ).all()
    
    # Sum historical data
    month_tokens = sum(r.total_tokens for r in month_records)
    month_cost = sum(r.markup_cost for r in month_records)
    month_requests = sum(r.total_requests for r in month_records)
    days_active = len(month_records)
    
    # Add today's usage (single source of truth)
    month_tokens += today_data['tokens']
    month_cost += today_data['cost']
    month_requests += today_data['requests']
    if today_data['tokens'] > 0:
        days_active += 1
    
    return {
        'tokens': month_tokens,
        'cost': month_cost,
        'requests': month_requests,
        'days_active': days_active
    }


def create_month_total_health_check(client_org_id: str) -> Dict[str, Any]:
    """
    Comprehensive health check for Month Total calculation accuracy
    
    Returns:
        Dictionary with health check results and recommendations
    """
    health_report = {
        "client_org_id": client_org_id,
        "timestamp": datetime.now().isoformat(),
        "checks": [],
        "overall_status": "healthy",
        "issues_found": 0,
        "recommendations": []
    }
    
    try:
        with get_db() as db:
            client = ClientOrganizationDB.get_client_by_id(client_org_id)
            if not client:
                health_report["overall_status"] = "error"
                health_report["checks"].append({
                    "check": "client_exists",
                    "status": "failed",
                    "message": f"Client {client_org_id} not found"
                })
                return health_report
            
            client_timezone = getattr(client, 'timezone', "Europe/Warsaw")
            today = get_client_local_date(client_timezone)
            
            # Check 1: Double counting validation
            validation_result = validate_no_double_counting(db, client_org_id, today)
            if not validation_result["valid"]:
                health_report["issues_found"] += 1
                health_report["overall_status"] = "warning"
                health_report["checks"].append({
                    "check": "double_counting",
                    "status": "failed",
                    "message": f"Double counting detected: {validation_result['issue']}",
                    "details": validation_result
                })
                health_report["recommendations"].append("Fix double counting issue immediately")
            else:
                health_report["checks"].append({
                    "check": "double_counting",
                    "status": "passed",
                    "message": "No double counting detected"
                })
            
            # Check 2: Timezone consistency
            server_today = date.today()
            if today != server_today:
                health_report["checks"].append({
                    "check": "timezone_consistency",
                    "status": "info",
                    "message": f"Client timezone differs from server: {client_timezone}",
                    "details": {
                        "client_date": today.isoformat(),
                        "server_date": server_today.isoformat(),
                        "timezone": client_timezone
                    }
                })
            else:
                health_report["checks"].append({
                    "check": "timezone_consistency",
                    "status": "passed",
                    "message": "Client and server dates aligned"
                })
            
            # Check 3: Live counter staleness
            live_counter = db.query(ClientLiveCounters).filter_by(
                client_org_id=client_org_id
            ).first()
            
            if live_counter:
                if live_counter.current_date != today:
                    health_report["issues_found"] += 1
                    health_report["overall_status"] = "warning"
                    health_report["checks"].append({
                        "check": "live_counter_staleness",
                        "status": "warning",
                        "message": f"Stale live counter detected: {live_counter.current_date} vs {today}",
                        "details": {
                            "live_counter_date": live_counter.current_date.isoformat(),
                            "expected_date": today.isoformat()
                        }
                    })
                    health_report["recommendations"].append("Perform daily rollover to fix stale counter")
                else:
                    health_report["checks"].append({
                        "check": "live_counter_staleness",
                        "status": "passed",
                        "message": "Live counter is current"
                    })
            else:
                health_report["checks"].append({
                    "check": "live_counter_staleness",
                    "status": "info",
                    "message": "No live counter exists (acceptable if no usage today)"
                })
            
            # Check 4: Month calculation consistency
            try:
                stats = get_enhanced_usage_stats_by_client(client_org_id, use_client_timezone=True)
                health_report["checks"].append({
                    "check": "month_calculation",
                    "status": "passed",
                    "message": "Month total calculation completed successfully",
                    "details": {
                        "month_cost": stats.this_month['cost'],
                        "month_tokens": stats.this_month['tokens'],
                        "days_active": stats.this_month['days_active']
                    }
                })
            except Exception as e:
                health_report["issues_found"] += 1
                health_report["overall_status"] = "error"
                health_report["checks"].append({
                    "check": "month_calculation",
                    "status": "failed",
                    "message": f"Month calculation failed: {str(e)}"
                })
                health_report["recommendations"].append("Investigate month calculation error")
            
    except Exception as e:
        health_report["overall_status"] = "error"
        health_report["checks"].append({
            "check": "health_check_execution",
            "status": "failed",
            "message": f"Health check execution failed: {str(e)}"
        })
    
    return health_report