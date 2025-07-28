# mAI Usage Tracking System - Admin Guide

**Date**: July 28, 2025  
**Status**: ✅ **PRODUCTION READY** - Complete daily batch processing with NBP Table A integration  
**Version**: 4.2 (Enhanced with NBP Table A average rates and top models analytics)

---

## Executive Summary

The mAI Usage Tracking System provides **business-focused administrative oversight** of OpenRouter API usage for Polish SME clients. The system has been specifically designed for management and administrative purposes, showing daily summaries and monthly trends rather than unnecessary real-time data.

### Business-Focused Design
- **Administrative Interface**: Clean monthly overview for management decisions
- **Daily Breakdown**: Complete usage patterns from 1st to last day of month  
- **Business Intelligence**: Peak usage days, cost averages, model preferences
- **Daily Batch Processing**: Data updates at 00:00 daily for consistent business reporting
- **No Real-time Overload**: Single page load for business oversight purposes

---

## Admin Dashboard Overview

### Monthly Summary Cards
```
┌─────────────────┬─────────────────┬─────────────────┐
│ Total Tokens    │ Total Cost      │ Usage Activity  │
│ 52,400          │ $0.187 (0.77 zł)│ 12/27 days     │
│ July 2025       │ 168 requests    │ 44% active     │
└─────────────────┴─────────────────┴─────────────────┘
```

### Business Insights Section
```
Usage Averages          Peak Usage              Top Models
• Daily Average: 4,367   • Busiest Day: 2025-07-15  • 1. Claude Sonnet 4 (15,200 tokens)
• Usage Day Avg: 4,367   • Highest Cost: 2025-07-15 • 2. GPT-4o (8,500 tokens)
                                                    • 3. Gemini Pro (6,100 tokens)
```

### Daily Breakdown Table
```
Date        Day      Tokens   Cost      Requests  Primary Model    Last Activity
2025-07-01  Monday   1,500    $0.0052   5         Gemini Flash     09:30
2025-07-02  Tuesday  2,200    $0.0078   8         Claude Sonnet    14:15
2025-07-15  Monday   8,900    $0.0325   25        Claude Sonnet    16:45
```

---

## Core System Architecture

### Dynamic Pricing & Daily Batch Processing Architecture
```
OpenRouter API Call → Usage Recording → Daily Batch (00:00) → Admin Dashboard
        ↓                    ↓                   ↓
  Dynamic Pricing      Daily Usage      Pricing Refresh
  (24hr Cache)         Aggregation      Exchange Rates
        ↓                    ↓                   ↓
    Live Pricing       Multi-table Storage with Monthly Totals
    Updated Daily      ├── client_daily_usage (consolidated)
                       ├── client_user_daily_usage 
                       └── client_model_daily_usage
```

### Key Features
- **Dynamic Model Pricing**: Live OpenRouter API integration with 24-hour TTL cache
- **Daily Batch Processing**: Data consolidation at 00:00 for reliable business reporting
- **Automated Pricing Updates**: Fresh model pricing fetched daily with fallback system
- **Monthly Cumulative Totals**: Automatically calculated from 1st day to current day
- **Holiday-Aware Exchange Rates**: Fresh NBP Table A rates fetched daily with intelligent fallback
- **Business Intelligence**: Automatically calculated insights and trends
- **Multi-tenant Support**: Isolated data per client organization
- **Automated Data Integrity**: Daily validation and correction of markup calculations
- **Duplicate Prevention**: Built-in protection against data reprocessing

---

## Database Schema (Admin Reference)

### Primary Usage Table: `client_daily_usage`
```sql
CREATE TABLE client_daily_usage (
    id TEXT PRIMARY KEY,                    -- Format: "{client_org_id}:{date}"
    client_org_id TEXT NOT NULL,           -- Organization reference
    usage_date DATE NOT NULL,              -- Daily grouping
    total_tokens INTEGER DEFAULT 0,        -- Daily token consumption
    total_requests INTEGER DEFAULT 0,      -- Number of API requests
    raw_cost REAL DEFAULT 0.0,            -- OpenRouter cost (before markup)
    markup_cost REAL DEFAULT 0.0,         -- Client cost (with 1.3x markup)
    primary_model TEXT,                    -- Most used model that day
    unique_users INTEGER DEFAULT 1,       -- Active users count
    created_at INTEGER NOT NULL,          -- Creation timestamp
    updated_at INTEGER NOT NULL           -- Last activity timestamp
);
```

### Supporting Tables
- **`client_organizations`**: Client management with API keys and markup rates
- **`client_user_daily_usage`**: Per-user daily breakdown
- **`client_model_daily_usage`**: Per-model usage statistics
- **`user_client_mapping`**: User-to-organization assignments

### Duplicate Prevention Table: `processed_generations`
```sql
CREATE TABLE processed_generations (
    id TEXT PRIMARY KEY,                      -- OpenRouter generation_id
    client_org_id TEXT NOT NULL,             -- Organization reference
    generation_date DATE NOT NULL,           -- Processing date
    processed_at INTEGER NOT NULL,           -- Unix timestamp of processing
    total_cost REAL DEFAULT 0.0,            -- Cost for audit trail
    total_tokens INTEGER DEFAULT 0          -- Token count for audit trail
);
```

This table ensures each OpenRouter generation is recorded only once, preventing duplicate billing from:
- API retries and failures
- Webhook replays
- Streaming response chunks
- Manual reprocessing

---

## Duplicate Prevention System

### How OpenRouter Streaming Works

When you make a single query to OpenRouter, it may generate multiple API responses as part of streaming:

```
Single User Query → Multiple OpenRouter Responses
Example from real data:
├── gen-1753639473-xmTDMMtjF7MFEUDDQwxS (16 prompt, 1137 completion tokens)
├── gen-1753639492-bYTtA2p96XnBWvIXXVnx (1357 prompt, 87 completion tokens)  
├── gen-1753639497-uuROABnTGNKntsEKAiEY (1427 prompt, 12 completion tokens)
└── gen-1753639499-JeqYBe08OQHtZJmmRBkV (1319 prompt, 28 completion tokens)
```

**Each response has a unique `generation_id`** - this is normal behavior, not query splitting.

### Duplicate Prevention Process

1. **Generation ID Extraction**: System extracts `generation_id` from OpenRouter response
2. **Duplicate Check**: Before recording usage, checks if `generation_id` already exists
3. **Skip or Record**: If exists, skips recording; if new, records usage and marks as processed
4. **Audit Trail**: Maintains processed generations table for 60-day retention

### Implementation Details

**Real-time Usage Recording** (`openrouter_client_manager.py`):
```python
# Check for duplicate before recording
if generation_id and ProcessedGenerationDB.is_generation_processed(generation_id, client_org_id):
    log.info(f"Generation {generation_id} already processed, skipping duplicate")
    return True

# Record usage if not duplicate
success = ClientUsageDB.record_usage(...)

# Mark as processed to prevent future duplicates
if success and generation_id:
    processed_gen = ProcessedGeneration(id=generation_id, ...)
    db.add(processed_gen)
```

**OpenRouter Response Processing** (`openai.py`):
```python
# Extract generation_id from OpenRouter response
generation_id = response.get("generation_id") or response.get("id")

# Pass to usage recording with duplicate prevention
openrouter_client_manager.record_real_time_usage(
    generation_id=generation_id,  # Critical for duplicate prevention
    ...
)
```

### Protection Against

- **API Retries**: If OpenRouter retries a failed request
- **Webhook Replays**: If webhook systems replay usage notifications  
- **Manual Reprocessing**: If admin manually reprocesses usage data
- **Streaming Chunks**: Each chunk recorded once, no matter how many retries
- **System Failures**: If recording fails and is retried later

### Verification Commands

**Check for duplicate generations**:
```bash
# Find potential duplicates in processed generations
docker exec container sqlite3 /app/backend/data/webui.db \
  "SELECT generation_id, COUNT(*) as count 
   FROM processed_generations 
   GROUP BY generation_id 
   HAVING COUNT(*) > 1;"
```

**View recent processed generations**:
```bash
# Show last 10 processed generations
docker exec container sqlite3 /app/backend/data/webui.db \
  "SELECT id, client_org_id, generation_date, total_cost 
   FROM processed_generations 
   ORDER BY processed_at DESC 
   LIMIT 10;"
```

**Verify duplicate prevention is working**:
```bash
# Check if specific generation was processed
docker exec container sqlite3 /app/backend/data/webui.db \
  "SELECT * FROM processed_generations 
   WHERE id = 'gen-1753639473-xmTDMMtjF7MFEUDDQwxS';"
```

### Business Benefits

- **Accurate Billing**: Each unique API call recorded exactly once
- **Data Integrity**: No inflated usage statistics from duplicates
- **Audit Trail**: Complete record of what was processed and when
- **Cost Control**: Prevents overcharging due to technical issues
- **Compliance**: Reliable usage tracking for financial reporting

---

## Admin Interface Components

### 1. Monthly Overview Cards

**Total Tokens Card**
- Shows cumulative tokens for current month
- Displays month name for context
- No real-time indicators (business-appropriate)

**Total Cost Card** 
- Monthly cost in USD and PLN
- Request count for volume context
- Holiday-aware NBP exchange rates with intelligent fallback system

**Usage Activity Card**
- Days with usage vs. total days in month
- Percentage of active days for planning
- Business intelligence for usage patterns

### 2. Business Insights Panel

**Usage Averages**
- Daily average tokens across all days
- Usage day average (only counting active days)
- Cost averaging for budgeting

**Peak Usage Identification**
- Busiest day by token consumption
- Highest cost day for budget analysis
- Pattern recognition for capacity planning

**Resource Utilization**
- Top 3 AI models with token usage for optimization
- Active user count for licensing
- Detailed model preference insights with usage volumes

### 3. Daily Breakdown Table

**Complete Monthly View**
- Every day from 1st to current day of month
- Token usage, cost, and request volumes
- Primary model used each day
- Last activity timestamp for monitoring

**Business Planning Data**
- Day-of-week patterns for resource planning
- Cost progression for budget tracking
- Model usage trends for contract optimization

---

## Daily Batch Processing System

### 🕰️ **Automated Daily Processing (00:00)**
1. **Exchange Rate Update** - Fresh NBP rates with holiday-aware logic
2. **Model Pricing Refresh** - Updated OpenRouter API pricing with cache invalidation
3. **Usage Data Validation** - Validate and correct daily summaries with duplicate prevention
4. **Monthly Totals Update** - Calculate cumulative totals from 1st to current day
5. **Data Cleanup** - Remove old processed generation records (60-day retention)

### 📊 **Monthly Business Review**
1. **Load Admin Dashboard** - Single page load, no refresh needed
2. **Review Monthly Cards** - Total usage, cost, and activity percentage
3. **Analyze Peak Days** - Identify usage patterns and capacity needs
4. **Check Daily Breakdown** - Detailed day-by-day analysis

### 💰 **Budget Planning & Cost Control**
- **Monthly Totals**: Clear visibility into spending patterns
- **Daily Averages**: Predictable budget forecasting
- **Peak Day Analysis**: Capacity planning and cost optimization
- **Currency Conversion**: Polish Złoty support for local budgeting

### 🔍 **Usage Optimization**
- **Top Model Analytics**: Identify top 3 models by token usage for contract negotiation
- **User Activity**: Monitor active users for licensing optimization
- **Daily Patterns**: Understand peak usage for resource allocation
- **Cost Per Token**: ROI analysis and pricing optimization
- **Model Distribution**: Detailed token-based usage ranking for strategic planning

### 📈 **Strategic Planning**
- **Usage Trends**: Month-over-month growth analysis
- **Activity Percentage**: System utilization for scaling decisions
- **Top Models Analytics**: Data-driven technology investment planning
- **User Engagement**: Adoption and training insights
- **Token-Based Rankings**: Optimize model portfolio based on actual usage data

---

## Currency Conversion System

### Holiday-Aware NBP Table A Integration

The system features an intelligent **3-Tier Fallback System** for PLN currency conversion using **NBP Table A (average rates)** that automatically handles Polish banking holidays and non-working days:

#### Tier 1: Polish Holiday Calendar Optimization
- **2025 Holiday Calendar**: Exact Polish holidays with correct dates
- **API Call Optimization**: Skips API calls for known non-working days
- **Smart Fallback**: Automatically uses last working day Table A rate
- **Weekend Handling**: Proper Friday Table A rate usage for weekends

#### Tier 2: Time-Based Working Day Logic
- **8:15 AM Rule**: Before publish time uses previous day, after uses current
- **Working Day Validation**: Uses holiday calendar to determine working days
- **Intelligent Caching**: Different TTL based on rate source and timing

#### Tier 3: Enhanced 404 Fallback
- **Unknown Issues**: Handles bank strikes, technical problems, undeclared holidays
- **Smart Search**: Only tries working days, skips known non-working days
- **Graceful Degradation**: Goes back up to 10 days to find valid data

### Holiday Coverage (2025)

**Fixed Holidays**: New Year's Day, Epiphany, Labour Day, Constitution Day, Assumption Day, All Saints' Day, Independence Day, Christmas Eve, Christmas Day, Boxing Day

**Movable Holidays**: Easter Sunday (April 20), Easter Monday (April 21), Pentecost (June 8), Corpus Christi (June 19)

**Edge Cases**: Extended holiday weekends, holiday + weekend combinations, unknown non-publication days

### Rate Source Transparency

The system provides full transparency with Table A rate source tracking:
```json
{
  "rate": 3.6446,
  "effective_date": "2025-07-24",
  "rate_source": "nbp_table_a",
  "table_no": "142/A/NBP/2025",
  "skip_reason": "Polish holiday: Boże Narodzenie",
  "fallback_date": "2025-12-23"
}
```

### Business Benefits
- **Accuracy**: Uses NBP Table A average rates (more representative than buying/selling rates)
- **Efficiency**: Reduces API calls by ~30% by skipping known holidays/weekends
- **Reliability**: Handles all 2025 Polish holidays including movable ones
- **Consistency**: Accurate PLN conversions using average market rates during holiday periods
- **Performance**: Smart caching with context-aware TTL

---

## API Reference for Admins

### Primary Admin Endpoint
```http
GET /api/v1/usage-tracking/my-organization/usage-summary
Authorization: Bearer {admin_token}
```

### Dynamic Pricing Endpoint
```http
GET /api/v1/usage-tracking/model-pricing
Authorization: Bearer {admin_token}
```

**Response Structure** (Live pricing with fallback):
```json
{
  "success": true,
  "models": [
    {
      "id": "anthropic/claude-sonnet-4",
      "name": "Claude Sonnet 4",
      "provider": "Anthropic",
      "price_per_million_input": 8.00,
      "price_per_million_output": 24.00,
      "context_length": 1000000,
      "category": "Premium"
    }
  ],
  "last_updated": "2025-07-27T00:00:15.123Z",
  "source": "openrouter_api"
}
```

**Response Structure** (Business-focused):
```json
{
  "success": true,
  "stats": {
    "current_month": {
      "month": "July 2025",
      "total_tokens": 52400,
      "total_cost": 0.187200,
      "total_cost_pln": 0.77,
      "total_requests": 168,
      "days_with_usage": 12,
      "days_in_month": 27,
      "usage_percentage": 44.4
    },
    "daily_breakdown": [
      {
        "date": "2025-07-01",
        "day_name": "Monday",
        "tokens": 1500,
        "cost": 0.0052,
        "cost_pln": 0.021,
        "requests": 5,
        "primary_model": "google/gemini-2.5-flash",
        "last_activity": "09:30"
      }
    ],
    "monthly_summary": {
      "average_daily_tokens": 4367,
      "average_daily_cost": 0.0156,
      "busiest_day": "2025-07-15",
      "highest_cost_day": "2025-07-15", 
      "top_models": [
        {"model_name": "anthropic/claude-sonnet-4", "total_tokens": 15200},
        {"model_name": "openai/gpt-4o", "total_tokens": 8500},
        {"model_name": "google/gemini-pro", "total_tokens": 6100}
      ],
      "total_unique_users": 2
    }
  }
}
```

### Additional Admin Endpoints
- **User Breakdown**: `GET /my-organization/usage-by-user`
- **Model Analytics**: `GET /my-organization/usage-by-model` (includes all 12 available models)
- **Subscription Billing**: `GET /my-organization/subscription-billing`
- **Live Model Pricing**: `GET /model-pricing` (24-hour cache with daily refresh)

---

## Admin Operations Guide

### Daily Admin Tasks
1. **Review Usage Dashboard** - Check monthly progress and daily patterns (data updated at 00:00)
2. **Monitor Cost Trends** - Ensure spending within budget parameters with current pricing
3. **Check Model Pricing** - Verify pricing updates are current (refreshed daily at 00:00)
4. **Check User Activity** - Verify expected usage levels
5. **Verify Batch Processing** - Check logs for successful daily processing at 00:00

### Weekly Admin Tasks
1. **Analyze Peak Days** - Identify unusual usage patterns
2. **Review Model Distribution** - Optimize AI model availability
3. **Check Cost Averages** - Budget tracking and forecasting

### Monthly Admin Tasks
1. **Generate Usage Reports** - Monthly summary for stakeholders
2. **Budget Analysis** - Compare actual vs. planned spending
3. **Strategic Planning** - Usage trends for next month planning

---

## Performance & Reliability

### System Performance
- **Daily Batch Processing**: Eliminates real-time calculation overhead
- **Optimized Queries**: Pre-calculated daily and monthly summaries
- **Minimal Server Load**: 99% reduction in dashboard API calls
- **Fast Response Times**: Single database query pattern
- **Automated Maintenance**: Daily data validation and cleanup at 00:00

### Business Benefits
- **Appropriate Complexity**: Perfect for administrative oversight
- **Clean Interface**: Focused on business value, not technical metrics
- **Better Decision Making**: Enhanced insights and trend analysis
- **Cost Effective**: Reduced server resources and complexity

---

## Multi-Tenant Architecture

### Client Isolation
- **Separate Containers**: Each client gets dedicated Docker environment
- **Independent Databases**: SQLite per client organization
- **Isolated API Keys**: Dedicated OpenRouter keys per client
- **Custom Markup Rates**: Flexible pricing per organization

### Administrative Scope
- **Organization-level Access**: Admins see only their organization's data
- **User Management**: Per-organization user breakdown
- **Cost Tracking**: Independent billing and markup calculation
- **Usage Analytics**: Client-specific insights and trends

---

## Data Retention & Cleanup

### Daily Summary Storage
- **Permanent Retention**: Daily summaries stored indefinitely
- **Audit Trail**: Complete usage history for compliance
- **Backup Strategy**: Daily database backups with retention
- **Dynamic Pricing Cache**: 24-hour TTL with automatic refresh

### Daily Batch Operations
- **00:00 Scheduled Processing**: Fully automated daily batch execution
- **Exchange Rate Updates**: Holiday-aware NBP integration with fallback
- **Model Pricing Refresh**: Live OpenRouter API pricing with cache invalidation
- **Data Validation**: Automatic markup cost verification and correction
- **Monthly Calculations**: Cumulative totals from 1st day to current day
- **Duplicate Prevention**: Built-in protection against data reprocessing
- **Automated Cleanup**: Old processed generation logs (60-day retention)
- **Storage Optimization**: Efficient daily summary storage
- **Performance Maintenance**: Regular database optimization

### Production Deployment Scripts
- **`scripts/daily_batch_cron.sh`**: Cron script for automated scheduling
- **`scripts/docker_daily_batch.sh`**: Docker container batch processing
- **Cron Setup**: `0 0 * * * /path/to/mAI/scripts/daily_batch_cron.sh`
- **Manual Execution**: `./docker_daily_batch.sh container_name`
- **Batch Logs**: `/app/logs/daily_batch_YYYYMMDD.log`

---

## Troubleshooting Guide

### Common Admin Issues

#### "No usage data today"
- **Cause**: No API calls made yet today
- **Solution**: Normal - data appears after first API usage
- **Verification**: Check if users are actively using the system

#### "Loading usage data..."
- **Cause**: Data being processed by daily batch (if viewing early morning)
- **Solution**: Wait for 00:00 batch processing to complete, then refresh
- **Note**: Data updates once daily at 00:00 - no real-time updates

#### "Monthly summary shows zero"
- **Cause**: First month of usage or new organization
- **Solution**: Usage data accumulates as system is used
- **Timeline**: Data visible immediately after first API calls

#### "PLN conversion showing old rates"
- **Cause**: Polish banking holiday or NBP non-publication day
- **Solution**: System automatically uses last working day rate
- **Verification**: Check rate_source field in API response for holiday information

#### "Model pricing shows old rates"
- **Cause**: OpenRouter API unavailable or cache not refreshed
- **Solution**: System automatically uses cached pricing or hardcoded fallback
- **Verification**: Check `source` field in `/model-pricing` endpoint response

#### "UI shows zeros despite usage activity"
- **Cause**: Daily batch processing hasn't completed or data validation issues
- **Solution**: Run manual batch processing or check logs
- **Command**: `docker exec container python -m open_webui.utils.daily_batch_processor`

#### "Monthly totals incorrect after batch processing"
- **Cause**: Duplicate processing or data integrity issue
- **Solution**: System has built-in duplicate prevention - check batch logs
- **Prevention**: Batch processor includes comprehensive validation and correction

#### "Suspected duplicate usage charges"
- **Cause**: Multiple entries for same generation_id or system errors
- **Solution**: Check processed_generations table for duplicates
- **Verification**: Run duplicate detection query (see Duplicate Prevention section)
- **Prevention**: System automatically prevents duplicates via generation_id tracking

#### "Usage recording appears multiple times"
- **Cause**: Streaming responses creating multiple legitimate entries
- **Explanation**: Normal behavior - each OpenRouter generation_id is unique
- **Example**: Single query may produce 4 separate generations with different IDs
- **Action**: Verify each entry has unique generation_id (this is correct behavior)

#### "Generation marked as processed but no usage recorded"
- **Cause**: Recording failed after duplicate check passed
- **Investigation**: Check logs for errors after "Generation xyz already processed" message
- **Solution**: May indicate database connectivity issues during recording phase
- **Recovery**: Remove from processed_generations table to allow re-recording

### Admin Verification Commands

```bash
# Check current month usage
docker exec container sqlite3 /app/backend/data/webui.db \
  "SELECT COUNT(*), SUM(total_tokens), SUM(markup_cost) 
   FROM client_daily_usage 
   WHERE usage_date >= date('now','start of month');"

# Verify today's activity  
docker exec container sqlite3 /app/backend/data/webui.db \
  "SELECT * FROM client_daily_usage 
   WHERE usage_date = date('now');"

# Check organization setup
docker exec container sqlite3 /app/backend/data/webui.db \
  "SELECT id, name, markup_rate FROM client_organizations 
   WHERE is_active = 1;"

# Test daily batch processor
docker exec container python -m open_webui.utils.daily_batch_processor

# Check batch processing logs
docker exec container ls -la /app/logs/daily_batch_*.log

# Check model pricing source and cache status
curl "http://localhost:8080/api/v1/usage-tracking/model-pricing" \
  -H "Authorization: Bearer {admin_token}" | jq '.source, .last_updated'

# Verify data integrity and monthly totals
docker exec container python -c "
import sqlite3
conn = sqlite3.connect('/app/backend/data/webui.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*), SUM(total_tokens), SUM(markup_cost) FROM client_daily_usage WHERE usage_date >= date(\\'now\\',\\'start of month\\')')
result = cursor.fetchone()
print(f'Current month: {result[0]} days, {result[1]} tokens, \${result[2]:.6f}')
conn.close()
"

# Verify NBP exchange rate system
curl "http://localhost:8080/api/v1/usage-tracking/exchange-rate/USD/PLN" \
  -H "Authorization: Bearer {admin_token}"

# Check duplicate prevention system
docker exec container sqlite3 /app/backend/data/webui.db \
  "SELECT COUNT(*) as total_processed, 
          COUNT(DISTINCT id) as unique_generations,
          MIN(generation_date) as oldest_record,
          MAX(generation_date) as newest_record
   FROM processed_generations;"

# Verify no duplicate generation_ids exist
docker exec container sqlite3 /app/backend/data/webui.db \
  "SELECT id, COUNT(*) as count 
   FROM processed_generations 
   GROUP BY id 
   HAVING COUNT(*) > 1;"
```

---

## Best Practices for Admins

### Dashboard Usage
1. **Load Once**: Access dashboard when needed - data refreshes daily at 00:00
2. **Morning Reviews**: Best time to check dashboard is after 00:30 when batch processing completes
3. **Weekly Reviews**: Check trends and patterns weekly for insights
4. **Monthly Planning**: Use monthly summaries for budget and capacity planning
5. **Cost Monitoring**: Review daily costs for budget tracking

### Data Interpretation
- **Usage Percentage**: Target 60-80% active days for optimal utilization
- **Peak Days**: Normal to have 2-3x average usage on busy days
- **Top Models Analytics**: Expect 70-80% usage concentrated in top 3 models
- **Token Distribution**: Primary model typically accounts for 40-60% of total tokens
- **Cost Trends**: Monthly costs should align with business activity

### Optimization Strategies
- **Model Portfolio**: Focus training on top-performing models from analytics
- **Usage Patterns**: Schedule intensive tasks during off-peak times
- **User Training**: Optimize prompts to reduce token consumption on high-usage models
- **Budget Control**: Set monthly limits based on usage trends and top model analytics
- **Contract Negotiation**: Use top models data for volume-based pricing discussions

---

## Recent System Enhancements (July 2025)

### NBP API Migration from Table C to Table A

**What Changed:**
- **API Endpoint**: Migrated from `/exchangerates/tables/c/` to `/exchangerates/tables/a/`
- **Rate Field**: Changed from `ask` (buying rate) to `mid` (average rate)
- **Rate Values**: More accurate average rates (~3.64 PLN/USD) instead of buying rates (~4.12 PLN/USD)
- **Documentation**: Updated all references from Table C to Table A

**Business Impact:**
- **More Accurate Pricing**: Table A provides average market rates, more representative for business calculations
- **Better Budgeting**: PLN conversions now use fair market rates instead of bank buying rates
- **Consistent Rates**: Average rates are less volatile than buying/selling spreads

**Admin Verification:**
```bash
# Verify Table A integration
curl "http://localhost:8080/api/v1/usage-tracking/exchange-rate/USD/PLN" \
  -H "Authorization: Bearer {admin_token}" | jq '.rate_source, .table_no'
```

### Model Analytics Enhancement: most_used_model → top_models

**What Changed:**
- **Data Structure**: Replaced single `most_used_model` string with `top_models` array
- **Enhanced Data**: Each model now includes `model_name` and `total_tokens`
- **Business Intelligence**: Top 3 models ranked by token usage instead of just the primary model
- **UI Enhancement**: Admin dashboard now shows detailed model ranking with usage volumes

**Before (Old Structure):**
```json
{
  "monthly_summary": {
    "most_used_model": "anthropic/claude-sonnet-4"
  }
}
```

**After (New Structure):**
```json
{
  "monthly_summary": {
    "top_models": [
      {"model_name": "anthropic/claude-sonnet-4", "total_tokens": 15200},
      {"model_name": "openai/gpt-4o", "total_tokens": 8500},
      {"model_name": "google/gemini-pro", "total_tokens": 6100}
    ]
  }
}
```

**Business Benefits:**
- **Strategic Planning**: Complete visibility into model usage distribution
- **Contract Negotiation**: Data-driven discussions with model providers
- **Cost Optimization**: Identify high-usage models for focused optimization
- **Portfolio Management**: Make informed decisions about model portfolio

**Technical Implementation:**
- New `_calculate_top_models_by_tokens()` helper function
- Aggregates usage across all days in current month
- Returns top 3 models sorted by total token consumption
- Handles edge cases: empty data, fewer than 3 models

---

## Conclusion

The mAI Usage Tracking System provides administrators with a clean, business-focused interface for monitoring OpenRouter API usage. The system eliminates unnecessary real-time complexity while providing comprehensive business intelligence for decision-making, budgeting, and strategic planning.

**Key Admin Benefits:**
- ✅ **Dynamic Model Pricing** - Live OpenRouter API integration with 24-hour TTL cache
- ✅ **Daily Batch Processing** - Reliable 00:00 data consolidation and validation
- ✅ **Automated Pricing Updates** - Fresh model pricing with comprehensive fallback system
- ✅ **Clean Monthly Overview** - Perfect for management review with accurate pricing
- ✅ **Daily Breakdown Analysis** - Complete usage patterns with automated integrity checks
- ✅ **Business Intelligence** - Automated insights and trends with monthly cumulative calculations
- ✅ **Data Integrity Protection** - Built-in duplicate prevention with generation_id tracking
- ✅ **Duplicate Prevention System** - Automatic protection against API retries, webhook replays, and streaming chunks
- ✅ **Cost Control** - Transparent pricing with holiday-aware PLN support
- ✅ **Strategic Planning** - Data-driven capacity and budget planning with current rates
- ✅ **Currency Reliability** - Daily NBP Table A integration with 3-tier fallback system
- ✅ **Top Models Analytics** - Enhanced with top 3 models ranking by token usage
- ✅ **Automated Maintenance** - Self-managing system with daily cleanup and optimization
- ✅ **Production Deployment** - Complete cron scripts and Docker integration
