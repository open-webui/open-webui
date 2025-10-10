#!/bin/bash
# SQLite + Supabase Sync System - Deployment Script
# Phase 1: Deploy HA Sync Cluster

set -euo pipefail

# ============================================================================
# BANNER
# ============================================================================

cat << 'EOF'
╔════════════════════════════════════════╗
║    Deploy Sync Cluster (HA Mode)      ║
║    Phase 1: High Availability         ║
╚════════════════════════════════════════╝
EOF

echo ""

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYNC_DIR="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$SYNC_DIR/docker"
CONFIG_DIR="$SYNC_DIR/config"

# Check if running from correct directory
if [[ ! -f "$DOCKER_DIR/docker-compose.sync-ha.yml" ]]; then
    echo "❌ Error: docker-compose.sync-ha.yml not found"
    echo "Please run this script from the mt/SYNC directory"
    exit 1
fi

# ============================================================================
# COLLECT CONFIGURATION
# ============================================================================

echo "🔧 Supabase Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Get Supabase project details
read -rp "Supabase Project Reference (e.g., dgjvrkoxxmbndvtxvqjv): " PROJECT_REF

if [[ -z "$PROJECT_REF" ]]; then
    echo "❌ Error: Project reference is required"
    exit 1
fi

read -rsp "Supabase Admin Password: " ADMIN_PASSWORD
echo ""

if [[ -z "$ADMIN_PASSWORD" ]]; then
    echo "❌ Error: Admin password is required"
    exit 1
fi

read -rp "Supabase Region (e.g., aws-1-us-east-2): " REGION

if [[ -z "$REGION" ]]; then
    echo "❌ Error: Region is required"
    exit 1
fi

echo ""
echo "🖥️  Host Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -rp "Host Name (default: $(hostname)): " HOST_NAME
HOST_NAME="${HOST_NAME:-$(hostname)}"

echo ""

# ============================================================================
# GENERATE CREDENTIALS
# ============================================================================

echo "🔐 Generating secure credentials..."
echo ""

# Generate sync_service password (32 random bytes, base64 encoded)
SYNC_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')
echo "✅ Generated sync_service password"

# Build database URLs
ADMIN_URL="postgresql://postgres.${PROJECT_REF}:${ADMIN_PASSWORD}@${REGION}.pooler.supabase.com:5432/postgres"
SYNC_URL="postgresql://sync_service:${SYNC_PASSWORD}@${REGION}.pooler.supabase.com:5432/postgres"

# ============================================================================
# UPDATE SYNC_SERVICE PASSWORD
# ============================================================================

echo ""
echo "🔑 Updating sync_service role password in Supabase..."
echo ""

# Create temporary Python script to update password
cat > /tmp/update_sync_password.py << 'PYEOF'
import asyncpg
import asyncio
import sys

async def update_password():
    try:
        admin_url = sys.argv[1]
        new_password = sys.argv[2]

        conn = await asyncpg.connect(admin_url, timeout=10)

        # Update password
        await conn.execute(
            "ALTER ROLE sync_service WITH ENCRYPTED PASSWORD $1",
            new_password
        )

        await conn.close()
        print("✅ sync_service password updated successfully")
        return True

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return False

sys.exit(0 if asyncio.run(update_password()) else 1)
PYEOF

# Run password update
if python3 /tmp/update_sync_password.py "$ADMIN_URL" "$SYNC_PASSWORD"; then
    echo ""
else
    echo "❌ Failed to update sync_service password"
    rm -f /tmp/update_sync_password.py
    exit 1
fi

rm -f /tmp/update_sync_password.py

# ============================================================================
# CREATE ENVIRONMENT FILE
# ============================================================================

echo "📝 Creating environment file..."
echo ""

ENV_FILE="$DOCKER_DIR/.env"

cat > "$ENV_FILE" << EOF
# SQLite + Supabase Sync System - Environment Configuration
# Generated: $(date)

# Supabase Connection (using sync_service role)
SUPABASE_URL=$SYNC_URL

# Host Configuration
HOST_NAME=$HOST_NAME

# Sync Settings
CACHE_TTL=300
HEARTBEAT_INTERVAL=30
LEASE_DURATION=60
LOG_LEVEL=INFO
LOG_FORMAT=json
BATCH_SIZE=1000

# Monitoring
ENABLE_METRICS=true
EOF

chmod 600 "$ENV_FILE"
echo "✅ Environment file created: $ENV_FILE"

# ============================================================================
# BUILD DOCKER IMAGE
# ============================================================================

echo ""
echo "🐳 Building Docker image..."
echo ""

cd "$SYNC_DIR"

if docker build -t ghcr.io/imagicrafter/openwebui-sync:latest -f docker/Dockerfile .; then
    echo "✅ Docker image built successfully"
else
    echo "❌ Docker build failed"
    exit 1
fi

# ============================================================================
# DEPLOY HA CLUSTER
# ============================================================================

echo ""
echo "🚀 Deploying HA sync cluster..."
echo ""

cd "$DOCKER_DIR"

# Stop any existing containers
if docker-compose -f docker-compose.sync-ha.yml ps -q 2>/dev/null | grep -q .; then
    echo "⚠️  Stopping existing sync cluster..."
    docker-compose -f docker-compose.sync-ha.yml down
fi

# Start new cluster
if docker-compose -f docker-compose.sync-ha.yml up -d; then
    echo "✅ Sync cluster started"
else
    echo "❌ Failed to start sync cluster"
    exit 1
fi

# ============================================================================
# WAIT FOR LEADER ELECTION
# ============================================================================

echo ""
echo "⏳ Waiting for leader election (15 seconds)..."
sleep 15

# ============================================================================
# VERIFY CLUSTER HEALTH
# ============================================================================

echo ""
echo "🏥 Verifying cluster health..."
echo ""

# Check primary
echo -n "  Primary (port 9443)... "
if curl -sf http://localhost:9443/health > /dev/null 2>&1; then
    echo "✅"
    PRIMARY_HEALTH=$(curl -s http://localhost:9443/health | jq -r '.is_leader')
else
    echo "❌"
    PRIMARY_HEALTH="false"
fi

# Check secondary
echo -n "  Secondary (port 9444)... "
if curl -sf http://localhost:9444/health > /dev/null 2>&1; then
    echo "✅"
    SECONDARY_HEALTH=$(curl -s http://localhost:9444/health | jq -r '.is_leader')
else
    echo "❌"
    SECONDARY_HEALTH="false"
fi

# ============================================================================
# DISPLAY CLUSTER STATUS
# ============================================================================

echo ""
echo "╔════════════════════════════════════════╗"
echo "║   HA Sync Cluster Deployed             ║"
echo "╚════════════════════════════════════════╝"
echo ""

echo "📊 Cluster Status:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

PRIMARY_STATUS=$(curl -s http://localhost:9443/health 2>/dev/null || echo '{"status":"unavailable"}')
SECONDARY_STATUS=$(curl -s http://localhost:9444/health 2>/dev/null || echo '{"status":"unavailable"}')

echo "Primary Container:"
echo "  URL:        http://localhost:9443"
echo "  Status:     $(echo "$PRIMARY_STATUS" | jq -r '.status')"
echo "  Is Leader:  $(echo "$PRIMARY_STATUS" | jq -r '.is_leader')"
echo "  Node ID:    $(echo "$PRIMARY_STATUS" | jq -r '.node_id')"
echo ""

echo "Secondary Container:"
echo "  URL:        http://localhost:9444"
echo "  Status:     $(echo "$SECONDARY_STATUS" | jq -r '.status')"
echo "  Is Leader:  $(echo "$SECONDARY_STATUS" | jq -r '.is_leader')"
echo "  Node ID:    $(echo "$SECONDARY_STATUS" | jq -r '.node_id')"
echo ""

echo "📈 Monitoring:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Metrics:    http://localhost:9443/metrics"
echo "  Logs:       docker-compose -f $DOCKER_DIR/docker-compose.sync-ha.yml logs -f"
echo ""

echo "📚 Useful Commands:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  View status:   curl http://localhost:9443/health | jq"
echo "  View logs:     docker-compose -f $DOCKER_DIR/docker-compose.sync-ha.yml logs -f"
echo "  Restart:       docker-compose -f $DOCKER_DIR/docker-compose.sync-ha.yml restart"
echo "  Stop:          docker-compose -f $DOCKER_DIR/docker-compose.sync-ha.yml down"
echo ""

# ============================================================================
# SAVE CREDENTIALS (SECURELY)
# ============================================================================

CREDS_FILE="$SYNC_DIR/.credentials"

cat > "$CREDS_FILE" << EOF
# SQLite + Supabase Sync System - Credentials
# Generated: $(date)
# KEEP THIS FILE SECURE - DO NOT COMMIT TO VERSION CONTROL

SUPABASE_PROJECT_REF=$PROJECT_REF
SUPABASE_REGION=$REGION
SYNC_SERVICE_PASSWORD=$SYNC_PASSWORD

# Connection URLs
ADMIN_URL=$ADMIN_URL
SYNC_URL=$SYNC_URL

# To use these credentials:
# source .credentials
# export SUPABASE_URL="\$SYNC_URL"
EOF

chmod 600 "$CREDS_FILE"

echo "🔐 Credentials saved securely to: $CREDS_FILE"
echo ""
echo "⚠️  IMPORTANT: Keep .credentials file secure and do not commit to git"
echo ""

# ============================================================================
# SUCCESS
# ============================================================================

echo "✅ Deployment complete!"
echo ""
