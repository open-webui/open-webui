"""
Optimized Flux Queries for InfluxDB-First Batch Processing
Provides efficient queries for daily aggregation and summary generation
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
from open_webui.usage_tracking.services.influxdb_first_service import influxdb_first_service

logger = logging.getLogger(__name__)


class InfluxDBBatchQueries:
    """Optimized Flux queries for batch processing operations"""
    
    def __init__(self):
        self.service = influxdb_first_service
    
    async def get_daily_usage_aggregated(
        self,
        client_org_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        Get aggregated usage data for a client on a specific day
        
        Optimized Flux Query:
        - Groups by client_org_id, model, external_user
        - Sums total_tokens and cost_usd
        - Single query per client for efficiency
        """
        try:
            if not self.service.enabled:
                logger.warning("InfluxDB service not enabled")
                return []
            
            # Convert datetime to RFC3339 format for Flux
            # If datetime is timezone-aware, use isoformat; otherwise add Z for UTC
            if start_time.tzinfo:
                start_rfc = start_time.isoformat()
                end_rfc = end_time.isoformat()
            else:
                start_rfc = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
                end_rfc = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            flux_query = f'''
            from(bucket: "{self.service.bucket}")
              |> range(start: {start_rfc}, stop: {end_rfc})
              |> filter(fn: (r) => r._measurement == "usage_tracking")
              |> filter(fn: (r) => r.client_org_id == "{client_org_id}")
              |> filter(fn: (r) => r._field == "total_tokens" or r._field == "cost_usd")
              |> group(columns: ["client_org_id", "model", "external_user", "_field"])
              |> sum()
              |> pivot(rowKey: ["client_org_id", "model", "external_user"], columnKey: ["_field"], valueColumn: "_value")
              |> yield(name: "daily_aggregated_usage")
            '''
            
            logger.debug(f"Executing batch aggregation query for client {client_org_id}")
            logger.debug(f"Query time range: {start_rfc} to {end_rfc}")
            
            # Execute query
            result = await self.service.query_data(flux_query)
            
            # Transform result to expected format
            aggregated_data = []
            if result:
                logger.debug(f"Query returned {len(result)} raw records")
                for record in result:
                    logger.debug(f"Record keys: {list(record.keys())}")
                    # Check if this is a pivot result
                    if "total_tokens" in record or "cost_usd" in record:
                        aggregated_data.append({
                            "client_org_id": record.get("client_org_id", client_org_id),
                            "model": record.get("model", "unknown"),
                            "external_user": record.get("external_user", "unknown"),
                            "total_tokens": int(record.get("total_tokens", 0)),
                            "cost_usd": float(record.get("cost_usd", 0.0))
                        })
                    else:
                        logger.warning(f"Unexpected record format: {record}")
            
            logger.debug(
                f"Retrieved {len(aggregated_data)} aggregated records for client {client_org_id}"
            )
            
            return aggregated_data
            
        except Exception as e:
            logger.error(f"Failed to get daily usage aggregation for client {client_org_id}: {e}")
            return []
    
    async def get_client_model_summary(
        self,
        client_org_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        Get model-level summary for a client
        
        Flux Query optimized for ClientDailyUsage table population
        """
        try:
            if not self.service.enabled:
                return []
            
            # Convert datetime to RFC3339 format for Flux
            if start_time.tzinfo:
                start_rfc = start_time.isoformat()
                end_rfc = end_time.isoformat()
            else:
                start_rfc = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
                end_rfc = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            flux_query = f'''
            from(bucket: "{self.service.bucket}")
              |> range(start: {start_rfc}, stop: {end_rfc})
              |> filter(fn: (r) => r._measurement == "usage_tracking")
              |> filter(fn: (r) => r.client_org_id == "{client_org_id}")
              |> filter(fn: (r) => r._field == "total_tokens" or r._field == "cost_usd")
              |> group(columns: ["client_org_id", "model", "_field"])
              |> sum()
              |> pivot(rowKey: ["client_org_id", "model"], columnKey: ["_field"], valueColumn: "_value")
              |> yield(name: "model_summary")
            '''
            
            result = await self.service.query_data(flux_query)
            
            model_summaries = []
            for record in result:
                model_summaries.append({
                    "client_org_id": record.get("client_org_id"),
                    "model": record.get("model", "unknown"),
                    "total_tokens": int(record.get("total_tokens", 0)),
                    "cost_usd": float(record.get("cost_usd", 0.0))
                })
            
            return model_summaries
            
        except Exception as e:
            logger.error(f"Failed to get model summary for client {client_org_id}: {e}")
            return []
    
    async def get_client_user_model_summary(
        self,
        client_org_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        Get user+model-level summary for a client
        
        Flux Query optimized for ClientUserDailyUsage table population
        """
        try:
            if not self.service.enabled:
                return []
            
            # Convert datetime to RFC3339 format for Flux
            if start_time.tzinfo:
                start_rfc = start_time.isoformat()
                end_rfc = end_time.isoformat()
            else:
                start_rfc = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
                end_rfc = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            flux_query = f'''
            from(bucket: "{self.service.bucket}")
              |> range(start: {start_rfc}, stop: {end_rfc})
              |> filter(fn: (r) => r._measurement == "usage_tracking")
              |> filter(fn: (r) => r.client_org_id == "{client_org_id}")
              |> filter(fn: (r) => r._field == "total_tokens" or r._field == "cost_usd")
              |> group(columns: ["client_org_id", "external_user", "model", "_field"])
              |> sum()
              |> pivot(rowKey: ["client_org_id", "external_user", "model"], columnKey: ["_field"], valueColumn: "_value")
              |> yield(name: "user_model_summary")
            '''
            
            result = await self.service.query_data(flux_query)
            
            user_model_summaries = []
            for record in result:
                user_model_summaries.append({
                    "client_org_id": record.get("client_org_id"),
                    "external_user": record.get("external_user", "unknown"),
                    "model": record.get("model", "unknown"),
                    "total_tokens": int(record.get("total_tokens", 0)),
                    "cost_usd": float(record.get("cost_usd", 0.0))
                })
            
            return user_model_summaries
            
        except Exception as e:
            logger.error(f"Failed to get user-model summary for client {client_org_id}: {e}")
            return []
    
    async def get_batch_processing_stats(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        Get overall statistics for batch processing period
        
        Useful for monitoring and validation
        """
        try:
            if not self.service.enabled:
                return {"total_records": 0, "total_clients": 0, "total_cost_usd": 0.0}
            
            # Convert datetime to RFC3339 format for Flux
            if start_time.tzinfo:
                start_rfc = start_time.isoformat()
                end_rfc = end_time.isoformat()
            else:
                start_rfc = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
                end_rfc = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            flux_query = f'''
            from(bucket: "{self.service.bucket}")
              |> range(start: {start_rfc}, stop: {end_rfc})
              |> filter(fn: (r) => r._measurement == "usage_tracking")
              |> filter(fn: (r) => r._field == "total_tokens" or r._field == "cost_usd")
              |> group(columns: ["_field"])
              |> sum()
              |> pivot(rowKey: [], columnKey: ["_field"], valueColumn: "_value")
              |> yield(name: "batch_stats")
            '''
            
            result = await self.service.query_data(flux_query)
            
            if result:
                stats = result[0]
                return {
                    "total_records": len(result),
                    "total_tokens": int(stats.get("total_tokens", 0)),
                    "total_cost_usd": float(stats.get("cost_usd", 0.0))
                }
            
            return {"total_records": 0, "total_tokens": 0, "total_cost_usd": 0.0}
            
        except Exception as e:
            logger.error(f"Failed to get batch processing stats: {e}")
            return {"total_records": 0, "total_tokens": 0, "total_cost_usd": 0.0}
    
    async def get_client_list_with_data(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[str]:
        """
        Get list of clients that have data in the specified time range
        
        Useful for optimizing batch processing (skip clients with no data)
        """
        try:
            if not self.service.enabled:
                return []
            
            # Convert datetime to RFC3339 format for Flux
            if start_time.tzinfo:
                start_rfc = start_time.isoformat()
                end_rfc = end_time.isoformat()
            else:
                start_rfc = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
                end_rfc = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            flux_query = f'''
            from(bucket: "{self.service.bucket}")
              |> range(start: {start_rfc}, stop: {end_rfc})
              |> filter(fn: (r) => r._measurement == "usage_tracking")
              |> filter(fn: (r) => r._field == "total_tokens")
              |> group(columns: ["client_org_id"])
              |> count()
              |> keep(columns: ["client_org_id"])
              |> yield(name: "clients_with_data")
            '''
            
            result = await self.service.query_data(flux_query)
            
            client_ids = [record.get("client_org_id") for record in result if record.get("client_org_id")]
            
            logger.debug(f"Found {len(client_ids)} clients with data in time range")
            
            return client_ids
            
        except Exception as e:
            logger.error(f"Failed to get client list with data: {e}")
            return []
    
    async def validate_data_consistency(
        self,
        client_org_id: str,
        processing_date: date
    ) -> Dict[str, Any]:
        """
        Validate data consistency for a client on a specific date
        
        Compares raw records count vs aggregated data
        """
        try:
            if not self.service.enabled:
                return {"consistent": True, "raw_records": 0, "aggregated_records": 0}
            
            # Create UTC-aware datetime objects
            from datetime import timezone as tz
            start_time = datetime.combine(processing_date, datetime.min.time()).replace(tzinfo=tz.utc)
            end_time = start_time + timedelta(days=1)
            
            # Convert datetime to RFC3339 format for Flux
            if start_time.tzinfo:
                start_rfc = start_time.isoformat()
                end_rfc = end_time.isoformat()
            else:
                start_rfc = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
                end_rfc = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # Count raw records
            raw_count_query = f'''
            from(bucket: "{self.service.bucket}")
              |> range(start: {start_rfc}, stop: {end_rfc})
              |> filter(fn: (r) => r._measurement == "usage_tracking")
              |> filter(fn: (r) => r.client_org_id == "{client_org_id}")
              |> filter(fn: (r) => r._field == "total_tokens")
              |> count()
              |> yield(name: "raw_count")
            '''
            
            raw_result = await self.service.query_data(raw_count_query)
            raw_count = raw_result[0].get("_value", 0) if raw_result else 0
            
            # Get aggregated data
            aggregated_data = await self.get_daily_usage_aggregated(
                client_org_id, start_time, end_time
            )
            aggregated_count = len(aggregated_data)
            
            # Calculate totals for additional validation
            total_tokens = sum(record.get("total_tokens", 0) for record in aggregated_data)
            total_cost = sum(record.get("cost_usd", 0.0) for record in aggregated_data)
            
            return {
                "consistent": raw_count > 0 and aggregated_count > 0,
                "raw_records": raw_count,
                "aggregated_records": aggregated_count,
                "total_tokens": total_tokens,
                "total_cost_usd": total_cost,
                "processing_date": processing_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to validate data consistency for client {client_org_id}: {e}")
            return {
                "consistent": False,
                "error": str(e),
                "raw_records": 0,
                "aggregated_records": 0
            }


# Global instance for batch queries
influxdb_batch_queries = InfluxDBBatchQueries()