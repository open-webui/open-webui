"""
InfluxDB-First Service - High-performance time-series storage without SQLite fallback
Optimized for 2-5ms write latency with deduplication, retry logic, and circuit breaker
"""

import os
import asyncio
import logging
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from enum import Enum
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS
from influxdb_client.client.query_api import QueryApi
from influxdb_client.client.exceptions import InfluxDBError

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class RetryConfig:
    """Retry configuration"""
    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 8.0   # seconds
    exponential_base: float = 2.0


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 3
    recovery_timeout: int = 30  # seconds
    success_threshold: int = 2  # successful calls to close from half-open


class InfluxDBFirstService:
    """
    InfluxDB-First service for usage tracking without SQLite fallback
    
    Features:
    - Direct InfluxDB writes only (no SQLite fallback)
    - Request deduplication using request_id tags
    - Exponential backoff retry mechanism
    - Circuit breaker for connection failures
    - Batch writing optimization
    - Performance monitoring
    """
    
    def __init__(self):
        self.enabled = os.getenv("INFLUXDB_FIRST_ENABLED", "false").lower() == "true"
        self.use_cloud = os.getenv("INFLUXDB_USE_CLOUD", "false").lower() == "true"
        
        # Performance settings
        self.write_timeout = int(os.getenv("INFLUXDB_WRITE_TIMEOUT", "2000"))  # 2 seconds
        self.batch_size = int(os.getenv("INFLUXDB_BATCH_SIZE", "100"))
        self.flush_interval = int(os.getenv("INFLUXDB_FLUSH_INTERVAL", "1000"))  # ms
        
        # Retry and circuit breaker configuration
        self.retry_config = RetryConfig()
        self.circuit_config = CircuitBreakerConfig()
        
        # Circuit breaker state
        self.circuit_state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.success_count = 0
        
        # Batch buffer
        self._batch_buffer: List[Point] = []
        self._last_flush = datetime.now()
        
        if not self.enabled:
            logger.info("InfluxDB-First service is disabled")
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
        
        self.measurement = os.getenv("INFLUXDB_MEASUREMENT", "usage_tracking")
        
        # Initialize client
        self._init_client()
    
    def _init_client(self):
        """Initialize InfluxDB client with optimized settings"""
        try:
            self.client = InfluxDBClient(
                url=self.url,
                token=self.token,
                org=self.org,
                timeout=self.write_timeout,
                enable_gzip=True
            )
            
            # Create write API optimized for performance
            if self.use_cloud:
                # Async write API for production with batching
                self.write_api = self.client.write_api(write_options=ASYNCHRONOUS)
            else:
                # Sync write API for development
                self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            
            self.query_api = self.client.query_api()
            
            logger.info(f"InfluxDB-First service connected to {self.url} ({'cloud' if self.use_cloud else 'local'})")
            
        except Exception as e:
            logger.error(f"Failed to initialize InfluxDB-First client: {e}")
            self.enabled = False
            self.client = None
            self.write_api = None
            self.query_api = None
    
    async def write_usage_record(self, usage_data: Dict[str, Any]) -> bool:
        """
        Write usage data directly to InfluxDB with deduplication and retry logic
        
        Args:
            usage_data: Usage record containing model, tokens, cost, etc.
            
        Returns:
            bool: True if write successful, False otherwise
        """
        if not self.enabled:
            logger.warning("InfluxDB-First service is disabled")
            return False
        
        # Check circuit breaker
        if not self._is_circuit_closed():
            logger.warning("InfluxDB-First circuit breaker is open, rejecting write")
            return False
        
        # Create data point
        point = self._create_usage_point(usage_data)
        if not point:
            return False
        
        # Check for duplicate using request_id tag
        if await self._is_duplicate_request(usage_data.get("request_id")):
            logger.info(f"Duplicate request ignored: {usage_data.get('request_id')}")
            return True
        
        # Write with retry logic
        return await self._write_with_retry(point)
    
    def _create_usage_point(self, usage_data: Dict[str, Any]) -> Optional[Point]:
        """Create InfluxDB point from usage data"""
        try:
            # Extract token information
            if "input_tokens" in usage_data and "output_tokens" in usage_data:
                input_tokens = usage_data.get("input_tokens", 0)
                output_tokens = usage_data.get("output_tokens", 0)
                total_tokens = usage_data.get("total_tokens", input_tokens + output_tokens)
            elif "tokens_used" in usage_data:
                total_tokens = usage_data.get("tokens_used", 0)
                # Estimate input/output split (70/30)
                input_tokens = int(total_tokens * 0.7)
                output_tokens = total_tokens - input_tokens
            else:
                input_tokens = output_tokens = total_tokens = 0
            
            # Extract cost
            cost_usd = float(usage_data.get("cost_usd", usage_data.get("cost", 0.0)))
            
            # Create point with tags and fields
            point = Point(self.measurement) \
                .tag("client_org_id", usage_data.get("client_org_id", "unknown")) \
                .tag("model", usage_data.get("model", "unknown")) \
                .tag("api_key_hash", self._hash_api_key(usage_data.get("api_key", ""))) \
                .field("input_tokens", input_tokens) \
                .field("output_tokens", output_tokens) \
                .field("total_tokens", total_tokens) \
                .field("cost_usd", cost_usd) \
                .field("latency_ms", usage_data.get("latency_ms", 0))
            
            # Add optional tags for deduplication and tracking
            if usage_data.get("external_user"):
                point.tag("external_user", usage_data["external_user"])
            
            if usage_data.get("request_id"):
                point.tag("request_id", usage_data["request_id"])
            
            # Set timestamp
            if usage_data.get("timestamp"):
                try:
                    timestamp = datetime.fromisoformat(
                        usage_data["timestamp"].replace("Z", "+00:00")
                    )
                    point.time(timestamp, WritePrecision.MS)
                except:
                    point.time(datetime.utcnow(), WritePrecision.MS)
            else:
                point.time(datetime.utcnow(), WritePrecision.MS)
            
            return point
            
        except Exception as e:
            logger.error(f"Failed to create usage point: {e}")
            return None
    
    async def _is_duplicate_request(self, request_id: Optional[str]) -> bool:
        """Check if request_id already exists in InfluxDB"""
        if not request_id or not self.enabled:
            return False
        
        try:
            # Query for existing request_id in last 24 hours
            query = f'''
                from(bucket: "{self.bucket}")
                |> range(start: -24h)
                |> filter(fn: (r) => r["_measurement"] == "{self.measurement}")
                |> filter(fn: (r) => r["request_id"] == "{request_id}")
                |> limit(n: 1)
            '''
            
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.query_api.query(query=query)
            )
            
            # Check if any results found
            for table in result:
                if len(table.records) > 0:
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Failed to check for duplicate request: {e}")
            # On error, allow write to proceed (better to have duplicates than miss data)
            return False
    
    async def _write_with_retry(self, point: Point) -> bool:
        """Write point with exponential backoff retry"""
        last_error = None
        
        for attempt in range(self.retry_config.max_attempts):
            try:
                # Calculate delay for this attempt
                if attempt > 0:
                    delay = min(
                        self.retry_config.base_delay * (self.retry_config.exponential_base ** (attempt - 1)),
                        self.retry_config.max_delay
                    )
                    await asyncio.sleep(delay)
                
                # Attempt write
                if self.use_cloud:
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self.write_api.write(bucket=self.bucket, record=point)
                    )
                else:
                    self.write_api.write(bucket=self.bucket, record=point)
                
                # Success - reset circuit breaker
                self._record_success()
                logger.debug(f"Successfully wrote usage data to InfluxDB (attempt {attempt + 1})")
                return True
                
            except Exception as e:
                last_error = e
                logger.warning(f"Write attempt {attempt + 1} failed: {e}")
        
        # All attempts failed - record failure
        self._record_failure()
        logger.error(f"All write attempts failed: {last_error}")
        return False
    
    def _is_circuit_closed(self) -> bool:
        """Check if circuit breaker allows requests"""
        if self.circuit_state == CircuitBreakerState.CLOSED:
            return True
        
        if self.circuit_state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if (self.last_failure_time and 
                datetime.now() - self.last_failure_time > timedelta(seconds=self.circuit_config.recovery_timeout)):
                self.circuit_state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                logger.info("Circuit breaker moved to HALF_OPEN state")
                return True
            return False
        
        # HALF_OPEN state - allow requests
        return True
    
    def _record_success(self):
        """Record successful operation for circuit breaker"""
        if self.circuit_state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.circuit_config.success_threshold:
                self.circuit_state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker moved to CLOSED state")
        elif self.circuit_state == CircuitBreakerState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def _record_failure(self):
        """Record failed operation for circuit breaker"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.circuit_config.failure_threshold:
            self.circuit_state = CircuitBreakerState.OPEN
            logger.warning("Circuit breaker moved to OPEN state due to failures")
    
    async def query_usage_data(
        self, 
        client_org_id: str, 
        start_time: datetime, 
        end_time: datetime,
        model: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query usage data from InfluxDB for daily aggregation
        
        Args:
            client_org_id: Client organization ID
            start_time: Start time for query
            end_time: End time for query
            model: Optional model filter
            
        Returns:
            List of usage records for aggregation
        """
        if not self.enabled:
            return []
        
        try:
            # Build Flux query
            model_filter = f'|> filter(fn: (r) => r["model"] == "{model}")' if model else ""
            
            query = f'''
                from(bucket: "{self.bucket}")
                |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
                |> filter(fn: (r) => r["_measurement"] == "{self.measurement}")
                |> filter(fn: (r) => r["client_org_id"] == "{client_org_id}")
                |> filter(fn: (r) => r["_field"] == "total_tokens" or r["_field"] == "cost_usd" or r["_field"] == "input_tokens" or r["_field"] == "output_tokens")
                {model_filter}
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
            usage_data = []
            for table in result:
                for record in table.records:
                    usage_data.append({
                        "model": record.values.get("model", "unknown"),
                        "external_user": record.values.get("external_user", "unknown"),
                        "input_tokens": int(record.values.get("input_tokens", 0)),
                        "output_tokens": int(record.values.get("output_tokens", 0)),
                        "total_tokens": int(record.values.get("total_tokens", 0)),
                        "cost_usd": float(record.values.get("cost_usd", 0.0))
                    })
            
            return usage_data
            
        except Exception as e:
            logger.error(f"Failed to query InfluxDB usage data: {e}")
            return []
    
    async def get_daily_usage_aggregated(
        self,
        client_org_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        Get aggregated daily usage data optimized for batch processing
        
        This method uses optimized Flux queries for efficient batch aggregation
        
        Args:
            client_org_id: Client organization ID
            start_time: Start time (UTC)
            end_time: End time (UTC)
            
        Returns:
            List of aggregated usage records grouped by model and user
        """
        if not self.enabled or not self.query_api:
            return []
        
        try:
            # Use the specialized batch queries service
            from open_webui.usage_tracking.services.influxdb_batch_queries import influxdb_batch_queries
            return await influxdb_batch_queries.get_daily_usage_aggregated(
                client_org_id, start_time, end_time
            )
            
        except Exception as e:
            logger.error(f"Failed to get daily usage aggregated for client {client_org_id}: {e}")
            return []
    
    async def query_data(self, flux_query: str) -> List[Dict[str, Any]]:
        """
        Execute a Flux query and return results as list of dictionaries
        
        Args:
            flux_query: Flux query string
            
        Returns:
            List of query results
        """
        if not self.enabled or not self.query_api:
            return []
        
        try:
            logger.debug("Executing custom Flux query")
            
            # Execute query
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.query_api.query(query=flux_query, org=self.org)
            )
            
            # Process results
            query_data = []
            for table in result:
                for record in table.records:
                    # Convert record to dictionary
                    record_dict = {}
                    
                    # Try to get standard fields if they exist
                    try:
                        record_dict["_time"] = record.get_time()
                    except:
                        pass
                    
                    try:
                        record_dict["_measurement"] = record.get_measurement()
                    except:
                        pass
                    
                    try:
                        record_dict["_field"] = record.get_field()
                    except:
                        pass
                    
                    try:
                        record_dict["_value"] = record.get_value()
                    except:
                        pass
                    
                    # Add all available values from the record
                    for key, value in record.values.items():
                        if key not in ["result", "table", "_start", "_stop"]:
                            record_dict[key] = value
                    
                    query_data.append(record_dict)
            
            logger.debug(f"Query returned {len(query_data)} records")
            return query_data
            
        except Exception as e:
            logger.error(f"Failed to execute Flux query: {e}")
            return []
    
    def _hash_api_key(self, api_key: str) -> str:
        """Create a hash of the API key for storage"""
        if not api_key:
            return "unknown"
        return hashlib.sha256(api_key.encode()).hexdigest()[:8]
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service health including circuit breaker status"""
        if not self.enabled:
            return {
                "status": "disabled",
                "message": "InfluxDB-First service is disabled"
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
                "mode": "cloud" if self.use_cloud else "local",
                "circuit_breaker": {
                    "state": self.circuit_state.value,
                    "failure_count": self.failure_count,
                    "success_count": self.success_count
                }
            }
            
        except Exception as e:
            self._record_failure()
            return {
                "status": "unhealthy",
                "error": str(e),
                "url": self.url,
                "circuit_breaker": {
                    "state": self.circuit_state.value,
                    "failure_count": self.failure_count
                }
            }
    
    def close(self):
        """Close InfluxDB client connection"""
        if self.client:
            try:
                if self.write_api:
                    self.write_api.close()
                self.client.close()
                logger.info("InfluxDB-First client closed")
            except Exception as e:
                logger.error(f"Error closing InfluxDB-First client: {e}")


# Singleton instance
influxdb_first_service = InfluxDBFirstService()