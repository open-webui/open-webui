import asyncio
import logging
from typing import Optional

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("WEBHOOK", logging.INFO))


class WebhookScheduler:
    """Background scheduler for webhook retry processing"""
    
    def __init__(self, retry_interval_minutes: int = 2):
        self.retry_interval_minutes = retry_interval_minutes
        self.running = False
        self.task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the background webhook retry scheduler"""
        if self.running:
            log.warning("Webhook scheduler is already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._run_scheduler())
        log.info(f"Started webhook retry scheduler (interval: {self.retry_interval_minutes} minutes)")
    
    async def stop(self):
        """Stop the background webhook retry scheduler"""
        if not self.running:
            return
        
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        log.info("Stopped webhook retry scheduler")
    
    async def _run_scheduler(self):
        """Main scheduler loop"""
        from open_webui.utils.webhook import process_webhook_retries
        
        while self.running:
            try:
                log.debug("Running webhook retry processing...")
                await process_webhook_retries()
                
                # Wait for the next interval
                await asyncio.sleep(self.retry_interval_minutes * 60)
                
            except asyncio.CancelledError:
                log.info("Webhook scheduler cancelled")
                break
            except Exception as e:
                log.exception(f"Error in webhook scheduler: {e}")
                # Continue running even if there's an error
                await asyncio.sleep(60)  # Wait 1 minute before retrying


# Global scheduler instance
webhook_scheduler = WebhookScheduler()


async def start_webhook_scheduler():
    """Start the global webhook scheduler"""
    await webhook_scheduler.start()


async def stop_webhook_scheduler():
    """Stop the global webhook scheduler"""
    await webhook_scheduler.stop()