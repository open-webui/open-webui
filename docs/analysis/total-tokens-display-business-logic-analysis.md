# Total Tokens Display Business Logic Analysis Report

## Executive Summary

## System Overview

**Architecture Pattern**: Clean Architecture with Component Composition
**Processing Model**: Daily Batch Processing (not real-time)
**Data Flow**: OpenRouter → Webhook → Daily Aggregation → UI Display
**Update Schedule**: 00:00 daily with NBP exchange rate integration

## 1. Business Logic Flow Mapping

### 1.1 Complete Data Flow Architecture

```
OpenRouter API Usage
↓
Webhook Processing (POST /webhook/openrouter-usage)
↓
Daily Usage Recording (ClientDailyUsage tables)
↓
Batch Calculation (00:00 daily with NBP rates)
↓
Month Total Aggregation (current_month calculation)
↓
Frontend API Call (GET /my-organization/usage-summary)
↓
StatCard Display ("Total Tokens" with "July 2025 • Batch Calculated")
```

### 1.2 Frontend Display Logic Flow

**Entry Point**: `/src/lib/components/admin/Settings/MyOrganizationUsage.svelte`

**Component Hierarchy**:
1. **MyOrganizationUsageContainer.svelte** (Orchestrator)
   - Manages state with Svelte stores
   - Calls `OrganizationUsageService.getUsageSummary()`
   - Renders StatCard components with calculated values

2. **StatCard Component** (Display)
   - Title: "Total Tokens"
   - Value: `FormatterService.formatNumber(usageData.current_month?.total_tokens || 0)`
   - Subtitle: `"{usageData.current_month?.month || 'Loading...'} • Batch Calculated"`

**Key Business Rule**: Zero values are displayed when `usageData.current_month.total_tokens` is undefined, null, or 0.

## 2. Backend Data Calculation Methods

### 2.1 Month Total Calculation Logic

**Primary Method**: `ClientUsageRepository.get_usage_stats_by_client()`
**Location**: `/backend/open_webui/models/organization_usage/client_usage_repository.py:160-276`

**Business Logic Steps**:

1. **Date Boundary Calculation**:
   ```python
   today = date.today()
   current_month_start = today.replace(day=1)
   # Queries from 1st to current day of month
   ```

2. **Database Query**:
   ```python
   month_records = db.query(ClientDailyUsage).filter(
       ClientDailyUsage.client_org_id == client_org_id,
       ClientDailyUsage.usage_date >= current_month_start,
       ClientDailyUsage.usage_date <= today
   ).order_by(ClientDailyUsage.usage_date).all()
   ```

3. **Aggregation Calculation**:
   ```python
   total_tokens = sum(r.total_tokens for r in month_records)
   total_cost = sum(r.markup_cost for r in month_records)  # 1.3x markup
   total_requests = sum(r.total_requests for r in month_records)
   ```

4. **Month Label Generation**:
   ```python
   current_month = {
       'month': today.strftime('%B %Y'),  # e.g., "July 2025"
       'total_tokens': total_tokens,
       'total_cost': total_cost,
       # ... other fields
   }
   ```

### 2.2 Data Source: ClientDailyUsage Table

**Schema**:
```sql
CREATE TABLE client_daily_usage (
    id TEXT PRIMARY KEY,  -- format: "{client_org_id}:{usage_date}"
    client_org_id TEXT,
    usage_date DATE,
    total_tokens INTEGER,
    total_requests INTEGER,
    raw_cost REAL,
    markup_cost REAL,     -- 1.3x multiplier applied
    primary_model TEXT,
    unique_users INTEGER,
    created_at INTEGER,
    updated_at INTEGER
);
```

**Current Data State** (from database analysis):
- One record exists: `dev_mai_client_d460a478:2025-07-27`
- Data: 700 tokens, 1 request, $0.0013 markup cost
- Date: 2025-07-27 (yesterday's data)

## 3. Why "Total Tokens" Shows "0"

### 3.1 Root Cause Analysis

**Primary Issue**: **Missing July 28, 2025 Data**

The system is currently displaying 0 tokens because:

1. **Date Range Logic**: Query looks for data from July 1-28, 2025
2. **Available Data**: Only July 27, 2025 data exists in database
3. **Current Date**: July 28, 2025 (today)
4. **Gap**: No data recorded for July 28, 2025 yet

### 3.2 Business Logic Verification

**Expected Behavior**: 
- If data exists for July 1-28: Show aggregate total
- If no data exists: Show 0 (current state)
- Month label: Always shows current month ("July 2025")

**Actual Database Query Result**:
```sql
-- Query executed: July 1-28, 2025 range
-- Found: 1 record (July 27)
-- Expected: Should show 700 tokens, not 0
```

**Discrepancy Identified**: The calculation logic should include the July 27 data (700 tokens), but the frontend shows 0, indicating a potential issue in:
- Data aggregation logic
- API response processing
- Frontend data binding

### 3.3 Detailed Investigation Points

**Critical Questions**:
1. Is the `month_records` query returning the July 27 data?
2. Is the `sum()` aggregation working correctly?
3. Is the API response structured properly?
4. Is the frontend parsing the response correctly?

## 4. "July 2025 • Batch Calculated" Label Analysis

### 4.1 Label Generation Logic

**Source Code**: Multiple locations
- Backend: `today.strftime('%B %Y')` → "July 2025"
- Frontend: `"• Batch Calculated"` (hardcoded string)

**Business Meaning**:
- **"July 2025"**: Current month being calculated
- **"Batch Calculated"**: Indicates daily batch processing (not real-time)

### 4.2 Label Business Rules

1. **Month Display**: Always shows current calendar month
2. **Batch Indicator**: Emphasizes business intelligence approach
3. **Update Timing**: Labels remain static until next batch run (00:00)

## 5. Complete Technical Workflow Documentation

### 5.1 Data Recording Workflow

**Trigger**: OpenRouter API usage generates webhook
**Process**:
1. `POST /webhook/openrouter-usage` receives usage data
2. `UsageService.record_usage_from_webhook()` processes data
3. `ClientUsageRepository.record_usage()` updates database
4. Three tables updated: `ClientDailyUsage`, `ClientUserDailyUsage`, `ClientModelDailyUsage`

### 5.2 Daily Batch Processing Workflow

**Schedule**: 00:00 daily (Polish timezone - Europe/Warsaw)
**Process**:
1. NBP API called for USD/PLN exchange rates
2. Historical data validated and corrected
3. Monthly totals recalculated
4. Cache invalidation and refresh

### 5.3 Frontend Display Workflow

**User Access**: Admin navigates to "My Organization Usage"
**Process**:
1. `MyOrganizationUsageContainer.svelte` mounts
2. `loadInitialData()` called automatically
3. `OrganizationUsageService.getUsageSummary()` API call
4. API calls `GET /my-organization/usage-summary`
5. Backend executes `get_usage_stats_by_client()` 
6. Response processed and displayed in StatCard

**Performance**: 10-second timeout with fallback data

## 6. Potential Issues Causing Zero Values

### 6.1 Data Processing Issues

1. **Missing Webhook Data**: No usage recorded for July 28
2. **Date Boundary Problems**: Query not including July 27 data
3. **Aggregation Errors**: Sum calculation returning 0 despite data
4. **API Response Issues**: Backend returning 0 in response
5. **Frontend Parsing**: UI not reading response correctly

### 6.2 Timing Issues

1. **Batch Processing Delay**: Data not yet processed for today
2. **Timezone Confusion**: Poland (UTC+2) vs system timezone
3. **Cache Staleness**: Old cached data being served
4. **Database Connection**: Query not reaching database

### 6.3 Configuration Issues

1. **Client Organization ID**: Wrong or missing client ID
2. **Environment Variables**: Missing configuration
3. **Database Schema**: Table structure mismatch
4. **Permission Issues**: Access denied to data

## 7. Recommended Investigation Steps

### 7.1 Immediate Diagnostics

1. **Verify Database Query**:
   ```sql
   SELECT * FROM client_daily_usage 
   WHERE client_org_id = 'dev_mai_client_d460a478' 
   AND usage_date >= '2025-07-01';
   ```

2. **Test API Endpoint**:
   ```bash
   curl -H "Authorization: Bearer <token>" \
        http://localhost:8080/api/v1/usage-tracking/my-organization/usage-summary
   ```

3. **Check Backend Logs**: Look for errors in `get_usage_stats_by_client()`

4. **Frontend Console**: Check for JavaScript errors in browser

### 7.2 Data Validation Steps

1. **Confirm Data Exists**: Verify July 27 record in database
2. **Test Aggregation**: Run calculation manually
3. **API Response Check**: Verify JSON structure
4. **Frontend Binding**: Confirm data reaches UI components

## 8. Business Impact Assessment

### 8.1 User Experience Impact

- **Admin Dashboard Confusion**: Zero values suggest no usage
- **Business Intelligence Failure**: Cannot track actual usage
- **Financial Planning Issues**: Inaccurate cost projections
- **Performance Monitoring**: Unable to assess system usage

### 8.2 System Reliability Assessment

**Positive Aspects**:
- Clean architecture with proper separation
- Comprehensive error handling
- Fallback mechanisms in place
- Detailed logging and monitoring

**Areas for Improvement**:
- Real-time data validation
- Better error reporting to users
- Data consistency checks
- Alerting for calculation failures

## 9. Architectural Recommendations

### 9.1 Short-term Fixes

1. **Add Debug Logging**: Enhanced logging in calculation methods
2. **Data Validation**: Verify aggregation logic is working
3. **API Response Validation**: Ensure proper JSON structure
4. **Frontend Error Handling**: Better error messages for users

### 9.2 Long-term Improvements

1. **Health Check Endpoints**: Monitor data pipeline health
2. **Real-time Validation**: Continuous data integrity checks
3. **User Notifications**: Alert users when data is processing
4. **Fallback Data Sources**: Alternative calculation methods

## 10. Conclusion

The "Total Tokens" showing "0" with "July 2025 • Batch Calculated" represents a well-architected system experiencing a data calculation issue. The business logic is sound, but there appears to be a disconnect between the available data (700 tokens from July 27) and the displayed value (0 tokens).

The "July 2025 • Batch Calculated" label is working correctly, indicating the system is properly identifying the current month and batch processing mode. The issue is specifically in the numerical calculation and display chain.

**Key Finding**: Database contains usage data, but the aggregation or display logic is not processing it correctly, resulting in zero values being shown to users.

**Recommended Action**: Focus investigation on the `get_usage_stats_by_client()` method and verify that the SQL query, aggregation logic, and API response structure are working as expected.

---

**Report Generated**: July 28, 2025  
**Analysis Scope**: Complete business logic workflow from OpenRouter integration to UI display  
**Architecture**: mAI OpenWebUI fork with Polish SME multi-tenant SaaS implementation