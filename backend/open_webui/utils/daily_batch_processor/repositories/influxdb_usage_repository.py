"""
InfluxDB-First Usage Repository - Reads raw data from InfluxDB, writes summaries to SQLite
Part of the InfluxDB-First architecture refactoring
"""

from typing import List, Tuple, Optional, Dict, Any
from datetime import date, datetime, timedelta, timezone
import logging

from ..utils.async_db import AsyncDatabase
from open_webui.usage_tracking.services.influxdb_first_service import influxdb_first_service

log = logging.getLogger(__name__)


class InfluxDBUsageRepository:
    """
    InfluxDB-First repository for usage data operations
    
    Architecture:
    - Reads raw usage data from InfluxDB
    - Writes daily summaries to SQLite
    - Maintains existing SQLite schema for aggregated data
    """
    
    def __init__(self, db: AsyncDatabase):
        self.db = db
        
    async def get_active_clients(self) -> List[Tuple[int, str, float]]:
        """Get all active client organizations from SQLite"""
        query = "SELECT id, name, markup_rate FROM client_organizations WHERE is_active = 1"
        return await self.db.fetchall(query)
    
    async def get_raw_usage_from_influxdb(
        self, 
        client_org_id: str,
        usage_date: date
    ) -> List[Dict[str, Any]]:
        """
        Get raw usage data from InfluxDB for a specific client and date
        
        Args:
            client_org_id: Client organization ID
            usage_date: Date to retrieve data for
            
        Returns:
            List of raw usage records from InfluxDB
        """
        # Calculate time range for the specific date
        start_time = datetime.combine(usage_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_time = start_time + timedelta(days=1)
        
        try:
            # Query InfluxDB for raw usage data
            usage_data = await influxdb_first_service.query_usage_data(
                client_org_id=str(client_org_id),
                start_time=start_time,
                end_time=end_time
            )
            
            log.debug(f"Retrieved {len(usage_data)} raw usage records from InfluxDB for client {client_org_id} on {usage_date}")
            return usage_data
            
        except Exception as e:
            log.error(f"Failed to retrieve raw usage from InfluxDB for client {client_org_id}: {e}")
            return []
    
    async def aggregate_influxdb_data(
        self, 
        raw_usage_data: List[Dict[str, Any]], 
        markup_rate: float
    ) -> Optional[Dict[str, Any]]:
        """
        Aggregate raw InfluxDB usage data into daily summary
        
        Args:
            raw_usage_data: List of raw usage records from InfluxDB
            markup_rate: Client's markup rate
            
        Returns:
            Aggregated daily usage data
        """
        if not raw_usage_data:
            return None
        
        # Aggregate the data
        total_tokens = sum(record.get("total_tokens", 0) for record in raw_usage_data)
        total_input_tokens = sum(record.get("input_tokens", 0) for record in raw_usage_data)
        total_output_tokens = sum(record.get("output_tokens", 0) for record in raw_usage_data)
        total_requests = len(raw_usage_data)
        raw_cost = sum(record.get("cost_usd", 0.0) for record in raw_usage_data)
        markup_cost = raw_cost * markup_rate
        
        # Find primary model (most used by tokens)
        model_usage = {}
        for record in raw_usage_data:
            model = record.get("model", "unknown")
            tokens = record.get("total_tokens", 0)
            model_usage[model] = model_usage.get(model, 0) + tokens
        
        primary_model = max(model_usage.items(), key=lambda x: x[1])[0] if model_usage else "unknown"
        
        return {
            "total_tokens": total_tokens,
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "total_requests": total_requests,
            "raw_cost": raw_cost,
            "markup_cost": markup_cost,
            "primary_model": primary_model
        }
    
    async def upsert_daily_summary(
        self, 
        client_id: int, 
        usage_date: date, 
        aggregated_data: Dict[str, Any]
    ) -> None:
        """
        Insert or update daily usage summary in SQLite
        
        Args:
            client_id: Client organization ID
            usage_date: Usage date
            aggregated_data: Aggregated usage data from InfluxDB
        """
        try:
            # Check if record already exists
            existing_query = """
                SELECT id FROM client_daily_usage 
                WHERE client_org_id = ? AND usage_date = ?
            """
            existing = await self.db.fetchone(existing_query, (client_id, usage_date))
            
            timestamp = int(datetime.now().timestamp())
            
            if existing:
                # Update existing record
                update_query = """
                    UPDATE client_daily_usage 
                    SET total_tokens = ?, input_tokens = ?, output_tokens = ?, 
                        total_requests = ?, raw_cost = ?, markup_cost = ?, 
                        primary_model = ?, updated_at = ?, data_source = ?
                    WHERE client_org_id = ? AND usage_date = ?
                """
                await self.db.execute(update_query, (
                    aggregated_data["total_tokens"],
                    aggregated_data["input_tokens"],
                    aggregated_data["output_tokens"],
                    aggregated_data["total_requests"],
                    aggregated_data["raw_cost"],
                    aggregated_data["markup_cost"],
                    aggregated_data["primary_model"],
                    timestamp,
                    "influxdb_first",
                    client_id,
                    usage_date
                ))
                log.debug(f"Updated daily summary for client {client_id} on {usage_date}")
            else:
                # Insert new record
                insert_query = """
                    INSERT INTO client_daily_usage 
                    (client_org_id, usage_date, total_tokens, input_tokens, output_tokens, 
                     total_requests, raw_cost, markup_cost, primary_model, 
                     created_at, updated_at, data_source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                await self.db.execute(insert_query, (
                    client_id,
                    usage_date,
                    aggregated_data["total_tokens"],
                    aggregated_data["input_tokens"],
                    aggregated_data["output_tokens"],
                    aggregated_data["total_requests"],
                    aggregated_data["raw_cost"],
                    aggregated_data["markup_cost"],
                    aggregated_data["primary_model"],
                    timestamp,
                    timestamp,
                    "influxdb_first"
                ))
                log.debug(f"Inserted daily summary for client {client_id} on {usage_date}")
                
        except Exception as e:
            log.error(f"Failed to upsert daily summary for client {client_id}: {e}")
            raise
    
    async def process_client_daily_aggregation(
        self, 
        client_id: int, 
        client_name: str, 
        markup_rate: float, 
        usage_date: date
    ) -> Optional[Dict[str, Any]]:
        """
        Process daily aggregation for a single client from InfluxDB to SQLite
        
        Args:
            client_id: Client organization ID
            client_name: Client organization name
            markup_rate: Client's markup rate
            usage_date: Date to process
            
        Returns:
            Aggregation result summary
        """
        try:
            # Get raw usage data from InfluxDB
            raw_data = await self.get_raw_usage_from_influxdb(str(client_id), usage_date)
            
            if not raw_data:
                log.debug(f"No usage data found in InfluxDB for client {client_name} on {usage_date}")
                return None
            
            # Aggregate the data
            aggregated_data = await self.aggregate_influxdb_data(raw_data, markup_rate)
            
            if not aggregated_data:
                return None
            
            # Store aggregated data in SQLite
            await self.upsert_daily_summary(client_id, usage_date, aggregated_data)
            
            return {
                "client_id": client_id,
                "client_name": client_name,
                "usage_date": usage_date.isoformat(),
                "raw_records_processed": len(raw_data),
                "aggregated_data": aggregated_data,
                "data_source": "influxdb_first"
            }
            
        except Exception as e:
            log.error(f"Failed to process daily aggregation for client {client_name}: {e}")
            return {
                "client_id": client_id,
                "client_name": client_name,
                "usage_date": usage_date.isoformat(),
                "error": str(e),
                "data_source": "influxdb_first"
            }
    
    # Legacy methods for backward compatibility (reading from SQLite summaries)
    async def get_client_daily_usage(
        self, 
        client_id: int, 
        usage_date: date
    ) -> Optional[Tuple[int, int, float, float, str]]:
        """Get daily usage summary from SQLite (for compatibility)"""
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
        """Update markup cost in SQLite summary"""
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
        """Get monthly usage summary from SQLite summaries"""
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
        """Get the most used model from SQLite summaries"""
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