import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
import uuid

import requests

from open_webui.config import DATA_DIR
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("BACKGROUND_SYNC", logging.INFO))

# Background sync configuration
SYNC_INTERVAL = 600  # 10 minutes
SYNC_DAYS_BACK = 0   # Sync only today's new data (start fresh)

# Using ORM instead of direct database access

class OpenRouterUsageSync:
    """OpenRouter usage synchronization manager"""
    
    def __init__(self):
        self.is_running = False
        
    async def get_openrouter_generations(self, api_key: str, limit: int = 100) -> Dict[str, Any]:
        """Fetch generation data from OpenRouter API"""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        url = "https://openrouter.ai/api/v1/generation"
        params = {
            "limit": limit,
            "order": "created_at",
            "order_direction": "desc"
        }
        
        try:
            # Use requests in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.get(url, headers=headers, params=params, timeout=30)
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            log.error(f"OpenRouter API error for key {api_key[:15]}...: {e}")
            return {"data": []}
    
    def record_usage_to_db(self, client_org_id: str, usage_data: Dict[str, Any]):
        """
        Record background sync usage directly to daily summaries
        This avoids conflicts with real-time live counters
        """
        try:
            from open_webui.models.organization_usage import (
                ClientDailyUsage, ClientUserDailyUsage, ClientModelDailyUsage, get_db
            )
            import time
            from datetime import datetime
            
            # Extract usage details from OpenRouter generation
            model_name = usage_data.get("model", "unknown")
            total_tokens = usage_data.get("total_tokens", 0)
            raw_cost = float(usage_data.get("total_cost", 0.0))
            markup_cost = raw_cost * 1.3  # mAI markup
            provider = usage_data.get("model", "").split("/")[0] if "/" in usage_data.get("model", "") else "unknown"
            
            # Determine the usage date from generation timestamp
            usage_date = date.today()
            created_at = usage_data.get("created_at")
            if created_at:
                try:
                    if created_at.endswith('Z'):
                        gen_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        gen_date = datetime.fromisoformat(created_at)
                    usage_date = gen_date.date()
                except:
                    pass  # Use today's date as fallback
            
            # Record directly to daily summaries to avoid live counter conflicts
            with get_db() as db:
                current_time = int(time.time())
                
                # 1. Update or create client daily usage
                summary_id = f"{client_org_id}_{usage_date.isoformat()}"
                daily_summary = db.query(ClientDailyUsage).filter_by(id=summary_id).first()
                
                if daily_summary:
                    # Update existing summary
                    daily_summary.total_tokens += total_tokens
                    daily_summary.total_requests += 1
                    daily_summary.raw_cost += raw_cost
                    daily_summary.markup_cost += markup_cost
                    daily_summary.updated_at = current_time
                else:
                    # Create new summary
                    daily_summary = ClientDailyUsage(
                        id=summary_id,
                        client_org_id=client_org_id,
                        usage_date=usage_date,
                        total_tokens=total_tokens,
                        total_requests=1,
                        raw_cost=raw_cost,
                        markup_cost=markup_cost,
                        primary_model=model_name,
                        unique_users=1,
                        created_at=current_time,
                        updated_at=current_time
                    )
                    db.add(daily_summary)
                
                # 2. Update background sync user usage
                user_usage_id = f"{client_org_id}:background_sync:{usage_date}"
                user_usage = db.query(ClientUserDailyUsage).filter_by(id=user_usage_id).first()
                
                if user_usage:
                    user_usage.total_tokens += total_tokens
                    user_usage.total_requests += 1
                    user_usage.raw_cost += raw_cost
                    user_usage.markup_cost += markup_cost
                    user_usage.updated_at = current_time
                else:
                    user_usage = ClientUserDailyUsage(
                        id=user_usage_id,
                        client_org_id=client_org_id,
                        user_id="background_sync",
                        usage_date=usage_date,
                        total_tokens=total_tokens,
                        total_requests=1,
                        raw_cost=raw_cost,
                        markup_cost=markup_cost,
                        openrouter_user_id=f"bg_sync_{client_org_id}",
                        created_at=current_time,
                        updated_at=current_time
                    )
                    db.add(user_usage)
                
                db.commit()
                
            log.debug(f"✅ Background sync: {total_tokens} tokens, ${markup_cost:.6f} for {model_name} on {usage_date}")
                
        except Exception as e:
            log.error(f"Background sync database error: {e}")
            # Don't fail silently - this is important for data integrity
    
    async def sync_organization_usage(self, org_id: str, org_name: str, api_key: str) -> Dict[str, Any]:
        """Sync usage for a single organization"""
        try:
            # Fetch recent generations from OpenRouter
            generations_data = await self.get_openrouter_generations(api_key, limit=50)
            generations = generations_data.get("data", [])
            
            synced_count = 0
            cutoff_date = date.today() - timedelta(days=SYNC_DAYS_BACK)
            
            for generation in generations:
                # Check if this generation is recent
                created_at = generation.get("created_at")
                if created_at:
                    try:
                        # Handle different datetime formats
                        if created_at.endswith('Z'):
                            gen_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        else:
                            gen_date = datetime.fromisoformat(created_at)
                        
                        if gen_date.date() >= cutoff_date:
                            # Record this usage
                            usage_data = {
                                "model": generation.get("model", "unknown"),
                                "total_tokens": generation.get("total_tokens", 0),
                                "total_cost": generation.get("total_cost", 0.0)
                            }
                            
                            # Run database operation in thread to avoid blocking
                            loop = asyncio.get_event_loop()
                            await loop.run_in_executor(
                                None, 
                                self.record_usage_to_db,
                                org_id,
                                usage_data
                            )
                            synced_count += 1
                    except (ValueError, TypeError) as e:
                        log.debug(f"Error parsing date {created_at}: {e}")
                        continue
            
            return {
                "organization": org_name,
                "synced_generations": synced_count,
                "status": "success"
            }
            
        except Exception as e:
            log.error(f"Failed to sync usage for {org_name}: {e}")
            return {
                "organization": org_name,
                "error": str(e),
                "status": "failed"
            }
    
    async def sync_all_organizations(self) -> List[Dict[str, Any]]:
        """Sync usage for all active organizations using ORM"""
        try:
            from open_webui.models.organization_usage import ClientOrganizationDB
            
            # Get all active organizations with API keys using ORM
            active_orgs = ClientOrganizationDB.get_all_active_clients()
            orgs = [(org.id, org.name, org.openrouter_api_key) 
                   for org in active_orgs 
                   if org.openrouter_api_key is not None]
            
        except Exception as e:
            log.error(f"Failed to get organizations via ORM: {e}")
            return []
        
        if not orgs:
            log.debug("No active organizations with API keys found")
            return []
        
        # Sync all organizations concurrently
        sync_tasks = [
            self.sync_organization_usage(org_id, org_name, api_key)
            for org_id, org_name, api_key in orgs
        ]
        
        results = await asyncio.gather(*sync_tasks, return_exceptions=True)
        
        # Handle any exceptions in results
        sync_results = []
        for result in results:
            if isinstance(result, Exception):
                sync_results.append({
                    "organization": "unknown",
                    "error": str(result),
                    "status": "failed"
                })
            else:
                sync_results.append(result)
        
        return sync_results

    async def daily_rollover_task(self):
        """
        Perform daily rollover at midnight for all client organizations
        This ensures stale "today" data gets properly archived
        """
        try:
            from open_webui.models.organization_usage import ClientUsageDB
            
            log.info("Starting daily rollover for all client organizations")
            result = ClientUsageDB.perform_daily_rollover_all_clients()
            
            if result["success"]:
                log.info(f"Daily rollover completed: {result['rollovers_performed']} clients processed")
            else:
                log.error(f"Daily rollover failed: {result['error']}")
            
            return result
            
        except Exception as e:
            log.error(f"Daily rollover task failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def calculate_seconds_until_midnight(self) -> int:
        """Calculate seconds until next midnight"""
        now = datetime.now()
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return int((tomorrow - now).total_seconds())

    async def background_sync_loop(self):
        """Main background sync loop with daily rollover scheduler"""
        self.is_running = True
        log.info(f"Starting background usage sync (interval: {SYNC_INTERVAL}s)")
        
        # Schedule first daily rollover
        next_rollover = self.calculate_seconds_until_midnight()
        log.info(f"Next daily rollover scheduled in {next_rollover} seconds")
        
        while self.is_running:
            try:
                # Create tasks for sync and rollover scheduling
                sync_task = asyncio.create_task(self._run_sync_cycle())
                rollover_task = asyncio.create_task(self._schedule_daily_rollover(next_rollover))
                
                # Wait for either task to complete
                done, pending = await asyncio.wait(
                    [sync_task, rollover_task], 
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Cancel pending tasks
                for task in pending:
                    task.cancel()
                
                # Handle completed task
                for task in done:
                    if task == rollover_task:
                        # Rollover completed, schedule next one in 24 hours
                        next_rollover = 24 * 3600  # 24 hours
                        log.info("Daily rollover completed, next scheduled in 24 hours")
                
            except asyncio.CancelledError:
                log.info("Background sync cancelled")
                break
            except Exception as e:
                log.error(f"Error in background sync loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def _run_sync_cycle(self):
        """Run a single sync cycle"""
        while self.is_running:
            try:
                log.debug("Running background usage sync...")
                results = await self.sync_all_organizations()
                
                successful = sum(1 for r in results if r.get("status") == "success")
                total = len(results)
                
                if results:
                    log.info(f"Background sync completed: {successful}/{total} organizations synced")
                    
                    # Log any failures
                    for result in results:
                        if result.get("status") == "failed":
                            log.warning(f"Sync failed for {result.get('organization')}: {result.get('error')}")
                
                # Wait for next sync
                await asyncio.sleep(SYNC_INTERVAL)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Error in sync cycle: {e}")
                await asyncio.sleep(60)

    async def _schedule_daily_rollover(self, seconds_until_midnight: int):
        """Schedule and run daily rollover"""
        await asyncio.sleep(seconds_until_midnight)
        await self.daily_rollover_task()
        
    def stop(self):
        """Stop the background sync service"""
        self.is_running = False

class OrganizationUsageBackgroundSync:
    """Background service for automatic organization usage data synchronization"""
    
    def __init__(self):
        self.is_running = False
        self.sync_task: Optional[asyncio.Task] = None
        self.sync_manager = OpenRouterUsageSync()
    
    async def start_sync_service(self):
        """Start the background sync service"""
        if self.is_running:
            log.info("Background sync service is already running")
            return
        
        log.info("Starting OpenRouter usage background sync service")
        self.is_running = True
        self.sync_task = asyncio.create_task(self.sync_manager.background_sync_loop())
        return self.sync_task
    
    async def stop_sync_service(self):
        """Stop the background sync service"""
        if not self.is_running:
            return
        
        log.info("Stopping OpenRouter usage background sync service")
        self.is_running = False
        self.sync_manager.is_running = False
        
        if self.sync_task and not self.sync_task.done():
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass
    
    async def force_sync(self) -> dict:
        """Force an immediate sync (for admin triggers)"""
        try:
            log.info("Force sync triggered")
            results = await self.sync_manager.sync_all_organizations()
            
            successful = sum(1 for r in results if r.get("status") == "success")
            total = len(results)
            
            return {
                "success": True,
                "message": f"Synced {successful}/{total} organizations",
                "results": results
            }
        except Exception as e:
            log.error(f"Force sync failed: {e}")
            return {"success": False, "message": str(e)}
    
    def get_status(self) -> dict:
        """Get the current status of the background sync service"""
        status = {
            "is_running": self.is_running,
            "sync_enabled": True,
            "sync_interval_seconds": SYNC_INTERVAL,
            "sync_days_back": SYNC_DAYS_BACK,
            "message": "OpenRouter usage sync active"
        }
        
        return status


# Global instance
organization_usage_sync = OrganizationUsageBackgroundSync()


async def init_background_sync():
    """Initialize the background sync service"""
    try:
        await organization_usage_sync.start_sync_service()
        log.info("OpenRouter usage background sync initialized successfully")
    except Exception as e:
        log.error(f"Failed to initialize background sync: {e}")


async def shutdown_background_sync():
    """Shutdown the background sync service"""
    try:
        await organization_usage_sync.stop_sync_service()
        log.info("Background sync service shut down successfully")
    except Exception as e:
        log.error(f"Error shutting down background sync: {e}")

async def manual_sync() -> List[Dict[str, Any]]:
    """Manually trigger a usage sync"""
    return await organization_usage_sync.sync_manager.sync_all_organizations()

def is_sync_running() -> bool:
    """Check if background sync is running"""
    return organization_usage_sync.is_running