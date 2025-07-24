import asyncio
import logging
import sqlite3
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
SYNC_DAYS_BACK = 1   # Sync last 1 day of data

# Database path
DB_PATH = f"{DATA_DIR}/webui.db"

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
        
        url = "https://openrouter.ai/api/v1/generations"
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
        """Record usage data to mAI database"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            today = date.today()
            timestamp = int(datetime.now().timestamp())
            
            # Extract usage details
            model_name = usage_data.get("model", "unknown")
            total_tokens = usage_data.get("total_tokens", 0)
            raw_cost = float(usage_data.get("total_cost", 0.0))
            markup_cost = raw_cost * 1.3  # mAI markup
            
            # Update live counters using INSERT OR REPLACE
            cursor.execute("""
                INSERT OR REPLACE INTO client_live_counters 
                (client_org_id, current_date, today_tokens, today_requests, 
                 today_raw_cost, today_markup_cost, last_updated)
                VALUES (
                    ?, ?, 
                    COALESCE((SELECT today_tokens FROM client_live_counters 
                             WHERE client_org_id = ? AND current_date = ?), 0) + ?,
                    COALESCE((SELECT today_requests FROM client_live_counters 
                             WHERE client_org_id = ? AND current_date = ?), 0) + 1,
                    COALESCE((SELECT today_raw_cost FROM client_live_counters 
                             WHERE client_org_id = ? AND current_date = ?), 0.0) + ?,
                    COALESCE((SELECT today_markup_cost FROM client_live_counters 
                             WHERE client_org_id = ? AND current_date = ?), 0.0) + ?,
                    ?
                )
            """, (
                client_org_id, today,
                client_org_id, today, total_tokens,
                client_org_id, today,
                client_org_id, today, raw_cost,
                client_org_id, today, markup_cost,
                timestamp
            ))
            
            conn.commit()
            log.debug(f"✅ Recorded {total_tokens} tokens, ${markup_cost:.6f} for {model_name}")
            
        except Exception as e:
            log.error(f"Database error: {e}")
            conn.rollback()
        finally:
            conn.close()
    
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
        """Sync usage for all active organizations"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id, name, openrouter_api_key 
                FROM client_organizations 
                WHERE is_active = 1 AND openrouter_api_key IS NOT NULL
            """)
            orgs = cursor.fetchall()
        except Exception as e:
            log.error(f"Failed to get organizations: {e}")
            return []
        finally:
            conn.close()
        
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
    
    async def background_sync_loop(self):
        """Main background sync loop"""
        self.is_running = True
        log.info(f"Starting background usage sync (interval: {SYNC_INTERVAL}s)")
        
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
                log.info("Background sync cancelled")
                break
            except Exception as e:
                log.error(f"Error in background sync loop: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(60)
        
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