# Phase 2: Batch Consolidation - InfluxDB-First Architecture

## Summary

This document summarizes the implementation of Phase 2: Batch Consolidation, which creates a unified batch processor that merges legacy SQLite batch processing with the new InfluxDB-First architecture.

## Architecture Overview

**Data Flow: InfluxDB (raw usage data) → SQLite (daily summaries)**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│                 │    │                  │    │                 │
│    InfluxDB     │    │  Unified Batch   │    │     SQLite      │
│  (Raw Usage)    │ -> │   Processor      │ -> │  (Summaries)    │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
      2-5ms                   Daily at                Existing APIs
      writes                  13:00 CET               100% compatible
```

## Key Features

### 1. Unified Processing Architecture
- **Single entry point**: `run_unified_daily_batch()`
- **Architecture decision**: Automatically chooses InfluxDB-First or legacy based on `INFLUXDB_FIRST_ENABLED`
- **100% backward compatibility**: All existing APIs continue to work unchanged
- **No business logic changes**: Preserves all existing functionality

### 2. InfluxDB-First Implementation
- **Optimized Flux queries**: Efficient batch aggregation with grouping
- **Smart data flow**: Raw data in InfluxDB, summaries in SQLite
- **Performance optimized**: Processes multiple clients in parallel
- **Markup validation**: Automatically corrects inconsistent markup calculations

### 3. Summary Tables Strategy
- **ClientDailyUsage**: Daily summaries per client and model
- **ClientUserDailyUsage**: Daily summaries per user and model  
- **DailyExchangeRate**: USD/PLN conversion rates from NBP
- **InfluxDBBatchRun**: Tracking and monitoring batch processing runs
- **ClientModelDailyUsage**: Extended model-level summaries (new)

## Files Created/Modified

### New Files
```
backend/
├── open_webui/utils/unified_batch_processor.py               # Main unified processor
├── open_webui/usage_tracking/services/influxdb_batch_queries.py  # Optimized Flux queries
├── open_webui/usage_tracking/models/batch_tracking.py        # New tracking models
├── create_batch_tracking_tables.py                          # Database migration
└── test_unified_batch_processor.py                          # Testing script
```

### Modified Files
```
backend/
├── open_webui/utils/batch_scheduler.py                      # Updated to use unified processor
├── open_webui/utils/daily_batch_processor/__init__.py       # Unified entry point
├── open_webui/utils/daily_batch_processor/models/batch_models.py  # Extended models
└── open_webui/usage_tracking/services/influxdb_first_service.py   # Added batch methods
```

## Implementation Details

### 1. Unified Batch Processor (`unified_batch_processor.py`)

**Core Class**: `UnifiedBatchProcessor`

**Main Method**: `run_daily_batch()`
- Detects InfluxDB-First mode vs legacy mode
- Processes yesterday's data (standard batch timing)
- Handles NBP exchange rate updates
- Manages client-by-client processing
- Provides comprehensive error handling

**Key Methods**:
- `_process_influxdb_first_batch()`: InfluxDB-First processing path
- `_process_client_influxdb_first()`: Per-client InfluxDB aggregation
- `_save_client_daily_usage()`: Updates ClientDailyUsage table
- `_save_client_user_daily_usage()`: Updates ClientUserDailyUsage table
- `health_check()`: Service health monitoring

### 2. Optimized Flux Queries (`influxdb_batch_queries.py`)

**Core Class**: `InfluxDBBatchQueries`

**Optimized Queries**:
```flux
// Daily aggregation by client, model, user
from(bucket: "mai_usage_raw_dev")
  |> range(start: dayStart, stop: dayEnd)
  |> filter(fn: (r) => r._measurement == "usage_tracking")
  |> filter(fn: (r) => r.client_org_id == "client_id")
  |> group(columns: ["client_org_id", "model", "external_user", "_field"])
  |> sum()
  |> pivot(rowKey: ["client_org_id", "model", "external_user"], 
           columnKey: ["_field"], valueColumn: "_value")
```

**Performance Features**:
- Single query per client for efficiency
- Groups by client_org_id, model, external_user
- Sums total_tokens and cost_usd
- Pivots data for easy processing

### 3. Batch Tracking Models (`batch_tracking.py`)

**New Tables**:

#### `influxdb_batch_runs`
Tracks all batch processing runs for monitoring:
- `processing_date`: Date being processed
- `clients_processed`: Number of clients processed
- `influxdb_records_processed`: Raw InfluxDB records read
- `sqlite_summaries_created`: Summary records created/updated
- `data_corrections`: Number of markup corrections
- `success`: Overall batch success status
- `duration_seconds`: Processing time
- `data_source`: Architecture used (influxdb_first/legacy_sqlite)

#### `client_model_daily_usage` (Extended)
Additional granularity for model usage tracking:
- `client_org_id`, `usage_date`, `model`: Composite key
- `total_tokens`, `input_tokens`, `output_tokens`: Token metrics
- `raw_cost_usd`, `markup_cost_usd`, `markup_cost_pln`: Cost metrics
- `source`: Data source tracking

### 4. Batch Scheduler Integration

**Updated Features**:
- Uses `run_unified_daily_batch()` instead of legacy processor
- Improved logging with InfluxDB-First metrics
- Enhanced error reporting with data source information
- Maintains 13:00 CET/CEST schedule for NBP rate alignment

## Configuration

### Environment Variables
```bash
# Enable InfluxDB-First architecture
INFLUXDB_FIRST_ENABLED=true

# InfluxDB connection (existing)
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=dev-token
INFLUXDB_ORG=mAI-dev
INFLUXDB_BUCKET=mai_usage_raw_dev

# NBP service for exchange rates
NBP_SERVICE_URL=http://localhost:8001

# Markup configuration
USAGE_MARKUP_MULTIPLIER=1.3

# Batch processing tuning
INFLUXDB_AGGREGATION_BATCH_SIZE=5
```

## Testing and Validation

### Test Script: `test_unified_batch_processor.py`

**Test Coverage**:
1. **Health Check Test**: Verifies service connectivity
2. **Instance Creation Test**: Validates processor initialization  
3. **Batch Processing Test**: Tests end-to-end processing
4. **InfluxDB Queries Test**: Validates Flux query execution
5. **Legacy Fallback Test**: Tests backward compatibility

**Usage**:
```bash
cd backend
python3 test_unified_batch_processor.py
```

### Database Migration: `create_batch_tracking_tables.py`

**Creates**:
- `influxdb_batch_runs` table for tracking
- `client_model_daily_usage` table for extended summaries
- Initial test records for validation

**Usage**:
```bash
cd backend
python3 create_batch_tracking_tables.py
```

## Benefits

### 1. Performance Improvements
- **Efficient aggregation**: Single query per client vs multiple individual queries
- **Parallel processing**: Multiple clients processed concurrently
- **Reduced database load**: No more SQLite raw data processing
- **Optimized writes**: InfluxDB handles 2-5ms write latency

### 2. Scalability Enhancements
- **Time-series optimized**: InfluxDB designed for high-volume time-series data
- **Horizontal scaling**: InfluxDB can scale across multiple nodes
- **Storage efficiency**: Compressed time-series storage vs SQLite rows
- **Query performance**: Flux queries optimized for aggregation

### 3. Operational Benefits
- **Unified architecture**: Single codebase handles both architectures
- **Comprehensive monitoring**: Batch run tracking and health checks
- **Error resilience**: Robust error handling and fallback mechanisms
- **Data consistency**: Automatic markup correction and validation

### 4. Development Benefits
- **100% backward compatibility**: No breaking changes to existing code
- **Clean architecture**: Separation of concerns between raw data and summaries
- **Testable design**: Isolated components with clear interfaces
- **Future ready**: Foundation for Phase 3 enhancements

## Data Flow Examples

### InfluxDB-First Mode (INFLUXDB_FIRST_ENABLED=true)
```
1. NBP Service → Exchange Rate → SQLite
2. InfluxDB Raw Usage → Flux Aggregation → Client Summaries
3. Client Summaries → SQLite (ClientDailyUsage, ClientUserDailyUsage)
4. Batch Statistics → InfluxDB Batch Run Record
```

### Legacy Mode (INFLUXDB_FIRST_ENABLED=false)
```
1. Fallback to existing daily_batch_processor
2. Standard SQLite aggregation processing
3. Existing summary table updates
```

## Monitoring and Observability

### Health Check Endpoint
```python
health_status = await health_check_unified_batch()
# Returns:
{
    "status": "healthy",
    "influxdb_first_enabled": true,
    "data_source": "influxdb_first",
    "services": {
        "influxdb": {"status": "operational"},
        "nbp": {"status": "operational", "test_rate": "4.1234"}
    }
}
```

### Batch Run Tracking
Every batch run is logged with:
- Processing date and duration
- Clients processed and records aggregated
- Data corrections applied
- Success/failure status
- Error details (if any)

### Logging Integration
Structured logging throughout with:
- Processing progress indicators
- Performance metrics
- Error context and debugging info
- Data validation results

## Next Steps (Phase 3)

The unified batch processor provides the foundation for:

1. **Enhanced Monitoring**: Grafana dashboards for batch processing metrics
2. **Advanced Analytics**: Time-series analysis of usage patterns
3. **Automated Scaling**: Dynamic batch processing based on data volume
4. **Real-time Alerting**: Notifications for batch processing failures
5. **Data Archival**: Automated old data cleanup and archival

## Conclusion

Phase 2: Batch Consolidation successfully unifies the InfluxDB-First architecture with existing batch processing while maintaining 100% backward compatibility. The implementation provides:

- **Seamless migration path** from legacy to InfluxDB-First
- **Performance optimizations** through efficient Flux queries
- **Robust monitoring** and error handling
- **Scalable architecture** ready for production workloads
- **Clean separation** between raw data and summary tables

The unified batch processor is production-ready and provides a solid foundation for future enhancements in Phase 3.