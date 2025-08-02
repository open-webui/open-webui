

# Daily Batch Process Workflow Analysis - mAI OpenWebUI

## Overview

The mAI daily batch process implements an **InfluxDB-First Architecture** for processing usage tracking data. It runs automatically at **13:00 CET/CEST** daily and aggregates raw InfluxDB usage data into SQLite summary tables for reporting and billing.

## 1\. Entry Point and Scheduling Mechanism

### Scheduler Initialization

  - **File**: `backend/open_webui/utils/batch_scheduler.py`
  - **Scheduler**: APScheduler with AsyncIOScheduler
  - **Trigger**: CronTrigger at 13:00 CET/CEST (Europe/Warsaw timezone)
  - **Initialization**: During FastAPI application startup via `lifespan` context manager
  - **Configuration**:
      - Max instances: 1 (prevents overlapping runs)
      - Coalesce: true (combines missed runs)
      - Misfire grace time: 3600 seconds (1 hour)

### Application Lifecycle

```python
# In main.py lifespan function
await init_batch_scheduler()  # Startup
# ...
await shutdown_batch_scheduler()  # Shutdown
```

### Manual Triggers

  - **Admin Endpoint**: `POST /api/admin/batch/trigger` (admin-only)
  - **Status Endpoint**: `GET /api/admin/batch/status` (admin-only)

### Command-Line Trigger

For development and operational purposes, the process can also be triggered directly from the command line. This is the preferred method for debugging and reprocessing data for specific days.

**Command:**

```bash
docker exec mai-backend-dev python3 -m open_webui.utils.unified_batch_processor --run-now --date YYYY-MM-DD
```

  - `--run-now`: Required to execute the process immediately.
  - `--date YYYY-MM-DD`: Optional, allows processing data from a specific day.

## 2\. Main Batch Processing Flow

### Unified Batch Processor

**File**: `backend/open_webui/utils/unified_batch_processor.py`

#### Step-by-Step Process:

**Phase 1: Initialization**

1.  Check `INFLUXDB_FIRST_ENABLED` environment variable
2.  Set processing date (defaults to yesterday)
3.  Initialize database session
4.  Configure timezone (Europe/Warsaw)
5.  Load markup multiplier (default: 1.3x)

**Phase 2: InfluxDB-First Processing**

```python
async def _process_influxdb_first_batch():
    # 1. Fetch USD/PLN exchange rate
    exchange_rate = await _fetch_exchange_rate(processing_date)
    await _save_exchange_rate(db, processing_date, exchange_rate)
    
    # 2. Get active client organizations
    client_orgs = await _get_active_clients(db)
    
    # 3. Process each client
    for client_org in client_orgs:
        await _process_client_influxdb_first(db, client_org, processing_date, exchange_rate)
```

## 3\. Data Flow: InfluxDB → SQLite Aggregation

### InfluxDB Query Strategy

**File**: `backend/open_webui/usage_tracking/services/influxdb_batch_queries.py`

#### Optimized Flux Queries:

```flux
from(bucket: "mai_usage_raw_dev")
  |> range(start: 2025-07-31T00:00:00Z, stop: 2025-08-01T00:00:00Z)
  |> filter(fn: (r) => r._measurement == "usage_tracking")
  |> filter(fn: (r) => r.client_org_id == "client-123")
  |> filter(fn: (r) => r._field == "total_tokens" or r._field == "cost_usd")
  |> group(columns: ["client_org_id", "model", "external_user", "_field"])
  |> sum()
  |> pivot(rowKey: ["client_org_id", "model", "external_user"], columnKey: ["_field"], valueColumn: "_value")
```

### Data Aggregation Process:

1.  **Raw Data Retrieval**: Query InfluxDB for daily usage per client
2.  **Model-Level Aggregation**: Group by model and sum tokens/costs
3.  **User-Model Aggregation**: Group by user+model combinations
4.  **SQLite Summary Creation**: Store aggregated data in summary tables

### Data Transformations:

```python
# For each InfluxDB record:
raw_cost_usd = float(record.get("cost_usd", 0.0))
markup_cost_usd = raw_cost_usd * self.markup_multiplier  # 1.3x
markup_cost_pln = markup_cost_usd * float(exchange_rate)
```

## 4\. Business Rules and Cost Calculations

### Markup Application

  - **Base Rate**: 1.3x (30% markup on OpenRouter costs)
  - **Configuration**: `USAGE_MARKUP_MULTIPLIER` environment variable
  - **Application Point**: Applied to USD costs before PLN conversion

### Currency Conversion

  - **Source**: NBP (National Bank of Poland) API via microservice
  - **Service URL**: `NBP_SERVICE_URL` (default: http://localhost:8001)
  - **Fallback Rate**: 4.0 PLN/USD if NBP service unavailable
  - **Caching**: Exchange rates cached in `DailyExchangeRateDB` table

### Cost Calculation Flow:

1.  **Raw Cost (USD)**: From InfluxDB (OpenRouter webhook data)
2.  **Markup Cost (USD)**: `raw_cost * markup_multiplier`
3.  **Final Cost (PLN)**: `markup_cost_usd * exchange_rate`

## 5\. Database Schema and Aggregation Logic

### SQLite Summary Tables:

#### ClientDailyUsage

  - **Purpose**: Daily usage summaries per client per model
  - **Key Fields**: `client_org_id`, `usage_date`, `model`, `total_tokens`, `total_cost`, `total_cost_pln`
  - **Source Tracking**: `source` field marks data origin ("influxdb\_first")

#### ClientUserDailyUsage

  - **Purpose**: Daily usage summaries per user per model per client
  - **Key Fields**: `client_org_id`, `user_email`, `usage_date`, `model`, `total_tokens`, `total_cost`, `total_cost_pln`
  - **User Tracking**: Links to `external_user` from InfluxDB data

#### DailyExchangeRateDB

  - **Purpose**: Historical exchange rates for accurate billing
  - **Key Fields**: `date`, `currency_from`, `currency_to`, `rate`, `source`
  - **Source**: "NBP" for Polish National Bank rates

### Data Correction Logic:

```python
if existing_record:
    old_cost = float(existing.total_cost)
    new_cost = summary["markup_cost_usd"]
    
    if abs(old_cost - new_cost) > 0.001:
        corrections += 1  # Track corrections for monitoring
        existing.total_cost = Decimal(str(new_cost))
```

## 6\. Error Handling and Retry Mechanisms

### Circuit Breaker Pattern

**File**: `backend/open_webui/usage_tracking/services/influxdb_first_service.py`

#### Configuration:

  - **Failure Threshold**: 3 failures trigger circuit open
  - **Recovery Timeout**: 30 seconds before attempting half-open
  - **Success Threshold**: 2 successes to close circuit from half-open

### Retry Strategy:

  - **Max Attempts**: 3 retries per operation
  - **Backoff**: Exponential backoff (1s, 2s, 4s, max 8s)
  - **Write Timeout**: 2000ms (2 seconds) for InfluxDB writes

### Error Categories:

1.  **InfluxDB Connection Failures**: Circuit breaker activation
2.  **NBP Service Unavailable**: Fallback to default exchange rate (4.0)
3.  **Client Processing Errors**: Continue with other clients, log errors
4.  **Database Transaction Failures**: Rollback and retry

## 7\. Integration with NBP Currency Service

### NBP Microservice

**File**: `nbp-service/app/main.py`

#### Features:

  - **Standalone Service**: Docker container (`mai-nbp-service`)
  - **Real/Mock Modes**: `MOCK_MODE` environment variable
  - **Caching**: Redis cache for production, in-memory for development
  - **Reliable Health Checks**: The `/health` endpoint is monitored using a Python-based check within Docker to ensure compatibility with minimal base images (replaces a `curl`-based approach).

#### API Endpoints:

  - **GET /api/usd-pln-rate**: Current rate or specific date
  - **GET /api/usd-pln-rate/range**: Rate range for date periods
  - **POST /api/cache/clear**: Admin cache clearing

### Error Handling:

```python
try:
    response = await client.get(f"{nbp_service_url}/api/usd-pln-rate")
    return Decimal(str(response.json()["rate"]))
except Exception as e:
    logger.warning("Using fallback exchange rate of 4.0 PLN/USD")
    return Decimal("4.0")
```

## 8\. Performance Characteristics and Monitoring

### Performance Metrics:

  - **InfluxDB Query Performance**: Optimized Flux queries with proper indexing
  - **Batch Processing Time**: Typically completes in under 60 seconds
  - **Memory Usage**: Processes clients sequentially to minimize memory footprint
  - **Database Operations**: Bulk operations with transaction batching

### Monitoring and Logging:

  - **Batch Run Tracking**: `InfluxDBBatchRunDB` table for audit trail
  - **Performance Metrics**: Duration, clients processed, records processed
  - **Error Tracking**: Error counts and messages stored
  - **Health Checks**: Unified health check endpoint for all services

### Key Performance Indicators:

```python
result_summary = {
    "clients_processed": 15,
    "influxdb_records_processed": 1247,
    "sqlite_summaries_created": 89,
    "data_corrections": 3,
    "total_duration_seconds": 43.2,
    "exchange_rate": 4.13
}
```

## 9\. Data Validation and Consistency

### Validation Mechanisms:

1.  **Duplicate Prevention**: Request ID deduplication in InfluxDB
2.  **Data Consistency Checks**: Compare InfluxDB vs SQLite totals
3.  **Exchange Rate Validation**: Reasonable range checks for rates
4.  **Client Data Isolation**: Multi-tenant data separation validation

### Consistency Verification:

```python
async def validate_data_consistency():
    raw_count = count_influxdb_records(client_id, date)
    aggregated_count = count_sqlite_summaries(client_id, date)
    return {"consistent": raw_count > 0 and aggregated_count > 0}
```

## 10\. Configuration and Environment Variables

### Key Environment Settings:

```env
# InfluxDB Configuration
INFLUXDB_FIRST_ENABLED=true
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=dev-token-for-testing-only
INFLUXDB_BUCKET=mai_usage_raw_dev

# NBP Service
NBP_SERVICE_URL=http://localhost:8001

# Business Logic
USAGE_MARKUP_MULTIPLIER=1.3

# Performance Tuning
INFLUXDB_WRITE_TIMEOUT=2000
INFLUXDB_BATCH_SIZE=100
```

## 11\. Fallback and Legacy Support

### Legacy SQLite Processing:

  - **Condition**: When `INFLUXDB_FIRST_ENABLED=false` or InfluxDB unavailable
  - **Implementation**: Falls back to legacy SQLite-based processing
  - **Data Source**: Direct SQLite webhook data instead of InfluxDB aggregation

### Dual-Write Compatibility:

  - **Transition Support**: Handles both InfluxDB and SQLite data sources during migration
  - **Data Source Tracking**: `source` field tracks data origin for debugging

## Summary

The mAI daily batch process represents a sophisticated **InfluxDB-First Architecture** that efficiently processes high-volume usage tracking data. Key strengths include:

1.  **Scalable Design**: InfluxDB optimized for time-series data with 2-5ms write performance
2.  **Robust Error Handling**: Circuit breaker patterns, retry mechanisms, and graceful fallbacks
3.  **Business Logic Accuracy**: Precise markup calculations and currency conversions
4.  **Multi-Tenant Security**: Client data isolation throughout the processing pipeline
5.  **Comprehensive Monitoring**: Detailed metrics and audit trails for operational visibility
6.  **Production-Ready**: Automatic scheduling, admin controls, and health monitoring