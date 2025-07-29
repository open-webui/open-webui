# mAI Production Deployment Guide - Organization Model Access

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [New Deployment Setup](#new-deployment-setup)
4. [Existing Deployment Migration](#existing-deployment-migration)
5. [Organization Management](#organization-management)
6. [Troubleshooting](#troubleshooting)
7. [Performance Monitoring](#performance-monitoring)
8. [Security Considerations](#security-considerations)

## Overview

This guide covers the production deployment of mAI with organization-based model access control. The system supports multiple organizations with isolated model access, automatic initialization, and high-performance querying.

### Key Features
- **Multi-tenant Architecture**: Each organization has isolated model access
- **Automatic Initialization**: Zero manual database setup required
- **High Performance**: Sub-millisecond query times with proper indexing
- **Security**: SQL injection protection and transaction safety
- **Scalability**: Supports 300+ concurrent users per container

## Prerequisites

### System Requirements
- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum (8GB recommended)
- 20GB disk space for data and logs
- Linux host (Ubuntu 20.04+ recommended)

### Environment Variables
```bash
# Required
OPENROUTER_API_KEY=sk-or-v1-xxxxx
OPENROUTER_EXTERNAL_USER=mai_client_companyname
ORGANIZATION_NAME="Company Name"
WEBUI_SECRET_KEY=<generate-secure-key>

# Optional
ENABLE_MODEL_FILTER=true
BYPASS_MODEL_ACCESS_CONTROL=false
WEBUI_SESSION_COOKIE_SECURE=true
WEBUI_SESSION_COOKIE_SAME_SITE=lax
```

## New Deployment Setup

### Step 1: Configure Environment

Create `.env` file:
```bash
# Generate secure key
openssl rand -hex 32 > webui_secret.txt

# Create .env
cat > .env << EOF
OPENROUTER_API_KEY=sk-or-v1-xxxxx
OPENROUTER_EXTERNAL_USER=mai_client_${CLIENT_NAME}
ORGANIZATION_NAME="${CLIENT_FULL_NAME}"
WEBUI_SECRET_KEY=$(cat webui_secret.txt)
ENABLE_MODEL_FILTER=true
BYPASS_MODEL_ACCESS_CONTROL=false
EOF

# Secure the file
chmod 600 .env
```

### Step 2: Configure Docker Compose

```yaml
version: '3.8'

services:
  mai-backend:
    image: ghcr.io/your-org/mai-backend:latest
    container_name: mai-backend-${CLIENT_NAME}
    env_file: .env
    volumes:
      - ./data:/app/backend/data
      - ./logs:/app/backend/logs
    ports:
      - "8080:8080"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G

  mai-frontend:
    image: ghcr.io/your-org/mai-frontend:latest
    container_name: mai-frontend-${CLIENT_NAME}
    environment:
      - PUBLIC_API_BASE_URL=http://mai-backend:8080/api
    ports:
      - "3000:3000"
    depends_on:
      - mai-backend
    restart: unless-stopped
```

### Step 3: Deploy

```bash
# Create directories
mkdir -p data logs

# Start services
docker-compose up -d

# Verify deployment
docker-compose ps
docker logs mai-backend-${CLIENT_NAME} --tail 50

# Check automatic initialization
docker exec mai-backend-${CLIENT_NAME} sqlite3 /app/backend/data/webui.db \
  "SELECT COUNT(*) FROM organization_models WHERE organization_id = 'mai_client_${CLIENT_NAME}';"
```

### Step 4: Initial Admin Setup

```bash
# First user becomes admin automatically
# Access the UI at http://your-server:3000
# Register with admin email

# Verify admin setup
docker exec mai-backend-${CLIENT_NAME} sqlite3 /app/backend/data/webui.db \
  "SELECT id, email, role FROM user WHERE role = 'admin';"
```

## Existing Deployment Migration

### Step 1: Backup Current Data

```bash
# Stop services
docker-compose down

# Backup database
cp data/webui.db data/webui.db.backup.$(date +%Y%m%d_%H%M%S)

# Backup configuration
tar -czf config_backup_$(date +%Y%m%d).tar.gz .env docker-compose.yml
```

### Step 2: Apply Organization Structure

Create migration script `migrate_to_organizations.py`:
```python
#!/usr/bin/env python3
"""
Migration script for existing deployments to organization model access.
"""

import sqlite3
import os
import time
from datetime import datetime

def migrate_database(db_path, org_id, org_name):
    """Migrate existing database to organization structure"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"Starting migration for organization: {org_name} ({org_id})")
    
    try:
        # Start transaction
        cursor.execute("BEGIN TRANSACTION")
        
        # Create organization tables if not exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS organization_models (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                model_id TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at INTEGER,
                updated_at INTEGER,
                UNIQUE(organization_id, model_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS organization_members (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT DEFAULT 'member',
                is_active INTEGER DEFAULT 1,
                joined_at INTEGER,
                UNIQUE(organization_id, user_id)
            )
        """)
        
        # Link all existing users to organization
        cursor.execute("""
            INSERT OR IGNORE INTO organization_members (id, organization_id, user_id, role, is_active, joined_at)
            SELECT 
                'om_' || user.id || '_' || ?,
                ?,
                user.id,
                CASE WHEN user.role = 'admin' THEN 'admin' ELSE 'member' END,
                1,
                ?
            FROM user
            WHERE user.role != 'pending'
        """, (org_id, org_id, int(time.time())))
        
        users_migrated = cursor.rowcount
        print(f"✅ Migrated {users_migrated} users to organization")
        
        # Link all active models to organization
        cursor.execute("""
            INSERT OR IGNORE INTO organization_models (id, organization_id, model_id, is_active, created_at, updated_at)
            SELECT 
                'orgmod_' || ? || '_' || model.id,
                ?,
                model.id,
                model.is_active,
                ?,
                ?
            FROM model
            WHERE model.base_model_id IS NULL
        """, (org_id, org_id, int(time.time()), int(time.time())))
        
        models_migrated = cursor.rowcount
        print(f"✅ Linked {models_migrated} models to organization")
        
        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_org_members_user_active ON organization_members(user_id, is_active)",
            "CREATE INDEX IF NOT EXISTS idx_org_members_org_active ON organization_members(organization_id, is_active)",
            "CREATE INDEX IF NOT EXISTS idx_org_models_org_active ON organization_models(organization_id, is_active)",
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_org_models_org_model ON organization_models(organization_id, model_id)"
        ]
        
        for idx in indexes:
            cursor.execute(idx)
        
        print("✅ Created performance indexes")
        
        # Commit transaction
        cursor.execute("COMMIT")
        print("✅ Migration completed successfully!")
        
        # Verify migration
        cursor.execute("SELECT COUNT(*) FROM organization_members WHERE organization_id = ?", (org_id,))
        member_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM organization_models WHERE organization_id = ?", (org_id,))
        model_count = cursor.fetchone()[0]
        
        print(f"\n📊 Migration Summary:")
        print(f"   Organization: {org_name}")
        print(f"   Members: {member_count}")
        print(f"   Models: {model_count}")
        
    except Exception as e:
        cursor.execute("ROLLBACK")
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 4:
        print("Usage: python migrate_to_organizations.py <db_path> <org_id> <org_name>")
        sys.exit(1)
    
    db_path = sys.argv[1]
    org_id = sys.argv[2]
    org_name = sys.argv[3]
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        sys.exit(1)
    
    migrate_database(db_path, org_id, org_name)
```

### Step 3: Run Migration

```bash
# Copy migration script to container
docker cp migrate_to_organizations.py mai-backend-${CLIENT_NAME}:/tmp/

# Run migration
docker exec mai-backend-${CLIENT_NAME} python3 /tmp/migrate_to_organizations.py \
  /app/backend/data/webui.db \
  "mai_client_${CLIENT_NAME}" \
  "${CLIENT_FULL_NAME}"

# Verify migration
docker exec mai-backend-${CLIENT_NAME} sqlite3 /app/backend/data/webui.db \
  "SELECT 'Users:', COUNT(*) FROM organization_members WHERE organization_id = 'mai_client_${CLIENT_NAME}'
   UNION ALL
   SELECT 'Models:', COUNT(*) FROM organization_models WHERE organization_id = 'mai_client_${CLIENT_NAME}';"
```

### Step 4: Update Configuration

```bash
# Update .env with organization settings
echo "OPENROUTER_EXTERNAL_USER=mai_client_${CLIENT_NAME}" >> .env
echo "ORGANIZATION_NAME=\"${CLIENT_FULL_NAME}\"" >> .env

# Restart services
docker-compose restart
```

## Organization Management

### Adding Users to Organization

```sql
-- Add single user
INSERT INTO organization_members (id, organization_id, user_id, role, is_active, joined_at)
VALUES (
    'om_' || <user_id> || '_' || <org_id>,
    '<org_id>',
    '<user_id>',
    'member',
    1,
    strftime('%s', 'now')
);

-- Add all active users
INSERT OR IGNORE INTO organization_members (id, organization_id, user_id, role, is_active, joined_at)
SELECT 
    'om_' || user.id || '_' || '<org_id>',
    '<org_id>',
    user.id,
    'member',
    1,
    strftime('%s', 'now')
FROM user
WHERE user.role NOT IN ('pending', 'banned');
```

### Managing Model Access

```sql
-- Enable model for organization
INSERT OR REPLACE INTO organization_models (id, organization_id, model_id, is_active, created_at, updated_at)
VALUES (
    'orgmod_' || '<org_id>' || '_' || '<model_id>',
    '<org_id>',
    '<model_id>',
    1,
    strftime('%s', 'now'),
    strftime('%s', 'now')
);

-- Disable model for organization
UPDATE organization_models 
SET is_active = 0, updated_at = strftime('%s', 'now')
WHERE organization_id = '<org_id>' AND model_id = '<model_id>';

-- List organization's active models
SELECT m.id, m.name, om.is_active
FROM organization_models om
JOIN model m ON om.model_id = m.id
WHERE om.organization_id = '<org_id>'
ORDER BY m.name;
```

### User Access Report

```sql
-- User model access report
CREATE VIEW IF NOT EXISTS user_model_access_report AS
SELECT 
    u.email as user_email,
    u.name as user_name,
    om.organization_id,
    COUNT(DISTINCT orgmod.model_id) as accessible_models,
    GROUP_CONCAT(DISTINCT m.name) as model_names
FROM user u
JOIN organization_members om ON u.id = om.user_id
JOIN organization_models orgmod ON om.organization_id = orgmod.organization_id
JOIN model m ON orgmod.model_id = m.id
WHERE om.is_active = 1 AND orgmod.is_active = 1
GROUP BY u.id, om.organization_id;
```

## Troubleshooting

### Common Issues

#### 1. Users Can't See Models

```bash
# Check user's organization membership
docker exec mai-backend-${CLIENT_NAME} sqlite3 /app/backend/data/webui.db \
  "SELECT * FROM organization_members WHERE user_id = '<user_id>';"

# Check organization's models
docker exec mai-backend-${CLIENT_NAME} sqlite3 /app/backend/data/webui.db \
  "SELECT m.id, m.name, om.is_active 
   FROM organization_models om 
   JOIN model m ON om.model_id = m.id 
   WHERE om.organization_id = '<org_id>';"

# Check if bypass is enabled (should be false)
docker exec mai-backend-${CLIENT_NAME} env | grep BYPASS_MODEL_ACCESS_CONTROL
```

#### 2. Performance Issues

```bash
# Check index usage
docker exec mai-backend-${CLIENT_NAME} sqlite3 /app/backend/data/webui.db \
  "EXPLAIN QUERY PLAN 
   SELECT DISTINCT model_id 
   FROM organization_models 
   WHERE organization_id = '<org_id>' AND is_active = 1;"

# Analyze database
docker exec mai-backend-${CLIENT_NAME} sqlite3 /app/backend/data/webui.db "ANALYZE;"

# Check database integrity
docker exec mai-backend-${CLIENT_NAME} sqlite3 /app/backend/data/webui.db "PRAGMA integrity_check;"
```

#### 3. Database Locked Errors

```bash
# Check for long-running transactions
docker exec mai-backend-${CLIENT_NAME} sqlite3 /app/backend/data/webui.db \
  "PRAGMA busy_timeout = 5000;"

# Enable WAL mode for better concurrency
docker exec mai-backend-${CLIENT_NAME} sqlite3 /app/backend/data/webui.db \
  "PRAGMA journal_mode=WAL;"
```

### Debug Mode

Enable debug logging:
```bash
# Add to .env
LOG_LEVEL=DEBUG
SRC_LOG_LEVELS_MODELS=DEBUG

# Restart and check logs
docker-compose restart
docker logs -f mai-backend-${CLIENT_NAME} 2>&1 | grep -E "(organization|model|access)"
```

## Performance Monitoring

### Query Performance Metrics

Create monitoring script `monitor_performance.py`:
```python
#!/usr/bin/env python3
"""Monitor organization model access performance"""

import sqlite3
import time
import statistics

def monitor_query_performance(db_path, org_id, iterations=100):
    """Test query performance"""
    
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    
    # Test queries
    queries = {
        "user_orgs": """
            SELECT DISTINCT organization_id 
            FROM organization_members 
            WHERE user_id = ? AND is_active = 1
        """,
        "org_models": """
            SELECT DISTINCT model_id 
            FROM organization_models 
            WHERE organization_id = ? AND is_active = 1
        """,
        "user_models_view": """
            SELECT DISTINCT model_id 
            FROM user_available_models 
            WHERE user_id = ?
        """
    }
    
    results = {}
    
    for query_name, query in queries.items():
        times = []
        
        for _ in range(iterations):
            start = time.perf_counter()
            if query_name == "org_models":
                conn.execute(query, (org_id,)).fetchall()
            else:
                conn.execute(query, ("test_user_id",)).fetchall()
            end = time.perf_counter()
            
            times.append((end - start) * 1000)  # Convert to ms
        
        results[query_name] = {
            "min": min(times),
            "max": max(times),
            "avg": statistics.mean(times),
            "median": statistics.median(times),
            "p95": statistics.quantiles(times, n=20)[18],  # 95th percentile
            "p99": statistics.quantiles(times, n=100)[98]  # 99th percentile
        }
    
    # Print results
    print(f"Performance Test Results ({iterations} iterations)")
    print("=" * 60)
    
    for query_name, metrics in results.items():
        print(f"\n{query_name}:")
        print(f"  Min:    {metrics['min']:.3f} ms")
        print(f"  Median: {metrics['median']:.3f} ms")
        print(f"  Avg:    {metrics['avg']:.3f} ms")
        print(f"  P95:    {metrics['p95']:.3f} ms")
        print(f"  P99:    {metrics['p99']:.3f} ms")
        print(f"  Max:    {metrics['max']:.3f} ms")
    
    conn.close()
    
    # Performance thresholds
    if all(metrics['p95'] < 1.0 for metrics in results.values()):
        print("\n✅ All queries performing well (P95 < 1ms)")
    else:
        print("\n⚠️  Some queries need optimization")

if __name__ == "__main__":
    monitor_query_performance("/app/backend/data/webui.db", "mai_client_example")
```

### Monitoring Dashboard

Add to your monitoring stack:
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'mai-backend'
    static_configs:
      - targets: ['mai-backend:8080']
    metrics_path: '/metrics'
```

## Security Considerations

### 1. Database Security

```bash
# Secure database file
chmod 600 data/webui.db

# Regular backups
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backups/mai"
DB_FILE="/app/backend/data/webui.db"
BACKUP_FILE="${BACKUP_DIR}/webui_$(date +%Y%m%d_%H%M%S).db"

mkdir -p ${BACKUP_DIR}
sqlite3 ${DB_FILE} ".backup '${BACKUP_FILE}'"
gzip ${BACKUP_FILE}

# Keep only last 30 days
find ${BACKUP_DIR} -name "*.gz" -mtime +30 -delete
EOF

chmod +x backup.sh
```

### 2. Network Security

```nginx
# nginx.conf for reverse proxy
server {
    listen 443 ssl http2;
    server_name mai.company.com;
    
    ssl_certificate /etc/ssl/certs/mai.crt;
    ssl_certificate_key /etc/ssl/private/mai.key;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /api {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Rate limiting
        limit_req zone=api burst=20 nodelay;
    }
}
```

### 3. Access Control

```bash
# Regular audit of user access
cat > audit_access.sh << 'EOF'
#!/bin/bash
echo "User Access Audit Report - $(date)"
echo "================================"

sqlite3 /app/backend/data/webui.db << SQL
.mode column
.headers on

-- Active users by organization
SELECT 
    om.organization_id,
    COUNT(DISTINCT om.user_id) as user_count,
    COUNT(DISTINCT orgmod.model_id) as model_count
FROM organization_members om
LEFT JOIN organization_models orgmod ON om.organization_id = orgmod.organization_id
WHERE om.is_active = 1
GROUP BY om.organization_id;

-- Users with admin role
SELECT 
    u.email,
    u.name,
    om.organization_id,
    u.last_active_at
FROM user u
JOIN organization_members om ON u.id = om.user_id
WHERE u.role = 'admin'
ORDER BY u.last_active_at DESC;
SQL
EOF

chmod +x audit_access.sh
```

## Maintenance

### Daily Tasks
- Monitor logs for errors
- Check backup completion
- Review performance metrics

### Weekly Tasks
- Run access audit
- Review user registrations
- Check disk usage

### Monthly Tasks
- Database optimization: `VACUUM`
- Review and rotate logs
- Update security patches

---

**Last Updated**: 2025-01-29
**Version**: 1.0
**Maintained By**: mAI DevOps Team