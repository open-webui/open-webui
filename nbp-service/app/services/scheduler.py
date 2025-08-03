"""
Background scheduler for periodic rate updates
"""
import asyncio
import logging
from datetime import datetime, time
from typing import Optional

from ..config import settings

logger = logging.getLogger(__name__)


class RateUpdateScheduler:
    """Scheduler for periodic exchange rate updates"""
    
    def __init__(self, nbp_client, cache_service):
        self.nbp_client = nbp_client
        self.cache_service = cache_service
        self.running = False
        self.task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the scheduler"""
        if self.running:
            return
        
        self.running = True
        self.task = asyncio.create_task(self._run())
        logger.info(f"Rate update scheduler started (interval: {settings.fetch_interval}s)")
    
    async def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Rate update scheduler stopped")
    
    async def _run(self):
        """Main scheduler loop"""
        while self.running:
            try:
                # Fetch current rate
                if not settings.mock_mode:
                    await self._update_rate()
                
                # Wait for next update
                await asyncio.sleep(settings.fetch_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in rate update scheduler: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def _update_rate(self):
        """Update the current exchange rate"""
        try:
            # Fetch current rate
            rate = await self.nbp_client.get_rate()
            logger.info(f"Updated USD/PLN rate: {rate.rate} (source: {rate.source})")
            
            # Also pre-fetch rate for today if different
            today = datetime.now().strftime("%Y-%m-%d")
            if rate.date != today:
                today_rate = await self.nbp_client.get_rate(today)
                logger.info(f"Pre-fetched today's rate: {today_rate.rate}")
                
        except Exception as e:
            logger.error(f"Failed to update exchange rate: {e}")
    
    async def update_daily_rate_at_time(self, hour: int = 8, minute: int = 0):
        """
        Update rate at a specific time each day
        Useful for ensuring fresh rates before daily batch processing
        """
        while self.running:
            try:
                now = datetime.now()
                target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # If target time has passed today, schedule for tomorrow
                if now >= target_time:
                    target_time = target_time.replace(day=target_time.day + 1)
                
                # Calculate seconds until target time
                wait_seconds = (target_time - now).total_seconds()
                
                logger.info(f"Next daily rate update scheduled at {target_time}")
                await asyncio.sleep(wait_seconds)
                
                if self.running and not settings.mock_mode:
                    await self._update_rate()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in daily rate scheduler: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour on error