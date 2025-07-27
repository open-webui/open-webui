"""
Repository for system settings and metadata
"""

from typing import Dict, Any, Optional
from datetime import datetime, date
import logging

from ..utils.async_db import AsyncDatabase

log = logging.getLogger(__name__)


class SystemRepository:
    """Repository for system settings and batch metadata"""
    
    def __init__(self, db: AsyncDatabase):
        self.db = db
        
    async def get_last_batch_run(self) -> Optional[datetime]:
        """Get the timestamp of the last successful batch run"""
        # This could be stored in a batch_runs table
        # For now, we'll use a simple approach
        query = """
            SELECT MAX(created_at) 
            FROM client_daily_usage 
            WHERE created_at IS NOT NULL
        """
        result = await self.db.fetchone(query)
        if result and result[0]:
            return datetime.fromtimestamp(result[0])
        return None
        
    async def record_batch_run(self, batch_result: Dict[str, Any]) -> None:
        """Record a batch run for audit purposes"""
        # This could be extended to store in a batch_runs table
        # with detailed metrics and results
        log.info(f"Batch run recorded: {batch_result.get('success', False)}")
        
    async def get_system_setting(self, key: str) -> Optional[Any]:
        """Get a system setting value"""
        # Could be extended to use a settings table
        settings = {
            "retention_days": 60,
            "batch_hour": 0,
            "fallback_usd_pln_rate": 4.0
        }
        return settings.get(key)
        
    async def update_system_setting(self, key: str, value: Any) -> None:
        """Update a system setting"""
        # Could be extended to use a settings table
        log.info(f"System setting updated: {key} = {value}")