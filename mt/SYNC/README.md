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

## 📖 Documentation

**IMPORTANT**: Before modifying ANY code in this directory, read:

- **[TECHNICAL_REFERENCE.md](TECHNICAL_REFERENCE.md)** - **REQUIRED READING** for developers
  - Single source of truth for implementation standards
  - Mandatory naming conventions and file paths
  - Pre-commit checklist must be followed
  - Prevents inconsistencies in variable names, paths, container names

**Other Documentation**:
- **[README.md](README.md)** - This file (architecture overview and user guide)
- **[IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)** - Project progress tracking
- **[CLUSTER_LIFECYCLE_FAQ.md](CLUSTER_LIFECYCLE_FAQ.md)** - Operational procedures and Q&A

## Directory Structure

```
mt/SYNC/
├── README.md                    # This file (user-facing docs)
├── TECHNICAL_REFERENCE.md       # ⚠️ REQUIRED READING for developers
├── IMPLEMENTATION_STATUS.md     # Project progress
├── CLUSTER_LIFECYCLE_FAQ.md     # Operations Q&A
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

- **Node A** (`openwebui-sync-node-a`):
  - Participates in leader election
  - Exposes REST API on port 9443
  - Executes sync jobs when elected leader
  - Manages state cache

- **Node B** (`openwebui-sync-node-b`):
  - Participates in leader election
  - Exposes REST API on port 9444
  - Automatically takes over leadership if Node A fails
  - Maintains synchronized state cache

**Important**: Container names (nodeA/nodeB) are **just identifiers** and do NOT determine leadership. Leadership is determined dynamically via PostgreSQL atomic operations. See [Understanding Leader Election](#understanding-leader-election) below.

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

### Client-Manager Integration

The sync system is fully integrated with `mt/client-manager.sh` as of version 2.0 (2025-10-14).

#### Managing Sync Cluster

Access comprehensive cluster management through the main menu:

```bash
cd mt
./client-manager.sh
# Select: 4) Manage Sync Cluster
# Available options:
#   1) Deploy Sync Cluster       - Full HA deployment (2 nodes + Supabase registration)
#   2) View Cluster Health        - Combined status of both nodes + leader info
#   3) Manage Sync Node A         - Individual node A operations
#   4) Manage Sync Node B         - Individual node B operations
#   5) Deregister Cluster         - Clean removal before host destruction
#   6) Help (Documentation)       - View README, TECHNICAL_REFERENCE, FAQ
#   7) Return to Main Menu
```

**Cluster Operations**:
- **Deploy**: Handles full cluster setup including IPv6, Docker config, node deployment, and Supabase registration
- **View Health**: Queries both nodes (9443, 9444) for health status and displays current leader
- **Individual Node Management**: Direct access to node-specific operations (logs, restart, etc.)
- **Deregister**: Safe cluster removal with sync-enabled client checks and cascade cleanup
- **Help**: Quick access to all documentation files via less/pager

**Workflow Examples**:

**Initial Cluster Deployment**:
```bash
# 1. Main menu → 4) Manage Sync Cluster
# 2. Select: 1) Deploy Sync Cluster
# 3. Review requirements and confirm
# 4. Script handles IPv6, Docker, containers, and Supabase
# 5. Returns to menu with deployment status
```

**Monitoring Cluster Health**:
```bash
# 1. Main menu → 4) Manage Sync Cluster
# 2. Select: 2) View Cluster Health
# 3. See: Node A status, Node B status, leader election info
# 4. Press Enter to return
```

**Before Host Destruction**:
```bash
# 1. Main menu → 4) Manage Sync Cluster
# 2. Select: 5) Deregister Cluster
# 3. Review what will be deleted
# 4. Type 'DEREGISTER' to confirm
# 5. Script cleans up Supabase metadata
# 6. Safe to destroy host/droplet
```

#### Managing Sync Nodes

Access sync node management through the deployment menu:

```bash
cd mt
./client-manager.sh
# Select: 3) Manage Existing Deployment
# Select: sync-node-a or sync-node-b [SYNC NODE]
# Available options:
#   1) View Cluster Status     - Full cluster health and leadership
#   2) View Health Check       - Individual node health and API status
#   3) View Container Logs     - Last 50 lines of logs
#   4) View Live Logs          - Follow mode for real-time monitoring
#   5) Restart Sync Node       - Graceful restart with health check
#   6) Stop Sync Node          - Stop with leadership transfer warning
#   7) Update Sync Node        - Instructions for updating to latest version
#   8) Return to Deployment List
```

**Key Features**:
- Automatic port detection (9443 for node-a, 9444 for node-b)
- JSON response formatting with jq (if available)
- Leadership status displayed in health checks
- Warnings for operations that affect cluster availability

#### Managing Client Sync

Configure sync for individual Open WebUI clients:

```bash
cd mt
./client-manager.sh
# Select: 3) Manage Existing Deployment
# Select: your-client-name [CLIENT]
# Select: 8) Sync Management
# Available options:
#   1) Register Client for Sync        - Create schema and enable syncing
#   2) Start/Resume Sync                - Enable automatic syncing
#   3) Pause Sync                       - Temporarily stop syncing (keeps data)
#   4) Manual Sync (Full)               - One-time complete sync
#   5) Manual Sync (Incremental)        - One-time recent changes sync
#   6) View Sync Status                 - Check sync enabled, interval, last sync
#   7) View Recent Sync Jobs            - Last 10 sync operations with details
#   8) Deregister Client                - Remove from sync (optional: delete data)
#   9) Help                             - View SCRIPTS_REFERENCE.md
#   10) Return to Client Menu
```

**Sync Operations**:
- All manual syncs use `triggered_by=manual-console` for tracking
- Status checks query Supabase directly for real-time information
- Recent jobs show: timestamp, status, sync type, rows synced, duration
- Help option displays full scripts reference documentation

#### Integration Benefits

1. **Unified Management**: Single interface for both Open WebUI and sync operations
2. **Container Detection**: Automatically distinguishes sync nodes from client deployments
3. **Safety Confirmations**: All destructive operations require explicit confirmation
4. **Error Handling**: Clear error messages with remediation steps
5. **Consistent UX**: Familiar menu patterns matching existing client-manager interface

#### Workflow Examples

**New Client Setup with Sync**:
```bash
# 1. Create client (via client-manager)
# 2. Select: 3) Manage Existing Deployment → your-client
# 3. Select: 8) Sync Management → 1) Register Client for Sync
# 4. Sync automatically enabled and scheduled
```

**Troubleshooting Sync Issues**:
```bash
# 1. Select: 3) Manage Existing Deployment → your-client
# 2. Select: 8) Sync Management → 6) View Sync Status
# 3. Check sync_enabled, status, last_sync_at
# 4. Select: 7) View Recent Sync Jobs
# 5. Look for failed jobs or patterns
# 6. If needed: 3) Pause Sync → Fix issue → 2) Start/Resume Sync
```

**Checking Cluster Health**:
```bash
# 1. Select: 3) Manage Existing Deployment → sync-node-a
# 2. Select: 1) View Cluster Status
# 3. Check: leader status, node health, last heartbeat
# 4. Select: 2) View Health Check
# 5. Verify: is_leader, uptime, API responding
```

**Note**: Cluster deployment and deregistration are now fully integrated into client-manager (main menu → option 4 → Manage Sync Cluster). Individual node operations, sync client registration, and all other sync functionality are also accessible through the unified menu interface.

## API Reference

### Health Check
```bash
GET http://localhost:9443/health

Response:
{
  "status": "healthy",
  "is_leader": true,
  "leader_id": "openwebui-sync-node-a",
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
docker exec openwebui-sync-node-a env | grep DATABASE_URL
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

## Understanding Leader Election

### Container Names vs Leadership Roles

**Critical Concept**: Container names (`openwebui-sync-node-a`, `openwebui-sync-node-b`) are **fixed identifiers** that do NOT determine leadership. Leadership is determined **dynamically** through PostgreSQL atomic operations.

**What This Means**:
- ✅ Node A can be the leader OR a follower
- ✅ Node B can be the leader OR a follower
- ✅ Leadership changes automatically based on health and lease expiration
- ✅ Container names never change, but leadership roles do

### How Leadership Is Determined

**Source of Truth**: PostgreSQL `sync_metadata.leader_election` table

Every 30 seconds (heartbeat interval), both containers execute this atomic operation:

```sql
INSERT INTO sync_metadata.leader_election
    (cluster_name, leader_id, acquired_at, expires_at)
VALUES
    ('prod-host-1', 'openwebui-sync-node-a', NOW(), NOW() + INTERVAL '60 seconds')
ON CONFLICT (cluster_name) DO UPDATE
SET
    leader_id = EXCLUDED.leader_id,
    expires_at = NOW() + INTERVAL '60 seconds'
WHERE
    -- Only succeed if:
    leader_election.expires_at < NOW()          -- Previous leader's lease expired
    OR leader_election.leader_id = EXCLUDED.leader_id  -- I'm already the leader
RETURNING
    leader_id = 'openwebui-sync-node-a' as is_leader;
```

**PostgreSQL Guarantees**:
- Only ONE container succeeds per heartbeat cycle
- Split-brain scenarios are impossible (ACID guarantees)
- Leader holds a 60-second lease
- Lease must be renewed every 30 seconds

### Leadership States and Transitions

```
┌─────────────────────────────────────────────────────────────┐
│                    Initial Deployment                        │
│  Both containers start and participate in election           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       v
              ┌────────────────┐
              │ First heartbeat│
              │ (race condition)│
              └────────┬────────┘
                       │
         ┌─────────────┴─────────────┐
         v                           v
    ┌─────────┐                 ┌─────────┐
    │ Node A  │                 │ Node B  │
    │ LEADER  │                 │ FOLLOWER│
    └────┬────┘                 └────┬────┘
         │                           │
         │ Heartbeat every 30s       │ Heartbeat rejected
         │ Lease renewed             │ (already has leader)
         │                           │
         v                           v
    ┌─────────────────────────────────────┐
    │  Normal Operation (60+ seconds)      │
    │  Node A: leader_id in DB             │
    │  Node B: follower, monitoring        │
    └──────────────┬──────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
        v                     v
   Node A crashes        Node A healthy
        │                     │
        v                     v
   ┌─────────┐           ┌─────────┐
   │ Lease   │           │ Node A  │
   │ expires │           │ renews  │
   │ (60s)   │           │ leader  │
   └────┬────┘           └─────────┘
        │
        v
   ┌─────────────────┐
   │ Next heartbeat  │
   │ from Node B     │
   │ (30s interval)  │
   └────┬────────────┘
        │
        v
   ┌──────────────────────────────┐
   │ Node B becomes LEADER        │
   │ (lease expired, acquires)    │
   │                              │
   │ DB: leader_id = 'node-b'     │
   └──────────────────────────────┘
```

### Checking Current Leader

**Three methods** (in order of reliability):

#### Method 1: Query Supabase (Most Reliable)

```sql
-- Direct query to leader_election table
SELECT leader_id, expires_at,
       CASE WHEN expires_at > NOW() THEN 'active' ELSE 'expired' END as status
FROM sync_metadata.leader_election
WHERE cluster_name = 'prod-host-1';
```

**Example output**:
```
leader_id                 | expires_at          | status
--------------------------|---------------------|--------
openwebui-sync-node-b     | 2025-10-10 10:32:00 | active
```

#### Method 2: Use v_cluster_health View (Recommended)

```sql
-- Comprehensive cluster status
SELECT hostname, leader_status, leader_lease_expires,
       seconds_since_heartbeat
FROM sync_metadata.v_cluster_health
WHERE cluster_name = 'prod-host-1';
```

**Example output**:
```
hostname                | leader_status | leader_lease_expires | seconds_since_heartbeat
------------------------|---------------|----------------------|------------------------
openwebui-sync-node-a   | follower      | 2025-10-10 10:32:00  | 15
openwebui-sync-node-b   | leader        | 2025-10-10 10:32:00  | 8
```

**Notice**: Node B is the leader even though it's named "node-b" (not "node-a")!

#### Method 3: Container Health API (Less Reliable)

```bash
# Check Node A
curl http://localhost:9443/health | jq '.is_leader'
# Returns: true or false

# Check Node B
curl http://localhost:9444/health | jq '.is_leader'
# Returns: true or false
```

**Limitation**: Requires containers to be running and network connectivity.

### Failover Scenarios

#### Scenario 1: Node A Crashes

```
Time    | Event                           | Leader in DB
--------|--------------------------------|-------------------
10:30:00| Node A is leader, healthy      | node-a
10:30:15| Node A crashes                 | node-a (lease still valid)
10:31:15| Node A lease expires (60s)     | node-a (expired)
10:31:30| Node B heartbeat (30s interval)| node-b (acquired!)
10:31:30| Node B becomes leader          | node-b
```

**Failover time**: ~35 seconds maximum (60s lease + 30s heartbeat interval)

#### Scenario 2: Node A Restarts After Crash

```
Time    | Event                           | Leader in DB
--------|--------------------------------|-------------------
10:31:30| Node B is leader               | node-b
10:32:00| Node A restarts                | node-b (still valid)
10:32:30| Node A tries to acquire        | node-b (rejected - lease valid)
10:33:00| Node B renews lease            | node-b
```

**Result**: Node B remains leader even though Node A is "back online"!

**Why?** Node B's lease hasn't expired, so Node A's heartbeat gets rejected.

#### Scenario 3: Both Nodes Restart

```
Time    | Event                           | Leader in DB
--------|--------------------------------|-------------------
10:30:00| Both nodes restart              | (old lease expired)
10:30:05| Node A heartbeat (wins race)   | node-a
10:30:10| Node B heartbeat (rejected)    | node-a
```

**Result**: Whichever container sends the first heartbeat becomes leader (race condition).

### Leadership Best Practices

**1. Don't Rely on Container Names**

❌ **Wrong assumption**: "Node A is always the leader because it's named 'node-a'"

✅ **Correct approach**: "Check `v_cluster_health` to see which node is currently leader"

**2. Always Check the Database**

❌ **Wrong**: Assuming leadership based on container name or startup order

✅ **Correct**: Query `sync_metadata.leader_election` or `v_cluster_health`

**3. Expect Leadership to Change**

❌ **Wrong**: Hard-coding logic that assumes Node A is always leader

✅ **Correct**: Query current leader before performing leader-specific operations

**4. Monitor Lease Expiration**

```sql
-- Alert if no valid leader for more than 2 minutes
SELECT cluster_name, leader_id, expires_at
FROM sync_metadata.leader_election
WHERE expires_at < NOW() - INTERVAL '2 minutes';
```

**5. Check Heartbeat Lag**

```sql
-- Alert if heartbeat is stale (> 5 minutes)
SELECT hostname, cluster_name, last_heartbeat,
       EXTRACT(EPOCH FROM (NOW() - last_heartbeat))::INTEGER as seconds_since_heartbeat
FROM sync_metadata.hosts
WHERE last_heartbeat < NOW() - INTERVAL '5 minutes';
```

### Key Takeaways

| Question | Answer |
|----------|--------|
| Do container names determine leadership? | ❌ NO |
| Can "node-b" become the leader? | ✅ YES |
| Can "node-a" be a follower? | ✅ YES |
| What determines leadership? | ⚡ PostgreSQL atomic operations + lease expiration |
| Where is the source of truth? | 📊 `sync_metadata.leader_election` table |
| Can both nodes be leaders? | ❌ NO (PostgreSQL prevents split-brain) |
| Can neither node be leader? | ⚠️ Only temporarily (if both down or lease expired) |
| How long does failover take? | ⏱️ ~35 seconds maximum |

---

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
docker exec openwebui-sync-node-a python3 -c "
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
- [ ] Verify both containers are running: `docker ps | grep sync-node`
- [ ] Check container logs: `docker logs openwebui-sync-node-a` and `docker logs openwebui-sync-node-b`
- [ ] Verify DATABASE_URL environment variable is set correctly
- [ ] Test Supabase connectivity from containers
- [ ] Check for expired lease: Should expire in 60 seconds
- [ ] Query `v_cluster_health` view to see current leader status

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
1. Check logs: `docker logs openwebui-sync-node-a` or `docker logs openwebui-sync-node-b`
2. Review Supabase dashboard for database errors
3. Consult troubleshooting section above
4. Query `v_cluster_health` view for cluster status
5. File issue on GitHub with logs and config

## License

Part of the Open WebUI multi-tenant management system.
