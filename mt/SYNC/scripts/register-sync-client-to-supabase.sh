#!/bin/bash
# SQLite + Supabase Sync System - Sync Registration Script
# Registers an Open WebUI container's SQLite database for automated syncing
#
# This script ONLY registers the sync - the sync cluster handles actual syncing.
#
# Usage: ./register-sync-client-to-supabase.sh CLIENT_NAME [CONTAINER_NAME] [SQLITE_PATH]
#
# What this script does:
# 1. Validates sync cluster health on local host
# 2. Calls register-client.sh to create schema and tables
# 3. Enables sync in client_deployments metadata
# 4. Validates registration was successful
#
# What this script does NOT do:
# - Does NOT perform actual data syncing (sync cluster handles that)
# - Does NOT modify client container or SQLite database
#
# Prerequisites:
# - Sync cluster deployed and running on same host
# - Client container exists and is running
# - .credentials file exists with ADMIN_URL and SYNC_URL

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

CLIENT_NAME="${1:-}"
CONTAINER_NAME="${2:-openwebui-${CLIENT_NAME}}"
SQLITE_PATH="${3:-/app/backend/data/webui.db}"

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
    echo "Usage: $0 CLIENT_NAME [CONTAINER_NAME] [SQLITE_PATH]"
    echo ""
    echo "Examples:"
    echo "  $0 chat"
    echo "  $0 acme-corp openwebui-acme-corp"
    echo "  $0 beta-client openwebui-beta-client /custom/path/webui.db"
    exit 1
fi

# Validate client name format (alphanumeric, hyphens, underscores only)
if ! [[ "$CLIENT_NAME" =~ ^[a-zA-Z0-9_-]+$ ]]; then
    echo -e "${RED}❌ Error: CLIENT_NAME must contain only alphanumeric characters, hyphens, and underscores${NC}"
    exit 1
fi

# Load credentials
CREDENTIALS_FILE="$SYNC_DIR/.credentials"
if [[ ! -f "$CREDENTIALS_FILE" ]]; then
    echo -e "${RED}❌ Error: Credentials file not found: $CREDENTIALS_FILE${NC}"
    echo "Run deploy-sync-cluster.sh first to create credentials"
    exit 1
fi

source "$CREDENTIALS_FILE"

if [[ -z "${ADMIN_URL:-}" ]]; then
    echo -e "${RED}❌ Error: ADMIN_URL not found in credentials file${NC}"
    exit 1
fi

if [[ -z "${SYNC_URL:-}" ]]; then
    echo -e "${RED}❌ Error: SYNC_URL not found in credentials file${NC}"
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

# Check sync cluster health
check_sync_cluster_health() {
    log_info "Checking sync cluster health..."

    local node_a_healthy=false
    local node_b_healthy=false

    # Check node-a
    if docker ps --format '{{.Names}}' | grep -q "^openwebui-sync-node-a$"; then
        if docker exec openwebui-sync-node-a curl -sf http://localhost:9443/health > /dev/null 2>&1; then
            node_a_healthy=true
            log_success "Sync cluster node-a is healthy"
        else
            log_warning "Sync cluster node-a is running but not responding to health checks"
        fi
    else
        log_error "Sync cluster node-a is not running"
    fi

    # Check node-b
    if docker ps --format '{{.Names}}' | grep -q "^openwebui-sync-node-b$"; then
        if docker exec openwebui-sync-node-b curl -sf http://localhost:9443/health > /dev/null 2>&1; then
            node_b_healthy=true
            log_success "Sync cluster node-b is healthy"
        else
            log_warning "Sync cluster node-b is running but not responding to health checks"
        fi
    else
        log_warning "Sync cluster node-b is not running (optional for single-node setup)"
    fi

    # At least one node must be healthy
    if [[ "$node_a_healthy" == false ]] && [[ "$node_b_healthy" == false ]]; then
        log_error "No healthy sync cluster nodes found"
        log_info "Deploy sync cluster first: cd $SYNC_DIR && ./scripts/deploy-sync-cluster.sh"
        return 1
    fi

    return 0
}

# Check if client container exists and is running
check_client_container() {
    log_info "Checking client container: $CONTAINER_NAME"

    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        log_success "Client container is running"
        return 0
    else
        log_error "Client container is not running: $CONTAINER_NAME"
        log_info "Start the container first: docker start $CONTAINER_NAME"
        return 1
    fi
}

# Validate SQLite database exists in container
check_sqlite_database() {
    log_info "Checking SQLite database in container..."

    if docker exec "$CONTAINER_NAME" test -f "$SQLITE_PATH" 2>/dev/null; then
        log_success "SQLite database found: $SQLITE_PATH"
        return 0
    else
        log_error "SQLite database not found: $SQLITE_PATH"
        return 1
    fi
}

# Check if client is already registered
check_existing_registration() {
    log_info "Checking for existing registration..."

    local is_registered
    is_registered=$(docker exec -i -e ADMIN_URL="$ADMIN_URL" -e CLIENT_NAME="$CLIENT_NAME" openwebui-sync-node-a python3 << 'PYEOF'
import asyncpg
import asyncio
import os

async def check_registration():
    admin_url = os.getenv('ADMIN_URL')
    client_name = os.getenv('CLIENT_NAME')
    if not admin_url or not client_name:
        return
    conn = await asyncpg.connect(admin_url)
    exists = await conn.fetchval('''
        SELECT EXISTS(
            SELECT 1 FROM sync_metadata.client_deployments
            WHERE client_name = $1
        )
    ''', client_name)
    await conn.close()
    print('true' if exists else 'false')

asyncio.run(check_registration())
PYEOF
)

    if [[ "$is_registered" == "true" ]]; then
        log_warning "Client '$CLIENT_NAME' is already registered"
        echo ""
        read -p "Do you want to re-register (update configuration)? [y/N] " confirm
        if [[ "$confirm" != "y" ]] && [[ "$confirm" != "Y" ]]; then
            log_info "Registration cancelled"
            return 1
        fi
        log_info "Proceeding with re-registration..."
    fi

    return 0
}

# Verify sync is enabled after registration
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
        SELECT sync_enabled, sync_interval, last_sync_status, status
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
    sync_enabled=$(echo "$sync_status" | python3 -c "import sys, json; print(json.load(sys.stdin)['sync_enabled'])")

    if [[ "$sync_enabled" == "True" ]]; then
        log_success "Sync is enabled for client: $CLIENT_NAME"

        # Display sync configuration
        echo ""
        echo -e "${BLUE}Sync Configuration:${NC}"
        echo "$sync_status" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"  Sync Enabled: {data['sync_enabled']}\")
print(f\"  Sync Interval: {data['sync_interval']} seconds\")
print(f\"  Status: {data['status']}\")
print(f\"  Last Sync Status: {data['last_sync_status']}\")
"
        return 0
    else
        log_error "Sync is not enabled"
        return 1
    fi
}

# ============================================================================
# MAIN REGISTRATION LOGIC
# ============================================================================

main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}SQLite Sync Registration${NC}"
    echo -e "${BLUE}========================================${NC}"
    log_info "Client: $CLIENT_NAME"
    log_info "Container: $CONTAINER_NAME"
    log_info "SQLite Path: $SQLITE_PATH"
    echo ""

    # Step 1: Check sync cluster health
    if ! check_sync_cluster_health; then
        log_error "Sync cluster is not healthy - cannot register sync"
        exit 1
    fi
    echo ""

    # Step 2: Check client container
    if ! check_client_container; then
        log_error "Client container is not available - cannot register sync"
        exit 1
    fi
    echo ""

    # Step 3: Check SQLite database
    if ! check_sqlite_database; then
        log_error "SQLite database is not accessible - cannot register sync"
        exit 1
    fi
    echo ""

    # Step 4: Check for existing registration
    if ! check_existing_registration; then
        exit 0
    fi
    echo ""

    # Step 5: Register client (creates schema, tables, and metadata)
    log_info "Registering client in sync system..."
    log_info "This will create Supabase schema and tables if they don't exist..."
    echo ""

    if "$SCRIPT_DIR/register-client.sh" "$CLIENT_NAME" "$CONTAINER_NAME" "$SQLITE_PATH"; then
        log_success "Client registration complete"
    else
        log_error "Failed to register client"
        exit 1
    fi
    echo ""

    # Step 6: Verify sync is enabled
    if ! verify_sync_enabled; then
        log_error "Sync verification failed"
        exit 1
    fi
    echo ""

    # Summary
    echo -e "${BLUE}========================================${NC}"
    echo -e "${GREEN}✅ Sync Registration Complete${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo -e "${GREEN}What happens next:${NC}"
    echo "  1. The sync cluster will automatically detect the new client"
    echo "  2. Periodic syncing will begin according to the configured interval"
    echo "  3. SQLite changes will be synced to Supabase schema: $CLIENT_NAME"
    echo ""
    echo -e "${BLUE}Monitoring sync activity:${NC}"
    echo "  - View sync cluster logs:"
    echo "    docker logs -f openwebui-sync-node-a"
    echo ""
    echo "  - Check sync status:"
    echo "    docker exec -i openwebui-sync-node-a python3 << 'PYEOF'"
    echo "import asyncpg, asyncio, os"
    echo "async def check():"
    echo "    conn = await asyncpg.connect(os.getenv('ADMIN_URL'))"
    echo "    row = await conn.fetchrow('''SELECT last_sync_at, last_sync_status"
    echo "        FROM sync_metadata.client_deployments WHERE client_name = \\$1''', '$CLIENT_NAME')"
    echo "    print(f'Last sync: {row[\"last_sync_at\"]} - Status: {row[\"last_sync_status\"]}')"
    echo "    await conn.close()"
    echo "asyncio.run(check())"
    echo "PYEOF"
    echo ""
    echo -e "${YELLOW}To deregister this client:${NC}"
    echo "  ./scripts/deregister-sync-client.sh $CLIENT_NAME"
    echo ""
}

# Run main
main "$@"
