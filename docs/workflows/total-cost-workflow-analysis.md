Wytłumacz mi na podstawie tej dokumentacji jak naliczane jest zużycie tokentów: # Total Cost Feature Workflow Analysis

## Overview
This document provides a comprehensive analysis of the "Total Cost" The feature displays dual-currency cost calculations with daily batch processing and real-time NBP exchange rate integration.

## Feature Architecture

### Core Components
- **Backend Cost Calculator**: `/backend/open_webui/utils/cost_calculator.py`
- **NBP Exchange Rate Client**: `/backend/open_webui/utils/nbp_client.py`
- **Daily Batch Processor**: `/backend/open_webui/utils/daily_batch_processor/`
- **Frontend Display Logic**: `/src/lib/components/admin/Settings/MyOrganizationUsage/`
- **Currency Formatter**: `/src/lib/components/admin/Settings/MyOrganizationUsage/services/formatters.ts`

---

## Complete Business Logic Flow

### 1. Cost Data Collection from OpenRouter

#### Entry Points
**Webhook Endpoint**: `POST /webhook/openrouter-usage`
- **File**: `/backend/open_webui/usage_tracking/routers/webhook_router.py`
- **Processing**: Background task execution to avoid blocking
- **Note**: OpenRouter doesn't have native webhooks, but endpoint exists for future integrations

**Manual Sync**: `POST /sync/openrouter-usage` (Primary method)
- **Authentication**: Admin-only access required
- **Usage**: Primary data collection method since OpenRouter lacks webhooks

#### Cost Calculation Engine
**Location**: `/backend/open_webui/utils/cost_calculator.py`

**Core Functions**:
```python
def calculate_markup_cost(raw_cost: float, markup_rate: float) -> float:
    # Business Rule: Apply 1.3x markup (30% markup)
    return raw_cost * markup_rate

def calculate_generation_costs(generation_data, client_org_id) -> Tuple[float, float, int]:
    # CRITICAL: Use correct OpenRouter API field names (Fixed 2025-01-27)
    # Use normalized tokens (not native tokens) as per OpenRouter docs
    prompt_tokens = generation_data.get("tokens_prompt", 0)
    completion_tokens = generation_data.get("tokens_completion", 0)
    tokens = prompt_tokens + completion_tokens
    
    # Use 'usage' field for cost (not 'total_cost')
    raw_cost = float(generation_data.get("usage", 0.0))
    
    # Apply: Client-specific markup rate (default 1.3x)
    # Return: (raw_cost, markup_cost, tokens)
```

**Validation Rules**:
- Raw cost cannot be negative
- Tokens cannot be negative
- Markup rate must be > 0
- Client organization must exist and be active

### 2. Exchange Rate Integration

#### NBP API Integration
**Location**: `/backend/open_webui/utils/nbp_client.py`

**Holiday-Aware Rate Fetching**:
```python
async def get_usd_pln_rate() -> Optional[Dict[str, Any]]:
    # TIER 1: Holiday Calendar Optimization
    # - Skip API calls for known Polish holidays/weekends
    # - Use last working day rate automatically
    
    # TIER 2: Working Day Strategy with Time Logic
    # - Before 11:30 AM: Might use previous day's rate
    # - After 11:30 AM: Current day rate should be available
    
    # TIER 3: Enhanced 404 Fallback
    # - Handles unknown non-publication days
    # - Searches backwards up to 10 days for valid rate
```

**Business Rules**:
- **NBP Table A** (Average rates) used for consistency
- **Publication Time**: 11:30 AM CET daily (based on NBP Resolution No. 51/2002)
- **Cache TTL**: 24 hours for standard rates, shorter for fallback scenarios
- **Fallback Rate**: 4.0 PLN if NBP unavailable

#### Exchange Rate Application Timing
**Service**: `/backend/open_webui/utils/daily_batch_processor/services/nbp_service.py`

```python
async def update_exchange_rates() -> ExchangeRateResult:
    # Fetch fresh rate with holiday-aware logic
    exchange_info = await get_exchange_rate_info()
    
    # Apply to all cost calculations
    result = ExchangeRateResult(
        usd_pln_rate=exchange_info.get("usd_pln", 4.0),
        effective_date=exchange_info.get("effective_date"),
        rate_source=exchange_info.get("rate_source")
    )
```

### 3. Daily Batch Processing Workflow

#### Batch Processing Schedule
- **Time**: 13:00 CET daily (1 PM CET)
- **Scope**: Full month recalculation (1st to current day)
- **Data Sources**: OpenRouter API, NBP exchange rates
- **Timing Rationale**: Aligned with NBP exchange rate publication schedule (11:30 AM CET)

#### Cost Aggregation Methods
**Multi-Level Aggregation**:
1. **Individual Generation Level**: Raw cost → Markup cost
2. **Daily Level**: Sum all generations per day per user
3. **User Level**: Aggregate user daily totals
4. **Organization Level**: Sum all user totals
5. **Monthly Level**: Running total from 1st to current day

**Business Logic Pattern**:
```python
# For each generation:
raw_cost = generation_data.get("total_cost", 0.0)
markup_cost = raw_cost * client.markup_rate  # Default 1.3x

# Daily aggregation:
daily_total_usd = sum(markup_costs_for_day)
daily_total_pln = daily_total_usd * current_exchange_rate

# Monthly running total:
monthly_total_usd = sum(daily_totals_from_1st_to_current)
monthly_total_pln = sum(daily_pln_totals_from_1st_to_current)
```

#### Currency Conversion Business Rules
1. **USD First**: All costs calculated in USD with markup
2. **PLN Conversion**: Applied using daily NBP rate at batch time
3. **Precision**: USD to 6 decimals for small amounts, PLN to 2 decimals
4. **Consistency**: Same exchange rate used for entire daily batch

---

## Frontend Display Logic

### Dual Currency Formatting
**Location**: `/src/lib/components/admin/Settings/MyOrganizationUsage/services/formatters.ts`

```typescript
static formatDualCurrency(usdAmount: number, plnAmount?: number): string {
    if (plnAmount !== undefined && plnAmount !== null) {
        return `${this.formatCurrency(usdAmount)} (${this.formatCurrency(plnAmount, 'PLN')})`;
    }
    // Fallback to USD only if PLN not available
    return this.formatCurrency(usdAmount);
}

static formatCurrency(amount: number, currency: 'USD' | 'PLN' = 'USD'): string {
    // For very small USD amounts, show 6 decimal places
    if (value > 0 && value < 0.01 && currency === 'USD') {
        return new Intl.NumberFormat('en-US', {
            minimumFractionDigits: 6,
            maximumFractionDigits: 6
        }).format(value);
    }
    // Standard 2 decimal places for normal amounts
    return new Intl.NumberFormat(locale, currencyOptions).format(value);
}
```

### Display Component Structure
**Location**: `/src/lib/components/admin/Settings/MyOrganizationUsage/MyOrganizationUsageContainer.svelte`

```svelte
<StatCard
    title="Total Cost"
    value={FormatterService.formatDualCurrency(
        usageData.current_month?.total_cost || 0, 
        usageData.current_month?.total_cost_pln || 0
    )}
    subtitle="{currentMonthName} • Batch Calculated"
    iconColor="green"
/>
```

### Label Generation Logic
**Components**:
1. **Month Name**: Dynamic JavaScript date formatting
   ```javascript
   currentMonthName = new Date().toLocaleDateString('en-US', { 
       month: 'long', 
       year: 'numeric' 
   });
   ```
2. **"Batch Calculated"**: Static label indicating daily batch processing
3. **Exchange Rate Notice**: Dynamic display of current NBP rate

### Zero Value Handling
**Rules**:
- **$0.00 (0,00 zł)**: Both currencies show zero when no usage
- **$0.00**: USD only if PLN conversion unavailable
- **Precision**: Small amounts show 6 decimals ($0.000123)

---

## Real-Time Streaming Usage Capture Architecture

### Production Streaming Response System
**Location**: `/backend/open_webui/routers/openai.py`

**Critical Achievement**: The system now captures **100% of OpenRouter usage** including streaming responses with **zero latency impact**.

#### UsageCapturingStreamingResponse Implementation
```python
class UsageCapturingStreamingResponse(StreamingResponse):
    """Production-ready streaming response with real-time usage capture"""
    
    async def __call__(self, scope, receive, send):
        # Stream content immediately to user (zero latency)
        async for chunk in self.content:
            yield chunk  # Real-time streaming preserved
            buffered_chunks.append(chunk)  # Background buffering
        
        # Parse final SSE chunk for usage data (background task)
        await self.extract_and_record_usage(buffered_chunks)
```

#### Key Technical Features
1. **Server-Sent Events (SSE) Parsing**: Processes streaming chunks in real-time
2. **Zero-Latency Design**: Content streams immediately, usage extraction in background
3. **Production Error Handling**: Graceful degradation with comprehensive logging
4. **Background Processing**: AsyncIO tasks for non-blocking operations

#### Real-Time Usage Data Flow
```
OpenRouter Streaming Response → SSE Chunk Parsing → Usage Data Extraction → 
Background Recording → Database Storage → Generation ID Deduplication
```

**Previously Missing Data**: ~50% of conversational usage was lost from streaming responses
**Current Coverage**: 100% of all OpenRouter queries (streaming + non-streaming)

---

## Integration Points

### OpenRouter Cost Webhooks
**Endpoints**:
- `POST /webhook/openrouter-usage`: Future webhook support
- `POST /sync/openrouter-usage`: Current manual sync method

**Data Flow**:
```
OpenRouter API → Manual Sync → Cost Calculator → Database Storage
```

**Key Data Points (Updated Field Mapping)**:
- `usage`: Raw USD cost from OpenRouter (not `total_cost`)
- `tokens_prompt` + `tokens_completion`: Token counts (not `total_tokens`)
- `model`: Model used for cost calculation
- `generation_id`: Unique identifier for duplicate prevention

### NBP API Integration
**Endpoint**: `https://api.nbp.pl/api/exchangerates/tables/a/{date}/`

**Data Flow**:
```
NBP API → Holiday-Aware Client → Cache → Daily Batch → Cost Conversion
```

**Response Structure**:
```json
{
    "rate": 3.6446,
    "effective_date": "2024-01-15",
    "table_no": "012/A/NBP/2024",
    "rate_source": "current|working_day|holiday_skip|fallback_404"
}
```

### Database Storage Patterns
**Tables**:
- `client_daily_usage`: Daily aggregated costs per organization
- `client_user_daily_usage`: Daily costs per user
- `client_organizations`: Markup rate configuration

**Storage Pattern**:
```sql
-- Daily cost storage
INSERT INTO client_daily_usage (
    client_org_id, date, total_cost_usd, total_cost_pln, 
    total_tokens, exchange_rate, effective_date
);

-- Monthly totals calculated as running sum
SELECT SUM(total_cost_usd) as monthly_total_usd,
       SUM(total_cost_pln) as monthly_total_pln
FROM client_daily_usage 
WHERE client_org_id = ? 
  AND date BETWEEN first_of_month AND current_date;
```

### Frontend API Consumption
**Endpoint**: `GET /my-organization/usage-summary`

**Response Structure**:
```json
{
    "current_month": {
        "total_cost": 123.45,
        "total_cost_pln": 450.67,
        "total_tokens": 50000,
        "month": "July 2025",
        "exchange_rate_info": {
            "usd_pln": 3.6446,
            "effective_date": "2024-01-15",
            "rate_source": "current"
        }
    }
}
```

---

## Business Rules Analysis

### Cost Calculation Formulas
1. **Base Formula**: `markup_cost = raw_cost × markup_rate`
2. **Default Markup**: 1.3x (30% markup) - configurable per client
3. **PLN Conversion**: `pln_cost = usd_cost × nbp_rate`
4. **Monthly Total**: Sum of daily totals from 1st to current day

### Exchange Rate Application Methodology
1. **Single Daily Rate**: One NBP rate applied to entire day's calculations
2. **Rate Priority**: Current > Working Day > Holiday Skip > Fallback
3. **Consistency**: Same rate used for all costs in daily batch
4. **Fallback**: 4.0 PLN/USD if NBP unavailable

### Rounding and Precision Rules
**USD Amounts**:
- Small amounts (< $0.01): 6 decimal places
- Standard amounts: 2 decimal places
- Display format: `$123.45` or `$0.000123`

**PLN Amounts**:
- Always 2 decimal places
- Display format: `450,67 zł` (Polish locale)

**Calculations**:
- Internal: Full precision maintained
- Storage: 6 decimal places for USD, 2 for PLN
- Display: Formatted per currency rules

### Error Handling Scenarios
1. **NBP API Unavailable**: Use fallback rate (4.0 PLN)
2. **Invalid Cost Data**: Skip generation, log warning
3. **Missing Client**: Throw CostCalculationError
4. **Negative Values**: Validation error, reject data
5. **Network Timeout**: Retry with exponential backoff

---

## Technical Implementation Details

### Caching Strategy
**Exchange Rate Cache**:
- **TTL**: 24 hours for stable rates
- **Reduced TTL**: 4 hours for fallback scenarios
- **Key Strategy**: Single key for USD/PLN rate
- **Invalidation**: Time-based expiry

**Frontend Cache**:
- **Component Level**: Svelte store-based state
- **API Level**: No explicit caching (relies on daily batch)
- **Static Data**: Exchange rate info cached with usage data

### Performance Characteristics
- **Batch Processing**: Handles full month recalculation in <5 minutes
- **API Response**: Usage summary loads in <500ms
- **Exchange Rate**: NBP API typically responds in <200ms
- **Frontend Rendering**: Dual currency display renders immediately

### Security Controls
1. **Admin Authentication**: Required for manual sync and admin data
2. **Client Isolation**: Database-level separation by client_org_id
3. **Input Validation**: Cost and token validation with proper error handling
4. **API Security**: Rate limiting and proper error responses

### Monitoring and Observability
**Logging Points**:
- Exchange rate fetching with source tracking
- Cost calculation errors with client context
- Batch processing completion status
- NBP API failures with fallback usage

**Metrics**:
- Daily batch processing duration
- Exchange rate source distribution
- Cost calculation error rates
- NBP API availability percentage

---

## Business Intelligence Features

### Automated Data Validation
- **Cross-Reference**: OpenRouter costs vs. internal calculations
- **Consistency Checks**: Daily totals vs. individual generations
- **Exchange Rate Validation**: NBP rate reasonableness checks
- **Anomaly Detection**: Unusual cost spikes or patterns

### Strategic Planning Support
- **Monthly Projections**: Based on current daily averages
- **Cost Trend Analysis**: Historical cost evolution tracking
- **Budget Monitoring**: Against monthly limits per organization
- **Model Usage Optimization**: Cost-per-token analysis by model

### Audit Trail
- **Complete History**: All usage data maintained indefinitely
- **Change Tracking**: Batch processing timestamps and sources
- **Exchange Rate History**: All NBP rates with effective dates
- **Error Logging**: Comprehensive failure tracking with context

---

## Configuration Management

### Client-Specific Settings
```python
class ClientOrganization:
    markup_rate: float = 1.3      # 30% markup default
    monthly_limit: Optional[float] # Spending limit
    is_active: bool = True         # Enable/disable organization
```

### System-Wide Settings
- **NBP API Base**: `https://api.nbp.pl/api`
- **Batch Time**: 13:00 CET daily
- **Cache TTL**: 24 hours standard, 4 hours fallback
- **Fallback Rate**: 4.0 PLN/USD

### Environment Variables
- `SRC_LOG_LEVELS`: Logging configuration
- NBP client timeout: 10 seconds
- Daily batch processor timeout: Configurable per operation

---

## Recently Fixed Critical Issues (2025-01-27)

### ✅ OpenRouter Field Mapping Corrections
- **Fixed**: Changed from incorrect `total_cost` to correct `usage` field
- **Fixed**: Changed from incorrect `total_tokens` to `tokens_prompt` + `tokens_completion`
- **Impact**: Resolved token/cost discrepancies between OpenRouter dashboard and mAI
- **Files Updated**: `/backend/open_webui/utils/cost_calculator.py`, `/backend/open_webui/usage_tracking/services/webhook_service.py`

### ✅ Streaming Usage Capture Implementation
- **Achievement**: 100% OpenRouter usage capture (previously ~50% data loss)
- **Implementation**: Production-ready `UsageCapturingStreamingResponse` class
- **Performance**: Zero latency added to streaming responses
- **Quality**: A+ production readiness with comprehensive error handling

### ✅ Broken Bulk Sync Resolution
- **Issue**: System calling non-existent `/api/v1/generations` endpoint (404 errors)
- **Solution**: Disabled broken bulk sync, enhanced real-time tracking
- **Result**: Eliminated API errors and improved system reliability

### ✅ Database Method Fixes
- **Added**: Missing `is_duplicate()` method for proper generation deduplication
- **Enhanced**: Float comparison tolerance for cost matching
- **Impact**: Eliminated silent failures in duplicate detection

---

## Conclusion

The "Total Cost" feature represents a sophisticated multi-currency cost tracking system with the following key strengths:

1. **Robust Exchange Rate Integration**: Holiday-aware NBP API client with multiple fallback strategies
2. **Accurate Cost Calculations**: Client-specific markup rates with comprehensive validation and correct OpenRouter field mapping
3. **Reliable Daily Processing**: Automated batch processing with full month recalculation
4. **User-Friendly Display**: Dual currency formatting with appropriate precision handling
5. **Business Intelligence**: Complete audit trail and trend analysis capabilities
6. **100% Usage Coverage**: Production streaming capture system with zero data loss
7. **Real-Time Accuracy**: Immediate usage recording with generation_id deduplication

The system successfully balances real-time accuracy with performance optimization through daily batch processing, ensuring consistent and reliable cost reporting for Polish SME users while maintaining full USD/PLN currency support. The recent implementation of streaming usage capture represents a critical achievement, eliminating the previous ~50% data loss and providing complete visibility into OpenRouter usage patterns with zero performance impact.
