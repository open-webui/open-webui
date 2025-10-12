#!/bin/bash
# SQLite + Supabase Sync System - Client Deregistration Script
# Removes client from sync system (does NOT delete data)
#
# Usage: ./deregister-client.sh CLIENT_NAME [--drop-schema]
#
# This script:
# 1. Removes client from sync_metadata.client_deployments
# 2. Optionally drops client schema (with --drop-schema flag)
#
# IMPORTANT: This does NOT delete the client container or SQLite database
# Use with caution - dropping schema will delete all synced data in Supabase

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

CLIENT_NAME="${1:-}"
DROP_SCHEMA="${2:-}"

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
    echo "Usage: $0 CLIENT_NAME [--drop-schema]"
    echo ""
    echo "Examples:"
    echo "  $0 chat                    # Deregister only (keeps schema and data)"
    echo "  $0 chat --drop-schema      # Deregister AND drop schema (deletes data)"
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
# MAIN DEREGISTRATION LOGIC
# ============================================================================

main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Client Deregistration${NC}"
    echo -e "${BLUE}========================================${NC}"
    log_info "Client: $CLIENT_NAME"
    echo ""

    # Check if sync cluster is running
    if ! docker ps --format '{{.Names}}' | grep -q "openwebui-sync-node-a"; then
        log_error "Sync cluster not running (node-a not found)"
        exit 1
    fi

    # Check if client exists
    log_info "Checking if client is registered..."

    CLIENT_EXISTS=$(docker exec -i -e ADMIN_URL="$ADMIN_URL" -e CLIENT_NAME="$CLIENT_NAME" openwebui-sync-node-a python3 << 'PYEOF'
import asyncpg
import asyncio
import os

async def check_client():
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

asyncio.run(check_client())
PYEOF
)

    if [[ "$CLIENT_EXISTS" != "true" ]]; then
        log_warning "Client '$CLIENT_NAME' not found in sync system"
        log_info "Nothing to deregister"
        exit 0
    fi

    # Warn about schema deletion
    if [[ "$DROP_SCHEMA" == "--drop-schema" ]]; then
        echo -e "${RED}⚠️  WARNING: You are about to DROP the schema and DELETE ALL SYNCED DATA${NC}"
        echo -e "${RED}⚠️  This action CANNOT be undone!${NC}"
        echo ""
        echo -e "${YELLOW}Schema to be dropped:${NC} $CLIENT_NAME"
        echo ""
        read -p "Type 'DELETE' to confirm schema deletion: " confirm

        if [[ "$confirm" != "DELETE" ]]; then
            log_info "Deregistration cancelled"
            exit 0
        fi
    fi

    # Step 1: Remove from client_deployments
    log_info "Removing client from sync system..."

    DEREGISTER_SQL="
    DELETE FROM sync_metadata.client_deployments
    WHERE client_name = '${CLIENT_NAME}'
    RETURNING client_name;
    "

    SQL_QUERY="$DEREGISTER_SQL" execute_sql "" 2>/dev/null

    if [ $? -eq 0 ]; then
        log_success "Client deregistered from sync system"
    else
        log_error "Failed to deregister client"
        exit 1
    fi

    # Step 2: Drop schema if requested
    if [[ "$DROP_SCHEMA" == "--drop-schema" ]]; then
        log_warning "Dropping schema: $CLIENT_NAME (this will delete all data)"

        DROP_SQL="DROP SCHEMA IF EXISTS \"${CLIENT_NAME}\" CASCADE;"

        SQL_QUERY="$DROP_SQL" execute_sql "" 2>/dev/null

        if [ $? -eq 0 ]; then
            log_success "Schema dropped: $CLIENT_NAME"
        else
            log_error "Failed to drop schema"
            exit 1
        fi
    fi

    # Summary
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${GREEN}✅ Client Deregistration Complete${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo -e "${GREEN}Client:${NC} $CLIENT_NAME"

    if [[ "$DROP_SCHEMA" == "--drop-schema" ]]; then
        echo -e "${GREEN}Schema:${NC} Dropped (data deleted)"
    else
        echo -e "${GREEN}Schema:${NC} Preserved (data still in Supabase)"
    fi

    echo ""
    echo -e "${BLUE}What was NOT deleted:${NC}"
    echo "  - Client container (if exists)"
    echo "  - SQLite database in container"

    if [[ "$DROP_SCHEMA" != "--drop-schema" ]]; then
        echo "  - Synced data in Supabase (schema still exists)"
        echo ""
        echo -e "${YELLOW}Note:${NC} To completely remove all data, run:"
        echo "  $0 $CLIENT_NAME --drop-schema"
    fi

    echo ""
    echo -e "${BLUE}To re-register this client:${NC}"
    echo "  ./scripts/register-client.sh $CLIENT_NAME"
    echo ""
}

# Run main
main "$@"
