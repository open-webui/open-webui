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

./scripts/sync-client-to-supabase.sh CLIENT_NAME [--full]

# Examples:
./scripts/sync-client-to-supabase.sh chat-test           # Incremental sync
./scripts/sync-client-to-supabase.sh chat-test --full    # Full sync
```

**When to use**:
- Manual sync for testing
- Force immediate sync outside scheduler
- Initial data migration after registration

**Note**: Automatic syncing happens via the scheduler (no manual execution needed)

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

## Console Menu Integration

These scripts are designed for console menu integration:

```
┌─────────────────────────────────────────┐
│  Sync Client Management                 │
├─────────────────────────────────────────┤
│  1. Register New Client                 │  → register-sync-client-to-supabase.sh
│  2. Start/Resume Sync                   │  → start-sync.sh
│  3. Pause Sync                          │  → pause-sync.sh
│  4. Manual Sync                         │  → sync-client-to-supabase.sh
│  5. View Sync Status                    │  → (custom query script)
│  6. Remove Client                       │  → deregister-client.sh
│  7. Exit                                │
└─────────────────────────────────────────┘
```

Each menu option maps to exactly ONE script with a clear, specific purpose.
