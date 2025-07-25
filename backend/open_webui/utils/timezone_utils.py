"""
Timezone Utilities for mAI Usage Tracking

Provides timezone-aware date calculations to ensure accurate
month boundaries and usage attribution for Polish and international clients.
"""

import logging
from datetime import datetime, date, timezone
from typing import Optional, Tuple
from zoneinfo import ZoneInfo
import time

log = logging.getLogger(__name__)


class TimezoneCalculationError(Exception):
    """Custom exception for timezone calculation errors"""
    pass


def get_client_local_date(client_timezone: str = "Europe/Warsaw") -> date:
    """
    Get current date in client's local timezone
    
    Args:
        client_timezone: Client's timezone (default: Poland)
        
    Returns:
        Current date in client's local timezone
        
    Raises:
        TimezoneCalculationError: If timezone is invalid
    """
    try:
        # Get current time in client's timezone
        client_tz = ZoneInfo(client_timezone)
        local_datetime = datetime.now(client_tz)
        return local_datetime.date()
    
    except Exception as e:
        log.error(f"Failed to get local date for timezone {client_timezone}: {e}")
        raise TimezoneCalculationError(f"Invalid timezone: {client_timezone}")


def get_client_month_start(client_timezone: str = "Europe/Warsaw") -> date:
    """
    Get start of current month in client's local timezone
    
    Args:
        client_timezone: Client's timezone (default: Poland)
        
    Returns:
        First day of current month in client's local timezone
        
    Raises:
        TimezoneCalculationError: If timezone is invalid
    """
    try:
        local_date = get_client_local_date(client_timezone)
        return local_date.replace(day=1)
    
    except Exception as e:
        log.error(f"Failed to get month start for timezone {client_timezone}: {e}")
        raise TimezoneCalculationError(f"Month start calculation failed: {str(e)}")


def get_timezone_offset_info(client_timezone: str = "Europe/Warsaw") -> dict:
    """
    Get detailed timezone offset information for client
    
    Args:
        client_timezone: Client's timezone
        
    Returns:
        Dictionary with timezone information
    """
    try:
        client_tz = ZoneInfo(client_timezone)
        now = datetime.now(client_tz)
        
        return {
            "timezone": client_timezone,
            "current_datetime": now.isoformat(),
            "current_date": now.date().isoformat(),
            "utc_offset": now.strftime("%z"),
            "timezone_name": now.strftime("%Z"),
            "is_dst": now.dst() is not None and now.dst().total_seconds() > 0
        }
    
    except Exception as e:
        log.error(f"Failed to get timezone info for {client_timezone}: {e}")
        return {
            "timezone": client_timezone,
            "error": str(e),
            "fallback_used": True
        }


def convert_server_date_to_client_date(
    server_date: date, 
    client_timezone: str = "Europe/Warsaw"
) -> date:
    """
    Convert server date to client's local date (accounting for timezone differences)
    
    Args:
        server_date: Date in server timezone
        client_timezone: Client's timezone
        
    Returns:
        Equivalent date in client's timezone
    """
    try:
        # Convert server date to datetime at midnight
        server_datetime = datetime.combine(server_date, datetime.min.time())
        
        # Assume server is in UTC (common for cloud deployments)
        server_datetime_utc = server_datetime.replace(tzinfo=timezone.utc)
        
        # Convert to client timezone
        client_tz = ZoneInfo(client_timezone)
        client_datetime = server_datetime_utc.astimezone(client_tz)
        
        return client_datetime.date()
    
    except Exception as e:
        log.warning(f"Failed to convert server date to client timezone: {e}")
        # Fallback: return original date
        return server_date


def validate_timezone(timezone_str: str) -> bool:
    """
    Validate if timezone string is valid
    
    Args:
        timezone_str: Timezone string to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        ZoneInfo(timezone_str)
        return True
    except Exception:
        return False


def get_month_date_range_for_client(
    client_timezone: str = "Europe/Warsaw"
) -> Tuple[date, date]:
    """
    Get the date range for current month in client's timezone
    
    Args:
        client_timezone: Client's timezone
        
    Returns:
        Tuple of (month_start_date, current_date) in client timezone
        
    Raises:
        TimezoneCalculationError: If calculation fails
    """
    try:
        current_date = get_client_local_date(client_timezone)
        month_start = current_date.replace(day=1)
        
        return month_start, current_date
    
    except Exception as e:
        log.error(f"Failed to get month date range for {client_timezone}: {e}")
        raise TimezoneCalculationError(f"Date range calculation failed: {str(e)}")


def is_same_day_in_timezone(
    date1: date, 
    date2: date, 
    client_timezone: str = "Europe/Warsaw"
) -> bool:
    """
    Check if two dates represent the same day in client's timezone
    
    Args:
        date1: First date
        date2: Second date  
        client_timezone: Client's timezone
        
    Returns:
        True if same day in client timezone, False otherwise
    """
    try:
        # Convert both dates to client timezone
        client_date1 = convert_server_date_to_client_date(date1, client_timezone)
        client_date2 = convert_server_date_to_client_date(date2, client_timezone)
        
        return client_date1 == client_date2
    
    except Exception as e:
        log.warning(f"Failed to compare dates in timezone {client_timezone}: {e}")
        # Fallback: direct comparison
        return date1 == date2


def get_polish_business_hours_info() -> dict:
    """
    Get information about Polish business hours and timezone
    Useful for understanding when Polish clients are most active
    
    Returns:
        Dictionary with Polish timezone information
    """
    try:
        poland_tz = ZoneInfo("Europe/Warsaw")
        now_poland = datetime.now(poland_tz)
        
        # Determine if it's business hours (9 AM - 5 PM weekdays)
        is_weekday = now_poland.weekday() < 5  # Monday = 0, Sunday = 6
        is_business_hours = 9 <= now_poland.hour < 17
        
        return {
            "current_time_poland": now_poland.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "timezone": "Europe/Warsaw",
            "is_dst": now_poland.dst() is not None and now_poland.dst().total_seconds() > 0,
            "utc_offset": now_poland.strftime("%z"),
            "is_business_hours": is_weekday and is_business_hours,
            "weekday": now_poland.strftime("%A"),
            "month_name_polish": {
                1: "Styczeń", 2: "Luty", 3: "Marzec", 4: "Kwiecień",
                5: "Maj", 6: "Czerwiec", 7: "Lipiec", 8: "Sierpień", 
                9: "Wrzesień", 10: "Październik", 11: "Listopad", 12: "Grudzień"
            }.get(now_poland.month, "Unknown")
        }
        
    except Exception as e:
        log.error(f"Failed to get Polish business hours info: {e}")
        return {
            "error": str(e),
            "timezone": "Europe/Warsaw",
            "fallback_used": True
        }


def log_timezone_transition(
    operation: str,
    client_id: str,
    server_date: date,
    client_date: date,
    client_timezone: str
) -> None:
    """
    Log timezone transitions for monitoring and debugging
    
    Args:
        operation: Operation being performed
        client_id: Client organization ID
        server_date: Date in server timezone
        client_date: Date in client timezone
        client_timezone: Client's timezone
    """
    if server_date != client_date:
        log.info(
            f"Timezone transition detected - {operation}: "
            f"Client {client_id}, Server date: {server_date}, "
            f"Client date ({client_timezone}): {client_date}"
        )


# Pre-validate Polish timezone on module import
if not validate_timezone("Europe/Warsaw"):
    log.error("Europe/Warsaw timezone not available - Polish timezone support may fail")
else:
    log.info("Polish timezone (Europe/Warsaw) validated successfully")