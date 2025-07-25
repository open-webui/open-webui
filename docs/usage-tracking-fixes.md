# Usage Tracking System Fixes

## Overview

This document describes the comprehensive fixes implemented to resolve critical issues with the "Today's Tokens (live)" functionality in the mAI usage tracking system.

## Issues Identified

### 🚨 Critical Issue #1: Background Sync Didn't Update Live Counters
- **Problem**: Background sync process (fetching from OpenRouter every 10 minutes) completely bypassed the `ClientLiveCounters` table
- **Impact**: "Today's Tokens (live)" showed 0 tokens despite actual usage
- **Root Cause**: Background sync only updated daily summaries, not live counters

### 🚨 Critical Issue #2: Dual Recording Systems
- **Problem**: Two separate, unsynchronized systems for recording usage data:
  - Manual/Webhook system using raw SQL (usage_tracking.py)  
  - Background sync system using SQLAlchemy ORM (background_sync.py)
- **Impact**: Data inconsistencies and maintenance complexity
- **Root Cause**: Different development approaches over time

### 🚨 Critical Issue #3: Data Freshness Problem
- **Problem**: Live counters became stale with no mechanism to restore them
- **Impact**: Users saw outdated usage information
- **Root Cause**: Missing fallback logic to populate live counters from daily summaries

### 🚨 Critical Issue #4: Workflow Inconsistency
- **Expected**: OpenRouter API → Background Sync → Live Counters → Frontend
- **Actual**: OpenRouter API → Background Sync → Daily Summaries (live counters empty)

## Fixes Implemented

### Fix #1: Background Sync Live Counter Updates

**File**: `backend/open_webui/utils/background_sync.py`

**Changes**:
- Added `ClientLiveCounters` import to background sync module
- Modified `record_usage_batch_to_db()` method to update live counters for today's data
- Added logic to handle both creation and incremental updates of live counters
- Ensures live counters are synchronized with daily summaries

**Key Code Addition**:
```python
# 4. Update live counters for today's data to ensure real-time UI accuracy
today = date.today()
today_generations = generations_by_date.get(today, [])

if today_generations:
    today_tokens = sum(g["tokens"] for g in today_generations)
    today_requests = len(today_generations)
    today_raw_cost = sum(g["raw_cost"] for g in today_generations)
    today_markup_cost = sum(g["markup_cost"] for g in today_generations)
    
    # Update or create live counter for today
    live_counter = db.query(ClientLiveCounters).filter_by(
        client_org_id=client_org_id
    ).first()
    
    if live_counter:
        # Handle stale vs current counter logic
        if live_counter.current_date != today:
            # Reset for today
            live_counter.current_date = today
            live_counter.today_tokens = today_tokens
            # ... etc
        else:
            # Add to existing
            live_counter.today_tokens += today_tokens
            # ... etc
    else:
        # Create new live counter
        live_counter = ClientLiveCounters(...)
        db.add(live_counter)
```

### Fix #2: Consolidated Recording Systems

**Files**: `backend/open_webui/routers/usage_tracking.py`

**Changes**:
- Replaced raw SQL operations with consolidated ORM approach
- Modified `record_usage_to_db()` to use `ClientUsageDB.record_usage()` method
- Updated real-time usage endpoint to use ORM methods
- Updated manual recording endpoint to use ORM methods

**Before (Raw SQL)**:
```python
cursor.execute("""
    INSERT OR REPLACE INTO client_live_counters 
    (client_org_id, current_date, today_tokens, ...)
    VALUES (?, ?, COALESCE(...), ...)
""", (...))
```

**After (ORM)**:
```python
success = ClientUsageDB.record_usage(
    client_org_id=client_org_id,
    user_id=user_id,
    openrouter_user_id=openrouter_user_id,
    model_name=model_name,
    usage_date=today,
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    raw_cost=raw_cost,
    markup_cost=markup_cost,
    provider=provider,
    request_metadata={"source": "webhook", "external_user": external_user}
)
```

### Fix #3: Fallback Logic Implementation

**File**: `backend/open_webui/models/organization_usage.py`

**Changes**:
- Enhanced `get_usage_stats_by_client()` method with comprehensive fallback logic
- Added automatic restoration of live counters from daily summaries when stale/missing
- Implemented creation of missing live counters from existing daily data

**Key Logic**:
```python
if live_counter:
    if live_counter.current_date != today:
        # Stale counter - check daily summaries for today's data
        today_summary = db.query(ClientDailyUsage).filter_by(
            client_org_id=client_org_id,
            usage_date=today
        ).first()
        
        if today_summary:
            # Restore from daily summary
            live_counter.current_date = today
            live_counter.today_tokens = today_summary.total_tokens
            # ... restore all fields
            log.info(f"Restored live counter from daily summary")
        else:
            # Reset to zero
            live_counter.current_date = today
            live_counter.today_tokens = 0
            # ... reset all fields
else:
    # No live counter exists - create from daily summary if available
    today_summary = db.query(ClientDailyUsage).filter_by(
        client_org_id=client_org_id,
        usage_date=today
    ).first()
    
    if today_summary:
        live_counter = ClientLiveCounters(
            client_org_id=client_org_id,
            current_date=today,
            today_tokens=today_summary.total_tokens,
            # ... populate from summary
        )
        db.add(live_counter)
        log.info(f"Created live counter from daily summary")
```

### Fix #4: Comprehensive Testing

**Files**: 
- `backend/tests/test_usage_tracking_integration.py`
- `backend/scripts/validate_usage_tracking_fixes.py`

**Test Coverage**:
- Background sync updates live counters correctly
- Fallback logic restores data from daily summaries  
- Consolidated recording system works end-to-end
- Real-time refresh returns accurate data
- Monthly totals include today's live data
- Concurrent operations are handled safely

## Data Flow After Fixes

### New Correct Workflow:
```
OpenRouter API (every 10min)
    ↓
Background Sync Process
    ↓
┌─ Daily Summaries (historical)
└─ Live Counters (today) ← FIXED
    ↓
Frontend API (every 30sec)
    ↓
"Today's Tokens (live)" Display ← NOW WORKS
```

### Fallback Mechanism:
```
Frontend Request
    ↓
Check Live Counter
    ↓
If Missing/Stale → Check Daily Summary
    ↓
If Found → Restore Live Counter
    ↓
Return Accurate Data
```

## Benefits

1. **Real-Time Accuracy**: "Today's Tokens (live)" now shows actual usage data
2. **System Reliability**: Fallback mechanisms prevent data loss
3. **Code Maintainability**: Single ORM-based recording system
4. **Data Consistency**: All paths update both daily summaries and live counters
5. **User Experience**: Live dashboard reflects actual spending patterns

## Validation

Run the validation script to verify all fixes:

```bash
cd backend
python scripts/validate_usage_tracking_fixes.py
```

Expected output:
```
✅ PASS    Background Sync Updates
✅ PASS    Fallback Logic  
✅ PASS    Consolidated Recording
✅ PASS    Real-Time Accuracy

Overall: 4/4 tests passed
🎉 All fixes are working correctly!
```

## Monitoring

Monitor these log messages to verify the system is working:

```
INFO: Restored live counter from daily summary for client client_xyz: 1500 tokens
INFO: Created live counter from daily summary for client client_xyz: 2300 tokens  
✅ Background sync batch: 5 generations, 12500 tokens, $0.162500
```

## Future Maintenance

1. **Database Migrations**: Ensure live counter table schema stays aligned
2. **Background Sync Monitoring**: Watch for sync failures that could affect live data
3. **Performance**: Monitor query performance as data grows
4. **Testing**: Run integration tests regularly, especially after OpenRouter API changes

## Related Files

- **Backend Models**: `backend/open_webui/models/organization_usage.py`
- **Background Sync**: `backend/open_webui/utils/background_sync.py` 
- **API Routes**: `backend/open_webui/routers/client_organizations.py`
- **Usage Tracking**: `backend/open_webui/routers/usage_tracking.py`
- **Frontend Component**: `src/lib/components/admin/Settings/MyOrganizationUsage.svelte`
- **Frontend API**: `src/lib/apis/organizations/index.ts`

## Summary

The "Today's Tokens (live)" functionality is now fully operational with:
- ✅ Background sync populates live counters
- ✅ Fallback logic prevents data loss  
- ✅ Consolidated recording system
- ✅ Real-time accuracy for user dashboard
- ✅ Comprehensive testing coverage

Users will now see accurate, real-time token usage and cost information in their mAI dashboard.