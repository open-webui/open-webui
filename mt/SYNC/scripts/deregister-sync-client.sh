#!/bin/bash
# SQLite + Supabase Sync System - Sync Deregistration Script
# Stops automated syncing for an Open WebUI container
#
# This script disables sync in the sync system WITHOUT deleting the schema or data.
# To completely remove the client and its data, use deregister-client.sh instead.
#
# Usage: ./deregister-sync-client.sh CLIENT_NAME
#
# What this script does:
# 1. Disables sync in client_deployments metadata
# 2. Sets status to 'inactive' so sync cluster ignores this client
#
# What this script does NOT do:
# - Does NOT delete the client schema in Supabase (data preserved)
# - Does NOT delete client registration (use deregister-client.sh for that)
# - Does NOT stop or remove the client container
# - Does NOT delete SQLite database
#
# Prerequisites:
# - Sync cluster deployed and running on same host
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
    echo "Note: This only DISABLES sync. To completely remove the client:"
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
        log_info "Nothing to deregister"
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

    return 0
}

# Disable sync for client
disable_sync() {
    log_info "Disabling sync for client: $CLIENT_NAME"

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
                status = 'inactive',
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
        log_success "Sync disabled for client: $CLIENT_NAME"
        return 0
    else
        log_error "Failed to disable sync: $result"
        return 1
    fi
}

# Verify sync is disabled
verify_sync_disabled() {
    log_info "Verifying sync is disabled..."

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
        log_success "Sync is disabled"
        return 0
    else
        log_error "Sync is still enabled"
        return 1
    fi
}

# ============================================================================
# MAIN DEREGISTRATION LOGIC
# ============================================================================

main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}SQLite Sync Deregistration${NC}"
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
    if ! check_client_exists; then
        exit 0
    fi

    # Step 3: Confirm action
    echo -e "${YELLOW}⚠️  This will DISABLE automated syncing for client: $CLIENT_NAME${NC}"
    echo ""
    echo "What will happen:"
    echo "  - Sync will be disabled in sync_metadata.client_deployments"
    echo "  - The sync cluster will stop syncing this client"
    echo "  - Client status will be set to 'inactive'"
    echo ""
    echo "What will NOT happen:"
    echo "  - Supabase schema and data will be PRESERVED"
    echo "  - Client container will NOT be stopped or removed"
    echo "  - SQLite database will NOT be modified"
    echo ""
    read -p "Continue with sync deregistration? [y/N] " confirm

    if [[ "$confirm" != "y" ]] && [[ "$confirm" != "Y" ]]; then
        log_info "Deregistration cancelled"
        exit 0
    fi
    echo ""

    # Step 4: Disable sync
    if ! disable_sync; then
        log_error "Failed to disable sync"
        exit 1
    fi
    echo ""

    # Step 5: Verify sync is disabled
    if ! verify_sync_disabled; then
        log_error "Verification failed"
        exit 1
    fi
    echo ""

    # Summary
    echo -e "${BLUE}========================================${NC}"
    echo -e "${GREEN}✅ Sync Deregistration Complete${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo -e "${GREEN}What was done:${NC}"
    echo "  - Sync disabled for client: $CLIENT_NAME"
    echo "  - Sync cluster will no longer sync this client"
    echo ""
    echo -e "${BLUE}What was NOT deleted:${NC}"
    echo "  - Client registration in sync_metadata.client_deployments (status: inactive)"
    echo "  - Supabase schema: $CLIENT_NAME (all data preserved)"
    echo "  - Client container (still running if it was before)"
    echo "  - SQLite database in container"
    echo ""
    echo -e "${YELLOW}To re-enable sync:${NC}"
    echo "  ./scripts/register-sync-client-to-supabase.sh $CLIENT_NAME"
    echo ""
    echo -e "${YELLOW}To completely remove client and optionally delete data:${NC}"
    echo "  ./scripts/deregister-client.sh $CLIENT_NAME            # Keep data"
    echo "  ./scripts/deregister-client.sh $CLIENT_NAME --drop-schema  # Delete data"
    echo ""
}

# Run main
main "$@"
