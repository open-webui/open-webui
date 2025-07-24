import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.organization_usage import OrganizationSettingsDB
from open_webui.utils.openrouter_org import openrouter_usage_service

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("BACKGROUND_SYNC", logging.INFO))

class OrganizationUsageBackgroundSync:
    """Background service for automatic organization usage data synchronization"""
    
    def __init__(self):
        self.is_running = False
        self.sync_task: Optional[asyncio.Task] = None
    
    async def start_sync_service(self):
        """Start the background sync service"""
        if self.is_running:
            log.info("Background sync service is already running")
            return
        
        log.info("Starting organization usage background sync service")
        self.is_running = True
        self.sync_task = asyncio.create_task(self._sync_loop())
        return self.sync_task
    
    async def stop_sync_service(self):
        """Stop the background sync service"""
        if not self.is_running:
            return
        
        log.info("Stopping organization usage background sync service")
        self.is_running = False
        
        if self.sync_task and not self.sync_task.done():
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass
    
    async def _sync_loop(self):
        """Main sync loop that runs continuously"""
        while self.is_running:
            try:
                # Get sync settings
                settings = OrganizationSettingsDB.get_settings()
                
                if not settings or not settings.sync_enabled:
                    log.debug("Organization usage sync is disabled")
                    await asyncio.sleep(3600)  # Check again in 1 hour
                    continue
                
                sync_interval_seconds = settings.sync_interval_hours * 3600
                
                # Check if it's time to sync
                should_sync = False
                if settings.last_sync_at is None:
                    should_sync = True
                    log.info("No previous sync found, performing initial sync")
                else:
                    last_sync = datetime.fromtimestamp(settings.last_sync_at)
                    time_since_sync = datetime.now() - last_sync
                    
                    if time_since_sync.total_seconds() >= sync_interval_seconds:
                        should_sync = True
                        log.info(f"Sync interval reached ({settings.sync_interval_hours}h), performing sync")
                
                if should_sync:
                    await self._perform_sync()
                else:
                    log.debug(f"Next sync in {sync_interval_seconds - (datetime.now() - datetime.fromtimestamp(settings.last_sync_at)).total_seconds():.0f} seconds")
                
                # Wait before next check (check every 10 minutes)
                await asyncio.sleep(600)
                
            except asyncio.CancelledError:
                log.info("Background sync service cancelled")
                break
            except Exception as e:
                log.error(f"Error in background sync loop: {e}")
                # Wait 5 minutes before retrying on error
                await asyncio.sleep(300)
    
    async def _perform_sync(self):
        """Perform the actual usage data synchronization"""
        try:
            log.info("Starting organization usage data sync")
            
            # Sync last 2 days to ensure we don't miss any data
            result = await openrouter_usage_service.manual_sync(days_back=2)
            
            if result.get("success"):
                stats = result.get("stats", {})
                log.info(
                    f"Sync completed successfully: "
                    f"processed {stats.get('processed', 0)}/{stats.get('total_records', 0)} records, "
                    f"errors: {stats.get('errors', 0)}"
                )
            else:
                log.error(f"Sync failed: {result.get('message', 'Unknown error')}")
                
        except Exception as e:
            log.error(f"Failed to perform background sync: {e}")
    
    async def force_sync(self) -> dict:
        """Force an immediate sync (for admin triggers)"""
        try:
            log.info("Force sync triggered")
            result = await openrouter_usage_service.manual_sync(days_back=7)
            return result
        except Exception as e:
            log.error(f"Force sync failed: {e}")
            return {"success": False, "message": str(e)}
    
    def get_status(self) -> dict:
        """Get the current status of the background sync service"""
        settings = OrganizationSettingsDB.get_settings()
        
        status = {
            "is_running": self.is_running,
            "sync_enabled": settings.sync_enabled if settings else False,
            "sync_interval_hours": settings.sync_interval_hours if settings else 1,
            "last_sync_at": settings.last_sync_at if settings else None,
        }
        
        if settings and settings.last_sync_at:
            last_sync = datetime.fromtimestamp(settings.last_sync_at)
            status["last_sync_human"] = last_sync.strftime("%Y-%m-%d %H:%M:%S")
            status["hours_since_last_sync"] = (datetime.now() - last_sync).total_seconds() / 3600
        
        return status


# Global instance
organization_usage_sync = OrganizationUsageBackgroundSync()


async def init_background_sync():
    """Initialize the background sync service"""
    try:
        # Check if organization settings exist and sync is enabled
        settings = OrganizationSettingsDB.get_settings()
        if settings and settings.sync_enabled and settings.openrouter_api_key:
            log.info("Initializing organization usage background sync")
            await organization_usage_sync.start_sync_service()
        else:
            log.info("Organization usage sync not configured or disabled")
    except Exception as e:
        log.error(f"Failed to initialize background sync: {e}")


async def shutdown_background_sync():
    """Shutdown the background sync service"""
    try:
        await organization_usage_sync.stop_sync_service()
        log.info("Background sync service shut down successfully")
    except Exception as e:
        log.error(f"Error shutting down background sync: {e}")