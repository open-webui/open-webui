# Daily Batch Processing Schedule Change - Option 1 Implementation

## Overview

Successfully implemented Option 1: Moving daily batch processing from 00:00 (midnight) to 13:00 (1 PM CET) to align with NBP (Polish National Bank) exchange rate publication schedule.

## Background

### Problem
- NBP publishes USD/PLN exchange rates at 11:30 AM CET based on calculations at 11:00 AM
- Previous midnight (00:00) batch processing caused a 1-day lag
- Monday's costs were calculated using Friday's exchange rate instead of Monday's rate
- This created confusion for Polish SME users who expected same-day rate accuracy

### Solution
- Move batch processing to 13:00 (1 PM CET/CEST)
- Ensures same-day exchange rates are used for daily cost conversion
- Provides more intuitive and accurate cost reporting

## Implementation Details

### 1. Scheduling Infrastructure

**New Component: `batch_scheduler.py`**
- Uses APScheduler with AsyncIOScheduler for robust scheduling
- Timezone-aware scheduling (Europe/Warsaw for CET/CEST)
- Automatic daylight saving time handling
- Error handling with comprehensive logging
- Grace period for missed runs (1 hour)
- Prevention of overlapping executions

**Key Features:**
```python
# Schedule daily batch processing at 13:00 CET/CEST
self.scheduler.add_job(
    func=self._run_batch_with_error_handling,
    trigger=CronTrigger(hour=13, minute=0, timezone=cet_tz),
    id='daily_batch_processing',
    name='Daily Batch Processing',
    replace_existing=True,
    max_instances=1,  # Prevent overlapping runs
    coalesce=True,    # Combine missed runs
    misfire_grace_time=3600  # 1 hour grace period
)
```

### 2. Application Integration

**Lifecycle Management:**
- Integrated scheduler initialization in `main.py` lifespan context
- Proper startup and shutdown handling
- Error isolation to prevent application startup failures

**Startup Sequence:**
```python
# Initialize daily batch processing scheduler
try:
    from open_webui.utils.batch_scheduler import init_batch_scheduler
    await init_batch_scheduler()
except Exception as e:
    log.error(f"Failed to initialize daily batch scheduler: {e}")
```

### 3. Admin Management API

**New Admin Endpoints:**
- `GET /api/v1/admin/batch/status` - Check scheduler status
- `POST /api/v1/admin/batch/trigger` - Manual batch processing trigger

**Example Usage:**
```bash
# Check scheduler status
curl -X GET "http://localhost:8080/api/v1/admin/batch/status" \
  -H "Authorization: Bearer <admin_token>"

# Manually trigger batch processing
curl -X POST "http://localhost:8080/api/v1/admin/batch/trigger" \
  -H "Authorization: Bearer <admin_token>"
```

### 4. Updated Documentation

**Files Modified:**
- `orchestrator.py` - Updated timing comments and documentation
- `daily_batch_processor_legacy.py` - Updated entry point documentation
- `billing_router.py` - Updated cache refresh timing comments
- `pricing_service.py` - Updated pricing refresh documentation
- `openrouter_models_old.py` - Updated cache timing comments
- `performance_comparison.py` - Updated deployment time reference

**Example Documentation Update:**
```python
async def run_daily_batch(self) -> BatchResult:
    """
    Main daily batch processing function
    Should be called at 13:00 (1 PM) CET daily via cron or scheduler
    
    Timing rationale:
    - NBP publishes USD/PLN rates at 11:30 AM CET based on 11:00 AM calculations
    - 13:00 execution ensures same-day exchange rates are used for daily cost conversion
    - Eliminates 1-day lag where Monday's costs used Friday's rates
    """
```

### 5. Dependencies

**Added Requirements:**
- `pytz==2024.2` - Timezone handling for CET/CEST
- `APScheduler==3.10.4` - Already present, utilized for scheduling

## Benefits Achieved

### Immediate Benefits
1. **Same-day Exchange Rate Accuracy**: Monday costs now use Monday's NBP rate
2. **Reduced User Confusion**: Costs align with user expectations
3. **More Intuitive Reporting**: Daily reports reflect current-day exchange rates
4. **Better Polish Market Alignment**: Timing matches Polish business hours

### Technical Benefits
1. **Robust Scheduling**: APScheduler provides enterprise-grade scheduling
2. **Timezone Awareness**: Automatic handling of CET/CEST transitions
3. **Error Resilience**: Comprehensive error handling and recovery
4. **Admin Control**: Manual trigger capability for testing/emergency use
5. **Monitoring**: Status endpoints for operational visibility

### Operational Benefits
1. **Afternoon Processing**: Better for monitoring during business hours
2. **Reduced Weekend Issues**: Exchange rate data is more current
3. **Improved Debugging**: Easier to diagnose issues during working hours

## Deployment Notes

### Production Deployment
1. **Gradual Rollout**: Deploy to staging environment first
2. **Monitor First Run**: Watch the first 13:00 execution carefully
3. **Verify Exchange Rates**: Confirm NBP rates are being used correctly
4. **User Communication**: Inform users about the timing change

### Monitoring
- Check scheduler status via admin API
- Monitor logs for successful 13:00 executions
- Verify exchange rate accuracy in daily reports
- Watch for any timing-related issues

### Rollback Plan
If issues arise, the system can be temporarily reverted to manual batch processing while investigating the scheduler configuration.

## Testing Recommendations

1. **Manual Trigger Testing**: Use admin API to test batch processing
2. **Timezone Testing**: Verify proper CET/CEST handling
3. **Exchange Rate Validation**: Confirm same-day NBP rates are used
4. **Error Handling**: Test scheduler behavior during failures
5. **User Acceptance**: Validate improved cost reporting with users

## Files Modified

**Core Components:**
- `open_webui/utils/batch_scheduler.py` (NEW)
- `open_webui/routers/batch_admin.py` (NEW)
- `open_webui/main.py` (scheduler integration)
- `requirements.txt` (pytz dependency)

**Documentation Updates:**
- `open_webui/utils/daily_batch_processor/orchestrator.py`
- `open_webui/utils/daily_batch_processor_legacy.py`
- `open_webui/usage_tracking/routers/billing_router.py`
- `open_webui/usage_tracking/services/pricing_service.py`
- `open_webui/utils/openrouter_models_old.py`
- `open_webui/utils/daily_batch_processor/performance_comparison.py`

## Conclusion

Option 1 has been successfully implemented with a robust, production-ready scheduling system. The 13:00 CET timing ensures optimal exchange rate accuracy while providing better operational visibility and user experience for Polish SME customers.

The implementation includes comprehensive error handling, admin management capabilities, and maintains backward compatibility with existing batch processing functionality.