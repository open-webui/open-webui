"""
Background sync utilities for OpenRouter usage data synchronization
"""

import asyncio
import logging
from typing import Optional

log = logging.getLogger(__name__)

class OpenRouterUsageSync:
    """Handles background synchronization of usage data with OpenRouter API"""
    
    def __init__(self):
        self.is_running = False
        self.sync_task: Optional[asyncio.Task] = None
    
    async def start_sync(self):
        """Start background sync process"""
        if self.is_running:
            log.warning("Background sync already running")
            return
        
        self.is_running = True
        log.info("Background sync started")
        # TODO: Implement actual sync logic
    
    async def stop_sync(self):
        """Stop background sync process"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.sync_task and not self.sync_task.done():
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass
        
        log.info("Background sync stopped")

# Global sync manager instance
_sync_manager: Optional[OpenRouterUsageSync] = None

async def init_background_sync():
    """Initialize background sync on application startup"""
    global _sync_manager
    
    if _sync_manager is None:
        _sync_manager = OpenRouterUsageSync()
    
    try:
        await _sync_manager.start_sync()
        log.info("✅ Background sync initialized successfully")
    except Exception as e:
        log.error(f"Failed to initialize background sync: {e}")

async def shutdown_background_sync():
    """Shutdown background sync on application teardown"""
    global _sync_manager
    
    if _sync_manager:
        try:
            await _sync_manager.stop_sync()
            log.info("✅ Background sync shutdown successfully")
        except Exception as e:
            log.error(f"Failed to shutdown background sync: {e}")
        finally:
            _sync_manager = None