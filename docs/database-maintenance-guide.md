# Database Maintenance Guide for Client Organization System

This guide covers essential database maintenance for the client organization usage tracking system.

## 📊 Database Growth Expectations

### Usage Patterns (Per Client Organization)
- **Small org (6 users)**: ~120 requests/day = 3,600/month = 43,200/year
- **Medium org (20 users)**: ~400 requests/day = 12,000/month = 144,000/year
- **Large org (50 users)**: ~1,000 requests/day = 30,000/month = 360,000/year

### Storage Projections (20 Client Organizations)
- **Year 1**: ~2.5 million usage records = ~500 MB
- **Year 2**: ~5 million usage records = ~1 GB  
- **Year 3**: ~7.5 million usage records = ~1.5 GB

**Main Growth Driver**: `client_usage` table (99% of data volume)

## 🗓️ Maintenance Schedule

### Daily Tasks (Automated)
```bash
# Run daily maintenance
python database_maintenance.py --daily

# Tasks performed:
# - Verify backup completion
# - Check error logs  
# - Monitor disk space usage
# - Alert on unusual usage spikes
```

### Weekly Tasks
```bash
# Run weekly maintenance
python database_maintenance.py --weekly

# Tasks performed:
# - Update table statistics
# - Rebuild fragmented indexes
# - Check slow query log
# - Validate data integrity
```

### Monthly Tasks
```bash
# Run monthly maintenance  
python database_maintenance.py --monthly

# Tasks performed:
# - Archive usage data older than 12 months
# - Generate monthly summary tables
# - Clean up test/debug data
# - Performance health check
# - Disk space planning
```

### Quarterly Tasks
```bash
# Run quarterly maintenance
python database_maintenance.py --quarterly

# Tasks performed:
# - Deep performance analysis
# - Index optimization review
# - Capacity planning update
# - Security audit
# - Backup restore testing
```

### Yearly Tasks
```bash
# Run yearly maintenance
python database_maintenance.py --yearly

# Tasks performed:
# - Major data archival (2+ years old)
# - Compliance data review
# - Database schema optimization
# - Disaster recovery testing
```

## 🧹 Data Retention Strategy

### Detailed Usage Records (`client_usage` table)
- **0-12 months**: Keep all detailed records (active billing)
- **12-24 months**: Archive to compressed storage (dispute resolution)
- **2+ years**: Keep monthly summaries only (compliance/audit)

### Client Organization Data
- **Active clients**: Keep indefinitely
- **Inactive clients**: Archive after 2 years
- **Test/debug data**: Delete after 30 days

### Archival Process
```sql
-- 1. Create monthly summary from detailed data
INSERT INTO client_usage_summary 
SELECT 
    client_org_id,
    DATE_TRUNC('month', usage_date) as month,
    SUM(total_tokens) as total_tokens,
    SUM(markup_cost) as total_cost,
    COUNT(*) as total_requests,
    COUNT(DISTINCT model_name) as models_used,
    COUNT(DISTINCT user_id) as active_users
FROM client_usage 
WHERE usage_date < CURRENT_DATE - INTERVAL '12 months'
GROUP BY client_org_id, DATE_TRUNC('month', usage_date);

-- 2. Export detailed records to archive storage
COPY (SELECT * FROM client_usage WHERE usage_date < CURRENT_DATE - INTERVAL '12 months') 
TO '/backup/archives/client_usage_2023.csv' CSV HEADER;

-- 3. Delete archived detailed records
DELETE FROM client_usage WHERE usage_date < CURRENT_DATE - INTERVAL '12 months';
```

## ⚡ Performance Optimization

### Database Indexes
```sql
-- Essential indexes for query performance
CREATE INDEX idx_client_usage_date_range ON client_usage (client_org_id, usage_date);
CREATE INDEX idx_client_usage_user_date ON client_usage (user_id, usage_date);
CREATE INDEX idx_client_usage_model ON client_usage (model_name);
CREATE INDEX idx_client_usage_created_at ON client_usage (created_at);

-- Composite indexes for common queries
CREATE INDEX idx_client_usage_reporting ON client_usage (client_org_id, usage_date, model_name);
```

### Table Partitioning (PostgreSQL)
```sql
-- Partition client_usage table by month for better performance
CREATE TABLE client_usage_y2024m01 PARTITION OF client_usage 
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE client_usage_y2024m02 PARTITION OF client_usage 
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- Auto-create partitions for future months
-- (Use pg_partman extension or custom scripts)
```

### Query Optimization Tips
```sql
-- Good: Use date ranges for efficient partition pruning
SELECT * FROM client_usage 
WHERE client_org_id = 'client-123' 
  AND usage_date >= '2024-01-01' 
  AND usage_date < '2024-02-01';

-- Bad: Avoid full table scans
SELECT * FROM client_usage WHERE model_name LIKE '%gpt%';

-- Good: Use specific model names
SELECT * FROM client_usage WHERE model_name = 'gpt-4';
```

## 💾 Backup Strategy

### Daily Backups
```bash
#!/bin/bash
# daily_backup.sh

# Database dump with compression
pg_dump -h localhost -U mai_user mai_db | gzip > /backup/daily/mai_db_$(date +%Y%m%d).sql.gz

# Keep 7 days of daily backups
find /backup/daily -name "mai_db_*.sql.gz" -mtime +7 -delete

# Verify backup integrity
gunzip -t /backup/daily/mai_db_$(date +%Y%m%d).sql.gz
```

### Weekly Full Backups
```bash
#!/bin/bash
# weekly_backup.sh

# Full database backup with all objects
pg_dumpall -h localhost -U postgres | gzip > /backup/weekly/mai_full_$(date +%Y%m%d).sql.gz

# Keep 4 weeks of weekly backups
find /backup/weekly -name "mai_full_*.sql.gz" -mtime +28 -delete
```

### Point-in-Time Recovery Setup
```bash
# Enable WAL archiving in postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'cp %p /backup/wal/%f'
```

## 📈 Monitoring and Alerts

### Database Size Monitoring
```sql
-- Monitor table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY size_bytes DESC;
```

### Growth Rate Monitoring
```sql
-- Track daily usage record growth
SELECT 
    usage_date,
    COUNT(*) as daily_records,
    SUM(COUNT(*)) OVER (ORDER BY usage_date ROWS 6 PRECEDING) as weekly_avg
FROM client_usage 
WHERE usage_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY usage_date
ORDER BY usage_date;
```

### Performance Monitoring
```sql
-- Check slow queries (PostgreSQL)
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
```

## 🚨 Alert Thresholds

### Set up monitoring alerts for:
- **Database size > 80% of allocated space**
- **Daily usage records > 150% of normal**
- **Query response time > 5 seconds**
- **Backup failure**
- **Disk space < 10% free**
- **Connection count > 80% of max**

## 🔧 Maintenance Tools

### Run Database Maintenance
```bash
# Interactive maintenance
python database_maintenance.py

# Automated maintenance (for cron jobs)
python database_maintenance.py --auto --log-file=/var/log/mai_maintenance.log
```

### Cron Job Setup
```bash
# Add to crontab
crontab -e

# Daily backup at 2 AM
0 2 * * * /path/to/daily_backup.sh

# Weekly maintenance on Sunday at 3 AM  
0 3 * * 0 cd /path/to/mai && python database_maintenance.py --weekly

# Monthly maintenance on 1st at 4 AM
0 4 1 * * cd /path/to/mai && python database_maintenance.py --monthly
```

## 🛠️ Emergency Procedures

### Database Recovery
```bash
# Restore from latest backup
gunzip -c /backup/daily/mai_db_20240724.sql.gz | psql -h localhost -U mai_user mai_db

# Point-in-time recovery
pg_basebackup -h localhost -D /tmp/recovery -U postgres
# (Follow PostgreSQL PITR documentation)
```

### Performance Emergency
```sql
-- Find and kill long-running queries
SELECT pid, query_start, query FROM pg_stat_activity 
WHERE state = 'active' AND query_start < NOW() - INTERVAL '5 minutes';

-- Kill specific query
SELECT pg_terminate_backend(pid);

-- Emergency index creation
CREATE INDEX CONCURRENTLY idx_emergency ON client_usage (usage_date) 
WHERE usage_date >= CURRENT_DATE - INTERVAL '7 days';
```

## 📝 Maintenance Log Template

Keep a maintenance log for audit purposes:

```
Date: 2024-07-24
Maintenance Type: Monthly
Performed By: Admin
Duration: 45 minutes

Tasks Completed:
✅ Archived 125,000 usage records (11 months old)  
✅ Cleaned up 5 test client organizations
✅ Updated table statistics
✅ Verified backup integrity
✅ Generated performance report

Issues Found:
- Query on model usage report taking 8 seconds (added index)
- Database size grew 15% this month (within expected range)

Next Actions:
- Monitor new index performance
- Plan for quarterly capacity review
- Consider partitioning implementation
```

This maintenance strategy ensures your client organization database remains performant, reliable, and compliant with business requirements.