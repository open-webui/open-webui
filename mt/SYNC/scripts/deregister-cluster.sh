#!/bin/bash
# SQLite + Supabase Sync System - Cluster Deregistration
# Run this script BEFORE destroying a Digital Ocean droplet or host server
#
# This ensures clean removal of cluster metadata from Supabase to prevent:
# - Orphaned leader election records
# - Stale host entries showing as "offline"
# - Client deployment records pointing to non-existent hosts
# - Unprocessed cache invalidation events

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYNC_DIR="$(dirname "$SCRIPT_DIR")"

# ============================================================================
# Configuration
# ============================================================================

CLUSTER_NAME="${CLUSTER_NAME:-$(hostname)}"
CREDENTIALS_FILE="${SYNC_DIR}/docker/.credentials"

# ============================================================================
# Functions
# ============================================================================

error() {
    echo "❌ ERROR: $1" >&2
    exit 1
}

warn() {
    echo "⚠️  WARNING: $1" >&2
}

info() {
    echo "ℹ️  $1"
}

success() {
    echo "✅ $1"
}

# ============================================================================
# Load Credentials
# ============================================================================

if [ ! -f "$CREDENTIALS_FILE" ]; then
    error "Credentials file not found: $CREDENTIALS_FILE"
fi

source "$CREDENTIALS_FILE"

if [ -z "${SUPABASE_ADMIN_URL:-}" ]; then
    error "SUPABASE_ADMIN_URL not found in credentials file"
fi

# ============================================================================
# Main Deregistration Process
# ============================================================================

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Sync Cluster Deregistration                                   ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Cluster: $CLUSTER_NAME"
echo "This will remove all cluster metadata from Supabase"
echo ""

# Check if cluster exists
info "Checking if cluster exists in Supabase..."

CLUSTER_CHECK=$(docker run --rm postgres:15-alpine psql "$SUPABASE_ADMIN_URL" -t -c \
    "SELECT COUNT(*) FROM sync_metadata.hosts WHERE cluster_name = '$CLUSTER_NAME';" 2>/dev/null || echo "0")

CLUSTER_CHECK=$(echo "$CLUSTER_CHECK" | tr -d '[:space:]')

if [ "$CLUSTER_CHECK" = "0" ]; then
    warn "Cluster '$CLUSTER_NAME' not found in Supabase (already deregistered or never registered)"
    exit 0
fi

success "Found cluster '$CLUSTER_NAME' with $CLUSTER_CHECK host(s)"

# Show what will be deleted
echo ""
info "Gathering cluster metadata..."
echo ""

echo "═══════════════════════════════════════════════════════════════════"
echo "Hosts in cluster:"
echo "═══════════════════════════════════════════════════════════════════"

docker run --rm postgres:15-alpine psql "$SUPABASE_ADMIN_URL" -c \
    "SELECT hostname, status, last_heartbeat,
     EXTRACT(EPOCH FROM (NOW() - last_heartbeat))::INTEGER as seconds_since_heartbeat
     FROM sync_metadata.hosts
     WHERE cluster_name = '$CLUSTER_NAME'
     ORDER BY hostname;"

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "Leader election status:"
echo "═══════════════════════════════════════════════════════════════════"

docker run --rm postgres:15-alpine psql "$SUPABASE_ADMIN_URL" -c \
    "SELECT leader_id, acquired_at, expires_at,
     CASE WHEN expires_at > NOW() THEN 'active' ELSE 'expired' END as lease_status
     FROM sync_metadata.leader_election
     WHERE cluster_name = '$CLUSTER_NAME';"

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "Client deployments on this cluster:"
echo "═══════════════════════════════════════════════════════════════════"

docker run --rm postgres:15-alpine psql "$SUPABASE_ADMIN_URL" -c \
    "SELECT cd.client_name, cd.container_name, cd.status, cd.sync_enabled,
     cd.last_sync_at, cd.last_sync_status
     FROM sync_metadata.client_deployments cd
     JOIN sync_metadata.hosts h ON cd.host_id = h.host_id
     WHERE h.cluster_name = '$CLUSTER_NAME'
     ORDER BY cd.client_name;"

echo ""
echo "═══════════════════════════════════════════════════════════════════"

# ============================================================================
# SAFETY CHECK: Verify no active sync-enabled clients
# ============================================================================

echo ""
info "Running safety checks..."

# Count clients with sync enabled
SYNC_ENABLED_COUNT=$(docker run --rm postgres:15-alpine psql "$SUPABASE_ADMIN_URL" -t -c \
    "SELECT COUNT(*)
     FROM sync_metadata.client_deployments cd
     JOIN sync_metadata.hosts h ON cd.host_id = h.host_id
     WHERE h.cluster_name = '$CLUSTER_NAME'
       AND cd.sync_enabled = true;" 2>/dev/null || echo "0")

SYNC_ENABLED_COUNT=$(echo "$SYNC_ENABLED_COUNT" | tr -d '[:space:]')

if [ "$SYNC_ENABLED_COUNT" != "0" ]; then
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║  ⚠️  CRITICAL WARNING: ACTIVE SYNC CLIENTS DETECTED           ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "❌ Cannot deregister cluster: $SYNC_ENABLED_COUNT client(s) have sync ENABLED"
    echo ""
    echo "Clients with sync enabled:"
    docker run --rm postgres:15-alpine psql "$SUPABASE_ADMIN_URL" -c \
        "SELECT cd.client_name, cd.container_name, cd.last_sync_at, cd.last_sync_status
         FROM sync_metadata.client_deployments cd
         JOIN sync_metadata.hosts h ON cd.host_id = h.host_id
         WHERE h.cluster_name = '$CLUSTER_NAME'
           AND cd.sync_enabled = true
         ORDER BY cd.client_name;"
    echo ""
    echo "═══════════════════════════════════════════════════════════════════"
    echo "REQUIRED ACTIONS before deregistration:"
    echo "═══════════════════════════════════════════════════════════════════"
    echo ""
    echo "For each client listed above, choose ONE of the following:"
    echo ""
    echo "Option 1: Disable sync for this client"
    echo "   - Use client-manager.sh to disable sync"
    echo "   - OR manually: UPDATE sync_metadata.client_deployments"
    echo "     SET sync_enabled = false WHERE client_name = 'CLIENT_NAME';"
    echo ""
    echo "Option 2: Migrate client to another host/cluster"
    echo "   - Deploy sync cluster on new host"
    echo "   - Migrate Open WebUI container to new host"
    echo "   - Update client_deployments.host_id to new host"
    echo ""
    echo "Option 3: Decommission the client deployment"
    echo "   - Stop the Open WebUI container"
    echo "   - Backup data if needed"
    echo "   - Delete from sync_metadata.client_deployments"
    echo ""
    echo "Once all sync-enabled clients are handled, re-run this script."
    echo ""
    error "Deregistration blocked due to active sync clients"
fi

success "Safety check passed: No active sync clients found"

# Count total clients (for informational purposes)
TOTAL_CLIENTS=$(docker run --rm postgres:15-alpine psql "$SUPABASE_ADMIN_URL" -t -c \
    "SELECT COUNT(*)
     FROM sync_metadata.client_deployments cd
     JOIN sync_metadata.hosts h ON cd.host_id = h.host_id
     WHERE h.cluster_name = '$CLUSTER_NAME';" 2>/dev/null || echo "0")

TOTAL_CLIENTS=$(echo "$TOTAL_CLIENTS" | tr -d '[:space:]')

if [ "$TOTAL_CLIENTS" != "0" ]; then
    warn "Found $TOTAL_CLIENTS client deployment(s) registered (sync disabled)"
    echo "  These will be deleted when the cluster is deregistered."
    echo "  If you want to preserve these client records for future use,"
    echo "  manually migrate them to another cluster before proceeding."
fi

# Confirm deletion
echo ""
echo "⚠️  WARNING: This will permanently delete:"
echo "   - All host records for cluster '$CLUSTER_NAME'"
echo "   - Leader election records (via CASCADE)"
echo "   - Client deployment records (via CASCADE) - $TOTAL_CLIENTS client(s)"
echo "   - Cache invalidation events (via CASCADE)"
echo "   - Sync job history (via CASCADE)"
echo ""
read -p "Are you sure you want to deregister this cluster? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Deregistration cancelled"
    exit 0
fi

# ============================================================================
# Step 1: Stop sync containers gracefully
# ============================================================================

echo ""
info "Step 1: Stopping sync containers..."

if docker ps -q --filter "name=openwebui-sync-" | grep -q .; then
    info "Found running sync containers, stopping gracefully..."

    # This triggers graceful shutdown which releases leadership
    docker stop openwebui-sync-primary openwebui-sync-secondary 2>/dev/null || true

    success "Sync containers stopped"

    # Wait a few seconds for leader release to propagate
    sleep 3
else
    info "No sync containers running"
fi

# ============================================================================
# Step 2: Delete cluster metadata from Supabase
# ============================================================================

echo ""
info "Step 2: Deleting cluster metadata from Supabase..."

# Delete hosts (CASCADE will handle related records)
docker run --rm postgres:15-alpine psql "$SUPABASE_ADMIN_URL" -c \
    "DELETE FROM sync_metadata.hosts WHERE cluster_name = '$CLUSTER_NAME';" || error "Failed to delete hosts"

success "Cluster metadata deleted from Supabase"

# ============================================================================
# Step 3: Verify deletion
# ============================================================================

echo ""
info "Step 3: Verifying deletion..."

VERIFY_HOSTS=$(docker run --rm postgres:15-alpine psql "$SUPABASE_ADMIN_URL" -t -c \
    "SELECT COUNT(*) FROM sync_metadata.hosts WHERE cluster_name = '$CLUSTER_NAME';" 2>/dev/null || echo "0")
VERIFY_HOSTS=$(echo "$VERIFY_HOSTS" | tr -d '[:space:]')

VERIFY_LEADER=$(docker run --rm postgres:15-alpine psql "$SUPABASE_ADMIN_URL" -t -c \
    "SELECT COUNT(*) FROM sync_metadata.leader_election WHERE cluster_name = '$CLUSTER_NAME';" 2>/dev/null || echo "0")
VERIFY_LEADER=$(echo "$VERIFY_LEADER" | tr -d '[:space:]')

if [ "$VERIFY_HOSTS" = "0" ] && [ "$VERIFY_LEADER" = "0" ]; then
    success "Cluster fully deregistered from Supabase"
else
    warn "Some records may remain:"
    [ "$VERIFY_HOSTS" != "0" ] && echo "  - Hosts: $VERIFY_HOSTS"
    [ "$VERIFY_LEADER" != "0" ] && echo "  - Leader election: $VERIFY_LEADER"
fi

# ============================================================================
# Step 4: Remove local containers and volumes (optional)
# ============================================================================

echo ""
read -p "Remove local sync containers and Docker volumes? (yes/no): " REMOVE_LOCAL

if [ "$REMOVE_LOCAL" = "yes" ]; then
    info "Removing local sync containers..."

    docker rm -f openwebui-sync-primary openwebui-sync-secondary 2>/dev/null || true

    # Check for sync-related volumes
    if docker volume ls --filter "name=sync" | grep -q sync; then
        info "Found sync-related volumes:"
        docker volume ls --filter "name=sync"

        read -p "Remove these volumes? (yes/no): " REMOVE_VOLUMES
        if [ "$REMOVE_VOLUMES" = "yes" ]; then
            docker volume ls --filter "name=sync" --format "{{.Name}}" | xargs -r docker volume rm
            success "Volumes removed"
        fi
    fi

    success "Local cleanup complete"
fi

# ============================================================================
# Summary
# ============================================================================

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Deregistration Complete                                       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Cluster '$CLUSTER_NAME' has been deregistered from Supabase"
echo ""
echo "✅ Host records: deleted"
echo "✅ Leader election: deleted (CASCADE)"
echo "✅ Client deployments: deleted (CASCADE)"
echo "✅ Cache events: deleted (CASCADE)"
echo ""
echo "You can now safely destroy the Digital Ocean droplet"
echo ""
echo "To re-deploy on a new host:"
echo "  1. Create new droplet"
echo "  2. Run: ./scripts/deploy-sync-cluster.sh"
echo ""
