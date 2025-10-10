# SQLite + Supabase Sync System (Phase 1)

## Overview

This directory contains the **Phase 1** implementation of a high-availability database synchronization system for multi-tenant Open WebUI deployments. The system maintains SQLite as the primary database for performance while using Supabase (PostgreSQL) as the authoritative state source with automatic conflict resolution and failover capabilities.

### Key Features (Phase 1)

- **Dual sync containers** (primary/secondary) with automatic leader election
- **Supabase as authoritative state** with local caching for resilience
- **One-way sync** SQLite → Supabase (bidirectional in Phase 2)
- **Restricted database roles** - No service role keys in containers
- **Automated conflict resolution** with configurable strategies
- **Comprehensive monitoring** via Prometheus metrics
- **High availability** with automatic failover

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Host Server                               │
│                                                               │
│  ┌──────────────────┐      ┌──────────────────┐             │
│  │ Sync Primary     │      │ Sync Secondary   │             │
│  │ (Port 9443)      │◄────►│ (Port 9444)      │             │
│  │ - Leader Election│      │ - Standby        │             │
│  │ - State Manager  │      │ - Health Monitor │             │
│  │ - REST API       │      │ - Failover Ready │             │
│  └────────┬─────────┘      └────────┬─────────┘             │
│           │                         │                        │
│           └─────────┬───────────────┘                        │
│                     │                                        │
│  ┌──────────────────▼──────────────────────────────┐        │
│  │ Client Containers (openwebui-*)                 │        │
│  │ - SQLite databases (local, fast)                │        │
│  │ - Synced every 1-60 minutes                     │        │
│  └──────────────────┬──────────────────────────────┘        │
└────────────────────│───────────────────────────────────────┘
                     │
                     │ One-way sync
                     ▼
         ┌───────────────────────────┐
         │   Supabase PostgreSQL     │
         │ (Authoritative State)     │
         │                           │
         │ - sync_metadata schema    │
         │ - client schemas          │
         │ - Conflict logs           │
         │ - Leader election table   │
         └───────────────────────────┘
```

## Directory Structure

```
mt/SYNC/
├── README.md                    # This file
├── config/                      # Configuration files
│   ├── conflict-resolution.json # Default conflict strategies
│   └── sync-intervals.json      # Sync timing configuration
├── docker/                      # Docker configuration
│   ├── Dockerfile               # Sync container image
│   ├── docker-compose.sync-ha.yml # HA deployment
│   └── entrypoint.sh            # Container startup script
├── scripts/                     # Bash scripts
│   ├── deploy-sync-cluster.sh   # Initial deployment
│   ├── sync-client-to-supabase.sh # Sync engine
│   └── test-failover.sh         # HA testing
├── python/                      # Python modules
│   ├── main.py                  # FastAPI application
│   ├── state_manager.py         # State management with caching
│   ├── leader_election.py       # HA leader election
│   ├── conflict_resolver.py     # Conflict resolution engine
│   └── metrics.py               # Prometheus metrics
└── logs/                        # Runtime logs (gitignored)
```

## Core Components

### 1. Sync Container Cluster

Two containers per host provide high availability:

- **Primary** (`openwebui-sync-primary`):
  - Runs leader election
  - Exposes REST API on port 9443
  - Executes sync jobs when leader
  - Manages state cache

- **Secondary** (`openwebui-sync-secondary`):
  - Participates in leader election
  - Health check endpoint on port 9444
  - Automatically takes over if primary fails
  - Maintains synchronized state cache

### 2. State Management System

**Supabase is the authoritative source** for all deployment state:

- **Cache-Aside Pattern**:
  - Local cache with 5-minute TTL
  - Cache miss triggers Supabase fetch
  - Writes go to Supabase first, then invalidate cache

- **Cluster Synchronization**:
  - State changes notify other containers via Supabase events
  - Cache invalidation across cluster
  - Reconciliation protocol for cache misses

### 3. Leader Election

Uses PostgreSQL atomic operations for distributed consensus:

```sql
INSERT INTO sync_metadata.leader_election
    (cluster_name, leader_id, acquired_at, expires_at)
VALUES
    ('prod-host-1', 'container-id', NOW(), NOW() + INTERVAL '60 seconds')
ON CONFLICT (cluster_name) DO UPDATE
SET
    leader_id = EXCLUDED.leader_id,
    acquired_at = NOW(),
    expires_at = NOW() + INTERVAL '60 seconds'
WHERE
    leader_election.expires_at < NOW()
    OR leader_election.leader_id = EXCLUDED.leader_id;
```

- **Lease Duration**: 60 seconds
- **Heartbeat Interval**: 30 seconds
- **Failover Time**: ~35 seconds (lease expiration + heartbeat)

### 4. Conflict Resolution

Automated resolution with configurable strategies per table:

**Strategies**:
- `newest_wins`: Use row with most recent `updated_at`
- `source_wins`: Always prefer SQLite version
- `target_wins`: Always prefer Supabase version
- `merge`: Merge changes using field-level rules
- `manual`: Flag for human review

**Configuration Example** (`config/conflict-resolution.json`):
```json
{
  "default_strategy": "newest_wins",
  "table_strategies": {
    "user": {
      "strategy": "newest_wins",
      "compare_field": "updated_at"
    },
    "chat": {
      "strategy": "merge",
      "merge_rules": {
        "messages": "append",
        "metadata": "newest_wins"
      }
    },
    "config": {
      "strategy": "manual",
      "notify": true
    }
  }
}
```

### 5. Security Architecture

**Restricted Database Role**:
```sql
CREATE ROLE sync_service WITH LOGIN ENCRYPTED PASSWORD '...';

-- Grant minimal permissions
GRANT USAGE ON SCHEMA sync_metadata TO sync_service;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA sync_metadata TO sync_service;
-- NO DELETE, NO DROP, NO CREATE

-- Per-client schema access
GRANT USAGE ON SCHEMA client_acme TO sync_service;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA client_acme TO sync_service;
```

**Row Level Security**:
```sql
ALTER TABLE sync_metadata.hosts ENABLE ROW LEVEL SECURITY;

CREATE POLICY sync_host_isolation ON sync_metadata.hosts
    FOR ALL
    TO sync_service
    USING (host_id = current_setting('app.current_host_id'));
```

**Credentials**:
- Stored in Docker secrets (not environment variables)
- Encrypted at rest
- Never logged or exposed via API

## Quick Start

### Prerequisites

1. **Supabase Project** with:
   - Project created and provisioned
   - `pgvector` extension enabled (for RAG features)
   - Admin access to create roles

2. **Docker Environment**:
   - Docker 20.10+
   - Docker Compose v2+
   - Access to `/var/run/docker.sock`

### Initial Deployment

```bash
# 1. Navigate to sync directory
cd /Users/justinmartin/github/open-webui/mt/SYNC

# 2. Configure Supabase credentials
# Edit docker/.env with your Supabase details

# 3. Deploy HA sync cluster
./scripts/deploy-sync-cluster.sh

# 4. Verify cluster health
curl http://localhost:9443/health | jq .
curl http://localhost:9444/health | jq .

# 5. Check leader election
curl http://localhost:9443/health | jq '.is_leader'
# Should return true for primary (or secondary if primary down)
```

### Integrate with Client Manager

The sync system integrates with `mt/client-manager.sh`:

```bash
./client-manager.sh
# Select "3) Manage Existing Deployment"
# Choose your client
# New option: "9) Configure Database Sync"
```

## API Reference

### Health Check
```bash
GET http://localhost:9443/health

Response:
{
  "status": "healthy",
  "is_leader": true,
  "leader_id": "openwebui-sync-primary",
  "cluster_name": "prod-host-1",
  "uptime_seconds": 3600,
  "last_sync": "2025-01-08T10:30:00Z"
}
```

### Get State
```bash
GET http://localhost:9443/api/v1/state?key=deployment.acme-corp

Response:
{
  "key": "deployment.acme-corp",
  "value": {
    "status": "active",
    "sync_enabled": true,
    "sync_interval": 300,
    "last_sync": "2025-01-08T10:25:00Z"
  },
  "cached": false
}
```

### Update State
```bash
PUT http://localhost:9443/api/v1/state
Content-Type: application/json

{
  "key": "deployment.acme-corp",
  "value": {
    "status": "active",
    "sync_enabled": true,
    "sync_interval": 600
  }
}

Response:
{
  "success": true,
  "updated_at": "2025-01-08T10:35:00Z"
}
```

### Trigger Manual Sync
```bash
POST http://localhost:9443/api/v1/sync/trigger
Content-Type: application/json

{
  "client_name": "acme-corp"
}

Response:
{
  "success": true,
  "sync_id": "sync_20250108_103500",
  "status": "running"
}
```

### Prometheus Metrics
```bash
GET http://localhost:9443/metrics

Response:
# HELP sync_operations_total Total number of sync operations
# TYPE sync_operations_total counter
sync_operations_total{client="acme-corp",status="success"} 145
sync_operations_total{client="acme-corp",status="failed"} 2

# HELP sync_duration_seconds Sync operation duration
# TYPE sync_duration_seconds histogram
sync_duration_seconds_bucket{client="acme-corp",le="1"} 10
sync_duration_seconds_bucket{client="acme-corp",le="5"} 120
...
```

## Monitoring

### Prometheus Configuration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'sync-cluster'
    static_configs:
      - targets:
        - 'localhost:9443'
        - 'localhost:9444'
    metrics_path: '/metrics'
```

### Key Metrics to Monitor

1. **sync_operations_total{status="failed"}** - Alert if > 5 in 10 minutes
2. **is_leader** - Ensure exactly one container has is_leader=1
3. **sync_duration_seconds** - Alert if p95 > 60 seconds
4. **conflicts_detected_total** - Monitor for unusual spikes
5. **state_sync_lag_seconds** - Alert if > 600 (10 minutes)

## Troubleshooting

### No Leader Elected

**Symptom**: Both containers show `is_leader: false`

**Solution**:
```bash
# Check leader_election table
docker exec openwebui-sync-primary python3 -c "
import psycopg2
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute('SELECT * FROM sync_metadata.leader_election')
print(cur.fetchall())
"

# Manually clear stuck lease
# (Only do this if both containers are healthy but neither is leader)
psql $SUPABASE_URL -c "DELETE FROM sync_metadata.leader_election WHERE cluster_name='prod-host-1'"
```

### Sync Failing with Permission Error

**Symptom**: `permission denied for table client_acme.user`

**Solution**:
```bash
# Grant permissions to sync_service role
psql $SUPABASE_ADMIN_URL <<EOF
GRANT USAGE ON SCHEMA client_acme TO sync_service;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA client_acme TO sync_service;
EOF
```

### High Conflict Rate

**Symptom**: `conflicts_detected_total` metric increasing rapidly

**Solution**:
1. Check conflict log:
   ```sql
   SELECT * FROM sync_metadata.conflict_log
   WHERE client_id='acme-corp'
   ORDER BY detected_at DESC LIMIT 20;
   ```

2. Adjust sync interval (reduce frequency):
   ```bash
   # Via API
   curl -X PUT http://localhost:9443/api/v1/state \
     -H "Content-Type: application/json" \
     -d '{"key":"deployment.acme-corp","value":{"sync_interval":900}}'
   ```

3. Review conflict resolution strategy for affected tables

### Failover Not Working

**Symptom**: Primary container down but secondary not taking over

**Checklist**:
- [ ] Verify secondary container is running: `docker ps | grep sync-secondary`
- [ ] Check secondary logs: `docker logs openwebui-sync-secondary`
- [ ] Verify DATABASE_URL environment variable is set correctly
- [ ] Test Supabase connectivity from secondary
- [ ] Check for expired lease: Should expire in 60 seconds

## Phase 2 Preview

**Upcoming Features** (not in Phase 1):
- Bidirectional sync (Supabase → SQLite restore)
- Cross-host migration orchestration
- DNS automation via provider abstraction
- SSL certificate management
- Blue-green deployment support
- mTLS authentication between components (Phase 3)

## Testing

### Run HA Failover Test
```bash
./scripts/test-failover.sh
```

### Run Security Validation
```bash
cd tests/
./test-security.sh
```

### Run Full Test Suite
```bash
cd tests/
./run-all-tests.sh
```

## Support

For issues or questions:
1. Check logs: `docker logs openwebui-sync-primary`
2. Review Supabase dashboard for database errors
3. Consult troubleshooting section above
4. File issue on GitHub with logs and config

## License

Part of the Open WebUI multi-tenant management system.
