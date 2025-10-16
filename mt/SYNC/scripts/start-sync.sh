#!/bin/bash
# SQLite + Supabase Sync System - Start/Resume Sync
# Enables automated syncing for a registered client
#
# This script ONLY enables sync for an already registered client.
# If the client is not registered, use register-sync-client-to-supabase.sh first.
#
# Usage: ./start-sync.sh CLIENT_NAME [SYNC_INTERVAL]
#   CLIENT_NAME: Name of the client to enable sync for
#   SYNC_INTERVAL: (Optional) Sync interval in seconds (e.g., 60, 300, 3600)
#
# What this script does:
# 1. Validates client is registered
# 2. Enables sync in client_deployments metadata
# 3. Sets status to 'active' so sync cluster picks it up
#
# What this script does NOT do:
# - Does NOT register new clients (use register-sync-client-to-supabase.sh)
# - Does NOT perform immediate sync (scheduler handles automatic syncing)
# - Does NOT create schemas or tables
#
# Prerequisites:
# - Sync cluster deployed and running
# - Client already registered (schema and tables created)

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

CLIENT_NAME="${1:-}"
SYNC_INTERVAL="${2:-}"  # Optional: sync interval in seconds

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYNC_DIR="$(dirname "$SCRIPT_DIR")"

# ============================================================================
# VALIDATION
# ============================================================================

if [[ -z "$CLIENT_NAME" ]]; then
    echo -e "${RED}❌ Error: CLIENT_NAME required${NC}"
    echo "Usage: $0 CLIENT_NAME"
    echo ""
    echo "Examples:"
    echo "  $0 chat"
    echo "  $0 acme-corp"
    echo ""
    echo "Note: Client must already be registered. To register a new client:"
    echo "  ./scripts/register-sync-client-to-supabase.sh CLIENT_NAME"
    exit 1
fi

# Load credentials
CREDENTIALS_FILE="$SYNC_DIR/.credentials"
if [[ ! -f "$CREDENTIALS_FILE" ]]; then
    echo -e "${RED}❌ Error: Credentials file not found: $CREDENTIALS_FILE${NC}"
    exit 1
fi

source "$CREDENTIALS_FILE"

if [[ -z "${ADMIN_URL:-}" ]]; then
    echo -e "${RED}❌ Error: ADMIN_URL not found in credentials file${NC}"
    exit 1
fi

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

log_info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✅${NC} $*"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ❌${NC} $*" >&2
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️${NC} $*"
}

# Check if sync cluster is running
check_sync_cluster() {
    if ! docker ps --format '{{.Names}}' | grep -q "^openwebui-sync-node-a$"; then
        log_error "Sync cluster not running (node-a not found)"
        return 1
    fi
    return 0
}

# Check if client is registered and get current status
check_client_status() {
    log_info "Checking client registration status..."

    local client_info
    client_info=$(docker exec -i -e ADMIN_URL="$ADMIN_URL" -e CLIENT_NAME="$CLIENT_NAME" openwebui-sync-node-a python3 << 'PYEOF'
import asyncpg
import asyncio
import os
import json

async def check_client():
    admin_url = os.getenv('ADMIN_URL')
    client_name = os.getenv('CLIENT_NAME')
    if not admin_url or not client_name:
        return
    conn = await asyncpg.connect(admin_url)
    row = await conn.fetchrow('''
        SELECT sync_enabled, status, last_sync_at, last_sync_status, sync_interval
        FROM sync_metadata.client_deployments
        WHERE client_name = $1
    ''', client_name)
    await conn.close()
    if row:
        print(json.dumps(dict(row)))

asyncio.run(check_client())
PYEOF
)

    if [[ -z "$client_info" ]]; then
        log_error "Client '$CLIENT_NAME' is not registered in sync system"
        log_info "Register the client first:"
        log_info "  ./scripts/register-sync-client-to-supabase.sh $CLIENT_NAME"
        return 1
    fi

    # Display current status
    echo ""
    echo -e "${BLUE}Current Sync Status:${NC}"
    echo "$client_info" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"  Sync Enabled: {data['sync_enabled']}\")
print(f\"  Status: {data['status']}\")
print(f\"  Sync Interval: {data['sync_interval']} seconds\")
print(f\"  Last Sync: {data['last_sync_at']}\")
print(f\"  Last Sync Status: {data['last_sync_status']}\")
"
    echo ""

    # Check if already enabled
    local sync_enabled
    sync_enabled=$(echo "$client_info" | python3 -c "import sys, json; print(json.load(sys.stdin)['sync_enabled'])")

    if [[ "$sync_enabled" == "True" ]]; then
        local sync_status
        sync_status=$(echo "$client_info" | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")

        if [[ "$sync_status" == "active" ]]; then
            log_warning "Sync is already enabled and active for client: $CLIENT_NAME"
            return 2  # Special code for already enabled
        fi
    fi

    return 0
}

# Enable sync for client
enable_sync() {
    log_info "Enabling sync for client: $CLIENT_NAME"
    if [[ -n "$SYNC_INTERVAL" ]]; then
        log_info "Setting sync interval to: $SYNC_INTERVAL seconds"
    fi

    local result
    result=$(docker exec -i -e ADMIN_URL="$ADMIN_URL" -e CLIENT_NAME="$CLIENT_NAME" -e SYNC_INTERVAL="$SYNC_INTERVAL" openwebui-sync-node-a python3 << 'PYEOF'
import asyncpg
import asyncio
import os

async def enable_sync():
    admin_url = os.getenv('ADMIN_URL')
    client_name = os.getenv('CLIENT_NAME')
    sync_interval = os.getenv('SYNC_INTERVAL')
    if not admin_url or not client_name:
        return False

    try:
        conn = await asyncpg.connect(admin_url)

        # Build UPDATE query based on whether sync_interval is provided
        if sync_interval and sync_interval.strip():
            await conn.execute('''
                UPDATE sync_metadata.client_deployments
                SET sync_enabled = true,
                    status = 'active',
                    sync_interval = $2,
                    updated_at = NOW()
                WHERE client_name = $1
            ''', client_name, int(sync_interval))
        else:
            # No sync_interval provided, don't modify it
            await conn.execute('''
                UPDATE sync_metadata.client_deployments
                SET sync_enabled = true,
                    status = 'active',
                    updated_at = NOW()
                WHERE client_name = $1
            ''', client_name)

        await conn.close()
        print('success')
        return True
    except Exception as e:
        print(f'error: {e}')
        return False

asyncio.run(enable_sync())
PYEOF
)

    if [[ "$result" == "success" ]]; then
        log_success "Sync enabled for client: $CLIENT_NAME"
        return 0
    else
        log_error "Failed to enable sync: $result"
        return 1
    fi
}

# Verify sync is enabled
verify_sync_enabled() {
    log_info "Verifying sync is enabled..."

    local sync_status
    sync_status=$(docker exec -i -e ADMIN_URL="$ADMIN_URL" -e CLIENT_NAME="$CLIENT_NAME" openwebui-sync-node-a python3 << 'PYEOF'
import asyncpg
import asyncio
import os
import json

async def check_sync():
    admin_url = os.getenv('ADMIN_URL')
    client_name = os.getenv('CLIENT_NAME')
    if not admin_url or not client_name:
        return
    conn = await asyncpg.connect(admin_url)
    row = await conn.fetchrow('''
        SELECT sync_enabled, status
        FROM sync_metadata.client_deployments
        WHERE client_name = $1
    ''', client_name)
    await conn.close()
    if row:
        print(json.dumps(dict(row)))

asyncio.run(check_sync())
PYEOF
)

    if [[ -z "$sync_status" ]]; then
        log_error "Failed to verify sync status"
        return 1
    fi

    local sync_enabled
    local status
    sync_enabled=$(echo "$sync_status" | python3 -c "import sys, json; print(json.load(sys.stdin)['sync_enabled'])")
    status=$(echo "$sync_status" | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")

    if [[ "$sync_enabled" == "True" ]] && [[ "$status" == "active" ]]; then
        log_success "Sync is enabled and active"
        return 0
    else
        log_error "Sync verification failed: enabled=$sync_enabled, status=$status"
        return 1
    fi
}

# ============================================================================
# MAIN LOGIC
# ============================================================================

main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Start/Resume Client Sync${NC}"
    echo -e "${BLUE}========================================${NC}"
    log_info "Client: $CLIENT_NAME"
    echo ""

    # Step 1: Check sync cluster
    if ! check_sync_cluster; then
        log_error "Sync cluster is not running"
        exit 1
    fi
    echo ""

    # Step 2: Check client status
    check_client_status
    local status_code=$?

    if [[ $status_code -eq 1 ]]; then
        # Client not registered
        exit 1
    elif [[ $status_code -eq 2 ]]; then
        # Already enabled
        log_info "No action needed"
        exit 0
    fi

    # Step 3: Enable sync
    if ! enable_sync; then
        log_error "Failed to enable sync"
        exit 1
    fi
    echo ""

    # Step 4: Verify sync is enabled
    if ! verify_sync_enabled; then
        log_error "Verification failed"
        exit 1
    fi
    echo ""

    # Summary
    echo -e "${BLUE}========================================${NC}"
    echo -e "${GREEN}✅ Sync Started Successfully${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo -e "${GREEN}What happens next:${NC}"
    echo "  - The sync cluster will detect the enabled client"
    echo "  - Automatic syncing will begin according to the configured interval"
    echo "  - SQLite changes will be synced to Supabase schema: $CLIENT_NAME"
    echo ""
    echo -e "${BLUE}Monitoring sync activity:${NC}"
    echo "  - View sync cluster logs:"
    echo "    docker logs -f openwebui-sync-node-a"
    echo ""
    echo -e "${YELLOW}To pause sync:${NC}"
    echo "  ./scripts/pause-sync.sh $CLIENT_NAME"
    echo ""
}

# Run main
main "$@"
