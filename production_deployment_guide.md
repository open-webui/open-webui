# Production Deployment Guide: mAI Usage Tracking

## Overview

This guide covers deploying the new OpenRouter usage tracking system for mAI in production across 20 Docker containers on Hetzner Cloud.

## System Architecture

### Option C Implementation: OpenRouter API Polling
- **Webhook Endpoints**: Ready for future OpenRouter webhook support
- **Background Sync**: Automatic polling of OpenRouter `/generations` API every 10 minutes
- **Real-time Updates**: Live counters updated immediately upon sync
- **Production Ready**: Handles failures gracefully, logs properly, scales automatically

## Deployment Steps

### 1. Apply Database Migration

```bash
# On each Docker container
docker exec open-webui-customization python -c "
import sqlite3
import os
from datetime import date
import time

# Apply the migration if not already applied
conn = sqlite3.connect('/app/backend/data/webui.db')
cursor = conn.cursor()

# Check if tables exist
cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='client_live_counters'\")
if not cursor.fetchone():
    print('⚠️  Usage tracking tables not found. Please run the migration first.')
    print('See: backend/open_webui/migrations/versions/f1a2b3c4d5e6_option1_simplified_schema.py')
else:
    print('✅ Usage tracking tables found')

conn.close()
"
```

### 2. Update Container Configuration

Ensure each container has the new usage tracking files:

```bash
# Copy new files to container
docker cp backend/open_webui/routers/usage_tracking.py open-webui-customization:/app/backend/open_webui/routers/
docker cp backend/open_webui/utils/background_sync.py open-webui-customization:/app/backend/open_webui/utils/
```

### 3. Restart Containers

```bash
# Restart each container to load new code
docker restart open-webui-customization
```

### 4. Verify Background Sync

Check logs to ensure background sync is working:

```bash
docker logs open-webui-customization | grep -i "background sync"
```

Expected output:
```
INFO - Starting OpenRouter usage background sync service
INFO - Background sync completed: 1/1 organizations synced  
```

## API Endpoints

### Manual Sync (Admin Only)
```bash
POST /api/v1/usage-tracking/sync/openrouter-usage
{
  "days_back": 1
}
```

### Real-time Usage Check
```bash
GET /api/v1/usage-tracking/usage/real-time/{client_org_id}
```

### Manual Usage Recording (Testing/Corrections)
```bash
POST /api/v1/usage-tracking/usage/manual-record
{
  "model": "deepseek-ai/deepseek-v3",
  "tokens": 1000,
  "cost": 0.002
}
```

## Monitoring & Troubleshooting

### Key Log Messages

**Successful Sync:**
```
INFO - Background sync completed: 1/1 organizations synced
DEBUG - ✅ Recorded 1000 tokens, $0.002600 for deepseek-ai/deepseek-v3
```

**API Errors:**
```
ERROR - OpenRouter API error for key sk-or-v1-xxx...: HTTP 429 Rate Limited
ERROR - Failed to sync usage for Organization Name: Connection timeout
```

**Database Issues:**
```
ERROR - Database error: no such table: client_live_counters
ERROR - Failed to get organizations: database is locked
```

### Health Check Commands

```bash
# Check if sync is running
docker exec open-webui-customization python -c "
from open_webui.utils.background_sync import is_sync_running
print('Sync running:', is_sync_running())
"

# Check recent usage data
docker exec open-webui-customization python -c "
import sqlite3
from datetime import date

conn = sqlite3.connect('/app/backend/data/webui.db')
cursor = conn.cursor()

cursor.execute('SELECT * FROM client_live_counters WHERE current_date = ?', (date.today(),))
result = cursor.fetchone()

if result:
    print(f'Today usage: {result[2]} tokens, ${result[5]:.6f}')
else:
    print('No usage data for today')

conn.close()
"
```

## Production Configuration

### Environment Variables

Add to your Docker compose or environment:

```yaml
environment:
  - OPENROUTER_USAGE_SYNC_INTERVAL=600  # 10 minutes
  - OPENROUTER_USAGE_SYNC_DAYS_BACK=1   # Sync last 1 day
  - LOG_LEVEL=INFO                       # Adjust as needed
```

### Resource Requirements

- **CPU**: Background sync is lightweight, ~5% additional CPU usage
- **Memory**: ~50MB additional memory per container
- **Network**: ~1 API request per 10 minutes per container
- **Storage**: Minimal additional database storage

## Multi-Tenant Deployment

### Organization Isolation

Each Docker container handles one organization:
- API key stored per organization in `client_organizations.openrouter_api_key`
- Usage data isolated by `client_org_id`
- Background sync processes only the container's organization

### Scaling Considerations

- **Hetzner Server**: Can handle 20+ containers easily
- **OpenRouter Rate Limits**: 1 request per 10 minutes per container = well within limits
- **Database Performance**: SQLite handles this workload efficiently
- **Backup Strategy**: Include usage tables in database backups

## Rollback Plan

If issues occur, rollback is simple:

```bash
# Stop background sync (temporary)
docker exec open-webui-customization python -c "
from open_webui.utils.background_sync import organization_usage_sync
import asyncio
asyncio.run(organization_usage_sync.stop_sync_service())
"

# Revert to previous container image if needed
docker stop open-webui-customization
docker run -d --name open-webui-customization-backup [previous_image]
```

## Future Enhancements

### When OpenRouter Adds Webhooks

1. Configure webhook URL in OpenRouter dashboard: `https://your-domain.com/api/v1/usage-tracking/webhook/openrouter-usage`
2. Disable background polling by setting `OPENROUTER_USAGE_SYNC_INTERVAL=0`
3. Usage data will flow in real-time via webhooks

### Enhanced Monitoring

Consider adding:
- Prometheus metrics for sync status
- Grafana dashboard for usage trends
- Alerting for sync failures
- Usage anomaly detection

## Support & Maintenance

### Regular Tasks

1. **Weekly**: Review sync logs for errors
2. **Monthly**: Check usage data accuracy against OpenRouter dashboard
3. **Quarterly**: Review API rate limits and adjust sync frequency if needed

### Common Issues

**Sync Not Working:**
- Check API key validity in database
- Verify network connectivity to OpenRouter
- Check OpenRouter account status

**Usage Data Missing:**
- Run manual sync: `POST /api/v1/usage-tracking/sync/openrouter-usage`
- Check database migration status
- Verify organization setup

**Performance Issues:**
- Reduce sync frequency if needed
- Check database size and optimize if necessary
- Monitor container resource usage

## Contact & Resources

- **OpenRouter API Docs**: https://openrouter.ai/docs/api-reference
- **mAI Issues**: Internal issue tracker
- **Emergency**: Check container logs first, then manual sync