#!/bin/bash
# SQLite + Supabase Sync System - Pause Sync
# Temporarily stops automated syncing for a client
#
# This script disables sync WITHOUT deleting the schema, data, or registration.
# To re-enable sync, use start-sync.sh.
# To completely remove the client, use deregister-client.sh.
#
# Usage: ./pause-sync.sh CLIENT_NAME
#
# What this script does:
# 1. Disables sync in client_deployments metadata
# 2. Sets status to 'paused' so sync cluster ignores this client
#
# What this script does NOT do:
# - Does NOT delete the client schema in Supabase (data preserved)
# - Does NOT delete client registration (use deregister-client.sh for that)
# - Does NOT stop or remove the client container
# - Does NOT delete SQLite database
#
# Prerequisites:
# - Sync cluster deployed and running
# - Client is currently registered

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

CLIENT_NAME="${1:-}"

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
    echo "Note: This only PAUSES sync. Data and registration are preserved."
    echo "To completely remove the client:"
    echo "  ./scripts/deregister-client.sh $CLIENT_NAME [--drop-schema]"
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

# Check if client is registered
check_client_exists() {
    log_info "Checking if client is registered..."

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
        SELECT sync_enabled, status, last_sync_at, last_sync_status
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
        log_warning "Client '$CLIENT_NAME' is not registered in sync system"
        log_info "Nothing to pause"
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
print(f\"  Last Sync: {data['last_sync_at']}\")
print(f\"  Last Sync Status: {data['last_sync_status']}\")
"
    echo ""

    # Check if already paused
    local sync_enabled
    sync_enabled=$(echo "$client_info" | python3 -c "import sys, json; print(json.load(sys.stdin)['sync_enabled'])")

    if [[ "$sync_enabled" == "False" ]]; then
        log_warning "Sync is already disabled for client: $CLIENT_NAME"
        return 2  # Special code for already disabled
    fi

    return 0
}

# Disable sync for client
disable_sync() {
    log_info "Pausing sync for client: $CLIENT_NAME"

    local result
    result=$(docker exec -i -e ADMIN_URL="$ADMIN_URL" -e CLIENT_NAME="$CLIENT_NAME" openwebui-sync-node-a python3 << 'PYEOF'
import asyncpg
import asyncio
import os

async def disable_sync():
    admin_url = os.getenv('ADMIN_URL')
    client_name = os.getenv('CLIENT_NAME')
    if not admin_url or not client_name:
        return False

    try:
        conn = await asyncpg.connect(admin_url)
        await conn.execute('''
            UPDATE sync_metadata.client_deployments
            SET sync_enabled = false,
                status = 'paused',
                updated_at = NOW()
            WHERE client_name = $1
        ''', client_name)
        await conn.close()
        print('success')
        return True
    except Exception as e:
        print(f'error: {e}')
        return False

asyncio.run(disable_sync())
PYEOF
)

    if [[ "$result" == "success" ]]; then
        log_success "Sync paused for client: $CLIENT_NAME"
        return 0
    else
        log_error "Failed to pause sync: $result"
        return 1
    fi
}

# Verify sync is disabled
verify_sync_disabled() {
    log_info "Verifying sync is paused..."

    local sync_enabled
    sync_enabled=$(docker exec -i -e ADMIN_URL="$ADMIN_URL" -e CLIENT_NAME="$CLIENT_NAME" openwebui-sync-node-a python3 << 'PYEOF'
import asyncpg
import asyncio
import os

async def check_sync():
    admin_url = os.getenv('ADMIN_URL')
    client_name = os.getenv('CLIENT_NAME')
    if not admin_url or not client_name:
        return
    conn = await asyncpg.connect(admin_url)
    enabled = await conn.fetchval('''
        SELECT sync_enabled
        FROM sync_metadata.client_deployments
        WHERE client_name = $1
    ''', client_name)
    await conn.close()
    print('true' if enabled else 'false')

asyncio.run(check_sync())
PYEOF
)

    if [[ "$sync_enabled" == "false" ]]; then
        log_success "Sync is paused"
        return 0
    else
        log_error "Sync is still enabled"
        return 1
    fi
}

# ============================================================================
# MAIN LOGIC
# ============================================================================

main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Pause Client Sync${NC}"
    echo -e "${BLUE}========================================${NC}"
    log_info "Client: $CLIENT_NAME"
    echo ""

    # Step 1: Check sync cluster
    if ! check_sync_cluster; then
        log_error "Sync cluster is not running"
        exit 1
    fi
    echo ""

    # Step 2: Check if client exists
    check_client_exists
    local status_code=$?

    if [[ $status_code -eq 1 ]]; then
        # Client not registered
        exit 0
    elif [[ $status_code -eq 2 ]]; then
        # Already disabled
        log_info "No action needed"
        exit 0
    fi

    # Step 3: Pause sync
    if ! disable_sync; then
        log_error "Failed to pause sync"
        exit 1
    fi
    echo ""

    # Step 4: Verify sync is disabled
    if ! verify_sync_disabled; then
        log_error "Verification failed"
        exit 1
    fi
    echo ""

    # Summary
    echo -e "${BLUE}========================================${NC}"
    echo -e "${GREEN}✅ Sync Paused Successfully${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo -e "${GREEN}What was done:${NC}"
    echo "  - Sync disabled for client: $CLIENT_NAME"
    echo "  - Sync cluster will no longer sync this client"
    echo ""
    echo -e "${BLUE}What was NOT deleted:${NC}"
    echo "  - Client registration in sync_metadata.client_deployments (status: paused)"
    echo "  - Supabase schema: $CLIENT_NAME (all data preserved)"
    echo "  - Client container (still running if it was before)"
    echo "  - SQLite database in container"
    echo ""
    echo -e "${YELLOW}To resume sync:${NC}"
    echo "  ./scripts/start-sync.sh $CLIENT_NAME"
    echo ""
    echo -e "${YELLOW}To completely remove client and optionally delete data:${NC}"
    echo "  ./scripts/deregister-client.sh $CLIENT_NAME            # Keep data"
    echo "  ./scripts/deregister-client.sh $CLIENT_NAME --drop-schema  # Delete data"
    echo ""
}

# Run main
main "$@"
