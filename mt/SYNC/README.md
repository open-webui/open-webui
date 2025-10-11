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

3. **IPv6 Connectivity** (required for Supabase direct database connection):
   - **Digital Ocean**: Enable IPv6 in Droplet settings (automatically configured by deployment script)
   - **AWS/Other**: Manual IPv6 configuration may be required
   - **Fallback**: Script will use IPv4 pooler connection if IPv6 unavailable (see IPv6 section below)

### Initial Deployment

```bash
# 1. Navigate to sync directory
cd /Users/justinmartin/github/open-webui/mt/SYNC

# 2. Configure Supabase credentials
# Edit docker/.env with your Supabase details

# 3. Deploy HA sync cluster
./scripts/deploy-sync-cluster.sh

# The script will automatically:
# - Detect cloud provider (Digital Ocean, AWS, etc.)
# - Configure IPv6 if available
# - Set up Docker IPv6 networking
# - Choose optimal database connection method
# - Deploy primary and secondary sync containers

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

## IPv6 Network Configuration

### Why IPv6 is Required

Supabase's **direct database connection** (`db.PROJECT_REF.supabase.co:5432`) is **IPv6-only**. This provides:
- **Lower latency** compared to pooler connection
- **Full PostgreSQL feature support** (no pooler limitations)
- **Better performance** for sync operations
- **Direct access** to database without intermediate proxy

The alternative **pooler connection** (`pooler.supabase.com:5432`) uses IPv4 but has limitations:
- Not all PostgreSQL features supported
- Higher latency through connection pooling proxy
- May have transaction mode restrictions

### Automatic IPv6 Configuration

The deployment script (`deploy-sync-cluster.sh`) **automatically configures IPv6** on supported cloud providers:

#### Digital Ocean (Automatic)

1. **Enable IPv6 in Droplet Settings** (one-time manual step):
   - Navigate to: Digital Ocean Control Panel → Droplets → Your Droplet → Networking
   - Click "Enable IPv6"
   - Wait ~30 seconds for provisioning

2. **Deployment Script Handles Everything Else**:
   - Detects Digital Ocean via metadata service
   - Queries IPv6 address, CIDR, and gateway from metadata
   - Configures network interface automatically
   - Sets up IPv6 routing
   - Verifies connectivity to Supabase
   - Configures Docker daemon for IPv6
   - Uses direct database connection

#### AWS (Manual Configuration May Be Required)

The script detects AWS but does not auto-configure IPv6. Manual steps:

```bash
# 1. Assign IPv6 CIDR block to VPC (AWS Console)
# 2. Assign IPv6 address to EC2 instance
# 3. Configure security group for IPv6
# 4. Add IPv6 address to network interface:

sudo ip -6 addr add YOUR_IPV6_ADDRESS/128 dev eth0
sudo ip -6 route add default via YOUR_IPV6_GATEWAY dev eth0

# 5. Test connectivity
ping6 -c 3 db.YOUR_PROJECT_REF.supabase.co

# 6. Run deployment script
./scripts/deploy-sync-cluster.sh
```

#### Other Cloud Providers / Bare Metal

The script will use **IPv4 pooler connection** as fallback if IPv6 is not detected.

To manually enable IPv6:

1. **Configure IPv6 address on server**:
   ```bash
   sudo ip -6 addr add YOUR_IPV6_ADDRESS/64 dev eth0
   sudo ip -6 route add default via YOUR_GATEWAY dev eth0
   ```

2. **Test connectivity**:
   ```bash
   ping6 -c 3 db.YOUR_PROJECT_REF.supabase.co
   nc -6 -zv db.YOUR_PROJECT_REF.supabase.co 5432
   ```

3. **Run deployment script** (will detect IPv6 and use direct connection)

### Docker IPv6 Configuration

The deployment script automatically configures Docker for IPv6:

1. **Backs up existing `/etc/docker/daemon.json`**
2. **Creates new configuration**:
   ```json
   {
     "ipv6": true,
     "fixed-cidr-v6": "fd00::/80"
   }
   ```
3. **Restarts Docker daemon**
4. **Adds IPv6 subnets to docker-compose network**:
   ```yaml
   networks:
     sync-network:
       driver: bridge
       enable_ipv6: true
       ipam:
         config:
           - subnet: 172.30.0.0/16    # IPv4
           - subnet: fd01::/64         # IPv6
   ```

### Connection Method Selection

The deployment script intelligently chooses the connection method:

```bash
# IPv6 Available → Use Direct Connection
DATABASE_URL="postgresql://sync_service:PASSWORD@db.PROJECT_REF.supabase.co:5432/postgres"

# IPv6 Not Available → Use Pooler (IPv4)
DATABASE_URL="postgresql://sync_service:PASSWORD@REGION.pooler.supabase.com:5432/postgres"
```

**Note**: The `sync_service` role may have restricted permissions on the pooler connection. Direct connection is recommended.

### Verifying IPv6 Configuration

After deployment, verify IPv6 is working:

```bash
# 1. Check IPv6 address is configured
ip -6 addr show | grep "scope global"

# 2. Test IPv6 route
ip -6 route show

# 3. Test connectivity to Supabase
ping6 -c 3 db.YOUR_PROJECT_REF.supabase.co

# 4. Test database connection
nc -6 -zv db.YOUR_PROJECT_REF.supabase.co 5432

# 5. Check container is using IPv6 connection
docker exec openwebui-sync-primary env | grep DATABASE_URL
# Should show: db.PROJECT_REF.supabase.co (not pooler.supabase.com)
```

### Troubleshooting IPv6

#### IPv6 Not Auto-Configured

**Symptom**: Deployment script reports "IPv6 not currently configured"

**Solutions**:
1. **Digital Ocean**: Ensure IPv6 is enabled in Droplet settings
2. **Check cloud provider support**: Not all providers offer IPv6
3. **Verify metadata service**: `curl -sf http://169.254.169.254/metadata/v1/interfaces/public/0/ipv6/address`
4. **Manual configuration**: See "Other Cloud Providers" section above

#### Connection Test Fails

**Symptom**: `nc -6 -zv db.PROJECT_REF.supabase.co 5432` fails

**Solutions**:
1. **Check IPv6 routing**: `ip -6 route show`
2. **Verify default route**: Should have route via gateway
3. **Test basic IPv6**: `ping6 google.com`
4. **Check firewall rules**: Ensure IPv6 traffic is allowed
5. **Restart networking**: `sudo systemctl restart networking`

#### Docker Containers Can't Connect

**Symptom**: Containers show "Network is unreachable" errors

**Solutions**:
1. **Verify Docker IPv6 config**: `cat /etc/docker/daemon.json`
2. **Check Docker service**: `sudo systemctl status docker`
3. **Inspect network**: `docker network inspect SYNC_sync-network | grep IPv6`
4. **Recreate containers**: `docker compose down && docker compose up -d`

#### Pooler Connection Instead of Direct

**Symptom**: DATABASE_URL contains `pooler.supabase.com` instead of `db.PROJECT_REF.supabase.co`

**Solutions**:
1. **Check IPv6 availability**: Script chose pooler because IPv6 test failed
2. **Verify connectivity manually**: Test with `nc -6 -zv db.PROJECT_REF.supabase.co 5432`
3. **Re-run deployment**: After fixing IPv6, re-run `./scripts/deploy-sync-cluster.sh`

## Cluster Lifecycle Management

### Deregistering a Cluster Before Host Destruction

**⚠️ IMPORTANT**: Before destroying a Digital Ocean droplet or decommissioning a host server, you must properly deregister the sync cluster from Supabase.

**Why Deregistration is Required**:
- Prevents orphaned metadata records in Supabase
- Releases leadership gracefully to allow other clusters to take over
- Cleans up client deployment records
- Removes stale cache invalidation events
- Avoids "ghost" hosts showing as offline in monitoring

**⚠️ CRITICAL SAFETY CHECKS**:

The deregistration script includes **automatic safety checks** that will:
1. ✅ **Block deregistration** if ANY Open WebUI clients have `sync_enabled = true`
2. ✅ **List all sync-enabled clients** with their sync status
3. ✅ **Provide clear remediation options** before allowing deregistration
4. ✅ **Warn about non-sync clients** that will be deleted

**Protection Against Data Loss**:
- **Cannot deregister** if active sync clients exist
- **Must explicitly handle** each sync-enabled client before proceeding:
  - **Option 1**: Disable sync for the client
  - **Option 2**: Migrate client to another host/cluster
  - **Option 3**: Decommission the client deployment
- **Will warn** about non-sync clients that will be deleted

**Deregistration Process**:

```bash
# SSH to the host that will be destroyed
ssh user@your-host

# Navigate to sync directory
cd /path/to/mt/SYNC

# Run deregistration script
./scripts/deregister-cluster.sh

# Follow prompts to:
# 1. Review cluster metadata that will be deleted
# 2. Confirm deletion
# 3. Optionally remove local Docker containers/volumes
```

**What the Script Does**:
1. ✅ Stops sync containers gracefully (releases leadership)
2. ✅ Displays cluster metadata (hosts, leader status, deployments)
3. ✅ Confirms deletion with user
4. ✅ Deletes host records from Supabase
5. ✅ CASCADE deletes related records:
   - Leader election entries
   - Client deployments
   - Cache events
   - Sync job history
6. ✅ Verifies complete removal
7. ✅ Optionally cleans up local Docker resources

**After Deregistration**:
- Host can be safely destroyed
- No orphaned records remain in Supabase
- Other clusters unaffected
- Ready for fresh deployment on new host

**Re-deploying on New Host**:
```bash
# After creating new droplet
./scripts/deploy-sync-cluster.sh
# Will create fresh cluster registration
```

### Manual Cleanup (If Host Was Destroyed Without Deregistration)

If you destroyed a host **without** running the deregistration script, clean up manually:

```bash
# Connect to Supabase with admin credentials
psql "postgresql://postgres:PASSWORD@db.PROJECT_REF.supabase.co:5432/postgres"

# Check for orphaned hosts
SELECT hostname, cluster_name, status, last_heartbeat
FROM sync_metadata.hosts
WHERE last_heartbeat < NOW() - INTERVAL '5 minutes';

# Delete specific cluster (replace 'old-cluster-name')
DELETE FROM sync_metadata.hosts WHERE cluster_name = 'old-cluster-name';

# Verify deletion (should show 0 rows)
SELECT COUNT(*) FROM sync_metadata.hosts WHERE cluster_name = 'old-cluster-name';
SELECT COUNT(*) FROM sync_metadata.leader_election WHERE cluster_name = 'old-cluster-name';
```

**Automated Cleanup (Future Enhancement)**:
Consider adding a scheduled job to automatically mark hosts as `offline` if:
- `last_heartbeat` > 5 minutes old
- Status still shows as `active`

This could be implemented as a PostgreSQL function triggered by `pg_cron` extension.

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
