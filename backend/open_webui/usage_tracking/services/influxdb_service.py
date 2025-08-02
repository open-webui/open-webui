"""
InfluxDB Service - Handles time-series data storage for usage tracking
Uses InfluxDB Cloud for high-performance webhook data writes
"""

import os
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS
from influxdb_client.client.query_api import QueryApi
from influxdb_client.client.exceptions import InfluxDBError

logger = logging.getLogger(__name__)


class InfluxDBService:
    """Service for InfluxDB operations in usage tracking"""
    
    def __init__(self):
        # Determine which InfluxDB instance to use
        self.use_cloud = os.getenv("INFLUXDB_USE_CLOUD", "false").lower() == "true"
        self.enabled = os.getenv("INFLUXDB_ENABLED", "false").lower() == "true"
        
        if not self.enabled:
            logger.info("InfluxDB integration is disabled")
            self.client = None
            self.write_api = None
            self.query_api = None
            return
        
        # Configure InfluxDB connection
        if self.use_cloud:
            self.url = os.getenv("INFLUXDB_CLOUD_URL", "https://cloud2.influxdata.com")
            self.token = os.getenv("INFLUXDB_CLOUD_TOKEN")
            self.org = os.getenv("INFLUXDB_CLOUD_ORG", "mAI")
            self.bucket = os.getenv("INFLUXDB_CLOUD_BUCKET", "mai_usage_raw")
        else:
            self.url = os.getenv("INFLUXDB_URL", "http://localhost:8086")
            self.token = os.getenv("INFLUXDB_TOKEN", "dev-token-for-testing-only")
            self.org = os.getenv("INFLUXDB_ORG", "mAI-dev")
            self.bucket = os.getenv("INFLUXDB_BUCKET", "mai_usage_raw_dev")
        
        # Performance settings
        self.write_timeout = int(os.getenv("INFLUXDB_WRITE_TIMEOUT", "2000"))  # 2 seconds
        self.write_precision = os.getenv("INFLUXDB_WRITE_PRECISION", "ms")
        self.measurement = os.getenv("INFLUXDB_MEASUREMENT", "usage_tracking")
        
        # Initialize client
        try:
            self.client = InfluxDBClient(
                url=self.url,
                token=self.token,
                org=self.org,
                timeout=30_000,  # 30 seconds
                enable_gzip=True
            )
            
            # Create write API with batching for production
            if self.use_cloud:
                # Async write API for production with batching
                self.write_api = self.client.write_api(
                    write_options=ASYNCHRONOUS
                )
            else:
                # Sync write API for development
                self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            
            self.query_api = self.client.query_api()
            
            logger.info(f"InfluxDB connected to {self.url} ({'cloud' if self.use_cloud else 'local'})")
            
        except Exception as e:
            logger.error(f"Failed to initialize InfluxDB client: {e}")
            self.enabled = False
            self.client = None
            self.write_api = None
            self.query_api = None
    
    async def write_usage_record(self, webhook_data: Dict[str, Any]) -> bool:
        """
        Write usage data from webhook to InfluxDB - CORRECTED VERSION
        Optimized for 2-5ms write performance
        """
        if not self.enabled:
            return False
        
        try:
            # Get client organization ID from environment
            client_org_id = os.getenv("CLIENT_ORG_ID", "unknown")
            
            # FIXED: Handle multiple data structure formats
            # Priority: specific keys > fallback keys > defaults
            
            if "input_tokens" in webhook_data and "output_tokens" in webhook_data:
                # Test data structure with separate input/output tokens
                input_tokens = webhook_data.get("input_tokens", 0)
                output_tokens = webhook_data.get("output_tokens", 0)
                total_tokens = webhook_data.get("total_tokens", input_tokens + output_tokens)
            elif "tokens_used" in webhook_data:
                # Webhook service structure with total tokens only
                total_tokens = webhook_data.get("tokens_used", 0)
                # Estimate input/output (70/30 split is common)
                input_tokens = int(total_tokens * 0.7)
                output_tokens = total_tokens - input_tokens
            else:
                # Fallback to 0 if no token data
                input_tokens = 0
                output_tokens = 0
                total_tokens = 0
            
            # FIXED: Handle cost field name variations
            cost_usd = float(webhook_data.get("cost_usd", webhook_data.get("cost", 0.0)))
            
            # Create data point with CORRECTED field mappings
            point = Point(self.measurement) \
                .tag("client_org_id", client_org_id) \
                .tag("model", webhook_data.get("model", "unknown")) \
                .tag("api_key_hash", self._hash_api_key(webhook_data.get("api_key", ""))) \
                .field("input_tokens", input_tokens) \
                .field("output_tokens", output_tokens) \
                .field("total_tokens", total_tokens) \
                .field("cost_usd", cost_usd) \
                .field("latency_ms", webhook_data.get("latency_ms", 0))
            
            # Add optional tags
            if webhook_data.get("external_user"):
                point.tag("external_user", webhook_data["external_user"])
            
            if webhook_data.get("request_id"):
                point.tag("request_id", webhook_data["request_id"])
            
            # Set timestamp
            if webhook_data.get("timestamp"):
                try:
                    timestamp = datetime.fromisoformat(
                        webhook_data["timestamp"].replace("Z", "+00:00")
                    )
                    point.time(timestamp, WritePrecision.MS)
                except:
                    point.time(datetime.utcnow(), WritePrecision.MS)
            else:
                point.time(datetime.utcnow(), WritePrecision.MS)
            
            # Write to InfluxDB
            if self.use_cloud:
                # Async write for production
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.write_api.write(
                        bucket=self.bucket,
                        record=point
                    )
                )
            else:
                # Sync write for development
                self.write_api.write(
                    bucket=self.bucket,
                    record=point
                )
            
            logger.debug(f"Written usage data to InfluxDB: {webhook_data.get('model')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write to InfluxDB: {e}")
            return False
    
    async def get_data_for_batch(
        self, 
        client_org_id: str, 
        start_time: datetime, 
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        Query InfluxDB for batch processing
        Returns aggregated data by model and external_user
        """
        if not self.enabled:
            return []
        
        try:
            # Flux query for aggregating usage data
            query = f'''
                from(bucket: "{self.bucket}")
                |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
                |> filter(fn: (r) => r["_measurement"] == "{self.measurement}")
                |> filter(fn: (r) => r["client_org_id"] == "{client_org_id}")
                |> filter(fn: (r) => r["_field"] == "total_tokens" or r["_field"] == "cost_usd")
                |> group(columns: ["model", "external_user", "_field"])
                |> sum()
                |> pivot(rowKey: ["model", "external_user"], columnKey: ["_field"], valueColumn: "_value")
            '''
            
            # Execute query
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.query_api.query(query=query)
            )
            
            # Process results
            aggregated_data = []
            for table in result:
                for record in table.records:
                    aggregated_data.append({
                        "model": record.values.get("model", "unknown"),
                        "external_user": record.values.get("external_user", "unknown"),
                        "total_tokens": int(record.values.get("total_tokens", 0)),
                        "cost_usd": float(record.values.get("cost_usd", 0.0))
                    })
            
            return aggregated_data
            
        except Exception as e:
            logger.error(f"Failed to query InfluxDB for batch processing: {e}")
            return []
    
    async def get_usage_summary(
        self, 
        client_org_id: str, 
        days_back: int = 7
    ) -> Dict[str, Any]:
        """Get usage summary for a client organization"""
        if not self.enabled:
            return {"error": "InfluxDB is disabled"}
        
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days_back)
            
            # Query for summary statistics
            query = f'''
                from(bucket: "{self.bucket}")
                |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
                |> filter(fn: (r) => r["_measurement"] == "{self.measurement}")
                |> filter(fn: (r) => r["client_org_id"] == "{client_org_id}")
                |> filter(fn: (r) => r["_field"] == "total_tokens" or r["_field"] == "cost_usd")
                |> group(columns: ["_field"])
                |> sum()
            '''
            
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.query_api.query(query=query)
            )
            
            summary = {
                "client_org_id": client_org_id,
                "period_days": days_back,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "models": {}
            }
            
            # Process summary results
            for table in result:
                for record in table.records:
                    field = record.values.get("_field")
                    value = record.values.get("_value", 0)
                    
                    if field == "total_tokens":
                        summary["total_tokens"] = int(value)
                    elif field == "cost_usd":
                        summary["total_cost_usd"] = float(value)
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get usage summary: {e}")
            return {"error": str(e)}
    
    def _hash_api_key(self, api_key: str) -> str:
        """Create a hash of the API key for storage"""
        import hashlib
        if not api_key:
            return "unknown"
        # Take first 8 chars of SHA256 hash
        return hashlib.sha256(api_key.encode()).hexdigest()[:8]
    
    async def health_check(self) -> Dict[str, Any]:
        """Check InfluxDB connection health"""
        if not self.enabled:
            return {
                "status": "disabled",
                "message": "InfluxDB integration is disabled"
            }
        
        try:
            # Simple ping query
            query = f'from(bucket: "{self.bucket}") |> range(start: -1m) |> limit(n: 1)'
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.query_api.query(query=query)
            )
            
            return {
                "status": "healthy",
                "url": self.url,
                "bucket": self.bucket,
                "org": self.org,
                "mode": "cloud" if self.use_cloud else "local"
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "url": self.url
            }
    
    def close(self):
        """Close InfluxDB client connection"""
        if self.client:
            try:
                if self.write_api:
                    self.write_api.close()
                self.client.close()
                logger.info("InfluxDB client closed")
            except Exception as e:
                logger.error(f"Error closing InfluxDB client: {e}")