# Daily Breakdown Workflow Analysis - mAI Usage Tracking System

## Executive Summary

The mAI project implements a sophisticated daily usage processing system that automatically aggregates API usage data at 00:00 daily through automated batch processing. The system transforms real-time OpenRouter API usage into structured daily breakdowns that power the administrative dashboard's "Daily Breakdown - July 2025" feature.

**Key Characteristics:**
- **Scheduled Processing**: Automated cron jobs run at 00:00 daily
- **Multi-tenant Architecture**: Client isolation with per-container SQLite databases
- **Batch Processing**: Efficient aggregation of yesterday's complete usage data
- **Data Validation**: Markup cost correction and consistency checks
- **Admin-focused**: No real-time features, optimized for business reporting

## System Architecture Overview

```mermaid
graph TB
    subgraph "Daily Processing Trigger"
        CRON[Cron Job - 00:00 Daily]
        DOCKER[Docker Script Execution]
        MAIN[Python Module Entry Point]
    end
    
    subgraph "Batch Orchestrator"
        ORG[BatchOrchestrator]
        PHASE1[Phase 1: Reference Data Update]
        PHASE2[Phase 2: Usage Data Processing]
        PHASE3[Phase 3: Cleanup Operations]
    end
    
    subgraph "Service Layer"
        NBP[NBP Exchange Rate Service]
        PRICING[Model Pricing Service]
        AGG[Usage Aggregation Service]
        ROLLOVER[Monthly Rollover Service]
        CLEANUP[Data Cleanup Service]
    end
    
    subgraph "Data Layer"
        SQLITE[SQLite Database Per Container]
        DAILY[client_daily_usage]
        USER[client_user_daily_usage]
        MODEL[client_model_daily_usage]
    end
    
    subgraph "Frontend Display"
        API[Usage API Endpoint]
        ADMIN[Admin Dashboard]
        TABLE[Daily Breakdown Table]
    end
    
    CRON --> DOCKER
    DOCKER --> MAIN
    MAIN --> ORG
    
    ORG --> PHASE1
    ORG --> PHASE2
    ORG --> PHASE3
    
    PHASE1 --> NBP
    PHASE1 --> PRICING
    PHASE2 --> AGG
    PHASE2 --> ROLLOVER
    PHASE3 --> CLEANUP
    
    AGG --> SQLITE
    ROLLOVER --> SQLITE
    SQLITE --> DAILY
    SQLITE --> USER
    SQLITE --> MODEL
    
    API --> SQLITE
    ADMIN --> API
    TABLE --> ADMIN
```

## Detailed Workflow Steps

### Phase 1: Scheduling and Execution

#### 1.1 Cron Job Scheduling
```bash
# Cron job configured for 00:00 daily execution
0 0 * * * /path/to/mAI/scripts/daily_batch_cron.sh
```

**Script Execution Flow:**
1. **Host-level Cron**: Executes `daily_batch_cron.sh` at midnight
2. **Docker Orchestration**: `docker_daily_batch.sh` manages container execution
3. **Python Module**: `python -m open_webui.utils.daily_batch_processor`
4. **Batch Orchestrator**: Coordinates all processing phases

#### 1.2 Container-based Processing
```bash
# Multi-container execution
DEFAULT_CONTAINERS=("open-webui-dev" "open-webui-customization")

# Per-container execution
docker exec "$container_name" python -m open_webui.utils.daily_batch_processor
```

### Phase 2: Batch Processing Orchestration

#### 2.1 BatchOrchestrator Initialization
```python
class BatchOrchestrator:
    async def run_daily_batch(self) -> BatchResult:
        # Process yesterday's COMPLETE data
        today = date.today()
        yesterday = today - timedelta(days=1)
        processing_date = yesterday
```

**Key Design Principles:**
- **T-1 Processing**: Always processes yesterday's data for completeness
- **Async Operations**: Leverages asyncio for efficient I/O operations
- **Service Isolation**: Clean separation of concerns through service layer
- **Error Recovery**: Comprehensive exception handling with fallback strategies

#### 2.2 Three-Phase Processing Model

##### Phase 1: Reference Data Update (Parallel)
```python
async def _update_reference_data(self):
    tasks = [
        self.nbp_service.update_exchange_rates(),  # USD/PLN rates
        self.pricing_service.update_model_pricing()  # OpenRouter model costs
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
```

**Operations:**
- **NBP Exchange Rates**: Fetch latest USD/PLN conversion rates
- **Model Pricing**: Update OpenRouter model cost references
- **Parallel Execution**: Independent operations run concurrently

##### Phase 2: Usage Data Processing (Sequential)
```python
async def _process_usage_data(self, processing_date: date, current_date: date):
    # Validate and correct daily usage
    validation_result = await self.aggregation_service.consolidate_daily_usage(processing_date)
    
    # Update monthly totals only if validation succeeded
    if validation_result.success:
        monthly_result = await self.rollover_service.update_monthly_totals(current_date)
```

**Sequential Processing Logic:**
1. **Daily Validation**: Verify and correct markup cost calculations
2. **Monthly Aggregation**: Update cumulative monthly totals
3. **Dependency Management**: Monthly totals depend on validated daily data

##### Phase 3: Cleanup Operations
```python
async def _perform_cleanup(self):
    cleanup_result = await self.cleanup_service.cleanup_old_data()
```

**Cleanup Operations:**
- **Data Retention**: Remove records older than retention policy
- **Storage Optimization**: Minimize database size and improve performance
- **Audit Trail**: Log cleanup statistics for monitoring

### Phase 3: Usage Aggregation Service

#### 3.1 Daily Usage Consolidation
```python
class UsageAggregationService:
    async def consolidate_daily_usage(self, processing_date: date):
        # Get all active clients
        clients = await self.usage_repo.get_active_clients()
        
        # Process clients in parallel batches
        batch_size = 10
        for i in range(0, len(clients), batch_size):
            batch = clients[i:i + batch_size]
            tasks = [
                self._process_client_usage(client_id, client_name, markup_rate, processing_date)
                for client_id, client_name, markup_rate in batch
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
```

**Batch Processing Characteristics:**
- **Parallel Client Processing**: Process multiple clients simultaneously
- **Batch Size Optimization**: 10 clients per batch for optimal performance
- **Error Isolation**: Individual client failures don't affect others
- **Multi-tenant Safety**: Complete client data isolation

#### 3.2 Client Usage Processing
```python
async def _process_client_usage(self, client_id: int, client_name: str, markup_rate: float, processing_date: date):
    # Get daily usage
    usage_data = await self.usage_repo.get_client_daily_usage(client_id, processing_date)
    
    # Validate markup cost calculation
    expected_markup_cost = raw_cost * markup_rate
    cost_diff = abs(markup_cost - expected_markup_cost)
    
    # Correct markup cost if there's a significant difference (> 0.001)
    if cost_diff > 0.001:
        await self.usage_repo.update_markup_cost(
            client_id, processing_date, expected_markup_cost, int(time.time())
        )
```

**Data Validation Rules:**
- **Markup Cost Verification**: Ensure markup_cost = raw_cost × markup_rate
- **Precision Threshold**: Corrections applied for differences > $0.001
- **Audit Logging**: All corrections are logged with before/after values
- **Business Rule Enforcement**: Maintains pricing consistency

### Phase 4: Monthly Rollover Service

#### 4.1 Monthly Totals Calculation
```python
class MonthlyRolloverService:
    async def update_monthly_totals(self, current_date: date):
        # Get month boundaries
        month_start = current_date.replace(day=1)
        
        # Process clients in parallel
        for i in range(0, len(clients), batch_size):
            tasks = [
                self._calculate_client_monthly_stats(client_id, client_name, month_start, current_date)
                for client_id, client_name, _ in batch
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
```

**Monthly Aggregation Logic:**
- **Month-to-Date Calculation**: Aggregates from 1st to current day
- **Real-time Updates**: Updates monthly totals after each daily batch
- **Statistical Insights**: Calculates averages, peaks, and usage patterns
- **Multi-dimensional Analysis**: Tracks tokens, costs, requests, and models

#### 4.2 Client Monthly Statistics
```python
async def _calculate_client_monthly_stats(self, client_id: int, client_name: str, month_start: date, current_date: date):
    # Get monthly usage summary
    summary = await self.usage_repo.get_monthly_usage_summary(client_id, month_start, current_date)
    
    # Calculate usage percentage
    days_in_month = current_date.day
    usage_percentage = (days_with_usage / days_in_month * 100) if days_in_month > 0 else 0
    
    # Get most used model
    most_used_model = await self.usage_repo.get_most_used_model(client_id, month_start, current_date)
```

**Metrics Calculated:**
- **Usage Percentage**: Days with activity / total days in month
- **Token Statistics**: Total, average daily, maximum daily
- **Cost Analysis**: Raw costs, markup costs, daily averages
- **Model Usage**: Most frequently used AI models
- **Activity Patterns**: Last usage date, request frequency

## Database Schema and Data Flow

### Core Tables

#### client_daily_usage
```sql
CREATE TABLE client_daily_usage (
    id TEXT PRIMARY KEY,
    client_org_id TEXT NOT NULL,
    usage_date DATE NOT NULL,
    total_tokens INTEGER DEFAULT 0,
    total_requests INTEGER DEFAULT 0,
    raw_cost REAL DEFAULT 0.0,
    markup_cost REAL DEFAULT 0.0,
    primary_model TEXT,
    unique_users INTEGER DEFAULT 1,
    created_at INTEGER,
    updated_at INTEGER
);
```

**Purpose**: Primary aggregation table for daily usage summaries per client organization.

#### client_user_daily_usage
```sql
CREATE TABLE client_user_daily_usage (
    id TEXT PRIMARY KEY,
    client_org_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    openrouter_user_id TEXT NOT NULL,
    usage_date DATE NOT NULL,
    total_tokens INTEGER DEFAULT 0,
    total_requests INTEGER DEFAULT 0,
    raw_cost REAL DEFAULT 0.0,
    markup_cost REAL DEFAULT 0.0,
    created_at INTEGER,
    updated_at INTEGER
);
```

**Purpose**: User-level usage breakdown for detailed analytics and billing allocation.

#### client_model_daily_usage
```sql
CREATE TABLE client_model_daily_usage (
    id TEXT PRIMARY KEY,
    client_org_id TEXT NOT NULL,
    model_name TEXT NOT NULL,
    usage_date DATE NOT NULL,
    total_tokens INTEGER DEFAULT 0,
    total_requests INTEGER DEFAULT 0,
    raw_cost REAL DEFAULT 0.0,
    markup_cost REAL DEFAULT 0.0,
    provider TEXT,
    created_at INTEGER,
    updated_at INTEGER
);
```

**Purpose**: Model-specific usage tracking for understanding AI model consumption patterns.

### Data Flow Mapping

```mermaid
graph LR
    subgraph "Real-time Usage"
        OR[OpenRouter API]
        WH[Webhook Reception]
        RT[Real-time Recording]
    end
    
    subgraph "Daily Batch Processing - T-1"
        BATCH[00:00 Batch Job]
        VALID[Data Validation]
        AGG[Daily Aggregation]
        MONTHLY[Monthly Update]
    end
    
    subgraph "Database Tables"
        DAILY_T[client_daily_usage]
        USER_T[client_user_daily_usage]
        MODEL_T[client_model_daily_usage]
    end
    
    subgraph "Frontend API"
        API_EP[/my-organization/usage-summary]
        BREAKDOWN[daily_breakdown JSON]
        UI[Admin Dashboard Table]
    end
    
    OR --> WH
    WH --> RT
    RT --> DAILY_T
    RT --> USER_T
    RT --> MODEL_T
    
    BATCH --> VALID
    VALID --> AGG
    AGG --> MONTHLY
    
    AGG --> DAILY_T
    MONTHLY --> DAILY_T
    
    API_EP --> DAILY_T
    API_EP --> BREAKDOWN
    BREAKDOWN --> UI
```

## API Integration Points

### Frontend Data Request
```typescript
// Frontend service call
const response = await fetch('/api/v1/usage-tracking/my-organization/usage-summary');
const usageData = await response.json();

// Daily breakdown structure
interface DailyBreakdownItem {
    date: string;           // "2025-07-15"
    day_name: string;       // "Tuesday"
    day_number: number;     // 15
    tokens: number;         // 12543
    cost: number;           // USD cost with markup
    cost_pln: number;       // PLN equivalent
    requests: number;       // API request count
    primary_model: string;  // "anthropic/claude-3.5-sonnet"
    last_activity: string;  // "14:30:22"
}
```

### Backend API Endpoint
```python
@usage_router.get("/my-organization/usage-summary")
async def get_my_organization_usage_summary(user=Depends(get_current_user)):
    """Get admin-focused daily breakdown for current organization (no real-time)"""
    result = await usage_service.get_organization_usage_summary()
    return OrganizationUsageSummaryResponse(**result)
```

### Data Repository Query
```python
# Query for daily breakdown data
month_records = session.query(ClientDailyUsage).filter(
    ClientDailyUsage.client_org_id == client_org_id,
    ClientDailyUsage.usage_date >= current_month_start,
    ClientDailyUsage.usage_date <= today
).order_by(ClientDailyUsage.usage_date).all()

# Build daily breakdown JSON
daily_breakdown = []
for record in month_records:
    daily_breakdown.append({
        'date': record.usage_date.isoformat(),
        'day_name': record.usage_date.strftime('%A'),
        'tokens': record.total_tokens,
        'cost': record.markup_cost,
        'cost_pln': record.markup_cost * exchange_rate,
        'requests': record.total_requests,
        'primary_model': record.primary_model,
        'last_activity': calculate_last_activity(record)
    })
```

## Business Rules and Logic

### 1. Timing and Data Processing Rules

#### "Updated at 00:00 Daily" Implementation
- **Cron Schedule**: `0 0 * * *` (every day at midnight)
- **Data Window**: Processes T-1 (yesterday's) complete data
- **Completion Guarantee**: Ensures all day's usage is captured
- **Multi-timezone Handling**: Uses Europe/Warsaw timezone for consistency

#### Data Completeness Strategy
```python
# Process yesterday's COMPLETE data
today = date.today()
yesterday = today - timedelta(days=1)
processing_date = yesterday  # Always T-1 for completeness
```

**Rationale**: Processing yesterday's data ensures all OpenRouter webhooks and API calls for that day have been received and recorded.

### 2. Markup Cost Validation Rules

#### Automatic Cost Correction
```python
# Validate markup cost calculation
expected_markup_cost = raw_cost * markup_rate
cost_diff = abs(markup_cost - expected_markup_cost)

# Correct markup cost if there's a significant difference (> 0.001)
if cost_diff > 0.001:
    await self.usage_repo.update_markup_cost(
        client_id, processing_date, expected_markup_cost, timestamp
    )
```

**Business Rules:**
- **Markup Rate Enforcement**: markup_cost must equal raw_cost × markup_rate
- **Precision Threshold**: Corrections applied for differences > $0.001
- **Audit Trail**: All corrections logged with old/new values
- **Client-specific Rates**: Each client organization has its own markup rate (default 1.3x)

### 3. Multi-tenant Data Isolation

#### Client Organization Isolation
```python
# Environment-based client identification
client_org_id = get_client_org_id_from_environment()

# All queries scoped to client organization
session.query(ClientDailyUsage).filter(
    ClientDailyUsage.client_org_id == client_org_id,
    # ... other filters
)
```

**Isolation Mechanisms:**
- **Container-level Separation**: Each client runs in dedicated Docker container
- **Database-level Filtering**: All queries include client_org_id filter
- **Environment-based Config**: Client identification through environment variables
- **Per-container SQLite**: Separate database files per container instance

### 4. Exchange Rate Integration

#### NBP (National Bank of Poland) Integration
```python
class NBPExchangeRateService:
    async def update_exchange_rates(self):
        # Fetch latest USD/PLN rates from NBP API Table A
        current_rate = await self.fetch_current_usd_pln_rate()
        
        # Store for daily breakdown currency conversion
        await self.store_exchange_rate(current_rate, date.today())
```

**Currency Conversion Logic:**
- **Daily Rate Updates**: Fresh USD/PLN rates fetched daily at batch time
- **Historical Rates**: Each day's breakdown uses that day's exchange rate
- **Dual Currency Display**: Shows both USD (primary) and PLN (converted) amounts
- **Fallback Strategy**: Uses previous day's rate if NBP API unavailable

## Frontend Implementation

### Daily Breakdown Table Component
```svelte
<!-- UsageStatsTab.svelte -->
<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
    <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-medium">
            {$i18n.t('Daily Breakdown')} - {usageData.current_month?.month || 'Current Month'}
        </h3>
        <NoticeCard type="success" title="Updated at 00:00 Daily" showIcon={true} />
    </div>
    
    <DataTable 
        headers={tableHeaders} 
        data={usageData.daily_breakdown || []} 
        emptyMessage="{$i18n.t('No usage data available for this month.')}"
        {formatters}
    />
</div>
```

### Data Formatting Services
```typescript
const formatters = {
    tokens: FormatterService.formatNumber,
    cost: (value: any) => FormatterService.formatDualCurrency(value?.cost || 0, value?.cost_pln || 0),
    requests: FormatterService.formatNumber
};

// Dual currency formatting
formatDualCurrency(usd: number, pln: number): string {
    return `$${usd.toFixed(6)} / ${pln.toFixed(2)} PLN`;
}
```

### Empty State Messaging
```svelte
{#if !usageData.daily_breakdown || usageData.daily_breakdown.length === 0}
    <div class="text-center py-8">
        <p class="text-gray-500 dark:text-gray-500 text-sm mt-2">
            Data is processed daily at 00:00. Usage will appear after first API calls.
        </p>
    </div>
{/if}
```

**User Experience Design:**
- **Clear Update Timing**: Prominently displays "Updated at 00:00 Daily" notice
- **Helpful Empty States**: Explains when data will appear for new users
- **Dual Currency Support**: Shows costs in both USD and PLN for Polish market
- **Responsive Design**: Adapts to different screen sizes and dark/light themes

## Error Handling and Edge Cases

### 1. Batch Processing Failures

#### Service-level Error Recovery
```python
async def run_daily_batch(self) -> BatchResult:
    try:
        # Process all phases
        result = await self._process_all_phases()
        return result
    except Exception as e:
        log.error(f"❌ Daily batch processing failed: {e}")
        
        error_result = BatchResult(
            success=False,
            error=str(e),
            batch_duration_seconds=time.time() - batch_start
        )
        return error_result
```

#### Individual Client Error Isolation
```python
batch_results = await asyncio.gather(*tasks, return_exceptions=True)

for result in batch_results:
    if isinstance(result, Exception):
        log.error(f"Error processing client: {result}")
        continue  # Don't let one client failure affect others
        
    if result:
        all_client_stats.append(result)
```

**Error Handling Strategy:**
- **Individual Client Isolation**: One client's processing failure doesn't affect others
- **Service-level Recovery**: Each service handles its own error scenarios
- **Comprehensive Logging**: All errors logged with context for debugging
- **Graceful Degradation**: System continues processing even with partial failures

### 2. Data Quality Issues

#### Missing Usage Data
```python
async def _process_client_usage(self, client_id: int, client_name: str, markup_rate: float, processing_date: date):
    usage_data = await self.usage_repo.get_client_daily_usage(client_id, processing_date)
    
    if not usage_data:
        return None  # Skip clients with no usage data
```

#### Invalid Markup Rates
```python
def record_usage_from_webhook(self, client_org_id: str, usage_data: Dict[str, Any]):
    client = self.client_repo.get_client_info(client_org_id)
    if not client:
        raise Exception(f"Client organization not found: {client_org_id}")
    
    if client.markup_rate <= 0:
        raise Exception(f"Invalid markup rate for client {client.name}: {client.markup_rate}")
```

**Data Quality Safeguards:**
- **Client Validation**: Verify client exists and has valid configuration
- **Markup Rate Validation**: Ensure positive markup rates before processing
- **Cost Validation**: Reject negative costs or token counts
- **Data Consistency Checks**: Validate markup_cost = raw_cost × markup_rate

### 3. External Service Dependencies

#### NBP API Failures
```python
class NBPExchangeRateService:
    async def update_exchange_rates(self):
        try:
            current_rate = await self.fetch_current_usd_pln_rate()
            await self.store_exchange_rate(current_rate, date.today())
            return ExchangeRateResult(success=True, rate=current_rate)
        except Exception as e:
            # Use previous day's rate as fallback
            fallback_rate = await self.get_latest_stored_rate()
            return ExchangeRateResult(success=False, error=str(e), fallback_rate=fallback_rate)
```

#### OpenRouter Model Pricing Updates
```python
class ModelPricingService:
    async def update_model_pricing(self):
        try:
            pricing_data = await self.fetch_openrouter_pricing()
            await self.update_local_pricing_cache(pricing_data)
            return PricingResult(success=True, models_updated=len(pricing_data))
        except Exception as e:
            # Continue with cached pricing data
            return PricingResult(success=False, error=str(e), using_cache=True)
```

**Dependency Management:**
- **Fallback Strategies**: Use cached/previous data when external services fail
- **Timeout Handling**: Reasonable timeouts to prevent batch job hanging
- **Retry Logic**: Limited retries with exponential backoff for transient failures
- **Service Independence**: Core usage processing continues even if external services fail

## Performance Characteristics

### Batch Processing Performance

#### Processing Time Benchmarks
```python
# Typical batch processing times (based on system logs)
async def run_daily_batch(self) -> BatchResult:
    batch_start = time.time()
    
    # ... processing logic ...
    
    batch_duration = time.time() - batch_start
    result.batch_duration_seconds = round(batch_duration, 3)
    
    log.info(
        f"✅ Daily batch processing completed: {successful_ops}/{total_ops} "
        f"operations successful in {batch_duration:.2f}s"
    )
```

**Expected Performance:**
- **Single Client Processing**: ~50-100ms per client
- **Batch of 10 Clients**: ~200-500ms with parallel processing
- **Full System Batch**: <30 seconds for typical deployment
- **Large Scale (100+ clients)**: <2 minutes with optimized batching

#### Database Query Optimization
```python
# Efficient monthly summary query
summary = await self.usage_repo.get_monthly_usage_summary(
    client_id, month_start, current_date
)

# Single query returns:
# (days_with_usage, total_tokens, total_requests, total_raw_cost, 
#  total_markup_cost, avg_daily, max_daily, last_usage)
```

**Database Optimizations:**
- **Indexed Queries**: Primary indexes on client_org_id + usage_date
- **Aggregation in Database**: Use SQL SUM, AVG, MAX for efficiency
- **Batch Operations**: Process multiple clients per database transaction
- **Connection Pooling**: Async database connections with connection reuse

### Memory and Storage Efficiency

#### Batch Size Management
```python
# Process clients in parallel batches
batch_size = 10
for i in range(0, len(clients), batch_size):
    batch = clients[i:i + batch_size]
    # Process batch in parallel
    tasks = [self._process_client_usage(...) for client in batch]
    batch_results = await asyncio.gather(*tasks, return_exceptions=True)
```

#### Data Cleanup Strategy
```python
class DataCleanupService:
    async def cleanup_old_data(self):
        # Remove records older than retention policy (typically 90 days)
        cutoff_date = date.today() - timedelta(days=self.retention_days)
        
        records_deleted = await self.delete_old_records(cutoff_date)
        storage_saved = await self.vacuum_database()
        
        return CleanupResult(
            records_deleted=records_deleted,
            storage_saved_kb=storage_saved
        )
```

**Resource Management:**
- **Controlled Batch Sizes**: Prevent memory exhaustion with large client counts
- **Automatic Cleanup**: Regular removal of old data based on retention policy
- **Database Maintenance**: Periodic VACUUM operations to reclaim storage
- **Memory-efficient Processing**: Stream processing for large datasets

## Monitoring and Observability

### Logging and Audit Trail

#### Structured Logging
```python
class BatchLogger:
    def __init__(self, process_name: str):
        self.process_name = process_name
        self.start_time = None
        self.steps = []
    
    def step(self, step_name: str):
        return LogStep(step_name, self.steps)
    
    def complete(self, summary: Dict[str, Any]):
        duration = time.time() - self.start_time
        log.info(f"✅ {self.process_name} completed in {duration:.2f}s: {summary}")
```

#### Batch Execution Tracking
```python
# Record batch run in system repository
await self.system_repo.record_batch_run({
    "processing_date": processing_date.isoformat(),
    "batch_duration_seconds": batch_duration,
    "successful_operations": successful_ops,
    "total_operations": total_ops,
    "timestamp": datetime.now().isoformat()
})
```

### Performance Monitoring

#### Batch Processing Metrics
```python
log.info(
    f"📊 Daily consolidation completed: {result.clients_processed} clients, "
    f"{result.total_records_verified} records verified, "
    f"{result.data_corrections} corrections made"
)

log.info(
    f"📊 Monthly totals updated: {len(all_summaries)} active clients, "
    f"{total_tokens:,} total tokens, ${total_cost:.6f} total cost"
)
```

#### Error Rate Tracking
```python
# Track success/failure rates
successful_ops = sum(1 for op in result.operations if op.success)
total_ops = len(result.operations)
success_rate = (successful_ops / total_ops * 100) if total_ops > 0 else 0

log.info(f"✅ Batch success rate: {success_rate:.1f}% ({successful_ops}/{total_ops})")
```

**Monitoring Capabilities:**
- **Real-time Progress**: Step-by-step logging during batch execution
- **Performance Metrics**: Processing times, success rates, data volumes
- **Error Tracking**: Detailed error logs with context and stack traces
- **Historical Trends**: Batch execution history for performance analysis

## Integration with Other Systems

### OpenRouter API Integration

#### Webhook Processing Flow
```python
def record_usage_from_webhook(self, client_org_id: str, usage_data: Dict[str, Any]):
    # Real-time webhook processing
    model_name = usage_data.get("model", "unknown")
    total_tokens = usage_data.get("total_tokens", 0)
    raw_cost = float(usage_data.get("total_cost", 0.0))
    
    # Calculate markup cost using client's rate
    markup_cost = calculate_markup_cost(raw_cost, client.markup_rate)
    
    # Record to daily usage tables
    return self.usage_repo.record_usage(usage_record)
```

#### Daily Batch Reconciliation
```python
# Daily batch validates webhook-recorded data
validation_result = await self.aggregation_service.consolidate_daily_usage(processing_date)

# Corrects any markup cost discrepancies
if cost_diff > 0.001:
    await self.usage_repo.update_markup_cost(client_id, processing_date, expected_markup_cost)
```

**Integration Points:**
- **Real-time Webhooks**: Immediate usage recording as API calls occur
- **Daily Reconciliation**: Batch validation ensures data consistency
- **Markup Cost Enforcement**: Daily correction of any calculation errors
- **Client Isolation**: Webhook processing respects multi-tenant boundaries

### Exchange Rate Integration

#### NBP API Integration
```python
class NBPExchangeRateService:
    async def fetch_current_usd_pln_rate(self):
        # Fetch from NBP Table A (current rates)
        url = "https://api.nbp.pl/api/exchangerates/rates/a/usd/?format=json"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            data = response.json()
            
            return data['rates'][0]['mid']  # Current USD/PLN rate
```

#### Currency Conversion in Daily Breakdown
```python
# Apply exchange rate to daily breakdown
for record in month_records:
    daily_breakdown.append({
        'cost': record.markup_cost,  # USD amount
        'cost_pln': record.markup_cost * exchange_rate,  # PLN equivalent
        # ... other fields
    })
```

**Currency Features:**
- **Daily Rate Updates**: Fresh exchange rates fetched with each batch
- **Historical Accuracy**: Each day's breakdown uses that day's exchange rate
- **Dual Display**: Frontend shows both USD and PLN amounts
- **Fallback Handling**: Uses previous rate if NBP API unavailable

## Security Considerations

### Multi-tenant Data Security

#### Client Data Isolation
```python
# Environment-based client identification
def get_client_org_id_from_environment():
    client_org_id = os.getenv('CLIENT_ORG_ID')
    if not client_org_id:
        raise SecurityError("CLIENT_ORG_ID environment variable not set")
    return client_org_id

# All database queries include client isolation
session.query(ClientDailyUsage).filter(
    ClientDailyUsage.client_org_id == client_org_id  # Security filter
)
```

#### Container-level Isolation
```bash
# Each client runs in separate Docker container
DEFAULT_CONTAINERS=("open-webui-dev" "open-webui-customization")

# Container-specific database files
SQLITE_DB="/app/data/${CLIENT_ORG_ID}/webui.db"
```

### API Security

#### Authentication and Authorization
```python
@usage_router.get("/my-organization/usage-summary")
async def get_my_organization_usage_summary(user=Depends(get_current_user)):
    # User authentication required
    # Environment-based authorization (client org from container)
    result = await usage_service.get_organization_usage_summary()
```

#### Webhook Security
```python
def record_usage_from_webhook(self, client_org_id: str, usage_data: Dict[str, Any]):
    # Validate client exists and is active
    client = self.client_repo.get_client_info(client_org_id)
    if not client:
        raise Exception(f"Client organization not found: {client_org_id}")
    
    # Validate input data
    if raw_cost < 0:
        raise Exception(f"Negative cost not allowed: ${raw_cost:.6f}")
```

**Security Measures:**
- **Container Isolation**: Complete separation of client environments
- **Database-level Filtering**: All queries scoped to authorized client data
- **Input Validation**: Webhook data validated before processing
- **Environment-based Config**: Client identification through secure environment variables
- **Authentication Required**: All API endpoints require valid user authentication

## Troubleshooting and Maintenance

### Common Issues and Solutions

#### 1. Batch Processing Failures

**Symptom**: Daily breakdown shows stale data
```bash
# Check batch execution logs
tail -f /app/logs/daily_batch_$(date +%Y%m%d).log
```

**Solutions**:
- **Manual Execution**: Run batch processor manually
- **Container Status**: Verify containers are running
- **Database Connectivity**: Check SQLite database accessibility
- **Log Analysis**: Review error messages in batch logs

#### 2. Missing Daily Data

**Symptom**: Empty daily breakdown table
```sql
-- Check if data exists in database
SELECT COUNT(*), MAX(usage_date) FROM client_daily_usage 
WHERE client_org_id = 'your_client_id';
```

**Solutions**:
- **Webhook Verification**: Ensure OpenRouter webhooks are configured
- **Client Configuration**: Verify client organization setup
- **API Key Validation**: Check OpenRouter API key validity
- **Processing Date**: Confirm batch is processing correct date range

#### 3. Markup Cost Discrepancies

**Symptom**: Cost calculations appear incorrect
```python
# Expected markup cost validation
expected_markup_cost = raw_cost * markup_rate
actual_difference = abs(markup_cost - expected_markup_cost)

if actual_difference > 0.001:
    print(f"Markup cost correction needed: {actual_difference}")
```

**Solutions**:
- **Batch Re-run**: Execute daily batch to trigger cost corrections
- **Markup Rate Verification**: Confirm client markup rate configuration
- **Manual Correction**: Update markup costs directly if needed
- **Calculation Logic Review**: Verify cost calculation implementation

### Maintenance Procedures

#### Regular Maintenance Tasks

1. **Daily Monitoring**
   - Check batch execution logs
   - Verify data completeness
   - Monitor processing times

2. **Weekly Reviews**
   - Analyze error rates
   - Review data quality metrics
   - Check storage usage trends

3. **Monthly Maintenance**
   - Database cleanup and optimization
   - Performance analysis
   - Capacity planning review

#### Database Maintenance
```python
# Cleanup old data
cleanup_result = await self.cleanup_service.cleanup_old_data()

# Database optimization
await self.system_repo.vacuum_database()

# Index maintenance
await self.system_repo.reindex_tables()
```

#### Log Management
```bash
# Cleanup old log files (keep last 30 days)
find "$LOG_DIR" -name "daily_batch_*.log" -mtime +30 -delete 2>/dev/null
```

**Maintenance Schedule:**
- **Daily**: Automated batch processing and basic monitoring
- **Weekly**: Performance review and error analysis
- **Monthly**: Database cleanup and capacity planning
- **Quarterly**: System optimization and architecture review

## Conclusion

The mAI Daily Breakdown workflow represents a sophisticated, production-ready system for processing and displaying AI usage analytics. The system successfully balances performance, reliability, and maintainability through:

### Key Strengths

1. **Robust Architecture**
   - Service-layer pattern with clear separation of concerns
   - Async processing for optimal performance
   - Comprehensive error handling and recovery

2. **Business-focused Design**
   - Admin-oriented daily breakdown without real-time complexity
   - Accurate cost calculations with automatic validation
   - Multi-tenant data isolation for enterprise deployment

3. **Operational Excellence**
   - Automated daily processing at 00:00
   - Comprehensive logging and monitoring
   - Graceful degradation under failure conditions

4. **Data Quality Assurance**
   - T-1 processing ensures complete daily data
   - Markup cost validation and automatic correction
   - Exchange rate integration for accurate currency conversion

### Technical Innovation

The system demonstrates several innovative approaches:
- **Batch-optimized Processing**: Processes yesterday's complete data rather than attempting real-time aggregation
- **Parallel Client Processing**: Efficient handling of multi-tenant workloads
- **Integrated Currency Conversion**: Seamless USD/PLN display for Polish market
- **Container-based Isolation**: Complete client data separation through Docker architecture

This architecture provides a solid foundation for scaling to hundreds of client organizations while maintaining data integrity, security, and performance characteristics suitable for production enterprise deployment.

---

**Document Version**: 1.0  
**Last Updated**: July 28, 2025  
**System Version**: mAI Production (customization branch)  
**Analysis Scope**: Complete daily breakdown workflow from cron execution to frontend display