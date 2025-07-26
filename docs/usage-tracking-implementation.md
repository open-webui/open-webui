# Usage Tracking Implementation

## Overview
mAI implements real-time usage tracking for OpenRouter API calls with automatic database recording and cost calculation with 1.3x markup.

## Key Components

### 1. Environment-Based Configuration
- All configuration via `.env` file
- Single organization per Docker instance
- No manual API key management needed

### 2. Automatic Database Initialization
**File**: `backend/open_webui/utils/usage_tracking_init.py`
- Runs on container startup via FastAPI lifespan
- Creates tables before querying (critical fix)
- Idempotent - safe to run multiple times

### 3. Usage Recording Module
**File**: `backend/open_webui/utils/openrouter_client_manager.py`
- Singleton pattern for consistent state
- `record_real_time_usage()` captures API responses
- Calculates markup cost (1.3x)
- Saves to database via ORM

### 4. Database Schema
```sql
-- Client organization with API key and markup
client_organizations (
  id TEXT PRIMARY KEY,        -- OPENROUTER_EXTERNAL_USER
  name TEXT,                  -- ORGANIZATION_NAME
  openrouter_api_key TEXT,
  markup_rate REAL DEFAULT 1.3
)

-- Daily usage per user
client_user_daily_usage (
  client_org_id TEXT,
  user_id TEXT,
  openrouter_user_id TEXT,    -- external_user from API
  total_tokens INTEGER,
  raw_cost REAL,
  markup_cost REAL
)

-- Daily usage per model
client_model_daily_usage (
  client_org_id TEXT,
  model_name TEXT,
  provider TEXT,
  total_tokens INTEGER,
  raw_cost REAL,
  markup_cost REAL
)
```

## Data Flow

1. **User Query** → OpenRouter API with `external_user`
2. **API Response** → Contains usage data (tokens, cost)
3. **openai.py Router** → Detects usage in response
4. **Background Task** → Calls `record_real_time_usage()`
5. **Database Save** → Updates daily usage tables
6. **UI Display** → Shows real usage in dashboard

## Testing

Use `test_usage_recording.py` to verify:
- Database tables exist
- Usage data is being recorded
- Costs are calculated correctly

## Production Deployment

1. Run `generate_client_env.py --production`
2. Deploy with `docker-compose-customization.yaml`
3. Usage tracking starts automatically
4. Monitor via Admin Dashboard