# Exchange Rate Workflow Documentation

## Executive Summary

The mAI project implements a sophisticated exchange rate system that integrates with the Polish National Bank (NBP) Web API to provide real-time USD/PLN currency conversion for multi-tenant usage tracking and billing. The system features holiday-aware caching, robust fallback mechanisms, and seamless integration with the usage tracking pipeline to ensure accurate billing in Polish złoty (PLN) for all clients.

### Key Features
- **Holiday-Aware Logic**: Intelligent handling of Polish holidays and weekends using comprehensive calendar data
- **Multi-Tier Fallback System**: Robust error handling with multiple fallback strategies
- **Smart Caching**: Time-aware caching with dynamic TTL based on rate source and timing
- **Real-Time Integration**: Seamless integration with OpenRouter usage tracking and billing systems
- **NBP Table A Compliance**: Uses official average exchange rates from Polish National Bank

## System Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Exchange Rate System                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │   NBP Client    │    │ Currency        │    │ Polish      │ │
│  │                 │    │ Converter       │    │ Holidays    │ │
│  │ • API requests  │    │                 │    │             │ │
│  │ • Caching       │    │ • Rate fetching │    │ • Calendar  │ │
│  │ • Error handling│◄──►│ • Conversions   │◄──►│ • Logic     │ │
│  │ • Fallback      │    │ • Fallbacks     │    │ • Working   │ │
│  │   logic         │    │                 │    │   days      │ │
│  └─────────────────┘    └─────────────────┘    └─────────────┘ │
│           │                       │                            │
│           ▼                       ▼                            │
│  ┌─────────────────┐    ┌─────────────────┐                   │
│  │ NBP Service     │    │ Usage Tracking  │                   │
│  │ (Batch)         │    │ Integration     │                   │
│  │                 │    │                 │                   │
│  │ • Daily updates │    │ • Real-time     │                   │
│  │ • Batch logging │    │   conversion    │                   │
│  │ • Result        │    │ • Billing       │                   │
│  │   tracking      │    │   support       │                   │
│  └─────────────────┘    └─────────────────┘                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    External Systems                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │ NBP Web API     │    │ Usage Dashboard │    │ Billing     │ │
│  │                 │    │                 │    │ System      │ │
│  │ • Table A rates │    │ • PLN display   │    │ • PLN       │ │
│  │ • JSON/XML      │    │ • Rate info     │    │   amounts   │ │
│  │ • Holiday       │    │ • Historical    │    │ • Exchange  │ │
│  │   handling      │    │   data          │    │   metadata  │ │
│  └─────────────────┘    └─────────────────┘    └─────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Integration Points

1. **Usage Tracking Service**: Real-time conversion during usage data processing
2. **Daily Batch Processor**: Automated exchange rate updates at midnight
3. **Frontend Dashboard**: PLN display with rate metadata
4. **Billing System**: PLN amounts with exchange rate traceability

## Function Documentation

### Core Components

#### NBPClient (`backend/open_webui/utils/nbp_client.py`)

**Primary Functions:**

##### `get_usd_pln_rate() -> Optional[Dict[str, Any]]`
**Purpose**: Fetch current USD/PLN exchange rate with intelligent fallback handling

**Business Logic Flow**:
1. Check in-memory cache for unexpired rate
2. Evaluate Polish holiday calendar for API call optimization
3. Apply time-aware logic based on NBP publish schedule (8:15 AM CET)
4. Execute enhanced fallback search for unknown non-publication days
5. Return rate with comprehensive metadata

**Return Structure**:
```python
{
    "rate": 3.6446,                    # USD/PLN average rate from Table A
    "effective_date": "2024-01-15",    # NBP publication date
    "table_no": "012/A/NBP/2024",      # Official NBP table reference
    "rate_source": "current",          # Strategy used: current|working_day|holiday_skip|fallback_404
    "skip_reason": "Weekend",          # Reason for API call skip (if applicable)
    "fallback_info": {...}             # Additional fallback metadata
}
```

##### `convert_usd_to_pln(usd_amount: float) -> Optional[Dict[str, Any]]`
**Purpose**: Convert USD amounts to PLN with rate metadata

**Input**: USD amount (float)
**Output**: Conversion result with full traceability
```python
{
    "usd": 100.00,
    "pln": 364.46,
    "rate": 3.6446,
    "effective_date": "2024-01-15"
}
```

#### Currency Converter (`backend/open_webui/utils/currency_converter.py`)

**Primary Functions:**

##### `get_current_usd_pln_rate() -> float`
**Purpose**: Simplified rate fetching with automatic fallback
- Returns NBP Table A average rate or fallback rate (3.64)
- Used for synchronous operations requiring guaranteed response

##### `get_exchange_rate_info() -> Dict[str, Any]`
**Purpose**: Detailed rate information with metadata
- Comprehensive rate data including source tracking
- Fallback indication for system monitoring
- Integration point for usage tracking system

##### `convert_usd_to_pln(usd_amount: float) -> Dict[str, Any]`
**Purpose**: Full conversion with detailed metadata
- Async conversion with complete traceability
- Integration with usage tracking billing

##### `convert_usd_to_pln_sync(usd_amount: float, rate: Optional[float]) -> float`
**Purpose**: Synchronous conversion for legacy integrations
- Emergency fallback for non-async contexts
- Uses provided rate or system fallback

#### Polish Holiday Calendar (`backend/open_webui/utils/polish_holidays.py`)

**Primary Functions:**

##### `is_working_day(check_date: date) -> bool`
**Purpose**: Determine if NBP publishes exchange rates on given date
- Evaluates weekends (Saturday/Sunday)
- Checks Polish public holiday calendar
- Critical for API call optimization

##### `get_last_working_day_before(target_date: date) -> date`
**Purpose**: Find fallback date for non-working days
- Handles extended holiday periods (Christmas, Easter)
- Prevents cascading API failures
- Ensures continuous rate availability

##### `get_nbp_rate_strategy(target_date: date) -> Dict[str, Any]`
**Purpose**: Intelligent strategy selection for rate fetching
- Recommends optimal approach based on date analysis
- Provides fallback dates and reasoning
- Supports proactive optimization

#### NBP Exchange Rate Service (`backend/open_webui/utils/daily_batch_processor/services/nbp_service.py`)

**Primary Functions:**

##### `update_exchange_rates() -> ExchangeRateResult`
**Purpose**: Batch processing component for daily rate updates
- Scheduled execution at midnight
- Comprehensive logging and error tracking
- Integration with batch processing pipeline

**Result Structure**:
```python
ExchangeRateResult(
    success=True,
    usd_pln_rate=3.6446,
    effective_date="2024-01-15",
    rate_source="nbp_table_a",
    fetched_at="2024-01-15T00:15:30",
    error=None
)
```

## Business Logic Workflow

### Primary Exchange Rate Fetch Workflow

```
START: Client requests USD/PLN rate
│
├─ STEP 1: Cache Check
│  ├─ Cache Hit (unexpired) → Return cached rate ✅
│  └─ Cache Miss/Expired → Continue to STEP 2
│
├─ STEP 2: Holiday Calendar Optimization
│  ├─ Is Working Day?
│  │  ├─ YES → Continue to STEP 3
│  │  └─ NO → TIER 1 Holiday Skip
│  │     ├─ Weekend → Use Friday rate
│  │     ├─ Polish Holiday → Use last working day
│  │     └─ Cache with holiday-specific TTL ✅
│  │
├─ STEP 3: Time-Aware Strategy
│  ├─ Before 8:15 AM CET?
│  │  ├─ YES → Try current, fallback to previous working day
│  │  └─ NO → Expect current day rate
│  │
├─ STEP 4: NBP API Request
│  ├─ Request: /api/exchangerates/tables/a/{date}/
│  ├─ Success (200) → Parse USD rate ✅
│  ├─ Not Found (404) → Continue to STEP 5
│  └─ Error (4xx/5xx) → Continue to STEP 5
│
├─ STEP 5: Enhanced Fallback Search (TIER 3)
│  ├─ Search backwards from target date
│  ├─ Skip known holidays/weekends
│  ├─ Try up to 10 working days
│  ├─ Found rate → Return with fallback metadata ✅
│  └─ No rate found → Return error ❌
│
└─ STEP 6: Cache Management
   ├─ Calculate dynamic TTL based on rate source
   ├─ Store in cache with expiration
   └─ Return rate with full metadata ✅
```

### Cache TTL Calculation Logic

```
CACHE TTL Decision Tree:
│
├─ Holiday Skip (weekend/holiday)
│  └─ TTL = Time until next working day publish time (8:15 AM)
│
├─ Working Day Rate (before publish time)
│  └─ TTL = Time until publish time (8:15 AM today)
│
├─ Fallback 404 (unknown non-publication)
│  └─ TTL = 4 hours (shorter for recovery detection)
│
├─ Current Rate (after publish time)
│  └─ TTL = 24 hours (standard cache period)
│
└─ Default
   └─ TTL = 24 hours
```

### Integration Workflow with Usage Tracking

```
Usage Data Processing Flow:
│
├─ OpenRouter Webhook Received
│  ├─ Raw usage data (USD amounts)
│  └─ Client identification
│
├─ Exchange Rate Integration
│  ├─ Call: get_exchange_rate_info()
│  ├─ Receive: Rate + metadata
│  └─ Cache: 24-hour TTL
│
├─ Currency Conversion
│  ├─ Convert: USD amounts → PLN
│  ├─ Preserve: Original USD amounts
│  └─ Store: Both currencies + rate metadata
│
├─ Data Storage
│  ├─ ClientDailyUsage: PLN amounts
│  ├─ Exchange rate info: Metadata
│  └─ Traceability: Rate source tracking
│
└─ Frontend Display
   ├─ Show: PLN amounts
   ├─ Display: Exchange rate info
   └─ Note: Rate effective date
```

## Data Models and Structures

### NBP API Response Structure (Table A)

```json
[
  {
    "table": "A",
    "no": "012/A/NBP/2024",
    "effectiveDate": "2024-01-15",
    "rates": [
      {
        "currency": "dolar amerykański",
        "code": "USD",
        "mid": 3.6446
      }
    ]
  }
]
```

### Internal Rate Data Structure

```typescript
interface ExchangeRateInfo {
  usd_pln: number;              // Exchange rate value
  effective_date: string;       // NBP publication date (ISO format)
  rate_source: string;          // Source strategy used
  table_no?: string;            // NBP table reference
  is_fallback: boolean;         // Whether fallback rate was used
  skip_reason?: string;         // Why API call was skipped
  fallback_info?: {             // Additional fallback metadata
    original_target: string;
    days_back: number;
    reason: string;
  }
}
```

### Cache Entry Structure

```python
{
  'data': {
    'rate': 3.6446,
    'effective_date': '2024-01-15',
    'table_no': '012/A/NBP/2024',
    'rate_source': 'current'
  },
  'expires_at': datetime(2024, 1, 16, 8, 15, 0)  # Dynamic expiration
}
```

### Usage Tracking Integration Types

```typescript
interface CurrentMonthUsage {
  month: string;
  total_tokens: number;
  total_cost: number;           // USD amount
  total_cost_pln: number;       // Converted PLN amount
  total_requests: number;
  exchange_rate_info?: ExchangeRateInfo;  // Rate metadata
}

interface DailyBreakdown {
  date: string;
  tokens: number;
  cost: number;                 // USD amount
  cost_pln: number;            // Converted PLN amount
  requests: number;
  primary_model: string;
}
```

## API Integration Details

### NBP Web API Specifications

**Base URL**: `https://api.nbp.pl/api`

**Endpoint Used**: `/exchangerates/tables/a/{date}/`
- **Method**: GET
- **Format**: JSON (default)
- **Rate Type**: Table A (average rates)
- **Currency**: USD (code: USD)

**Request Headers**:
```http
Accept: application/json
User-Agent: mAI/1.0
```

**Response Codes**:
- `200 OK`: Data available
- `404 Not Found`: No data for date (holiday/weekend)
- `400 Bad Request`: Invalid request format
- `5xx`: Server errors

**Rate Limits**: No explicit limits documented
**Data Availability**: Since January 2, 2002
**Query Limit**: Maximum 93-day range per request

### Holiday Publication Schedule

**Publication Time**: 8:15 AM CET daily
**Working Days**: Monday-Friday (excluding Polish holidays)
**Non-Publication Days**:
- Weekends (Saturday, Sunday)
- Polish public holidays
- Undeclared bank holidays
- Technical maintenance periods

## Caching Strategy

### Cache Architecture

**Type**: In-memory cache with TTL
**Scope**: Per NBPClient instance
**Thread Safety**: Single-threaded async operations
**Persistence**: Non-persistent (resets on restart)

### Cache Key Strategy

**Primary Key**: `"usd_pln_rate"`
**Scope**: Application-wide (single rate cache)
**Invalidation**: Time-based expiration only

### Dynamic TTL Calculation

**Holiday/Weekend Rates**:
- Cache until next working day publish time
- Prevents unnecessary API calls during known non-publication periods

**Pre-Publish Working Day Rates**:
- Cache until current day publish time (8:15 AM)
- Allows fresh rate pickup when available

**Fallback Rates (404 scenarios)**:
- 4-hour TTL for unknown non-publication days
- Enables quick recovery detection

**Standard Current Rates**:
- 24-hour TTL for stable daily rates
- Standard cache period for published rates

### Cache Management

**Memory Cleanup**: Automatic expired entry removal
**Cache Warming**: Not implemented (on-demand only)
**Cache Statistics**: Not tracked
**Cache Invalidation**: Time-based only (no manual invalidation)

## Error Handling and Fallbacks

### Multi-Tier Fallback Architecture

#### Tier 1: Holiday Calendar Optimization
**Purpose**: Proactive API call avoidance
**Mechanism**: Polish holiday calendar lookup
**Action**: Use last working day rate
**Benefits**: Reduces API load, improves response time

#### Tier 2: Time-Aware Strategy
**Purpose**: Handle publish time uncertainty
**Mechanism**: 8:15 AM CET threshold logic
**Action**: Intelligent current vs. previous day selection
**Benefits**: Handles early morning scenarios

#### Tier 3: Enhanced 404 Fallback
**Purpose**: Handle unknown non-publication days
**Mechanism**: Backward search through working days
**Action**: Find most recent available rate
**Benefits**: Handles unexpected scenarios (strikes, technical issues)

#### Tier 4: System Fallback
**Purpose**: Guarantee service availability
**Mechanism**: Hardcoded fallback rate (3.64 PLN)
**Action**: Return approximate rate with fallback indicator
**Benefits**: Prevents complete system failure

### Error Recovery Patterns

**Network Timeouts**:
- 10-second timeout per request
- Single retry with exponential backoff
- Fallback to cached or default rate

**API Rate Limiting**:
- Not explicitly handled (no documented limits)
- Natural rate limiting through caching

**Invalid Responses**:
- JSON parsing error handling
- Missing data field validation
- Graceful degradation to fallback

**Holiday Calculation Errors**:
- Fallback to weekend logic
- Conservative working day estimation
- System logging for monitoring

## Integration Points

### Usage Tracking Service Integration

**File**: `backend/open_webui/usage_tracking/services/usage_service.py`

**Integration Method**:
```python
from open_webui.utils.currency_converter import get_exchange_rate_info

# During usage data processing
exchange_info = await get_exchange_rate_info()
current_month_data["exchange_rate_info"] = exchange_info
```

**Data Flow**:
1. Usage webhook received from OpenRouter
2. Exchange rate fetched during processing
3. USD amounts converted to PLN
4. Both currencies stored with rate metadata
5. Frontend displays PLN with rate information

### Daily Batch Processor Integration

**File**: `backend/open_webui/utils/daily_batch_processor/services/nbp_service.py`

**Integration Method**:
```python
class NBPExchangeRateService:
    async def update_exchange_rates(self) -> ExchangeRateResult:
        exchange_info = await get_exchange_rate_info()
        # Process and log results
```

**Batch Processing Flow**:
1. Midnight batch processing trigger
2. Exchange rate refresh
3. Result logging and tracking
4. Integration with other batch operations

### Frontend Dashboard Integration

**Files**:
- `src/lib/components/admin/Settings/MyOrganizationUsage/MyOrganizationUsageContainer.svelte`
- `src/lib/components/admin/Settings/MyOrganizationUsage/types/usage.ts`

**Display Integration**:
```typescript
{#if usageData?.current_month?.exchange_rate_info}
  <NoticeCard 
    type="info" 
    title="Exchange rate: 1 USD = {usageData.current_month.exchange_rate_info.usd_pln.toFixed(4)} PLN (NBP rate from {usageData.current_month.exchange_rate_info.effective_date})" 
  />
{/if}
```

**User Experience**:
- PLN amounts displayed prominently
- Exchange rate information shown with effective date
- Rate source transparency for audit purposes
- Historical rate consistency for monthly views

## Technical Specifications

### Configuration Parameters

**NBP API Configuration**:
```python
NBP_API_BASE = "https://api.nbp.pl/api"  # Base API URL
FALLBACK_USD_PLN_RATE = 3.64             # Emergency fallback rate
```

**Request Configuration**:
```python
timeout = 10                              # Request timeout (seconds)
headers = {
    "Accept": "application/json",
    "User-Agent": "mAI/1.0"
}
```

**Cache Configuration**:
```python
default_ttl = timedelta(hours=24)         # Standard cache TTL
min_ttl = timedelta(minutes=5)            # Minimum cache TTL
fallback_ttl = timedelta(hours=4)         # Fallback scenario TTL
```

### Performance Characteristics

**Response Times**:
- Cache Hit: <1ms
- NBP API Call: 100-500ms
- Fallback Search: 200-1000ms (depends on search depth)

**Memory Usage**:
- Cache Entry: ~200 bytes per rate
- Working Set: <1KB (single rate cache)

**Network Usage**:
- Daily API Calls: 1-5 (with optimal caching)
- Request Size: ~100 bytes
- Response Size: ~500 bytes

### Rate Limits and Quotas

**NBP API Limits**:
- No documented rate limits
- Implicit fair use policy
- 93-day maximum range per query

**Internal Limits**:
- 10-day maximum fallback search
- Single concurrent request per client
- 10-second request timeout

### Monitoring and Logging

**Log Levels**:
- DEBUG: Cache operations, date calculations
- INFO: Rate fetches, fallback usage, holiday logic
- WARNING: API failures, fallback activations
- ERROR: Complete system failures

**Log Examples**:
```
INFO: ✅ USD/PLN rate: 3.6446 from 2024-01-15 (source: current)
INFO: 🗓️  Weekend: Using rate from 2024-01-12 (rate: 3.6421)
WARNING: ⚠️ No rate available on expected working day 2024-01-15 after publish time
ERROR: ❌ Failed to get USD/PLN rate - all strategies exhausted
```

**Metrics Tracking**:
- Rate source distribution (current/working_day/holiday_skip/fallback_404)
- Cache hit/miss ratios
- API call frequency
- Fallback activation frequency

### Security Considerations

**API Security**:
- HTTPS-only communication (NBP requirement as of August 2025)
- No authentication required (public API)
- User-Agent identification for service identification

**Data Security**:
- No sensitive data caching
- Public exchange rate information only
- No user-specific data in exchange rate system

**Rate Limiting Protection**:
- Conservative caching to minimize API load
- Holiday calendar optimization reduces unnecessary calls
- Graceful degradation prevents service disruption

### Deployment Considerations

**Environment Requirements**:
- Python 3.12+ with async/await support
- aiohttp for HTTP client functionality
- Network access to api.nbp.pl (HTTPS)

**Configuration Management**:
- Environment variables for API base URL
- Configurable fallback rates per deployment
- Log level configuration support

**Health Checks**:
- Exchange rate freshness monitoring
- API availability checks
- Cache performance metrics
- Fallback activation alerts

---

## Conclusion

The mAI exchange rate system provides a robust, intelligent, and highly available currency conversion service that seamlessly integrates with the usage tracking and billing pipeline. Through its multi-tier fallback architecture, holiday-aware optimization, and smart caching strategy, the system ensures accurate and timely PLN conversions for all billing operations while maintaining excellent performance and reliability characteristics.

The system's design prioritizes business continuity through comprehensive error handling while providing full transparency and traceability for audit and compliance purposes. Integration points across the application stack ensure consistent currency handling from raw usage data processing through frontend display.

**Generated on**: 2025-01-28  
**Version**: 1.0  
**Last Updated**: 2025-01-28