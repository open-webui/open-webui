# Sync System Scripts Reference

This document provides a clear reference for all client sync management scripts. Each script has a single, specific purpose aligned with its name.

## Script Overview

### Client Lifecycle
```
[New Client] → register-client.sh → [Schema + Tables Created]
                                  ↓
                     register-sync-client-to-supabase.sh → [Sync Enabled]
                                  ↓
                              [Syncing Active]
                                  ↓
                           pause-sync.sh → [Sync Paused]
                                  ↓
                          start-sync.sh → [Syncing Active]
                                  ↓
                        deregister-client.sh → [Client Removed]
```

## Core Scripts

### 1. register-client.sh
**Purpose**: Create Supabase schema and initialize Open WebUI tables for a new client

**What it does**:
- ✅ Checks if schema already exists (prevents overwriting)
- ✅ Creates PostgreSQL schema with client name
- ✅ Grants `sync_service` role access to schema
- ✅ Initializes Open WebUI tables (user, chat, message, etc.)
- ✅ Registers client in `sync_metadata.client_deployments`

**What it does NOT do**:
- ❌ Does NOT start syncing automatically
- ❌ Does NOT sync existing SQLite data

**Usage**:
```bash
./scripts/register-client.sh CLIENT_NAME [CONTAINER_NAME] [SQLITE_PATH]

# Examples:
./scripts/register-client.sh chat-test
./scripts/register-client.sh acme-corp openwebui-acme-corp
./scripts/register-client.sh beta-client openwebui-beta /custom/path/webui.db
```

**Next step**: Use `register-sync-client-to-supabase.sh` or `start-sync.sh` to enable syncing

---

### 2. register-sync-client-to-supabase.sh
**Purpose**: Complete registration workflow for a new client (convenience wrapper)

**What it does**:
- ✅ Validates sync cluster health
- ✅ Checks client container is running
- ✅ Verifies SQLite database exists
- ✅ Calls `register-client.sh` to create schema/tables
- ✅ Enables automatic syncing

**What it does NOT do**:
- ❌ Does NOT perform initial data sync (scheduler handles this)

**Usage**:
```bash
./scripts/register-sync-client-to-supabase.sh CLIENT_NAME [CONTAINER_NAME] [SQLITE_PATH]

# Examples:
./scripts/register-sync-client-to-supabase.sh chat-test
./scripts/register-sync-client-to-supabase.sh acme-corp openwebui-acme-corp
```

**When to use**: New client setup - creates schema AND enables sync in one command

---

### 3. start-sync.sh ⭐ NEW
**Purpose**: Enable/resume automatic syncing for an already registered client

**What it does**:
- ✅ Sets `sync_enabled = true` in client_deployments
- ✅ Sets `status = 'active'`
- ✅ Sync cluster begins automatic syncing

**What it does NOT do**:
- ❌ Does NOT register new clients (use `register-sync-client-to-supabase.sh`)
- ❌ Does NOT create schemas or tables
- ❌ Does NOT trigger immediate sync (scheduler handles this)

**Usage**:
```bash
./scripts/start-sync.sh CLIENT_NAME

# Examples:
./scripts/start-sync.sh chat-test
./scripts/start-sync.sh acme-corp
```

**When to use**:
- Resume syncing after using `pause-sync.sh`
- Re-enable syncing for a client that was paused

---

### 4. pause-sync.sh ⭐ NEW
**Purpose**: Temporarily stop automatic syncing (preserves all data and registration)

**What it does**:
- ✅ Sets `sync_enabled = false` in client_deployments
- ✅ Sets `status = 'paused'`
- ✅ Sync cluster stops syncing this client

**What it does NOT do**:
- ❌ Does NOT delete schema or data in Supabase
- ❌ Does NOT delete client registration
- ❌ Does NOT stop or remove client container
- ❌ Does NOT delete SQLite database

**Usage**:
```bash
./scripts/pause-sync.sh CLIENT_NAME

# Examples:
./scripts/pause-sync.sh chat-test
./scripts/pause-sync.sh acme-corp
```

**When to use**:
- Temporarily stop syncing during maintenance
- Pause syncing before making manual database changes
- Stop syncing without losing data

**To resume**: Use `start-sync.sh CLIENT_NAME`

---

### 5. sync-client-to-supabase.sh
**Purpose**: Execute one-time manual sync from SQLite to Supabase

**What it does**:
- ✅ Runs inside sync container via Docker
- ✅ Syncs all Open WebUI tables (user, chat, message, etc.)
- ✅ Creates sync job entry in `sync_metadata.sync_jobs`
- ✅ Updates `last_sync_at` timestamp

**What it does NOT do**:
- ❌ Does NOT run automatically (use scheduler for that)
- ❌ Does NOT register clients

**Usage**:
```bash
# Must run from SYNC directory with credentials loaded
cd mt/SYNC
source .credentials
export DATABASE_URL="$SYNC_URL"

./scripts/sync-client-to-supabase.sh CLIENT_NAME [TRIGGERED_BY] [--full]

# Examples:
./scripts/sync-client-to-supabase.sh chat-test                    # Manual sync (default)
./scripts/sync-client-to-supabase.sh chat-test manual --full      # Manual full sync
./scripts/sync-client-to-supabase.sh chat-test scheduler          # Scheduler sync (for testing)
./scripts/sync-client-to-supabase.sh chat-test --triggered-by api --full  # API full sync
```

**TRIGGERED_BY values**:
- `manual` (default) - Manual execution by user
- `scheduler` - Automated sync by scheduler
- `api` - REST API triggered sync
- Custom username - Can specify any username for tracking

**When to use**:
- Manual sync for testing
- Force immediate sync outside scheduler
- Initial data migration after registration

**Note**: Automatic syncing happens via the scheduler (no manual execution needed). The `triggered_by` parameter is automatically set by the system based on how the sync was initiated.

---

### 6. deregister-client.sh
**Purpose**: Completely remove client from sync system (optionally delete data)

**What it does**:
- ✅ Removes client from `sync_metadata.client_deployments`
- ✅ Optionally drops schema and deletes all Supabase data (with `--drop-schema`)

**What it does NOT do**:
- ❌ Does NOT stop or remove client container
- ❌ Does NOT delete SQLite database

**Usage**:
```bash
./scripts/deregister-client.sh CLIENT_NAME [--drop-schema]

# Examples:
./scripts/deregister-client.sh chat-test                # Keep Supabase data
./scripts/deregister-client.sh chat-test --drop-schema  # DELETE all data
```

**When to use**:
- Remove client permanently
- Clean up after testing
- Delete client data (with `--drop-schema`)

**⚠️  Warning**: `--drop-schema` DELETES ALL DATA in Supabase (cannot be undone)

---

## Deprecated Scripts

### deregister-sync-client.sh ❌ DEPRECATED
**Status**: Replaced by `pause-sync.sh`

**Why deprecated**: Name was confusing - it paused sync but didn't actually "deregister"

**Migration**:
```bash
# Old (deprecated):
./scripts/deregister-sync-client.sh chat-test

# New (use instead):
./scripts/pause-sync.sh chat-test
```

---

## Quick Reference Table

| Script | Purpose | Creates Schema | Enables Sync | Preserves Data |
|--------|---------|----------------|--------------|----------------|
| `register-client.sh` | Create schema & tables | ✅ | ❌ | N/A |
| `register-sync-client-to-supabase.sh` | Complete new client setup | ✅ | ✅ | N/A |
| `start-sync.sh` | Enable automatic syncing | ❌ | ✅ | ✅ |
| `pause-sync.sh` | Pause automatic syncing | ❌ | ❌ | ✅ |
| `sync-client-to-supabase.sh` | Manual one-time sync | ❌ | ❌ | ✅ |
| `deregister-client.sh` | Remove client | ❌ | ❌ | Optional |

---

## Common Workflows

### New Client Setup
```bash
# Option 1: All-in-one (recommended for new clients)
./scripts/register-sync-client-to-supabase.sh chat-test

# Option 2: Step-by-step
./scripts/register-client.sh chat-test
./scripts/start-sync.sh chat-test
```

### Pause and Resume Syncing
```bash
# Pause syncing (keeps data)
./scripts/pause-sync.sh chat-test

# Resume syncing later
./scripts/start-sync.sh chat-test
```

### Manual Sync
```bash
cd mt/SYNC
source .credentials
export DATABASE_URL="$SYNC_URL"
./scripts/sync-client-to-supabase.sh chat-test --full
```

### Complete Client Removal
```bash
# Option 1: Keep Supabase data
./scripts/deregister-client.sh chat-test

# Option 2: Delete everything
./scripts/deregister-client.sh chat-test --drop-schema
```

---

## Script Requirements

All scripts require:
- ✅ Sync cluster deployed and running (`openwebui-sync-node-a`)
- ✅ `.credentials` file exists in `mt/SYNC/`
- ✅ `ADMIN_URL` set in credentials

Additional requirements:
- `sync-client-to-supabase.sh` requires `DATABASE_URL` environment variable
- `register-sync-client-to-supabase.sh` requires client container running

---

## Troubleshooting

### "Client already registered" error
**Problem**: Trying to register a client that already exists

**Solution**:
- Use `start-sync.sh` instead of `register-sync-client-to-supabase.sh`
- Or use `deregister-client.sh` first, then re-register

### "Schema already exists" warning
**Problem**: `register-client.sh` detects existing schema with tables

**Solution**: Script automatically skips schema initialization to protect data

### "DATABASE_URL not set" error
**Problem**: `sync-client-to-supabase.sh` requires DATABASE_URL

**Solution**:
```bash
cd mt/SYNC
source .credentials
export DATABASE_URL="$SYNC_URL"
./scripts/sync-client-to-supabase.sh CLIENT_NAME
```

### Sync not triggering automatically
**Problem**: Client registered but not syncing

**Check**:
1. Is sync enabled? `docker exec -i openwebui-sync-node-a python3 << 'EOF'
   import asyncpg, asyncio, os
   async def check():
       conn = await asyncpg.connect(os.getenv('ADMIN_URL'))
       row = await conn.fetchrow('SELECT sync_enabled, status FROM sync_metadata.client_deployments WHERE client_name = $1', 'CLIENT_NAME')
       print(f'sync_enabled={row["sync_enabled"]}, status={row["status"]}')
       await conn.close()
   asyncio.run(check())
   EOF`

2. If `sync_enabled=False`, use: `./scripts/start-sync.sh CLIENT_NAME`

---

## REST API Integration

The sync system provides REST API endpoints for programmatic control.

### API Endpoints

**Base URL**: `http://localhost:9443` (node-a) or `http://localhost:9444` (node-b)

#### 1. Health Check
```bash
GET /health

# Example:
curl -s http://localhost:9443/health | jq
```

**Response**:
```json
{
  "status": "healthy",
  "node_id": "default-cluster-primary",
  "role": "primary",
  "is_leader": true,
  "cluster_name": "default-cluster",
  "uptime_seconds": 3600.5,
  "leader_id": "default-cluster-primary"
}
```

#### 2. Trigger Manual Sync (Leader Only)
```bash
POST /api/v1/sync/trigger
Content-Type: application/json

{
  "client_name": "chat-test",
  "full_sync": false
}

# Example:
curl -X POST http://localhost:9443/api/v1/sync/trigger \
  -H "Content-Type: application/json" \
  -d '{"client_name": "chat-test", "full_sync": false}'
```

**Parameters**:
- `client_name` (required): Name of the client to sync
- `full_sync` (optional): `true` for full sync, `false` for incremental (default)

**Response**:
```json
{
  "status": "queued",
  "client": "chat-test",
  "full_sync": false,
  "queued_at": "2025-10-14T14:30:00.123456"
}
```

**Note**: This endpoint sets `triggered_by='api'` automatically.

#### 3. Get Cluster Status
```bash
GET /api/v1/cluster/status

# Example:
curl -s http://localhost:9443/api/v1/cluster/status | jq
```

**Response**:
```json
{
  "cluster_name": "default-cluster",
  "nodes": [
    {
      "host_id": "uuid-1",
      "hostname": "openwebui-sync-node-a",
      "cluster_name": "default-cluster",
      "last_heartbeat": "2025-10-14T14:30:00",
      "status": "healthy",
      "is_leader": true
    }
  ]
}
```

#### 4. Get State (Cache)
```bash
GET /api/v1/state/{key}

# Example:
curl -s http://localhost:9443/api/v1/state/my-key | jq
```

#### 5. Update State
```bash
PUT /api/v1/state/{key}
Content-Type: application/json

{
  "key": "my-key",
  "value": {"data": "value"}
}
```

#### 6. Get Unresolved Conflicts
```bash
GET /api/v1/conflicts?client_name=chat-test&limit=100

# Example:
curl -s "http://localhost:9443/api/v1/conflicts?client_name=chat-test" | jq
```

### API Usage Examples

#### Python
```python
import requests

# Trigger sync
response = requests.post(
    'http://localhost:9443/api/v1/sync/trigger',
    json={'client_name': 'chat-test', 'full_sync': False}
)
print(response.json())

# Check health
health = requests.get('http://localhost:9443/health').json()
print(f"Leader: {health['is_leader']}, Uptime: {health['uptime_seconds']}s")
```

#### JavaScript/Node.js
```javascript
// Trigger sync
const response = await fetch('http://localhost:9443/api/v1/sync/trigger', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ client_name: 'chat-test', full_sync: false })
});
const result = await response.json();
console.log(result);
```

#### Shell Script
```bash
#!/bin/bash
# Trigger sync via API with error handling

SYNC_API="http://localhost:9443/api/v1/sync/trigger"
CLIENT_NAME="chat-test"

response=$(curl -s -w "\n%{http_code}" -X POST "$SYNC_API" \
  -H "Content-Type: application/json" \
  -d "{\"client_name\": \"$CLIENT_NAME\", \"full_sync\": false}")

http_code=$(echo "$response" | tail -1)
body=$(echo "$response" | head -1)

if [ "$http_code" = "200" ]; then
  echo "✅ Sync queued: $body"
else
  echo "❌ Error ($http_code): $body"
  exit 1
fi
```

### API vs Script Comparison

| Method | triggered_by | Use Case |
|--------|-------------|----------|
| **API** `/api/v1/sync/trigger` | `api` | Programmatic integration, webhooks, automated workflows |
| **Script** `sync-client-to-supabase.sh` | `manual` | Manual execution, testing, debugging |
| **Scheduler** (automatic) | `scheduler` | Periodic automated syncing |

---

## Console Menu Integration

These scripts are designed for easy console menu integration. Here's a complete implementation guide:

### Basic Menu Template

```bash
#!/bin/bash
# Sync Management Console Menu

SCRIPT_DIR="/path/to/mt/SYNC/scripts"

show_menu() {
    clear
    echo "╔═════════════════════════════════════════╗"
    echo "║    Sync Client Management Console      ║"
    echo "╠═════════════════════════════════════════╣"
    echo "║  1. Register New Client                 ║"
    echo "║  2. Start/Resume Sync                   ║"
    echo "║  3. Pause Sync                          ║"
    echo "║  4. Manual Sync (Full)                  ║"
    echo "║  5. Manual Sync (Incremental)           ║"
    echo "║  6. View Sync Status                    ║"
    echo "║  7. View Recent Sync Jobs               ║"
    echo "║  8. Remove Client                       ║"
    echo "║  9. Exit                                ║"
    echo "╚═════════════════════════════════════════╝"
}

read_client_name() {
    read -p "Enter client name: " client_name
    if [[ -z "$client_name" ]]; then
        echo "❌ Client name required"
        return 1
    fi
}

case_1_register() {
    echo "=== Register New Client ==="
    read_client_name || return
    read -p "Container name [openwebui-$client_name]: " container_name
    container_name=${container_name:-openwebui-$client_name}

    "$SCRIPT_DIR/register-sync-client-to-supabase.sh" "$client_name" "$container_name"
    read -p "Press Enter to continue..."
}

case_2_start() {
    echo "=== Start/Resume Sync ==="
    read_client_name || return
    "$SCRIPT_DIR/start-sync.sh" "$client_name"
    read -p "Press Enter to continue..."
}

case_3_pause() {
    echo "=== Pause Sync ==="
    read_client_name || return
    "$SCRIPT_DIR/pause-sync.sh" "$client_name"
    read -p "Press Enter to continue..."
}

case_4_manual_full() {
    echo "=== Manual Full Sync ==="
    read_client_name || return

    cd "$SCRIPT_DIR/.."
    source .credentials
    export DATABASE_URL="$SYNC_URL"

    ./scripts/sync-client-to-supabase.sh "$client_name" "manual-console" --full
    read -p "Press Enter to continue..."
}

case_5_manual_incremental() {
    echo "=== Manual Incremental Sync ==="
    read_client_name || return

    cd "$SCRIPT_DIR/.."
    source .credentials
    export DATABASE_URL="$SYNC_URL"

    ./scripts/sync-client-to-supabase.sh "$client_name" "manual-console"
    read -p "Press Enter to continue..."
}

case_6_status() {
    echo "=== Sync Status ==="
    read_client_name || return

    docker exec -i openwebui-sync-node-a python3 << EOF
import asyncpg, asyncio, os, sys

async def check_status():
    try:
        conn = await asyncpg.connect(os.getenv('ADMIN_URL'))
        row = await conn.fetchrow('''
            SELECT sync_enabled, status, sync_interval, last_sync_at, last_sync_status
            FROM sync_metadata.client_deployments
            WHERE client_name = \$1
        ''', '$client_name')

        if row:
            print(f"Client: $client_name")
            print(f"  Sync Enabled: {row['sync_enabled']}")
            print(f"  Status: {row['status']}")
            print(f"  Interval: {row['sync_interval']}s")
            print(f"  Last Sync: {row['last_sync_at']}")
            print(f"  Last Status: {row['last_sync_status']}")
        else:
            print(f"❌ Client '$client_name' not found")

        await conn.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

asyncio.run(check_status())
EOF
    read -p "Press Enter to continue..."
}

case_7_recent_jobs() {
    echo "=== Recent Sync Jobs ==="

    docker exec -i openwebui-sync-node-a python3 << 'EOF'
import asyncpg, asyncio, os, sys

async def show_jobs():
    try:
        conn = await asyncpg.connect(os.getenv('ADMIN_URL'))
        rows = await conn.fetch('''
            SELECT job_id, client_name, started_at, status,
                   sync_type, triggered_by, rows_synced, duration_seconds
            FROM sync_metadata.sync_jobs
            ORDER BY started_at DESC
            LIMIT 10
        ''')

        print(f"{'Client':<15} {'Started':<20} {'Status':<10} {'Type':<6} {'By':<10} {'Rows':<8} {'Duration':<8}")
        print("-" * 100)

        for row in rows:
            duration = f"{row['duration_seconds']:.1f}s" if row['duration_seconds'] else "-"
            print(f"{row['client_name']:<15} {str(row['started_at']):<20} {row['status']:<10} "
                  f"{row['sync_type']:<6} {row['triggered_by']:<10} {row['rows_synced'] or 0:<8} {duration:<8}")

        await conn.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

asyncio.run(show_jobs())
EOF
    read -p "Press Enter to continue..."
}

case_8_remove() {
    echo "=== Remove Client ==="
    read_client_name || return
    read -p "Delete schema and data? (y/N): " delete_schema

    if [[ "$delete_schema" =~ ^[Yy]$ ]]; then
        "$SCRIPT_DIR/deregister-client.sh" "$client_name" --drop-schema
    else
        "$SCRIPT_DIR/deregister-client.sh" "$client_name"
    fi
    read -p "Press Enter to continue..."
}

# Main loop
while true; do
    show_menu
    read -p "Select option (1-9): " choice

    case $choice in
        1) case_1_register ;;
        2) case_2_start ;;
        3) case_3_pause ;;
        4) case_4_manual_full ;;
        5) case_5_manual_incremental ;;
        6) case_6_status ;;
        7) case_7_recent_jobs ;;
        8) case_8_remove ;;
        9) echo "Goodbye!"; exit 0 ;;
        *) echo "Invalid option"; sleep 2 ;;
    esac
done
```

### Menu Feature Mapping

| Menu Option | Script/Tool | triggered_by | Notes |
|-------------|-------------|--------------|-------|
| 1. Register New Client | `register-sync-client-to-supabase.sh` | - | Creates schema + enables sync |
| 2. Start/Resume Sync | `start-sync.sh` | - | Enables automatic syncing |
| 3. Pause Sync | `pause-sync.sh` | - | Temporarily stops syncing |
| 4. Manual Full Sync | `sync-client-to-supabase.sh` | `manual-console` | Full data sync with custom trigger |
| 5. Manual Incremental | `sync-client-to-supabase.sh` | `manual-console` | Incremental sync with custom trigger |
| 6. View Sync Status | SQL query via Python | - | Shows current sync configuration |
| 7. View Recent Jobs | SQL query via Python | - | Shows last 10 sync jobs |
| 8. Remove Client | `deregister-client.sh` | - | Optional schema deletion |

### Console Menu Benefits

1. **User-friendly**: No need to remember script names or parameters
2. **Error handling**: Input validation and confirmation prompts
3. **Consistent UX**: Uniform interface for all operations
4. **Custom triggered_by**: Use `manual-console` to distinguish menu-triggered syncs
5. **Status visibility**: Easy access to sync status and history

---

## Monitoring Sync Jobs

### Query Recent Sync Jobs
```bash
docker exec -i openwebui-sync-node-a python3 << 'EOF'
import asyncpg, asyncio, os

async def show_jobs():
    conn = await asyncpg.connect(os.getenv('ADMIN_URL'))
    rows = await conn.fetch('''
        SELECT job_id, client_name, started_at, completed_at,
               status, sync_type, triggered_by, rows_synced,
               rows_failed, duration_seconds
        FROM sync_metadata.sync_jobs
        WHERE client_name = $1
        ORDER BY started_at DESC
        LIMIT 10
    ''', 'chat-test')

    for row in rows:
        print(dict(row))

    await conn.close()

asyncio.run(show_jobs())
EOF
```

### Filter by triggered_by
```sql
-- Manual syncs only
SELECT * FROM sync_metadata.sync_jobs
WHERE triggered_by = 'manual'
ORDER BY started_at DESC LIMIT 10;

-- Automated syncs (scheduler + API)
SELECT * FROM sync_metadata.sync_jobs
WHERE triggered_by IN ('scheduler', 'api')
ORDER BY started_at DESC LIMIT 10;

-- Console menu syncs
SELECT * FROM sync_metadata.sync_jobs
WHERE triggered_by = 'manual-console'
ORDER BY started_at DESC LIMIT 10;
```

### Performance Metrics
```sql
-- Average sync duration by trigger type
SELECT triggered_by,
       COUNT(*) as total_syncs,
       AVG(duration_seconds) as avg_duration,
       AVG(rows_synced) as avg_rows
FROM sync_metadata.sync_jobs
WHERE status = 'success'
GROUP BY triggered_by
ORDER BY triggered_by;
```

---

Each menu option maps to exactly ONE script with a clear, specific purpose.
