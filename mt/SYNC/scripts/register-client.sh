#!/bin/bash
# SQLite + Supabase Sync System - Client Registration Script
# Automates Steps 1 & 2: Register client and create schema in Supabase
#
# Usage: ./register-client.sh CLIENT_NAME [CONTAINER_NAME] [SQLITE_PATH]
#
# This script:
# 1. Creates client schema in Supabase
# 2. Grants sync_service access to the schema
# 3. Registers client in sync_metadata.client_deployments
# 4. Creates Open WebUI tables in client schema (mirrors SQLite structure)
#
# Prerequisites:
# - Sync cluster deployed and running
# - .credentials file exists with ADMIN_URL

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

# Check if container exists
check_container() {
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        return 0
    else
        log_warning "Container $CONTAINER_NAME not found (will register anyway)"
        return 1
    fi
}

# Execute SQL via Python in sync container
execute_sql() {
    local sql_query="${SQL_QUERY:-}"

    if [[ -z "$sql_query" ]]; then
        log_error "SQL_QUERY environment variable not set"
        return 1
    fi

    docker exec -i -e ADMIN_URL="$ADMIN_URL" -e SQL_QUERY="$sql_query" openwebui-sync-node-a python3 << 'PYEOF'
import asyncpg
import asyncio
import sys
import os

async def run_sql():
    try:
        admin_url = os.getenv('ADMIN_URL')
        sql_query = os.getenv('SQL_QUERY')

        if not admin_url:
            print("Error: ADMIN_URL not set", file=sys.stderr)
            return False

        if not sql_query:
            print("Error: SQL_QUERY not set", file=sys.stderr)
            return False

        conn = await asyncpg.connect(admin_url)
        result = await conn.fetch(sql_query)
        await conn.close()

        if result:
            for row in result:
                print(dict(row))
        return True
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False

success = asyncio.run(run_sql())
sys.exit(0 if success else 1)
PYEOF
}

# ============================================================================
# MAIN REGISTRATION LOGIC
# ============================================================================

main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Client Registration${NC}"
    echo -e "${BLUE}========================================${NC}"
    log_info "Client: $CLIENT_NAME"
    log_info "Container: $CONTAINER_NAME"
    log_info "SQLite Path: $SQLITE_PATH"
    echo ""

    # Step 0: Check prerequisites
    log_info "Checking prerequisites..."

    if ! docker ps --format '{{.Names}}' | grep -q "openwebui-sync-node-a"; then
        log_error "Sync cluster not running (node-a not found)"
        log_info "Deploy sync cluster first: cd mt/SYNC && ./scripts/deploy-sync-cluster.sh"
        exit 1
    fi

    check_container || log_warning "Container will need to be started manually"

    # Step 1: Create client schema (with quotes for names containing hyphens)
    log_info "Creating client schema: ${CLIENT_NAME}..."

    SQL_QUERY="CREATE SCHEMA IF NOT EXISTS \"${CLIENT_NAME}\";" \
    execute_sql "" 2>/dev/null

    if [ $? -eq 0 ]; then
        log_success "Schema created: ${CLIENT_NAME}"
    else
        log_error "Failed to create schema"
        exit 1
    fi

    # Step 2: Grant sync_service access using helper function
    log_info "Granting sync_service access to schema..."

    SQL_QUERY="SELECT sync_metadata.grant_client_access('${CLIENT_NAME}');" \
    execute_sql "" 2>/dev/null

    if [ $? -eq 0 ]; then
        log_success "Access granted to sync_service"
    else
        log_error "Failed to grant access"
        exit 1
    fi

    # Step 3: Create Open WebUI tables in client schema
    log_info "Creating Open WebUI tables in ${CLIENT_NAME} schema..."
    log_info "This will start Open WebUI temporarily to initialize database schema"
    log_info "This process takes about 30-60 seconds..."
    echo ""

    # Build DATABASE_URL for the client schema
    # Format: postgresql://postgres.PROJECT:PASS@REGION.pooler.supabase.com:5432/postgres?options=--search_path%3Dclient_schema

    # URL-encode the schema name (hyphens are safe, no need to encode)
    ENCODED_SCHEMA=$(python3 -c "import urllib.parse; print(urllib.parse.quote('${CLIENT_NAME}', safe=''))")

    # Append search_path to ADMIN_URL using --search_path format (note: double dash)
    if [[ "$ADMIN_URL" == *"?"* ]]; then
        CLIENT_DATABASE_URL="${ADMIN_URL}&options=--search_path%3D${ENCODED_SCHEMA}"
    else
        CLIENT_DATABASE_URL="${ADMIN_URL}?options=--search_path%3D${ENCODED_SCHEMA}"
    fi

    # Generate unique temporary port (10000 + random number to avoid conflicts)
    TEMP_PORT=$((10000 + RANDOM % 10000))
    INIT_CONTAINER="${CLIENT_NAME}-schema-init-$$"

    log_info "Using temporary port: $TEMP_PORT"
    log_info "Starting initialization container..."

    # Remove any leftover container with this name
    docker rm -f "$INIT_CONTAINER" > /dev/null 2>&1

    # Start temporary container with client schema
    # Note: Don't set VECTOR_DB to avoid pgvector errors during schema init
    if ! docker run -d \
        --name "$INIT_CONTAINER" \
        -p "${TEMP_PORT}:8080" \
        -e DATABASE_URL="$CLIENT_DATABASE_URL" \
        ghcr.io/imagicrafter/open-webui:main > /dev/null 2>&1; then
        log_error "Failed to create initialization container"
        exit 1
    fi

    # Wait for schema initialization
    log_info "Waiting for schema initialization..."
    MAX_WAIT=180
    WAITED=0
    INITIALIZED=false

    while [ $WAITED -lt $MAX_WAIT ]; do
        LOGS=$(docker logs "$INIT_CONTAINER" 2>&1)

        # Check for successful migration completion (happens before app startup)
        if echo "$LOGS" | grep -q "Running upgrade.*Add oauth_session table"; then
            # Last migration has run - schema is initialized
            log_info "Database migrations completed"
            sleep 2  # Give it a moment to finish
            INITIALIZED=true
            break
        fi

        # Check for successful startup indicators (backup checks)
        if echo "$LOGS" | grep -q "Application startup complete"; then
            INITIALIZED=true
            break
        fi

        if echo "$LOGS" | grep -q "Uvicorn running on"; then
            INITIALIZED=true
            break
        fi

        if echo "$LOGS" | grep -q "Started server process"; then
            INITIALIZED=true
            break
        fi

        # Check for fatal errors
        if echo "$LOGS" | grep -qi "fatal\|critical\|cannot connect"; then
            log_error "Fatal error during initialization"
            echo "Last logs:"
            docker logs --tail 20 "$INIT_CONTAINER"
            break
        fi

        echo -n "."
        sleep 3
        WAITED=$((WAITED + 3))
    done

    echo ""

    # Cleanup initialization container
    log_info "Cleaning up initialization container..."
    docker stop "$INIT_CONTAINER" > /dev/null 2>&1
    docker rm "$INIT_CONTAINER" > /dev/null 2>&1

    if [ "$INITIALIZED" = true ]; then
        log_success "Created Open WebUI tables using schema initialization"
    else
        log_error "Schema initialization timed out or failed"
        exit 1
    fi

    # Step 4: Register client in sync_metadata.client_deployments
    log_info "Registering client in sync metadata..."

    # Get host_id from sync cluster
    # Try to find a host matching the container name pattern, or use most recent
    HOST_ID=$(docker exec -i -e ADMIN_URL="$ADMIN_URL" openwebui-sync-node-a python3 << 'PYEOF'
import asyncpg
import asyncio
import os

async def get_host_id():
    admin_url = os.getenv('ADMIN_URL')
    if not admin_url:
        return
    conn = await asyncpg.connect(admin_url)

    # Try to find a host with "node-a" in the name
    host_id = await conn.fetchval('''
        SELECT host_id FROM sync_metadata.hosts
        WHERE hostname LIKE '%node-a%' OR hostname LIKE '%node_a%'
        ORDER BY last_heartbeat DESC
        LIMIT 1
    ''')

    # If no match, use the most recent heartbeat from any host
    if not host_id:
        host_id = await conn.fetchval('''
            SELECT host_id FROM sync_metadata.hosts
            ORDER BY last_heartbeat DESC
            LIMIT 1
        ''')

    await conn.close()
    if host_id:
        print(str(host_id))

asyncio.run(get_host_id())
PYEOF
)

    if [[ -z "$HOST_ID" ]]; then
        log_error "Could not find host_id for sync cluster"
        log_info "Make sure sync cluster is running and healthy"
        exit 1
    fi

    log_info "Using host_id: $HOST_ID"

    REGISTER_SQL="
    INSERT INTO sync_metadata.client_deployments
    (deployment_id, client_name, host_id, sqlite_path, sync_enabled, sync_interval, last_sync_status)
    VALUES
    (gen_random_uuid(), '${CLIENT_NAME}', '${HOST_ID}'::uuid, '${SQLITE_PATH}', true, 300, 'pending')
    ON CONFLICT (client_name) DO UPDATE
    SET
        host_id = EXCLUDED.host_id,
        sqlite_path = EXCLUDED.sqlite_path,
        sync_enabled = true,
        updated_at = NOW()
    RETURNING deployment_id, client_name, sync_enabled;
    "

    SQL_QUERY="$REGISTER_SQL" execute_sql "" 2>/dev/null

    if [ $? -eq 0 ]; then
        log_success "Client registered in sync system"
    else
        log_error "Failed to register client"
        exit 1
    fi

    # Summary
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${GREEN}✅ Client Registration Complete${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo -e "${GREEN}Schema:${NC} ${CLIENT_NAME}"
    echo -e "${GREEN}Container:${NC} ${CONTAINER_NAME}"
    echo -e "${GREEN}Tables:${NC} Open WebUI schema initialized"
    echo -e "${GREEN}Sync:${NC} Enabled (300s interval)"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo ""
    echo "1. Verify client container is running:"
    echo "   docker ps | grep $CONTAINER_NAME"
    echo ""
    echo "2. Run initial sync:"
    echo "   cd mt/SYNC"
    echo "   source .credentials"
    echo "   export DATABASE_URL=\"\$SYNC_URL\""
    echo "   ./scripts/sync-client-to-supabase.sh $CLIENT_NAME --full"
    echo ""
    echo "3. Verify data in Supabase:"
    echo "   docker exec -i openwebui-sync-node-a python3 << 'PYEOF'"
    echo "import asyncpg, asyncio, os"
    echo "async def check():"
    echo "    conn = await asyncpg.connect(os.getenv('ADMIN_URL'))"
    echo "    for table in ['user', 'chat', 'message']:"
    echo "        count = await conn.fetchval(f'SELECT COUNT(*) FROM ${CLIENT_NAME}.\"{table}\"')"
    echo "        print(f'{table}: {count} rows')"
    echo "    await conn.close()"
    echo "asyncio.run(check())"
    echo "PYEOF"
    echo ""
    echo -e "${YELLOW}Note:${NC} To deregister this client, run:"
    echo "   ./scripts/deregister-client.sh $CLIENT_NAME"
    echo ""
}

# Run main
main "$@"
