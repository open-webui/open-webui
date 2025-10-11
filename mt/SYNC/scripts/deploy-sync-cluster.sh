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
# IPv6 DETECTION AND CONFIGURATION
# ============================================================================

echo "🌐 IPv6 Network Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Detect cloud provider
detect_cloud_provider() {
    if curl -sf -m 2 http://169.254.169.254/metadata/v1/id > /dev/null 2>&1; then
        echo "digitalocean"
    elif curl -sf -m 2 http://169.254.169.254/latest/meta-data/instance-id > /dev/null 2>&1; then
        echo "aws"
    else
        echo "unknown"
    fi
}

CLOUD_PROVIDER=$(detect_cloud_provider)
echo "Detected cloud provider: $CLOUD_PROVIDER"

# Check and configure IPv6
setup_ipv6() {
    echo ""
    echo "Checking IPv6 availability..."

    # Check if IPv6 is already configured
    if ip -6 addr show 2>/dev/null | grep -q "scope global"; then
        IPV6_CONFIGURED=true
        IPV6_ADDR=$(ip -6 addr show | grep "scope global" | head -1 | awk '{print $2}' | cut -d/ -f1)
        echo "✅ IPv6 already configured: $IPV6_ADDR"
    else
        IPV6_CONFIGURED=false
        echo "⚠️  IPv6 not currently configured"
    fi

    # Try to get IPv6 info from cloud metadata
    if [ "$CLOUD_PROVIDER" = "digitalocean" ]; then
        echo "Querying Digital Ocean metadata for IPv6..."
        IPV6_ADDR=$(curl -sf http://169.254.169.254/metadata/v1/interfaces/public/0/ipv6/address 2>/dev/null)
        IPV6_CIDR=$(curl -sf http://169.254.169.254/metadata/v1/interfaces/public/0/ipv6/cidr 2>/dev/null)
        IPV6_GATEWAY=$(curl -sf http://169.254.169.254/metadata/v1/interfaces/public/0/ipv6/gateway 2>/dev/null)

        if [ -n "$IPV6_ADDR" ]; then
            echo "✅ IPv6 available in DO metadata: $IPV6_ADDR"

            if [ "$IPV6_CONFIGURED" = false ]; then
                echo "Configuring IPv6 on primary interface..."
                PRIMARY_IFACE=$(ip route | grep default | awk '{print $5}' | head -1)

                ip -6 addr add ${IPV6_ADDR}/${IPV6_CIDR##*/} dev "$PRIMARY_IFACE" 2>/dev/null || true
                ip -6 route add default via "$IPV6_GATEWAY" dev "$PRIMARY_IFACE" 2>/dev/null || true

                echo "✅ IPv6 configured on $PRIMARY_IFACE"
                IPV6_CONFIGURED=true
            fi
        else
            echo "❌ IPv6 not available in DO metadata"
            echo ""
            echo "To enable IPv6 on Digital Ocean:"
            echo "  1. Go to: https://cloud.digitalocean.com/droplets"
            echo "  2. Select this droplet"
            echo "  3. Click 'Networking' → 'IPv6' → 'Enable'"
            echo "  4. Wait 30 seconds for propagation"
            echo ""
            read -rp "Press Enter after enabling IPv6 in DO control panel, or Ctrl+C to abort..."

            # Retry after user enables
            sleep 5
            IPV6_ADDR=$(curl -sf http://169.254.169.254/metadata/v1/interfaces/public/0/ipv6/address 2>/dev/null)
            if [ -z "$IPV6_ADDR" ]; then
                echo "❌ IPv6 still not available. Deployment will use pooler connection."
                return 1
            fi

            # Configure after enabling
            IPV6_CIDR=$(curl -sf http://169.254.169.254/metadata/v1/interfaces/public/0/ipv6/cidr)
            IPV6_GATEWAY=$(curl -sf http://169.254.169.254/metadata/v1/interfaces/public/0/ipv6/gateway)
            PRIMARY_IFACE=$(ip route | grep default | awk '{print $5}' | head -1)

            ip -6 addr add ${IPV6_ADDR}/${IPV6_CIDR##*/} dev "$PRIMARY_IFACE"
            ip -6 route add default via "$IPV6_GATEWAY" dev "$PRIMARY_IFACE"

            echo "✅ IPv6 configured: $IPV6_ADDR"
            IPV6_CONFIGURED=true
        fi
    fi

    # Test IPv6 connectivity to Supabase
    if [ "$IPV6_CONFIGURED" = true ]; then
        echo ""
        echo "Testing IPv6 connectivity to Supabase..."
        if timeout 5 nc -6 -zv db.${PROJECT_REF}.supabase.co 5432 2>&1 | grep -q "succeeded\|Connected"; then
            echo "✅ IPv6 connectivity to Supabase: SUCCESS"
            USE_IPV6_CONNECTION=true
        else
            echo "⚠️  IPv6 configured but cannot reach Supabase database"
            USE_IPV6_CONNECTION=false
        fi
    else
        USE_IPV6_CONNECTION=false
    fi

    return 0
}

# Setup Docker IPv6
setup_docker_ipv6() {
    echo ""
    echo "Configuring Docker for IPv6..."

    if [ -f /etc/docker/daemon.json ] && grep -q '"ipv6": true' /etc/docker/daemon.json; then
        echo "✅ Docker IPv6 already enabled"
        return
    fi

    echo "Enabling IPv6 in Docker daemon..."

    # Backup existing config if it exists
    if [ -f /etc/docker/daemon.json ]; then
        cp /etc/docker/daemon.json /etc/docker/daemon.json.backup.$(date +%Y%m%d-%H%M%S)
    fi

    # Create new config with IPv6
    cat > /etc/docker/daemon.json << 'DOCKER_EOF'
{
  "ipv6": true,
  "fixed-cidr-v6": "fd00::/64"
}
DOCKER_EOF

    echo "Restarting Docker daemon..."
    systemctl restart docker
    sleep 10

    # Verify Docker restarted
    if systemctl is-active --quiet docker; then
        echo "✅ Docker IPv6 enabled and daemon restarted"
    else
        echo "❌ Docker failed to restart"
        exit 1
    fi
}

# Run IPv6 setup
setup_ipv6
IPV6_RESULT=$?

# Setup Docker IPv6 if system IPv6 is available
if [ "$IPV6_CONFIGURED" = true ]; then
    setup_docker_ipv6
fi

echo ""

# ============================================================================
# GENERATE CREDENTIALS
# ============================================================================

echo "🔐 Generating secure credentials..."
echo ""

# Generate sync_service password (32 random bytes, base64 encoded)
SYNC_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')
echo "✅ Generated sync_service password"

# URL encode function for passwords
urlencode() {
    local string="${1}"
    local strlen=${#string}
    local encoded=""
    local pos c o

    for (( pos=0 ; pos<strlen ; pos++ )); do
        c=${string:$pos:1}
        case "$c" in
            [-_.~a-zA-Z0-9] ) o="${c}" ;;
            * ) printf -v o '%%%02x' "'$c"
        esac
        encoded+="${o}"
    done
    echo "${encoded}"
}

# URL encode passwords for database URLs
ENCODED_ADMIN_PASSWORD=$(urlencode "$ADMIN_PASSWORD")
ENCODED_SYNC_PASSWORD=$(urlencode "$SYNC_PASSWORD")

# Build database URLs based on IPv6 availability
if [ "$USE_IPV6_CONNECTION" = true ]; then
    echo "Using direct IPv6 database connection..."
    ADMIN_URL="postgresql://postgres:${ENCODED_ADMIN_PASSWORD}@db.${PROJECT_REF}.supabase.co:5432/postgres"
    SYNC_URL="postgresql://sync_service:${ENCODED_SYNC_PASSWORD}@db.${PROJECT_REF}.supabase.co:5432/postgres"
else
    echo "Using pooler connection (IPv4)..."
    ADMIN_URL="postgresql://postgres.${PROJECT_REF}:${ENCODED_ADMIN_PASSWORD}@${REGION}.pooler.supabase.com:5432/postgres"
    SYNC_URL="postgresql://sync_service:${ENCODED_SYNC_PASSWORD}@${REGION}.pooler.supabase.com:5432/postgres"
    echo "⚠️  Note: Pooler requires postgres admin credentials. sync_service role may not work."
fi

# ============================================================================
# UPDATE SYNC_SERVICE PASSWORD
# ============================================================================

echo ""
echo "🔑 Updating sync_service role password in Supabase..."
echo ""

# Use psql via Docker if available, or skip password update
if command -v docker &> /dev/null; then
    # Use official postgres Docker image to run psql
    if docker run --rm postgres:15-alpine psql "$ADMIN_URL" \
        -c "ALTER ROLE sync_service WITH ENCRYPTED PASSWORD '$SYNC_PASSWORD';" 2>&1 | tee /tmp/psql_output.log; then

        if grep -q "ERROR" /tmp/psql_output.log; then
            echo "❌ Failed to update sync_service password"
            echo "⚠️  You may need to manually update the password in Supabase:"
            echo "   ALTER ROLE sync_service WITH ENCRYPTED PASSWORD 'your-password';"
            echo ""
            read -rp "Continue anyway? (y/N): " CONTINUE
            if [[ ! "$CONTINUE" =~ ^[Yy]$ ]]; then
                exit 1
            fi
        else
            echo "✅ sync_service password updated successfully"
        fi
    else
        echo "⚠️  Could not update password automatically"
        echo "You can update it manually in Supabase SQL Editor:"
        echo "   ALTER ROLE sync_service WITH ENCRYPTED PASSWORD '$SYNC_PASSWORD';"
        echo ""
        read -rp "Continue anyway? (y/N): " CONTINUE
        if [[ ! "$CONTINUE" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    rm -f /tmp/psql_output.log
else
    echo "⚠️  Docker not available, skipping password update"
    echo "Please update manually in Supabase:"
    echo "   ALTER ROLE sync_service WITH ENCRYPTED PASSWORD '$SYNC_PASSWORD';"
    echo ""
    read -rp "Continue? (y/N): " CONTINUE
    if [[ ! "$CONTINUE" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""

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
if docker compose -f docker-compose.sync-ha.yml ps -q 2>/dev/null | grep -q .; then
    echo "⚠️  Stopping existing sync cluster..."
    docker compose -f docker-compose.sync-ha.yml down
fi

# Start new cluster
if docker compose -f docker-compose.sync-ha.yml up -d; then
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
echo "  Logs:       docker compose -f $DOCKER_DIR/docker-compose.sync-ha.yml logs -f"
echo ""

echo "📚 Useful Commands:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  View status:   curl http://localhost:9443/health | jq"
echo "  View logs:     docker compose -f $DOCKER_DIR/docker-compose.sync-ha.yml logs -f"
echo "  Restart:       docker compose -f $DOCKER_DIR/docker-compose.sync-ha.yml restart"
echo "  Stop:          docker compose -f $DOCKER_DIR/docker-compose.sync-ha.yml down"
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
