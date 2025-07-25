# OpenRouter Integration & Usage Tracking

## Overview

mAI includes production-ready OpenRouter integration with automated usage tracking and 1.3x markup pricing. The system automatically polls OpenRouter's API every 10 minutes to fetch usage data and display it in the admin dashboard.

## Quick Setup

### 1. Admin Configuration
1. **Login as Admin**: First registered user automatically becomes admin
2. **Navigate to Settings**: Click Settings in sidebar
3. **Go to Connections**: Select "Connections" tab
4. **Add OpenRouter Key**: Enter your OpenRouter API key (format: `sk-or-v1-...`)
5. **Automatic Setup**: System automatically:
   - Stores API key securely in database
   - Starts background sync service
   - Creates organization mapping
   - Begins usage tracking

### 2. User Management
1. **Disable Public Signup**: System automatically disables signup after first user
2. **Create User Accounts**: Navigate to Admin → Users
3. **Add Employees**: Create accounts for 4-19 company employees
4. **Distribute Credentials**: Provide login details to employees

### 3. Usage Monitoring
- **Real-time Dashboard**: Settings → Usage shows live usage data
- **30-second Updates**: Dashboard refreshes automatically
- **Historical Data**: Daily trends, per-user, and per-model breakdowns
- **Accurate Costs**: Fixed currency formatting shows precise costs (e.g., $0.002002)

## Background Sync Service ✅ PRODUCTION READY

### How It Works
The system solves the "streaming response problem" where OpenRouter's Server-Sent Events (SSE) bypass traditional usage recording:

```
1. User makes chat request → OpenRouter streaming response (SSE)
2. Background service polls OpenRouter /generation API every 10 minutes
3. Fetches actual usage data with costs and token counts
4. Updates database with aggregated usage per organization
5. Admin dashboard displays real-time usage and costs
```

### Key Features
- **Automatic Polling**: Every 10 minutes (configurable)
- **Error Recovery**: Handles API failures and container restarts
- **Production Logging**: Comprehensive logs for monitoring
- **Multi-tenant**: Isolated usage tracking per client organization
- **Accurate Billing**: 1.3x markup automatically calculated

### Configuration
Environment variables for fine-tuning:

```bash
# Sync frequency (default: 600 seconds = 10 minutes)
OPENROUTER_USAGE_SYNC_INTERVAL=600

# How many days back to sync (default: 1)
OPENROUTER_USAGE_SYNC_DAYS_BACK=1

# Logging level for monitoring
LOG_LEVEL=INFO
```

## API Endpoints

### Admin Endpoints
Manual sync and monitoring endpoints for administrators:

#### Trigger Manual Sync
```bash
curl -X POST "http://localhost:3000/api/v1/usage-tracking/sync/openrouter-usage" \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{"days_back": 1}'
```

**Response:**
```json
{
  "status": "completed",
  "results": [
    {
      "organization": "Company Name",
      "synced_generations": 5,
      "status": "success"
    }
  ],
  "total_organizations": 1
}
```

#### Check Real-time Usage
```bash
curl "http://localhost:3000/api/v1/usage-tracking/usage/real-time/{client_org_id}" \
  -H "Authorization: Bearer {token}"
```

**Response:**
```json
{
  "client_org_id": "org_123",
  "date": "2025-07-24",
  "tokens": 1751,
  "requests": 2,
  "cost": 0.002002,
  "last_updated": 1721808000
}
```

#### Manual Usage Recording (Testing/Corrections)
```bash
curl -X POST "http://localhost:3000/api/v1/usage-tracking/usage/manual-record" \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-ai/deepseek-v3",
    "tokens": 1000,
    "cost": 0.002
  }'
```

### Legacy Endpoints
The system maintains compatibility with existing client organization endpoints:

- `GET /client_organizations/usage/my-organization` - User's organization usage
- `GET /client_organizations/usage/my-organization/today` - Today's usage for user's org
- `GET /client_organizations/usage/summary` - Organization usage statistics

## Database Schema

### Core Tables
The usage tracking system uses 7 optimized tables:

#### `client_organizations`
- Client organization management
- OpenRouter API key storage (encrypted)
- Markup rates (default 1.3x) and monthly limits

#### `client_live_counters`  
- **Real-time usage data** for today only
- Updated immediately after sync
- Primary source for dashboard metrics

#### `client_daily_usage`
- Daily usage summaries per organization
- Historical data for trend analysis

#### `client_user_daily_usage`
- Per-user daily usage within organizations
- Individual employee usage tracking

#### `client_model_daily_usage`
- Per-model daily usage statistics
- AI model performance and cost breakdown

## Frontend Dashboard

### Usage Tab (Admin Only)
Location: Settings → Usage

#### Real-Time Metrics Cards
- **Today's Tokens**: Live token count with pulsing indicator
- **Today's Cost**: Real-time cost with 1.3x markup applied (fixed formatting)
- **Month Total**: Aggregated monthly usage and costs
- **Daily Average**: Calculated average daily spend

#### Tabbed Analytics
1. **Daily Trend**: Historical usage over last 30 days with charts
2. **Usage Stats**: Detailed comparisons and percentages
3. **By User**: Per-user breakdown (admin sees all users)
4. **By Model**: Per-AI-model usage statistics

#### Auto-Refresh System
- **30-second updates** for today's live data
- **Manual refresh** button for immediate updates
- **Last updated** timestamp display
- **Fixed currency display** shows 6 decimal places for small amounts

## Production Database Tools

### Database Initialization
```bash
# Initialize all tables with sample data for testing
python create_tables.py
```

### Safe Database Cleanup
```bash
# Clean usage data while preserving configuration
python clean_usage_database.py
```

### Complete Database Reset
```bash
# Complete reset (use with caution)
python complete_usage_reset.py
```

## Container Management

### Health Checks
```bash
# Check background sync status
docker logs mai-container | grep -i "background sync"

# Verify sync is running
docker logs mai-container | grep "Starting background usage sync"

# Check for sync errors  
docker logs mai-container | grep -i "error" | grep -i "sync"
```

### Usage Data Verification
```bash
# Check today's usage data
docker exec mai-container python -c "
from datetime import date
import sqlite3

conn = sqlite3.connect('/app/backend/data/webui.db')
cursor = conn.cursor()

cursor.execute('SELECT * FROM client_live_counters WHERE current_date = ?', (date.today(),))
result = cursor.fetchone()

if result:
    print(f'Today usage: {result[2]} tokens, \${result[5]:.6f}')
else:
    print('No usage data for today')

conn.close()
"
```

### OpenRouter API Testing
```bash
# Test API connectivity with your key
curl -H "Authorization: Bearer sk-or-v1-your-key" \
  "https://openrouter.ai/api/v1/generation?limit=1"

# Expected response: JSON with generation data
```

## Troubleshooting

### Common Issues

#### Sync Not Working
**Symptoms**: Dashboard shows no usage data, logs show sync errors

**Solutions**:
1. **Check API Key**: Verify OpenRouter key in Settings → Connections
2. **Test API Access**: Use curl command above to test key validity
3. **Check Logs**: Look for specific error messages in container logs
4. **Manual Sync**: Trigger manual sync via API endpoint

#### Currency Showing $0.00
**Symptoms**: Token counts show but costs display as $0.00

**Status**: ✅ **FIXED** - Updated currency formatting shows 6 decimal places for small amounts

#### Historical Data Empty
**Symptoms**: Daily Trend, By User, By Model tabs show no data

**Solutions**:
1. **Initialize Database**: Run `python create_tables.py` for sample data
2. **Wait for Sync**: Background sync needs 10-20 minutes to populate data
3. **Check Sync Logs**: Verify sync is running and successful

#### Container Startup Issues
**Symptoms**: Container keeps restarting, won't stay running

**Status**: ✅ **FIXED** - Resolved syntax and import errors in usage tracking code

### Log Messages

#### Successful Sync
```
INFO - Starting background usage sync (interval: 600s)
INFO - Background sync completed: 1/1 organizations synced
DEBUG - ✅ Recorded 1000 tokens, $0.002600 for deepseek-ai/deepseek-v3
```

#### API Errors
```
ERROR - OpenRouter API error for key sk-or-v1-xxx...: HTTP 429 Rate Limited
ERROR - Failed to sync usage for Organization Name: Connection timeout
ERROR - OpenRouter API error for key sk-or-v1-xxx...: HTTP 401 Unauthorized
```

#### Database Issues
```
ERROR - Database error: no such table: client_live_counters
ERROR - Failed to get organizations: database is locked
```

## Billing & Cost Management

### Markup Calculation
```
Raw Cost (from OpenRouter) × 1.3 = Client Cost
Example: $0.10 × 1.3 = $0.13 (charged to client)
Profit: $0.03 per request
```

### Monthly Billing Cycle
- **Billing Period**: 1st to last day of each month
- **Reset Date**: Automatically resets on 1st of each month
- **Historical Data**: Preserved for accounting and analytics

### Cost Tracking Features
- **Real-time Cost Updates**: Dashboard shows current month spending
- **Daily Cost Breakdown**: Historical cost trends over time
- **Per-User Costs**: Individual employee usage and costs
- **Per-Model Costs**: Cost breakdown by AI model and provider
- **Markup Transparency**: Clear display of base cost + markup

## Security & Privacy

### API Key Security
- **Encrypted Storage**: OpenRouter keys stored encrypted in database
- **Access Control**: Only admin users can view/modify API keys
- **Key Rotation**: Easy key replacement through Settings interface

### Data Isolation
- **Single-Tenant**: Each container has completely isolated database
- **User Privacy**: Individual usage tracked but not shared between organizations
- **Audit Trail**: All configuration changes logged for security

### Rate Limiting
- **Background Sync**: Respects OpenRouter rate limits (max 1 request per 10 minutes)
- **API Endpoints**: Built-in rate limiting on manual sync endpoints
- **Error Handling**: Graceful handling of rate limit responses

## Future Enhancements

### Webhook Support (When Available)
The system is ready for OpenRouter webhook support:

1. **Webhook Endpoint**: Already implemented at `/api/v1/usage-tracking/webhook/openrouter-usage`
2. **Real-time Updates**: When OpenRouter adds webhooks, usage will be instant
3. **Polling Disable**: Set `OPENROUTER_USAGE_SYNC_INTERVAL=0` to disable polling

### Planned Features
- **CSV Export**: Usage data export for accounting systems
- **Usage Alerts**: Notifications when approaching monthly limits
- **Advanced Analytics**: Interactive charts and usage predictions
- **Multi-currency Support**: Support for non-USD billing
- **API Rate Optimization**: Intelligent sync frequency based on usage patterns

## Support

### Getting Help
For issues with the usage tracking system:

1. **Check Logs**: Always start with container logs for error details
2. **Verify Setup**: Ensure API key is valid and sync is running
3. **Test Endpoints**: Use curl commands to test API connectivity
4. **Database Tools**: Use provided scripts for database management

### Performance Monitoring
- **CPU Usage**: ~5% additional CPU for background sync
- **Memory Usage**: ~50MB additional memory per container
- **Network Usage**: ~1 API request per 10 minutes
- **Storage**: Minimal database storage (~1KB per day per organization)

The system is designed for production deployment with 20+ containers on a single Hetzner server, providing reliable usage tracking with minimal resource overhead.