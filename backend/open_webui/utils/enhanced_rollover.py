"""
Enhanced Daily Rollover with Proper Locking and Transaction Management

Addresses rollover timing issues and race conditions identified in Month Total analysis.
"""

import logging
import time
from datetime import datetime, date, timedelta
from typing import Dict, Any, List
from contextlib import contextmanager

from open_webui.models.organization_usage import (
    ClientLiveCounters, ClientDailyUsage, ClientOrganizationDB, get_db
)
from open_webui.utils.timezone_utils import get_client_local_date

log = logging.getLogger(__name__)


class RolloverError(Exception):
    """Custom exception for rollover operations"""
    pass


@contextmanager
def rollover_transaction():
    """Context manager for rollover operations with proper error handling"""
    with get_db() as db:
        try:
            yield db
            db.commit()
            log.debug("Rollover transaction committed successfully")
        except Exception as e:
            db.rollback()
            log.error(f"Rollover transaction rolled back: {e}")
            raise RolloverError(f"Rollover transaction failed: {str(e)}")


def perform_atomic_daily_rollover_all_clients() -> Dict[str, Any]:
    """
    Enhanced daily rollover with proper locking and timezone awareness
    
    Returns:
        Dictionary with rollover results and statistics
    """
    rollover_start = time.time()
    
    try:
        with rollover_transaction() as db:
            # Get all live counters that need rollover with exclusive lock
            stale_counters = db.query(ClientLiveCounters).filter(
                ClientLiveCounters.current_date < date.today()
            ).with_for_update().all()  # Exclusive lock to prevent race conditions
            
            if not stale_counters:
                return {
                    "success": True,
                    "rollovers_performed": 0,
                    "duration_seconds": time.time() - rollover_start,
                    "message": "No stale counters found - all clients up to date"
                }
            
            rollover_results = []
            successful_rollovers = 0
            failed_rollovers = 0
            
            for live_counter in stale_counters:
                try:
                    # Get client timezone for proper date calculation
                    client = ClientOrganizationDB.get_client_by_id(live_counter.client_org_id)
                    client_timezone = "Europe/Warsaw"  # Default to Poland
                    
                    if client:
                        client_timezone = getattr(client, 'timezone', "Europe/Warsaw")
                    
                    # Calculate proper "today" for this client
                    client_today = get_client_local_date(client_timezone)
                    
                    # Perform rollover for this specific counter
                    rollover_result = perform_single_client_rollover(
                        db, live_counter, client_today, client_timezone
                    )
                    
                    rollover_results.append(rollover_result)
                    
                    if rollover_result["success"]:
                        successful_rollovers += 1
                    else:
                        failed_rollovers += 1
                        
                except Exception as e:
                    log.error(f"Failed to rollover client {live_counter.client_org_id}: {e}")
                    rollover_results.append({
                        "client_org_id": live_counter.client_org_id,
                        "success": False,
                        "error": str(e),
                        "stale_date": live_counter.current_date.isoformat()
                    })
                    failed_rollovers += 1
            
            duration = time.time() - rollover_start
            
            log.info(f"Daily rollover completed: {successful_rollovers} successful, {failed_rollovers} failed, {duration:.2f}s")
            
            return {
                "success": failed_rollovers == 0,
                "rollovers_performed": successful_rollovers,
                "failed_rollovers": failed_rollovers,
                "duration_seconds": duration,
                "details": rollover_results,
                "message": f"Processed {len(stale_counters)} stale counters"
            }
            
    except Exception as e:
        log.error(f"Daily rollover process failed: {e}")
        return {
            "success": False,
            "rollovers_performed": 0,
            "failed_rollovers": 0,
            "duration_seconds": time.time() - rollover_start,
            "error": str(e),
            "message": "Rollover process failed"
        }


def perform_single_client_rollover(
    db, live_counter: ClientLiveCounters, client_today: date, client_timezone: str
) -> Dict[str, Any]:
    """
    Perform rollover for a single client with timezone awareness
    
    Args:
        db: Database session
        live_counter: Client's live counter to rollover
        client_today: Today's date in client's timezone
        client_timezone: Client's timezone
        
    Returns:
        Dictionary with rollover results
    """
    try:
        client_org_id = live_counter.client_org_id
        stale_date = live_counter.current_date
        
        # Only create daily summary if there was actual usage
        if live_counter.today_tokens > 0:
            # Create daily summary for the stale date
            summary_id = f"{client_org_id}_{stale_date.isoformat()}"
            
            # Check if daily summary already exists (prevent duplicates)
            existing_summary = db.query(ClientDailyUsage).filter_by(id=summary_id).first()
            
            if existing_summary:
                log.warning(f"Daily summary already exists for {client_org_id} on {stale_date} - updating")
                # Update existing summary (add to existing values in case of partial rollover)
                existing_summary.total_tokens += live_counter.today_tokens
                existing_summary.total_requests += live_counter.today_requests
                existing_summary.raw_cost += live_counter.today_raw_cost
                existing_summary.markup_cost += live_counter.today_markup_cost
                existing_summary.updated_at = int(time.time())
            else:
                # Create new daily summary
                daily_summary = ClientDailyUsage(
                    id=summary_id,
                    client_org_id=client_org_id,
                    usage_date=stale_date,
                    total_tokens=live_counter.today_tokens,
                    total_requests=live_counter.today_requests,
                    raw_cost=live_counter.today_raw_cost,
                    markup_cost=live_counter.today_markup_cost,
                    primary_model="aggregated",
                    unique_users=1,
                    created_at=int(time.time()),
                    updated_at=int(time.time())
                )
                db.add(daily_summary)
            
            log.info(f"Rolled over {live_counter.today_tokens} tokens from {stale_date} to daily summary for client {client_org_id}")
        
        # Reset live counter for client's "today"
        original_tokens = live_counter.today_tokens
        live_counter.current_date = client_today
        live_counter.today_tokens = 0
        live_counter.today_requests = 0
        live_counter.today_raw_cost = 0.0
        live_counter.today_markup_cost = 0.0
        live_counter.last_updated = int(time.time())
        
        return {
            "client_org_id": client_org_id,
            "success": True,
            "stale_date": stale_date.isoformat(),
            "client_today": client_today.isoformat(),
            "client_timezone": client_timezone,
            "tokens_rolled_over": original_tokens,
            "created_daily_summary": original_tokens > 0,
            "message": f"Successfully rolled over {original_tokens} tokens"
        }
        
    except Exception as e:
        log.error(f"Single client rollover failed for {live_counter.client_org_id}: {e}")
        return {
            "client_org_id": live_counter.client_org_id,
            "success": False,
            "stale_date": stale_date.isoformat() if 'stale_date' in locals() else "unknown",
            "error": str(e),
            "message": "Rollover failed"
        }


def perform_timezone_aware_rollover_by_client(client_org_id: str) -> Dict[str, Any]:
    """
    Perform rollover for a specific client considering their timezone
    Useful for manual rollover operations
    
    Args:
        client_org_id: Client organization ID
        
    Returns:
        Dictionary with rollover results
    """
    try:
        with rollover_transaction() as db:
            # Get client and live counter with lock
            client = ClientOrganizationDB.get_client_by_id(client_org_id)
            if not client:
                return {
                    "success": False,
                    "error": f"Client {client_org_id} not found",
                    "message": "Client not found"
                }
            
            live_counter = db.query(ClientLiveCounters).filter_by(
                client_org_id=client_org_id
            ).with_for_update().first()
            
            if not live_counter:
                return {
                    "success": True,
                    "message": "No live counter found - nothing to rollover",
                    "client_org_id": client_org_id
                }
            
            # Get client's timezone and calculate proper dates
            client_timezone = getattr(client, 'timezone', "Europe/Warsaw")
            client_today = get_client_local_date(client_timezone)
            
            if live_counter.current_date >= client_today:
                return {
                    "success": True,
                    "message": "Live counter is current - no rollover needed",
                    "client_org_id": client_org_id,
                    "current_date": live_counter.current_date.isoformat(),
                    "client_today": client_today.isoformat()
                }
            
            # Perform the rollover
            return perform_single_client_rollover(db, live_counter, client_today, client_timezone)
            
    except Exception as e:
        log.error(f"Timezone-aware rollover failed for client {client_org_id}: {e}")
        return {
            "success": False,
            "client_org_id": client_org_id,
            "error": str(e),
            "message": "Rollover failed"
        }


def get_rollover_health_status() -> Dict[str, Any]:
    """
    Get health status of rollover operations across all clients
    
    Returns:
        Dictionary with rollover health information
    """
    try:
        with get_db() as db:
            # Get all live counters
            live_counters = db.query(ClientLiveCounters).all()
            
            if not live_counters:
                return {
                    "status": "healthy",
                    "message": "No live counters found",
                    "total_clients": 0,
                    "stale_counters": 0,
                    "current_counters": 0
                }
            
            server_today = date.today()
            stale_counters = []
            current_counters = []
            timezone_mismatches = []
            
            for counter in live_counters:
                if counter.current_date < server_today:
                    stale_counters.append({
                        "client_org_id": counter.client_org_id,
                        "stale_date": counter.current_date.isoformat(),
                        "days_stale": (server_today - counter.current_date).days,
                        "tokens": counter.today_tokens
                    })
                else:
                    current_counters.append(counter.client_org_id)
                
                # Check for timezone mismatches
                try:
                    client = ClientOrganizationDB.get_client_by_id(counter.client_org_id)
                    if client:
                        client_timezone = getattr(client, 'timezone', "Europe/Warsaw")
                        if client_timezone != "Europe/Warsaw":  # Default server assumption
                            client_today = get_client_local_date(client_timezone)
                            if client_today != server_today:
                                timezone_mismatches.append({
                                    "client_org_id": counter.client_org_id,
                                    "client_timezone": client_timezone,
                                    "client_date": client_today.isoformat(),
                                    "server_date": server_today.isoformat()
                                })
                except Exception as e:
                    log.warning(f"Failed to check timezone for client {counter.client_org_id}: {e}")
            
            status = "healthy"
            if len(stale_counters) > 0:
                status = "needs_rollover"
            if len(stale_counters) > len(live_counters) * 0.1:  # More than 10% stale
                status = "critical"
            
            return {
                "status": status,
                "timestamp": datetime.now().isoformat(),
                "total_clients": len(live_counters),
                "current_counters": len(current_counters),
                "stale_counters": len(stale_counters),
                "timezone_mismatches": len(timezone_mismatches),
                "stale_details": stale_counters[:10],  # Limit to first 10
                "timezone_details": timezone_mismatches[:5],  # Limit to first 5
                "recommendations": [
                    "Run daily rollover if stale counters exist",
                    "Monitor timezone mismatches for Polish clients",
                    "Check rollover scheduler if status is critical"
                ] if len(stale_counters) > 0 else ["Rollover status is healthy"]
            }
            
    except Exception as e:
        log.error(f"Failed to get rollover health status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to check rollover health"
        }


def cleanup_old_daily_summaries(retention_days: int = 90) -> Dict[str, Any]:
    """
    Clean up old daily summaries to prevent database bloat
    
    Args:
        retention_days: Number of days to keep (default: 90 days)
        
    Returns:
        Dictionary with cleanup results
    """
    try:
        with rollover_transaction() as db:
            cutoff_date = date.today() - timedelta(days=retention_days)
            
            # Find old records
            old_records = db.query(ClientDailyUsage).filter(
                ClientDailyUsage.usage_date < cutoff_date
            ).all()
            
            if not old_records:
                return {
                    "success": True,
                    "records_deleted": 0,
                    "cutoff_date": cutoff_date.isoformat(),
                    "message": "No old records found to delete"
                }
            
            # Delete old records
            deleted_count = db.query(ClientDailyUsage).filter(
                ClientDailyUsage.usage_date < cutoff_date
            ).delete()
            
            log.info(f"Cleaned up {deleted_count} daily usage records older than {cutoff_date}")
            
            return {
                "success": True,
                "records_deleted": deleted_count,
                "cutoff_date": cutoff_date.isoformat(),
                "retention_days": retention_days,
                "message": f"Successfully deleted {deleted_count} old records"
            }
            
    except Exception as e:
        log.error(f"Failed to cleanup old daily summaries: {e}")
        return {
            "success": False,
            "records_deleted": 0,
            "error": str(e),
            "message": "Cleanup failed"
        }