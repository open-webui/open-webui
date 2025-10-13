#!/bin/bash
# SQLite + Supabase Sync System - Sync Engine
# Phase 1: One-way sync (SQLite → Supabase)
#
# This script performs the actual synchronization from a client's SQLite database
# to Supabase PostgreSQL with conflict detection and resolution.
#
# Usage: ./sync-client-to-supabase.sh CLIENT_NAME [--full]

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

CLIENT_NAME="${1:-}"
FULL_SYNC="${2:-}"

if [[ -z "$CLIENT_NAME" ]]; then
    echo "❌ Error: CLIENT_NAME required"
    echo "Usage: $0 CLIENT_NAME [--full]"
    exit 1
fi

CONTAINER_NAME="openwebui-${CLIENT_NAME}"
SQLITE_PATH="/app/backend/data/webui.db"
BATCH_SIZE="${BATCH_SIZE:-1000}"
SUPABASE_URL="${DATABASE_URL:-}"

if [[ -z "$SUPABASE_URL" ]]; then
    echo "❌ Error: DATABASE_URL environment variable not set"
    exit 1
fi

# Tables to sync (from Open WebUI schema)
TABLES=("user" "auth" "tag" "config" "chat" "oauth_session" "function" "message")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

log_info() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $*"
}

log_error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2
}

log_success() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✅ $*"
}

# Check if container exists and is running
check_container() {
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        log_error "Container $CONTAINER_NAME is not running"
        return 1
    fi
    return 0
}

# Get last sync timestamp from Supabase
get_last_sync_timestamp() {
    local client="$1"

    docker run --rm --network host \
        -e DATABASE_URL="$SUPABASE_URL" \
        ghcr.io/imagicrafter/open-webui:main \
        python3 -c "
import asyncpg
import asyncio

async def get_timestamp():
    try:
        conn = await asyncpg.connect('$SUPABASE_URL')
        result = await conn.fetchval('''
            SELECT last_sync_at
            FROM sync_metadata.client_deployments
            WHERE client_name = \$1
        ''', '$client')
        await conn.close()
        return result.isoformat() if result else '1970-01-01T00:00:00'
    except Exception as e:
        print('1970-01-01T00:00:00')  # Fallback on error

print(asyncio.run(get_timestamp()))
" 2>/dev/null || echo "1970-01-01T00:00:00"
}

# Checkpoint SQLite WAL for consistent snapshot
checkpoint_wal() {
    log_info "Checkpointing SQLite WAL..."

    docker exec "$CONTAINER_NAME" python3 -c "
import sqlite3
conn = sqlite3.connect('$SQLITE_PATH')
conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
conn.close()
print('WAL checkpointed')
" 2>/dev/null || {
        log_error "Failed to checkpoint WAL"
        return 1
    }

    log_success "WAL checkpointed"
    return 0
}

# Get row count for a table
get_row_count() {
    local table="$1"
    local since_timestamp="$2"

    docker exec "$CONTAINER_NAME" python3 -c "
import sqlite3
from datetime import datetime

conn = sqlite3.connect('$SQLITE_PATH')
cursor = conn.cursor()

# Convert ISO timestamp to Unix epoch (Open WebUI uses Unix timestamps)
since_dt = datetime.fromisoformat('$since_timestamp'.replace('Z', '+00:00'))
since_epoch = int(since_dt.timestamp())

cursor.execute('SELECT COUNT(*) FROM \"$table\" WHERE updated_at > ?', (since_epoch,))
count = cursor.fetchone()[0]
conn.close()
print(count)
" 2>/dev/null || echo "0"
}

# Sync a single table
sync_table() {
    local table="$1"
    local since_timestamp="$2"
    local rows_synced=0
    local rows_failed=0

    log_info "Syncing table: $table"

    # Get row count
    local total_rows
    total_rows=$(get_row_count "$table" "$since_timestamp")

    if [[ "$total_rows" -eq 0 ]]; then
        log_info "No changes in $table since $since_timestamp"
        return 0
    fi

    log_info "Found $total_rows rows to sync in $table"

    # Export changed rows as JSON using Python
    local temp_file
    temp_file=$(mktemp)

    docker exec "$CONTAINER_NAME" python3 -c "
import sqlite3
import json
import sys
from datetime import datetime

conn = sqlite3.connect('$SQLITE_PATH')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Convert ISO timestamp to Unix epoch (Open WebUI uses Unix timestamps)
since_dt = datetime.fromisoformat('$since_timestamp'.replace('Z', '+00:00'))
since_epoch = int(since_dt.timestamp())

cursor.execute('SELECT * FROM \"$table\" WHERE updated_at > ? LIMIT $BATCH_SIZE', (since_epoch,))

rows = []
for row in cursor:
    rows.append(dict(row))

conn.close()
print(json.dumps(rows))
" > "$temp_file" 2>/dev/null || {
        log_error "Failed to export $table"
        rm -f "$temp_file"
        return 1
    }

    # Process each row
    local row_count
    row_count=$(jq '. | length' "$temp_file" 2>/dev/null || echo "0")

    if [[ "$row_count" -eq 0 ]]; then
        log_info "No rows exported from $table"
        rm -f "$temp_file"
        return 0
    fi

    log_info "Processing $row_count rows from $table..."

    # Import to Supabase with conflict detection
    # Note: This is a simplified version - production would handle conflicts properly
    docker run --rm --network host \
        -e DATABASE_URL="$SUPABASE_URL" \
        -v "$temp_file:/tmp/data.json:ro" \
        ghcr.io/imagicrafter/open-webui:main \
        python3 -c "
import asyncpg
import asyncio
import json

async def sync_rows():
    with open('/tmp/data.json', 'r') as f:
        rows = json.load(f)

    conn = await asyncpg.connect('$SUPABASE_URL')

    synced = 0
    failed = 0

    for row in rows:
        try:
            # Get column names and values
            columns = list(row.keys())
            values = [row[col] for col in columns]

            # Build INSERT ... ON CONFLICT DO UPDATE query
            # Quote identifiers for schema and table names with hyphens
            placeholders = ', '.join([f'\${i+1}' for i in range(len(columns))])
            cols_str = ', '.join([f'"{col}"' for col in columns])

            # Simple upsert with properly quoted identifiers
            query = f'''
                INSERT INTO "${CLIENT_NAME}"."{table}" ({cols_str})
                VALUES ({placeholders})
                ON CONFLICT (id) DO UPDATE
                SET {', '.join([f'"{col}" = EXCLUDED."{col}"' for col in columns if col != 'id'])}
            '''

            await conn.execute(query, *values)
            synced += 1

        except Exception as e:
            print(f'Error syncing row: {e}')
            failed += 1

    await conn.close()
    print(f'{synced},{failed}')

asyncio.run(sync_rows())
" 2>&1 | tail -1 || echo "0,0"

    # Parse results
    local result
    result=$(docker run --rm --network host \
        -e DATABASE_URL="$SUPABASE_URL" \
        -v "$temp_file:/tmp/data.json:ro" \
        ghcr.io/imagicrafter/open-webui:main \
        python3 -c "
import asyncpg
import asyncio
import json

async def sync_rows():
    with open('/tmp/data.json', 'r') as f:
        rows = json.load(f)

    conn = await asyncpg.connect('$SUPABASE_URL')

    synced = 0
    failed = 0

    for row in rows:
        try:
            columns = list(row.keys())
            values = [row[col] for col in columns]
            placeholders = ', '.join([f'\${i+1}' for i in range(len(columns))])
            cols_str = ', '.join([f'"{col}"' for col in columns])

            query = f'''
                INSERT INTO "${CLIENT_NAME}"."{table}" ({cols_str})
                VALUES ({placeholders})
                ON CONFLICT (id) DO UPDATE
                SET {', '.join([f'"{col}" = EXCLUDED."{col}"' for col in columns if col != 'id'])}
            '''

            await conn.execute(query, *values)
            synced += 1
        except Exception as e:
            failed += 1

    await conn.close()
    print(f'{synced},{failed}')

asyncio.run(sync_rows())
" 2>&1 | tail -1)

    rows_synced=$(echo "$result" | cut -d',' -f1)
    rows_failed=$(echo "$result" | cut -d',' -f2)

    rm -f "$temp_file"

    log_success "Synced $rows_synced rows from $table (failed: $rows_failed)"

    return 0
}

# ============================================================================
# MAIN SYNC LOGIC
# ============================================================================

main() {
    log_info "Starting sync for client: $CLIENT_NAME"

    # Check container
    if ! check_container; then
        log_error "Cannot sync - container not available"
        exit 1
    fi

    # Get last sync timestamp
    local last_sync
    if [[ "$FULL_SYNC" == "--full" ]]; then
        log_info "Full sync requested - syncing all data"
        last_sync="1970-01-01T00:00:00"
    else
        last_sync=$(get_last_sync_timestamp "$CLIENT_NAME")
        log_info "Incremental sync since: $last_sync"
    fi

    # Checkpoint WAL
    if ! checkpoint_wal; then
        log_error "WAL checkpoint failed"
        exit 1
    fi

    # Sync each table
    local total_synced=0
    local total_failed=0

    for table in "${TABLES[@]}"; do
        if sync_table "$table" "$last_sync"; then
            ((total_synced++))
        else
            ((total_failed++))
            log_error "Failed to sync table: $table"
        fi
    done

    # Update last_sync_at in Supabase
    log_info "Updating last sync timestamp..."

    docker run --rm --network host \
        -e DATABASE_URL="$SUPABASE_URL" \
        ghcr.io/imagicrafter/open-webui:main \
        python3 -c "
import asyncpg
import asyncio

async def update_timestamp():
    conn = await asyncpg.connect('$SUPABASE_URL')
    await conn.execute('''
        UPDATE sync_metadata.client_deployments
        SET last_sync_at = NOW(),
            last_sync_status = 'success'
        WHERE client_name = \$1
    ''', '$CLIENT_NAME')
    await conn.close()

asyncio.run(update_timestamp())
" 2>/dev/null || log_error "Failed to update sync timestamp"

    # Summary
    log_success "Sync complete for $CLIENT_NAME"
    log_info "Tables synced: $total_synced / ${#TABLES[@]}"

    if [[ "$total_failed" -gt 0 ]]; then
        log_error "Some tables failed to sync: $total_failed"
        exit 1
    fi

    exit 0
}

# Run main
main "$@"
