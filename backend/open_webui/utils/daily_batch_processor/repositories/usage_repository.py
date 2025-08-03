"""
Repository for usage data access with async operations
"""

from typing import List, Tuple, Optional, Dict, Any
from datetime import date
import logging

from ..utils.async_db import AsyncDatabase

log = logging.getLogger(__name__)


class UsageRepository:
    """Async repository for usage data operations"""
    
    def __init__(self, db: AsyncDatabase):
        self.db = db
        
    async def get_active_clients(self) -> List[Tuple[int, str, float]]:
        """Get all active client organizations"""
        query = "SELECT id, name, markup_rate FROM client_organizations WHERE is_active = 1"
        return await self.db.fetchall(query)
        
    async def get_client_daily_usage(
        self, 
        client_id: int, 
        usage_date: date
    ) -> Optional[Tuple[int, int, float, float, str]]:
        """Get daily usage for a specific client and date"""
        query = """
            SELECT total_tokens, total_requests, raw_cost, markup_cost, primary_model
            FROM client_daily_usage 
            WHERE client_org_id = ? AND usage_date = ?
        """
        return await self.db.fetchone(query, (client_id, usage_date))
        
    async def update_markup_cost(
        self, 
        client_id: int, 
        usage_date: date, 
        new_markup_cost: float,
        timestamp: int
    ) -> None:
        """Update markup cost for a client's daily usage"""
        query = """
            UPDATE client_daily_usage 
            SET markup_cost = ?, updated_at = ?
            WHERE client_org_id = ? AND usage_date = ?
        """
        await self.db.execute(query, (new_markup_cost, timestamp, client_id, usage_date))
        
    async def get_monthly_usage_summary(
        self, 
        client_id: int, 
        start_date: date, 
        end_date: date
    ) -> Optional[Tuple]:
        """Get monthly usage summary for a client"""
        query = """
            SELECT 
                COUNT(*) as days_with_usage,
                SUM(total_tokens) as total_tokens,
                SUM(total_requests) as total_requests,
                SUM(raw_cost) as total_raw_cost,
                SUM(markup_cost) as total_markup_cost,
                AVG(total_tokens) as avg_daily_tokens,
                MAX(total_tokens) as max_daily_tokens,
                MAX(usage_date) as last_usage_date
            FROM client_daily_usage 
            WHERE client_org_id = ? 
            AND usage_date >= ? 
            AND usage_date <= ?
        """
        return await self.db.fetchone(query, (client_id, start_date, end_date))
        
    async def get_most_used_model(
        self, 
        client_id: int, 
        start_date: date, 
        end_date: date
    ) -> Optional[str]:
        """Get the most used model for a client in a date range"""
        query = """
            SELECT primary_model, SUM(total_tokens) as model_tokens
            FROM client_daily_usage 
            WHERE client_org_id = ? 
            AND usage_date >= ? 
            AND usage_date <= ?
            AND primary_model IS NOT NULL
            GROUP BY primary_model
            ORDER BY model_tokens DESC
            LIMIT 1
        """
        result = await self.db.fetchone(query, (client_id, start_date, end_date))
        return result[0] if result else None
        
    async def batch_update_markup_costs(
        self, 
        updates: List[Tuple[float, int, int, date]]
    ) -> None:
        """Batch update markup costs for multiple records"""
        query = """
            UPDATE client_daily_usage 
            SET markup_cost = ?, updated_at = ?
            WHERE client_org_id = ? AND usage_date = ?
        """
        await self.db.executemany(query, updates)