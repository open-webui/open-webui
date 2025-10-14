# Cluster Lifecycle Management - Frequently Asked Questions

**Date**: 2025-10-10
**Project**: SQLite + Supabase Sync System (Phase 1)

---

## Question 1: Does client-manager support cluster lifecycle management?

### Short Answer
**YES (PARTIAL)** - The client-manager (`mt/client-manager.sh`) now supports sync node management and client sync operations as of 2025-10-14.

### Current State

**✅ What client-manager.sh CAN do**:
- Create and manage Open WebUI client deployments
- Migrate individual clients from SQLite to PostgreSQL/Supabase
- View database configuration for PostgreSQL clients
- Start/stop/restart client containers
- Change client domains and OAuth settings
- Generate nginx configurations
- **NEW: Manage sync nodes (view status, logs, restart)**
- **NEW: Register clients with sync system**
- **NEW: Enable/disable sync for clients (start/pause)**
- **NEW: Monitor sync status and view recent jobs**
- **NEW: Perform manual syncs (full and incremental)**
- **NEW: Deregister clients from sync system**
- **NEW: View cluster health and leader status**

**❌ What client-manager.sh CANNOT do (yet)**:
- Deploy new sync clusters (use `SYNC/scripts/deploy-sync-cluster.sh`)
- Deregister clusters before host destruction (use `SYNC/scripts/deregister-cluster.sh`)
- Initial cluster deployment (still requires manual script execution)

### Integration Status

**Phase 1.5 - Client-Manager Integration** ✅ **IMPLEMENTED** (2025-10-14):

The sync system and client-manager are now **INTEGRATED**:
- **Sync Node Management**: Available via client-manager menu (Option 3 → Select sync-node)
- **Client Sync Management**: Available via client-manager menu (Option 3 → Select client → Option 8)
- **Cluster Deployment**: Still requires `mt/SYNC/scripts/deploy-sync-cluster.sh`
- **Cluster Deregistration**: Still requires `mt/SYNC/scripts/deregister-cluster.sh`

### How to Access Sync Features

**To manage sync nodes** (view status, logs, restart):
```bash
cd mt
./client-manager.sh
# Select: 3) Manage Existing Deployment
# Select: sync-node-a or sync-node-b
# Menu shows: View Cluster Status, View Health Check, View Logs, Restart, Stop, Update
```

**To manage client sync** (enable, disable, view status):
```bash
cd mt
./client-manager.sh
# Select: 3) Manage Existing Deployment
# Select: your-client-name
# Select: 8) Sync Management
# Menu shows: Register, Start/Resume, Pause, Manual Sync, View Status, View Jobs, Deregister, Help
```

**To deploy/deregister clusters**, use dedicated scripts:
```bash
# Deploy sync cluster (initial setup)
cd mt/SYNC
./scripts/deploy-sync-cluster.sh

# Deregister cluster (before destroying host)
cd mt/SYNC
./scripts/deregister-cluster.sh
```

---

## Question 2: Does deregistration validate that no Open WebUI clients are configured for sync?

### Short Answer
**YES (NOW)** - As of today (2025-10-10), the enhanced `deregister-cluster.sh` script includes **comprehensive safety checks**.

### Safety Checks Implemented

#### ✅ Active Sync Client Detection

The script will **BLOCK deregistration** if ANY client has `sync_enabled = true`:

```sql
-- Automatically checks this:
SELECT COUNT(*)
FROM sync_metadata.client_deployments cd
JOIN sync_metadata.hosts h ON cd.host_id = h.host_id
WHERE h.cluster_name = 'YOUR_CLUSTER'
  AND cd.sync_enabled = true;
```

If count > 0, deregistration is **blocked** with error message.

#### ✅ Detailed Sync Client Report

When sync-enabled clients are detected, the script shows:
- Client name
- Container name
- Last sync timestamp
- Last sync status (success/failed/running/pending)

#### ✅ Clear Remediation Options

The script provides **three explicit options** for each sync-enabled client:

**Option 1: Disable Sync**
- Use client-manager.sh (when integration is built)
- OR manual SQL: `UPDATE sync_metadata.client_deployments SET sync_enabled = false WHERE client_name = 'CLIENT_NAME';`

**Option 2: Migrate to Another Cluster/Host**
- Deploy sync cluster on new host
- Migrate Open WebUI container to new host
- Update `client_deployments.host_id` to new host's ID

**Option 3: Decommission Client**
- Stop the Open WebUI container
- Backup data if needed
- Delete from `sync_metadata.client_deployments`

#### ✅ Non-Sync Client Warning

For clients with `sync_enabled = false`, the script:
- Shows count of affected clients
- Warns they will be deleted (via CASCADE)
- Suggests manual migration if records should be preserved

### Protection Flow

```
┌─────────────────────────────────────┐
│ Run deregister-cluster.sh           │
└──────────────┬──────────────────────┘
               │
               v
┌──────────────────────────────────────┐
│ Check: sync_enabled clients?         │
└──────────────┬───────────────────────┘
               │
         ┌─────┴─────┐
         │           │
      YES│           │NO
         v           v
┌─────────────┐  ┌────────────────┐
│ ❌ BLOCK    │  │ ✅ ALLOW      │
│ Exit script │  │ Continue with  │
│ Show clients│  │ warning about  │
│ Show options│  │ non-sync       │
└─────────────┘  │ clients        │
                 └────────┬───────┘
                          │
                          v
                 ┌────────────────┐
                 │ User confirms  │
                 │ deletion       │
                 └────────┬───────┘
                          │
                          v
                 ┌────────────────┐
                 │ Deregister     │
                 │ cluster        │
                 └────────────────┘
```

### Example Output When Blocked

```
╔════════════════════════════════════════════════════════════════╗
║  ⚠️  CRITICAL WARNING: ACTIVE SYNC CLIENTS DETECTED           ║
╚════════════════════════════════════════════════════════════════╝

❌ Cannot deregister cluster: 2 client(s) have sync ENABLED

Clients with sync enabled:
┌──────────────┬────────────────────────┬─────────────────────┬──────────┐
│ client_name  │ container_name         │ last_sync_at        │ status   │
├──────────────┼────────────────────────┼─────────────────────┼──────────┤
│ acme-corp    │ openwebui-acme-corp    │ 2025-10-10 10:30:00 │ success  │
│ beta-client  │ openwebui-beta-client  │ 2025-10-10 10:25:00 │ success  │
└──────────────┴────────────────────────┴─────────────────────┴──────────┘

═══════════════════════════════════════════════════════════════════
REQUIRED ACTIONS before deregistration:
═══════════════════════════════════════════════════════════════════

For each client listed above, choose ONE of the following:

Option 1: Disable sync for this client
   - Use client-manager.sh to disable sync
   - OR manually: UPDATE sync_metadata.client_deployments
     SET sync_enabled = false WHERE client_name = 'CLIENT_NAME';

Option 2: Migrate client to another host/cluster
   - Deploy sync cluster on new host
   - Migrate Open WebUI container to new host
   - Update client_deployments.host_id to new host

Option 3: Decommission the client deployment
   - Stop the Open WebUI container
   - Backup data if needed
   - Delete from sync_metadata.client_deployments

Once all sync-enabled clients are handled, re-run this script.

❌ ERROR: Deregistration blocked due to active sync clients
```

### Example Output When Allowed

```
✅ Safety check passed: No active sync clients found

⚠️  WARNING: Found 1 client deployment(s) registered (sync disabled)
  These will be deleted when the cluster is deregistered.
  If you want to preserve these client records for future use,
  manually migrate them to another cluster before proceeding.

⚠️  WARNING: This will permanently delete:
   - All host records for cluster 'prod-host-1'
   - Leader election records (via CASCADE)
   - Client deployment records (via CASCADE) - 1 client(s)
   - Cache invalidation events (via CASCADE)
   - Sync job history (via CASCADE)

Are you sure you want to deregister this cluster? (yes/no):
```

---

## Question 3: What about clients not configured for sync?

### Development Clients (Sync Not Configured)

**These are SAFE to leave** when deregistering a cluster:

**Scenario**: You have development Open WebUI instances that:
- Use SQLite (not PostgreSQL)
- Were created via `client-manager.sh`
- Were **NEVER registered** with the sync system
- Have **NO entry** in `sync_metadata.client_deployments`

**Impact of Cluster Deregistration**: **NONE**
- These clients are not tracked in Supabase
- No CASCADE deletes will affect them
- They continue running independently
- No sync metadata to clean up

**Example**:
```bash
# Development client created with:
./client-manager.sh
# → Create new deployment: dev-test
# → Port: 8083
# → Domain: localhost:8083
# → Database: SQLite (default)
# → Sync: Not configured (not registered with sync system)

# This client is NOT affected by cluster deregistration
```

### Registered Clients (Sync Disabled)

**These WILL BE DELETED** when deregistering:

**Scenario**: You previously enabled sync for a client, then disabled it:
- Client has entry in `sync_metadata.client_deployments`
- `sync_enabled = false`
- Still references this cluster's `host_id`

**Impact of Cluster Deregistration**: **DELETED**
- When `sync_metadata.hosts` is deleted
- CASCADE deletes `client_deployments` records
- Historical data about this client is lost
- **Open WebUI container is NOT affected** (only metadata)

**To Preserve**:
```sql
-- Before deregistering, migrate client record to new cluster
UPDATE sync_metadata.client_deployments
SET host_id = 'NEW_CLUSTER_HOST_ID'
WHERE client_name = 'my-client'
  AND sync_enabled = false;
```

---

## Database Schema Reference

### CASCADE Relationships

When a host is deleted from `sync_metadata.hosts`:

```sql
-- These tables have ON DELETE CASCADE:
sync_metadata.client_deployments
   └─> deployment_id references client_deployments
       └─> conflict_log (CASCADE)
       └─> sync_jobs (CASCADE)

sync_metadata.leader_election
   └─> leader_host_id references hosts (CASCADE)

sync_metadata.cache_events
   └─> host_id references hosts (CASCADE)
```

**Impact**: Deleting a host deletes:
1. All client deployment records for this host
2. All conflict logs for those deployments
3. All sync jobs for those deployments
4. All leader election records for this cluster
5. All cache invalidation events for this host

---

## Operational Procedures

### Before Destroying a Host

**Step 1: Inventory Sync-Enabled Clients**
```bash
cd mt/SYNC
./scripts/deregister-cluster.sh
# Script will list all sync-enabled clients and block if any exist
```

**Step 2: Handle Each Sync-Enabled Client**

Choose one option per client:

**Option A: Disable Sync**
```sql
-- If client should stay on this host but stop syncing
UPDATE sync_metadata.client_deployments
SET sync_enabled = false,
    last_sync_status = 'stopped'
WHERE client_name = 'CLIENT_NAME';
```

**Option B: Migrate to New Cluster**
```bash
# 1. Deploy sync cluster on new host
ssh new-host
cd /path/to/mt/SYNC
./scripts/deploy-sync-cluster.sh

# 2. Get new host ID
docker run --rm postgres:15-alpine psql "$SUPABASE_ADMIN_URL" -c \
  "SELECT host_id, hostname, cluster_name FROM sync_metadata.hosts ORDER BY created_at DESC LIMIT 1;"

# 3. Update client record
docker run --rm postgres:15-alpine psql "$SUPABASE_ADMIN_URL" -c \
  "UPDATE sync_metadata.client_deployments
   SET host_id = 'NEW_HOST_ID'
   WHERE client_name = 'CLIENT_NAME';"

# 4. Migrate Open WebUI container to new host
# (Manual process - backup/restore data volume)
```

**Option C: Decommission Client**
```bash
# Stop container
docker stop openwebui-CLIENT_NAME

# Backup data
docker run --rm -v openwebui-CLIENT_NAME-data:/data \
  -v $(pwd):/backup alpine \
  tar czf /backup/CLIENT_NAME-backup.tar.gz -C /data .

# Delete from Supabase
docker run --rm postgres:15-alpine psql "$SUPABASE_ADMIN_URL" -c \
  "DELETE FROM sync_metadata.client_deployments WHERE client_name = 'CLIENT_NAME';"

# Remove container
docker rm openwebui-CLIENT_NAME
```

**Step 3: Deregister Cluster**
```bash
# After all sync-enabled clients are handled
cd mt/SYNC
./scripts/deregister-cluster.sh
# Follow prompts, script will now succeed
```

**Step 4: Destroy Host**
```bash
# Safe to destroy Digital Ocean droplet
# All metadata cleaned up
# No orphaned records in Supabase
```

---

## Summary

### Question 1: Client-Manager Integration
**Status**: ✅ **IMPLEMENTED** (2025-10-14)
**Current State**: Sync node and client sync management integrated into client-manager
**Access**: Via client-manager.sh menu (Option 3 → Select deployment → Sync options)
**Remaining Gap**: Cluster deployment and deregistration still require dedicated scripts

### Question 2: Sync Client Safety Checks
**Status**: ✅ **IMPLEMENTED** (as of 2025-10-10)
**Protection**: Deregistration blocked if sync-enabled clients exist
**Validation**: Automatic checks with detailed reporting
**Options**: Three clear remediation paths provided

### Question 3: Development Clients
**Status**: ✅ **SAFE**
**Impact**: Development clients without sync registration are unaffected
**Note**: Only registered clients (sync enabled or disabled) are affected by cluster deregistration

---

## Next Steps

### Immediate (Your Fresh Deployment Test)
Since you're destroying the current droplet and creating a fresh one:

1. **Check if any clients have sync enabled** (likely NONE if you haven't deployed sync yet)
2. **Run deregister script** to clean up any test data
3. **Destroy droplet** - safe because no production sync clients exist
4. **Create fresh droplet** with IPv6 enabled
5. **Deploy sync cluster** using enhanced deployment script
6. **Test end-to-end** including deregistration safety checks

### Future Enhancements
1. **Client-Manager Integration** (Phase 1.5):
   - Add "Configure Sync" menu option
   - Enable/disable sync for clients
   - View sync status and history
   - Cluster management functions

2. **Automated Migration Tools** (Phase 2):
   - Cross-host client migration scripts
   - Bulk client transfer utilities
   - Cluster failover automation

3. **Monitoring & Alerts** (Phase 2):
   - Alert on orphaned hosts (heartbeat > 5 min)
   - Alert on sync failures
   - Dashboard for cluster health

---

**Last Updated**: 2025-10-14
**Script Version**: deregister-cluster.sh v1.1 (with safety checks)
**Client-Manager Version**: v2.0 (with sync integration)
