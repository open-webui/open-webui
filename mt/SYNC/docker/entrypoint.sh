#!/bin/bash
# SQLite + Supabase Sync System - Container Entrypoint
# Phase 1: High Availability Sync Container

set -euo pipefail

# ============================================================================
# ENVIRONMENT VALIDATION
# ============================================================================

echo "========================================"
echo "  Open WebUI Sync Container"
echo "========================================"
echo ""

# Required environment variables
: "${DATABASE_URL:?ERROR: DATABASE_URL not set}"
: "${ROLE:?ERROR: ROLE not set (must be 'primary' or 'secondary')}"
: "${CLUSTER_NAME:?ERROR: CLUSTER_NAME not set}"

# Validate ROLE
if [[ "$ROLE" != "primary" && "$ROLE" != "secondary" && "$ROLE" != "node-a" && "$ROLE" != "node-b" ]]; then
    echo "❌ ERROR: ROLE must be 'primary', 'secondary', 'node-a', or 'node-b', got: $ROLE"
    exit 1
fi

# Optional environment variables with defaults
export HOST_ID="${HOST_ID:-$(uuidgen)}"
export API_PORT="${API_PORT:-9443}"
export CACHE_TTL="${CACHE_TTL:-300}"
export HEARTBEAT_INTERVAL="${HEARTBEAT_INTERVAL:-30}"
export LEASE_DURATION="${LEASE_DURATION:-60}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"
export LOG_FORMAT="${LOG_FORMAT:-text}"

# ============================================================================
# DISPLAY CONFIGURATION
# ============================================================================

echo "Configuration:"
echo "  Role:              $ROLE"
echo "  Cluster:           $CLUSTER_NAME"
echo "  Host ID:           $HOST_ID"
echo "  API Port:          $API_PORT"
echo "  Cache TTL:         ${CACHE_TTL}s"
echo "  Heartbeat:         ${HEARTBEAT_INTERVAL}s"
echo "  Lease Duration:    ${LEASE_DURATION}s"
echo "  Log Level:         $LOG_LEVEL"
echo ""

# ============================================================================
# PRE-FLIGHT CHECKS
# ============================================================================

echo "Running pre-flight checks..."

# Test database connection
echo -n "  - Testing database connection... "
if python3 -c "
import asyncpg
import asyncio
import sys

async def test_connection():
    try:
        conn = await asyncpg.connect('$DATABASE_URL', timeout=10)
        await conn.close()
        return True
    except Exception as e:
        print(f'\\nERROR: {e}', file=sys.stderr)
        return False

sys.exit(0 if asyncio.run(test_connection()) else 1)
" 2>&1; then
    echo "✅"
else
    echo "❌"
    echo "ERROR: Cannot connect to database"
    exit 1
fi

# Check if sync_metadata schema exists
echo -n "  - Checking sync_metadata schema... "
if python3 -c "
import asyncpg
import asyncio
import sys

async def check_schema():
    try:
        conn = await asyncpg.connect('$DATABASE_URL', timeout=10)
        result = await conn.fetchval('''
            SELECT EXISTS (
                SELECT 1 FROM information_schema.schemata
                WHERE schema_name = 'sync_metadata'
            )
        ''')
        await conn.close()
        return result
    except Exception as e:
        print(f'\\nERROR: {e}', file=sys.stderr)
        return False

sys.exit(0 if asyncio.run(check_schema()) else 1)
" 2>&1; then
    echo "✅"
else
    echo "❌"
    echo "ERROR: sync_metadata schema not found. Please run database initialization scripts."
    exit 1
fi

# Check conflict resolution config
echo -n "  - Checking configuration files... "
if [[ -f "/app/config/conflict-resolution-default.json" ]]; then
    echo "✅"
else
    echo "⚠️  Warning: conflict-resolution-default.json not found"
fi

echo ""
echo "✅ Pre-flight checks passed"
echo ""

# ============================================================================
# START APPLICATION
# ============================================================================

echo "Starting sync service..."
echo "Node ID: ${CLUSTER_NAME}-${ROLE}"
echo ""

cd /app/python

# Start FastAPI application
exec python3 -m uvicorn main:app \
    --host 0.0.0.0 \
    --port "$API_PORT" \
    --log-level "$(echo "$LOG_LEVEL" | tr '[:upper:]' '[:lower:]')"
