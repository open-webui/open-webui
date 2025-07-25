import asyncio
import logging
import hashlib
import time
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
MAX_CONCURRENT_SYNCS = 5  # Limit concurrent organization syncs
API_RETRY_ATTEMPTS = 3  # Maximum retry attempts for API calls
RETRY_BACKOFF_FACTOR = 2  # Exponential backoff multiplier

# Using ORM instead of direct database access

class OpenRouterUsageSync:
    """OpenRouter usage synchronization manager"""
    
    def __init__(self):
        self.is_running = False
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_SYNCS)
        self.api_call_count = 0
        self.last_api_reset = time.time()
        
    async def get_openrouter_generations(self, api_key: str, limit: int = 50, retry_attempt: int = 0) -> Dict[str, Any]:
        """Fetch generation data from OpenRouter API with retry logic"""
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
            # Rate limiting check
            await self._enforce_rate_limit()
            
            # Use requests in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.get(url, headers=headers, params=params, timeout=30)
            )
            response.raise_for_status()
            self.api_call_count += 1
            return response.json()
            
        except requests.RequestException as e:
            if retry_attempt < API_RETRY_ATTEMPTS:
                backoff_delay = RETRY_BACKOFF_FACTOR ** retry_attempt
                log.warning(f"API error for key {api_key[:15]}..., retrying in {backoff_delay}s: {e}")
                await asyncio.sleep(backoff_delay)
                return await self.get_openrouter_generations(api_key, limit, retry_attempt + 1)
            else:
                log.error(f"OpenRouter API error after {API_RETRY_ATTEMPTS} attempts for key {api_key[:15]}...: {e}")
                return {"data": []}
    
    async def _enforce_rate_limit(self):
        """Enforce API rate limiting (conservative approach)"""
        current_time = time.time()
        
        # Reset counter every hour
        if current_time - self.last_api_reset > 3600:
            self.api_call_count = 0
            self.last_api_reset = current_time
        
        # Conservative limit: max 100 calls per hour (well under most API limits)
        if self.api_call_count >= 100:
            sleep_time = 3600 - (current_time - self.last_api_reset)
            if sleep_time > 0:
                log.warning(f"Rate limit reached, sleeping for {sleep_time:.0f} seconds")
                await asyncio.sleep(sleep_time)
                self.api_call_count = 0
                self.last_api_reset = time.time()

    def record_usage_batch_to_db(self, client_org_id: str, generations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Record multiple generations in a single transaction with deduplication
        Returns stats about processed vs skipped generations
        """
        try:
            from open_webui.models.organization_usage import (
                ClientDailyUsage, ClientUserDailyUsage, ClientModelDailyUsage, 
                ProcessedGenerationDB, get_db
            )
            import time
            from datetime import datetime
            
            processed_count = 0
            skipped_count = 0
            total_tokens = 0
            total_cost = 0.0
            
            # Group generations by date for efficient processing
            generations_by_date = {}
            
            for generation in generations:
                # Generate unique generation ID (OpenRouter should provide this)
                generation_id = generation.get("id")
                if not generation_id:
                    # Fallback: create hash-based ID from generation data
                    gen_hash = hashlib.md5(
                        f"{generation.get('created_at', '')}{generation.get('model', '')}{generation.get('total_tokens', 0)}{generation.get('total_cost', 0)}".encode()
                    ).hexdigest()
                    generation_id = f"bg_sync_{gen_hash}"
                
                # Check if already processed
                if ProcessedGenerationDB.is_generation_processed(generation_id, client_org_id):
                    skipped_count += 1
                    continue
                
                # Parse generation date
                usage_date = date.today()
                created_at = generation.get("created_at")
                if created_at:
                    try:
                        if created_at.endswith('Z'):
                            gen_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        else:
                            gen_date = datetime.fromisoformat(created_at)
                        usage_date = gen_date.date()
                    except:
                        pass  # Use today's date as fallback
                
                # Group by date
                if usage_date not in generations_by_date:
                    generations_by_date[usage_date] = []
                
                # Extract generation details
                gen_tokens = generation.get("total_tokens", 0)
                gen_raw_cost = float(generation.get("total_cost", 0.0))
                gen_markup_cost = gen_raw_cost * 1.3  # mAI markup
                model_name = generation.get("model", "unknown")
                provider = model_name.split("/")[0] if "/" in model_name else "unknown"
                
                generations_by_date[usage_date].append({
                    "id": generation_id,
                    "tokens": gen_tokens,
                    "raw_cost": gen_raw_cost,
                    "markup_cost": gen_markup_cost,
                    "model": model_name,
                    "provider": provider
                })
                
                total_tokens += gen_tokens
                total_cost += gen_markup_cost
                processed_count += 1
            
            # Process all generations in a single database transaction
            with get_db() as db:
                current_time = int(time.time())
                
                # Process each date group
                for usage_date, date_generations in generations_by_date.items():
                    date_tokens = sum(g["tokens"] for g in date_generations)
                    date_requests = len(date_generations)
                    date_raw_cost = sum(g["raw_cost"] for g in date_generations)
                    date_markup_cost = sum(g["markup_cost"] for g in date_generations)
                    primary_model = date_generations[0]["model"] if date_generations else "unknown"
                    
                    # 1. Update or create client daily usage
                    summary_id = f"{client_org_id}_{usage_date.isoformat()}"
                    daily_summary = db.query(ClientDailyUsage).filter_by(id=summary_id).first()
                    
                    if daily_summary:
                        daily_summary.total_tokens += date_tokens
                        daily_summary.total_requests += date_requests
                        daily_summary.raw_cost += date_raw_cost
                        daily_summary.markup_cost += date_markup_cost
                        daily_summary.updated_at = current_time
                    else:
                        daily_summary = ClientDailyUsage(
                            id=summary_id,
                            client_org_id=client_org_id,
                            usage_date=usage_date,
                            total_tokens=date_tokens,
                            total_requests=date_requests,
                            raw_cost=date_raw_cost,
                            markup_cost=date_markup_cost,
                            primary_model=primary_model,
                            unique_users=1,
                            created_at=current_time,
                            updated_at=current_time
                        )
                        db.add(daily_summary)
                    
                    # 2. Update background sync user usage
                    user_usage_id = f"{client_org_id}:background_sync:{usage_date}"
                    user_usage = db.query(ClientUserDailyUsage).filter_by(id=user_usage_id).first()
                    
                    if user_usage:
                        user_usage.total_tokens += date_tokens
                        user_usage.total_requests += date_requests
                        user_usage.raw_cost += date_raw_cost
                        user_usage.markup_cost += date_markup_cost
                        user_usage.updated_at = current_time
                    else:
                        user_usage = ClientUserDailyUsage(
                            id=user_usage_id,
                            client_org_id=client_org_id,
                            user_id="background_sync",
                            usage_date=usage_date,
                            total_tokens=date_tokens,
                            total_requests=date_requests,
                            raw_cost=date_raw_cost,
                            markup_cost=date_markup_cost,
                            openrouter_user_id=f"bg_sync_{client_org_id}",
                            created_at=current_time,
                            updated_at=current_time
                        )
                        db.add(user_usage)
                    
                    # 3. Mark all generations as processed
                    for generation in date_generations:
                        ProcessedGenerationDB.mark_generation_processed(
                            generation["id"], client_org_id, usage_date, 
                            generation["raw_cost"], generation["tokens"]
                        )
                
                db.commit()
            
            result = {
                "processed": processed_count,
                "skipped": skipped_count,
                "total_tokens": total_tokens,
                "total_cost": total_cost
            }
            
            if processed_count > 0:
                log.debug(f"✅ Background sync batch: {processed_count} generations, {total_tokens} tokens, ${total_cost:.6f} (skipped {skipped_count} duplicates)")
            
            return result
                
        except Exception as e:
            log.error(f"Background sync batch database error: {e}")
            return {
                "processed": 0,
                "skipped": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "error": str(e)
            }
    
    async def sync_organization_usage(self, org_id: str, org_name: str, api_key: str) -> Dict[str, Any]:
        """Sync usage for a single organization with rate limiting and batch processing"""
        async with self.semaphore:  # Rate limiting via semaphore
            try:
                # Fetch recent generations from OpenRouter
                generations_data = await self.get_openrouter_generations(api_key, limit=50)
                generations = generations_data.get("data", [])
                
                if not generations:
                    return {
                        "organization": org_name,
                        "synced_generations": 0,
                        "skipped_generations": 0,
                        "status": "success",
                        "message": "No generations found"
                    }
                
                # Filter generations by date
                cutoff_date = date.today() - timedelta(days=SYNC_DAYS_BACK)
                recent_generations = []
                
                for generation in generations:
                    created_at = generation.get("created_at")
                    if created_at:
                        try:
                            # Handle different datetime formats
                            if created_at.endswith('Z'):
                                gen_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            else:
                                gen_date = datetime.fromisoformat(created_at)
                            
                            if gen_date.date() >= cutoff_date:
                                recent_generations.append(generation)
                        except (ValueError, TypeError) as e:
                            log.debug(f"Error parsing date {created_at}: {e}")
                            continue
                
                if not recent_generations:
                    return {
                        "organization": org_name,
                        "synced_generations": 0,
                        "skipped_generations": 0,
                        "status": "success",
                        "message": "No recent generations found"
                    }
                
                # Process all recent generations in a single batch
                loop = asyncio.get_event_loop()
                batch_result = await loop.run_in_executor(
                    None,
                    self.record_usage_batch_to_db,
                    org_id,
                    recent_generations
                )
                
                return {
                    "organization": org_name,
                    "synced_generations": batch_result.get("processed", 0),
                    "skipped_generations": batch_result.get("skipped", 0),
                    "total_tokens": batch_result.get("total_tokens", 0),
                    "total_cost": batch_result.get("total_cost", 0.0),
                    "status": "success" if "error" not in batch_result else "partial_success",
                    "error": batch_result.get("error")
                }
                
            except Exception as e:
                log.error(f"Failed to sync usage for {org_name}: {e}")
                return {
                    "organization": org_name,
                    "error": str(e),
                    "status": "failed"
                }
    
    async def sync_all_organizations(self) -> List[Dict[str, Any]]:
        """Sync usage for all active organizations with controlled concurrency"""
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
        
        log.info(f"Starting sync for {len(orgs)} organizations (max {MAX_CONCURRENT_SYNCS} concurrent)")
        
        # Sync all organizations with controlled concurrency via semaphore  
        sync_tasks = [
            self.sync_organization_usage(org_id, org_name, api_key)
            for org_id, org_name, api_key in orgs
        ]
        
        results = await asyncio.gather(*sync_tasks, return_exceptions=True)
        
        # Aggregate results and statistics
        sync_results = []
        total_synced = 0
        total_skipped = 0
        total_tokens = 0
        total_cost = 0.0
        failed_count = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                org_name = orgs[i][1] if i < len(orgs) else "unknown"
                sync_results.append({
                    "organization": org_name,
                    "error": str(result),
                    "status": "failed"
                })
                failed_count += 1
            else:
                sync_results.append(result)
                total_synced += result.get("synced_generations", 0)
                total_skipped += result.get("skipped_generations", 0)
                total_tokens += result.get("total_tokens", 0)
                total_cost += result.get("total_cost", 0.0)
        
        # Log summary statistics
        success_count = len(orgs) - failed_count
        log.info(f"Sync completed: {success_count}/{len(orgs)} orgs successful, "
                f"{total_synced} generations processed, {total_skipped} duplicates skipped, "
                f"{total_tokens} tokens, ${total_cost:.4f} total cost")
        
        if failed_count > 0:
            log.warning(f"{failed_count} organizations failed to sync")
        
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
        """Main background sync loop with separated rollover scheduling"""
        self.is_running = True
        log.info(f"Starting background usage sync (interval: {SYNC_INTERVAL}s)")
        
        # Start the daily rollover scheduler as a separate task
        rollover_scheduler_task = asyncio.create_task(self._daily_rollover_scheduler())
        
        # Start the main sync cycle
        sync_cycle_task = asyncio.create_task(self._run_sync_cycle())
        
        try:
            # Wait for either task to complete (they should run indefinitely)
            done, pending = await asyncio.wait(
                [sync_cycle_task, rollover_scheduler_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # If either task completes unexpectedly, cancel the other and restart
            for task in pending:
                task.cancel()
                
            # Log which task completed
            for task in done:
                if task == sync_cycle_task:
                    log.warning("Sync cycle task completed unexpectedly")
                elif task == rollover_scheduler_task:
                    log.warning("Rollover scheduler task completed unexpectedly")
                    
        except asyncio.CancelledError:
            log.info("Background sync cancelled")
            # Clean up tasks
            sync_cycle_task.cancel()
            rollover_scheduler_task.cancel()
            
            try:
                await sync_cycle_task
            except asyncio.CancelledError:
                pass
                
            try:
                await rollover_scheduler_task
            except asyncio.CancelledError:
                pass
                
        except Exception as e:
            log.error(f"Error in background sync loop: {e}")
            # Clean up and retry
            sync_cycle_task.cancel()
            rollover_scheduler_task.cancel()
            await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def _daily_rollover_scheduler(self):
        """Separate scheduler for daily rollover tasks"""
        while self.is_running:
            try:
                # Calculate time until next midnight
                seconds_until_midnight = await self.calculate_seconds_until_midnight()
                log.info(f"Next daily rollover scheduled in {seconds_until_midnight} seconds")
                
                # Wait until midnight
                await asyncio.sleep(seconds_until_midnight)
                
                if self.is_running:  # Check if still running after sleep
                    # Perform daily rollover
                    log.info("Performing scheduled daily rollover")
                    await self.daily_rollover_task()
                    
                    # Also clean up old processed generations
                    try:
                        from open_webui.models.organization_usage import ProcessedGenerationDB
                        cleaned = ProcessedGenerationDB.cleanup_old_processed_generations(90)
                        log.info(f"Cleaned up {cleaned} old processed generation records")
                    except Exception as e:
                        log.error(f"Error cleaning up processed generations: {e}")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Error in rollover scheduler: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour before retrying

    async def _run_sync_cycle(self):
        """Run continuous sync cycles"""
        while self.is_running:
            try:
                log.debug("Running background usage sync...")
                results = await self.sync_all_organizations()
                
                successful = sum(1 for r in results if r.get("status") in ["success", "partial_success"])
                total = len(results)
                
                if results:
                    log.info(f"Background sync completed: {successful}/{total} organizations synced")
                    
                    # Log any failures
                    for result in results:
                        if result.get("status") == "failed":
                            log.warning(f"Sync failed for {result.get('organization')}: {result.get('error')}")
                        elif result.get("status") == "partial_success":
                            log.warning(f"Partial sync for {result.get('organization')}: {result.get('error')}")
                
                # Wait for next sync
                await asyncio.sleep(SYNC_INTERVAL)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Error in sync cycle: {e}")
                await asyncio.sleep(60)

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