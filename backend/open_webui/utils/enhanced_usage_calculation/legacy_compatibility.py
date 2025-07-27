"""
Legacy compatibility layer for enhanced_usage_calculation.py
Maintains 100% backward compatibility while using new optimized implementation
"""

import logging
from datetime import datetime, date as DateType
from typing import Optional, Dict, Any
import time

from .calculator import calculate_usage, invalidate_client_cache
from .models.calculation_models import CalculationRequest, AggregationType
from .models.result_models import DailyUsageData
from open_webui.models.organization_usage import (
    ClientDailyUsage, ClientOrganization, 
    ClientUsageStatsResponse
)
from open_webui.internal.db import get_db

log = logging.getLogger(__name__)


# Legacy exception for compatibility
class MonthTotalCalculationError(Exception):
    """Custom exception for month total calculation errors"""
    pass


def get_enhanced_usage_stats_by_client(
    client_org_id: str, 
    use_client_timezone: bool = True,
    prevent_double_counting: bool = True
) -> ClientUsageStatsResponse:
    """
    Enhanced usage stats calculation with timezone support and double counting prevention
    
    This is the legacy API maintained for backward compatibility.
    Now uses the optimized calculator under the hood.
    
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
        # Create calculation request
        request = CalculationRequest(
            client_org_id=client_org_id,
            aggregation_type=AggregationType.MONTHLY,
            use_client_timezone=use_client_timezone,
            prevent_double_counting=prevent_double_counting,
            include_details=True  # Need daily history for legacy response
        )
        
        # Execute calculation using new optimized calculator
        result = calculate_usage(request)
        
        if not result.success:
            raise MonthTotalCalculationError(f"Calculation failed: {result.error}")
        
        # Extract data from result
        month_data = result.data.get('month_summary', {})
        daily_history = result.data.get('daily_history', [])
        
        # Get today's data (will be the most recent in daily history or separate query)
        today_data = _get_today_data(client_org_id, use_client_timezone)
        
        # Get client name
        client_name = "Unknown"
        with get_db() as db:
            client = db.query(ClientOrganization).filter_by(id=client_org_id).first()
            if client:
                client_name = client.name
        
        # Build legacy response format
        return ClientUsageStatsResponse(
            today=today_data,
            this_month=month_data,
            daily_history=daily_history,
            client_org_name=client_name
        )
        
    except Exception as e:
        log.error(f"Enhanced usage stats calculation failed for client {client_org_id}: {e}")
        raise MonthTotalCalculationError(f"Usage stats calculation failed: {str(e)}")


def validate_no_double_counting(db, client_org_id: str, today: DateType) -> Dict[str, Any]:
    """
    Validate that today's data doesn't exist in both live counter and daily summary
    
    Legacy function maintained for compatibility.
    Note: ClientLiveCounters table no longer exists in refactored architecture.
    
    Returns:
        Dictionary with validation results and recommended action
    """
    # Check if today's data exists in daily summary
    daily_summary = db.query(ClientDailyUsage).filter_by(
        client_org_id=client_org_id,
        usage_date=today
    ).first()
    
    has_daily_data = daily_summary is not None
    
    # Since we no longer have live counters, validation is simpler
    return {
        "valid": True,
        "has_daily_data": has_daily_data,
        "has_live_data": False,  # No live counters in new architecture
        "recommended_action": "no_action_needed"
    }


def create_month_total_health_check(client_org_id: str) -> Dict[str, Any]:
    """
    Comprehensive health check for Month Total calculation accuracy
    
    Legacy function maintained for compatibility.
    
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
        # Run calculation to verify it works
        request = CalculationRequest(
            client_org_id=client_org_id,
            aggregation_type=AggregationType.MONTHLY,
            use_client_timezone=True,
            prevent_double_counting=True
        )
        
        result = calculate_usage(request)
        
        if result.success:
            health_report["checks"].append({
                "check": "month_calculation",
                "status": "passed",
                "message": "Month total calculation completed successfully",
                "details": {
                    "execution_time_ms": result.execution_time_ms,
                    "cache_hit_rate": result.cache_hit_rate,
                    "queries_executed": result.queries_executed
                }
            })
            
            # Check performance
            if result.execution_time_ms > 100:
                health_report["issues_found"] += 1
                health_report["overall_status"] = "warning"
                health_report["checks"].append({
                    "check": "performance",
                    "status": "warning",
                    "message": f"Calculation took {result.execution_time_ms:.2f}ms (target: <100ms)"
                })
                health_report["recommendations"].append(
                    "Consider warming cache during off-peak hours"
                )
        else:
            health_report["issues_found"] += 1
            health_report["overall_status"] = "error"
            health_report["checks"].append({
                "check": "month_calculation",
                "status": "failed",
                "message": f"Month calculation failed: {result.error}"
            })
            
    except Exception as e:
        health_report["overall_status"] = "error"
        health_report["checks"].append({
            "check": "health_check_execution",
            "status": "failed",
            "message": f"Health check execution failed: {str(e)}"
        })
    
    return health_report


def _get_today_data(client_org_id: str, use_client_timezone: bool) -> Dict[str, Any]:
    """Get today's usage data"""
    try:
        with get_db() as db:
            # Get client timezone
            client = db.query(ClientOrganization).filter_by(id=client_org_id).first()
            client_timezone = "Europe/Warsaw"
            if client and hasattr(client, 'timezone'):
                client_timezone = client.timezone
            
            # Get today's date in client timezone
            if use_client_timezone:
                from .services.timezone_service import get_client_local_date
                today = get_client_local_date(client_timezone)
            else:
                today = DateType.today()
            
            # Get today's usage
            daily_summary = db.query(ClientDailyUsage).filter_by(
                client_org_id=client_org_id,
                usage_date=today
            ).first()
            
            if daily_summary:
                return {
                    'tokens': daily_summary.total_tokens,
                    'cost': daily_summary.markup_cost,
                    'requests': daily_summary.total_requests,
                    'last_updated': datetime.fromtimestamp(
                        daily_summary.updated_at
                    ).strftime('%H:%M:%S') if daily_summary.updated_at else 'Unknown'
                }
            
            return {
                'tokens': 0,
                'cost': 0.0,
                'requests': 0,
                'last_updated': 'No usage today'
            }
            
    except Exception as e:
        log.error(f"Failed to get today's data: {e}")
        return {
            'tokens': 0,
            'cost': 0.0,
            'requests': 0,
            'last_updated': 'Error'
        }


# Legacy function exports for backward compatibility
__all__ = [
    'MonthTotalCalculationError',
    'get_enhanced_usage_stats_by_client',
    'validate_no_double_counting',
    'create_month_total_health_check'
]