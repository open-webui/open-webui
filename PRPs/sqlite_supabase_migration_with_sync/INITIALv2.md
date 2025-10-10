# INITIAL.md (Revised)


## READ:
- mt/README.md
- mt/DB_MIGRATION/README.md
- code base in the mt/ folder
- PRPs/sqlite_supabase_migration_with_sync/README.md (during the first attempt to create a PRP Claude got ahead of itself and started development.  YOU MUST CREATE THE PRP as instructed. DO NOT START DEVELOPMENT UNTIL I TELL YOU)

## FEATURE:

**SQLite + Supabase Sync System for Multi-Tenant Open WebUI Deployments with State Authority and High Availability**

- Implements the phase 1 of three phases that will enable protecting clients Open WebUI databases and enable an automated host to host migration for managing and scaling a multi-tenant Open WebUI solution.
- SQLite remains primary for Open WebUI performance (eliminates 100x streaming latency)
- **Supabase as authoritative state source** with local caching for resilience
- **Clustered sync containers** (primary/secondary) for high availability from Phase 1
- **Restricted database roles** for security (no service role keys in containers)
- **Automated conflict resolution** with configurable strategies
- Configurable sync intervals (1-minute, 5-minute, hourly, daily) per deployment
- Multi-tenant Supabase schema design (one schema per client)
- One-way sync in Phase 1 (SQLite → Supabase), bidirectional in Phase 2
- Cross-host migration capability (Phase 2)
- API-based architecture with health checks and state synchronization

### Core Components (Phase 1):

1. **Sync Container Cluster** (`openwebui-sync-primary`, `openwebui-sync-secondary`)
   - Two containers per host for high availability
   - Leader election using Supabase atomic operations
   - Shared work queue with distributed locking
   - Automatic failover with 30-second heartbeat
   - Docker containers with centralized image: `ghcr.io/imagicrafter/openwebui-sync:latest`
   - REST API on primary (port 9443), health check only on secondary (port 9444)

2. **State Management System**
   - **Supabase as authoritative source** for all deployment state
   - Local state cache with 5-minute TTL
   - Cache invalidation on state changes
   - Reconciliation protocol for cache misses
   - Atomic state transitions using PostgreSQL transactions

3. **Security Architecture**
   - **Restricted sync role** with minimal permissions
   - Per-client schema access controls
   - No DELETE permissions on any schema
   - Encrypted credentials in Docker secrets
   - API authentication using JWT tokens (mTLS in Phase 3)

4. **Conflict Resolution Engine**
   - Automated resolution for common conflicts
   - Configurable strategies per table
   - Conflict log for audit trail
   - Manual override capability via client-manager

5. **Sync Engine** (`sync-client-to-supabase.sh`)
   - Incremental sync using `updated_at` timestamps
   - WAL mode for consistent snapshots
   - Batch processing (1000 rows per transaction)
   - Automatic retry with exponential backoff
   - Progress tracking in Supabase

6. **Client Manager Integration**
   - Menu option: "Configure database sync"
   - View sync status and conflict log
   - Manual sync trigger
   - Change sync interval
   - Enable/disable sync per deployment

### Phased Architecture Implementation:

**Phase 1 - Foundation with HA (Current Focus):**
- **State Authority**: Supabase is source of truth, local cache for performance
- **High Availability**: Dual sync containers with leader election
- **Security**: Restricted database roles, encrypted secrets
- **Conflict Resolution**: Automated with configurable strategies
- One-way sync (SQLite → Supabase)
- Comprehensive monitoring and alerting

**Phase 2 - Migration & Bidirectional Sync:**
- Cross-host migration orchestration
- Bidirectional sync (Supabase → SQLite restore)
- DNS automation via provider abstraction
- SSL certificate management
- Blue-green deployment support

**Phase 3 - Intelligence & Optimization:**
- mTLS authentication between components
- AI-driven sync scheduling
- Predictive conflict resolution
- Auto-scaling based on load
- Multi-region replication

### State Management Architecture:

```python
# State authority implementation
class StateManager:
    def __init__(self):
        self.cache = {}
        self.cache_expiry = {}
        self.ttl = 300  # 5 minutes
        
    async def get_state(self, key: str) -> dict:
        """Get state with cache-aside pattern"""
        # Check cache first
        if self._is_cache_valid(key):
            return self.cache[key]
        
        # Cache miss - fetch from Supabase (authoritative)
        state = await self._fetch_from_supabase(key)
        
        # Update local cache
        self._update_cache(key, state)
        
        return state
    
    async def update_state(self, key: str, state: dict) -> bool:
        """Update state - Supabase first, then cache"""
        # Update authoritative source first
        success = await self._update_supabase(key, state)
        
        if success:
            # Invalidate local cache to force refresh
            self._invalidate_cache(key)
            # Notify secondary container via Supabase event
            await self._notify_cluster(key, 'invalidate')
        
        return success
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is still valid"""
        if key not in self.cache:
            return False
        return time.time() < self.cache_expiry[key]
```

### High Availability Architecture:

```yaml
# Docker Compose for HA sync containers
version: '3.8'

services:
  sync-primary:
    image: ghcr.io/imagicrafter/openwebui-sync:latest
    container_name: openwebui-sync-primary
    environment:
      - ROLE=primary
      - API_PORT=9443
      - CLUSTER_NAME=prod-host-1
      - HEARTBEAT_INTERVAL=30
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - sync-secrets:/secrets:ro
    secrets:
      - db_sync_password
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9443/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  sync-secondary:
    image: ghcr.io/imagicrafter/openwebui-sync:latest
    container_name: openwebui-sync-secondary
    environment:
      - ROLE=secondary
      - API_PORT=9444
      - CLUSTER_NAME=prod-host-1
      - HEARTBEAT_INTERVAL=30
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - sync-secrets:/secrets:ro
    secrets:
      - db_sync_password
    restart: unless-stopped
    depends_on:
      - sync-primary

secrets:
  db_sync_password:
    external: true

volumes:
  sync-secrets:
    driver: local
```

### Security Implementation:

```sql
-- Create restricted sync role for containers
CREATE ROLE sync_service WITH LOGIN ENCRYPTED PASSWORD 'generate-strong-password';

-- Grant minimal permissions for sync operations
GRANT USAGE ON SCHEMA sync_metadata TO sync_service;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA sync_metadata TO sync_service;
-- NO DELETE permission

-- Per-client schema permissions (executed for each client)
GRANT USAGE ON SCHEMA client_name TO sync_service;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA client_name TO sync_service;
-- NO DELETE, NO DROP, NO CREATE permissions

-- Row Level Security for sync_metadata
ALTER TABLE sync_metadata.hosts ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_metadata.client_deployments ENABLE ROW LEVEL SECURITY;

-- Policy: Sync service can only see/modify its own host's data
CREATE POLICY sync_host_isolation ON sync_metadata.hosts
    FOR ALL
    TO sync_service
    USING (host_id = current_setting('app.current_host_id'));

CREATE POLICY sync_deployment_isolation ON sync_metadata.client_deployments
    FOR ALL
    TO sync_service
    USING (host_id = current_setting('app.current_host_id'));
```

### Conflict Resolution Configuration:

```json
{
  "conflict_resolution": {
    "default_strategy": "newest_wins",
    "table_strategies": {
      "user": {
        "strategy": "newest_wins",
        "compare_field": "updated_at"
      },
      "chat": {
        "strategy": "merge",
        "merge_rules": {
          "messages": "append",
          "metadata": "newest_wins"
        }
      },
      "oauth_session": {
        "strategy": "source_wins",
        "reason": "Active sessions should not be overwritten"
      },
      "config": {
        "strategy": "manual",
        "notify": true,
        "reason": "Configuration changes require review"
      }
    },
    "resolution_log": {
      "enabled": true,
      "retention_days": 30,
      "include_data_snapshot": false
    }
  }
}
```

### Conflict Resolution Implementation:

```python
class ConflictResolver:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.strategies = {
            'newest_wins': self._resolve_newest_wins,
            'source_wins': self._resolve_source_wins,
            'target_wins': self._resolve_target_wins,
            'merge': self._resolve_merge,
            'manual': self._flag_manual_resolution
        }
    
    async def resolve_conflict(self, table: str, source_row: dict, 
                               target_row: dict) -> dict:
        """Resolve conflict based on configured strategy"""
        strategy = self._get_strategy(table)
        
        # Log conflict detection
        await self._log_conflict(table, source_row, target_row, strategy)
        
        # Apply resolution strategy
        resolved = self.strategies[strategy](source_row, target_row, table)
        
        # Log resolution
        await self._log_resolution(table, resolved, strategy)
        
        return resolved
    
    def _resolve_newest_wins(self, source: dict, target: dict, table: str) -> dict:
        """Resolution: Use the row with most recent updated_at"""
        compare_field = self.config['table_strategies'][table].get(
            'compare_field', 'updated_at'
        )
        
        source_time = datetime.fromisoformat(source[compare_field])
        target_time = datetime.fromisoformat(target[compare_field])
        
        return source if source_time > target_time else target
    
    def _resolve_merge(self, source: dict, target: dict, table: str) -> dict:
        """Resolution: Merge based on configured rules"""
        merge_rules = self.config['table_strategies'][table]['merge_rules']
        merged = target.copy()
        
        for field, rule in merge_rules.items():
            if rule == 'append':
                # Append lists/arrays
                merged[field] = target.get(field, []) + source.get(field, [])
            elif rule == 'newest_wins':
                # Take newest value for this field
                if source['updated_at'] > target['updated_at']:
                    merged[field] = source[field]
            elif rule == 'union':
                # Union of sets
                merged[field] = list(set(target.get(field, []) | 
                                        set(source.get(field, []))))
        
        return merged
```

### Leader Election for HA Containers:

```python
class LeaderElection:
    def __init__(self, cluster_name: str, node_id: str):
        self.cluster_name = cluster_name
        self.node_id = node_id
        self.is_leader = False
        self.lease_duration = 60  # seconds
        
    async def participate(self):
        """Participate in leader election"""
        while True:
            try:
                # Attempt to acquire or renew leadership
                acquired = await self._try_acquire_leadership()
                
                if acquired:
                    self.is_leader = True
                    await self._perform_leader_duties()
                else:
                    self.is_leader = False
                    await self._perform_follower_duties()
                    
                await asyncio.sleep(self.lease_duration / 2)
                
            except Exception as e:
                logger.error(f"Leader election error: {e}")
                self.is_leader = False
                await asyncio.sleep(5)
    
    async def _try_acquire_leadership(self) -> bool:
        """Try to acquire or renew leadership via atomic DB operation"""
        query = """
        INSERT INTO sync_metadata.leader_election 
            (cluster_name, leader_id, acquired_at, expires_at)
        VALUES 
            ($1, $2, NOW(), NOW() + INTERVAL '60 seconds')
        ON CONFLICT (cluster_name) DO UPDATE
        SET 
            leader_id = EXCLUDED.leader_id,
            acquired_at = NOW(),
            expires_at = NOW() + INTERVAL '60 seconds'
        WHERE 
            leader_election.expires_at < NOW()
            OR leader_election.leader_id = EXCLUDED.leader_id
        RETURNING leader_id = $2 as is_leader;
        """
        
        result = await db.fetchval(query, self.cluster_name, self.node_id)
        return result
```

### Database Schema Updates:

```sql
-- Leader election table for HA coordination
CREATE TABLE sync_metadata.leader_election (
    cluster_name VARCHAR(100) PRIMARY KEY,
    leader_id VARCHAR(100) NOT NULL,
    acquired_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL
);

-- Conflict resolution log
CREATE TABLE sync_metadata.conflict_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id VARCHAR(100) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    conflict_type VARCHAR(50) NOT NULL,
    source_data JSONB,
    target_data JSONB,
    resolution_strategy VARCHAR(50),
    resolved_data JSONB,
    detected_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(100), -- 'automatic' or username
    INDEX idx_conflicts_client (client_id, detected_at DESC)
);

-- State cache invalidation events
CREATE TABLE sync_metadata.cache_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    host_id UUID REFERENCES sync_metadata.hosts(host_id),
    cache_key VARCHAR(255) NOT NULL,
    action VARCHAR(20) NOT NULL, -- 'invalidate', 'refresh'
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    INDEX idx_cache_events_unprocessed (host_id, processed_at)
        WHERE processed_at IS NULL
);
```

### Sync Process with Conflict Resolution:

```bash
# sync-client-to-supabase.sh modifications
sync_with_conflict_resolution() {
    local client_name=$1
    local conflict_config="/sync-data/config/${client_name}-conflicts.json"
    
    # Start WAL snapshot for consistency
    sqlite3 "$SQLITE_PATH" "PRAGMA wal_checkpoint(TRUNCATE);"
    sqlite3 "$SQLITE_PATH" "BEGIN IMMEDIATE TRANSACTION;"
    
    # Get changes since last sync
    local changes=$(sqlite3 "$SQLITE_PATH" "
        SELECT * FROM $table 
        WHERE updated_at > '$last_sync_timestamp'
    ")
    
    # Process each change with conflict detection
    for row in $changes; do
        # Check if row exists in Supabase
        existing=$(psql "$SUPABASE_URL" -c "
            SELECT * FROM ${client_name}.${table}
            WHERE id = '${row.id}'
        ")
        
        if [[ -n "$existing" ]]; then
            # Conflict detected - resolve using configured strategy
            resolved=$(python3 /sync/conflict_resolver.py \
                --table "$table" \
                --source "$row" \
                --target "$existing" \
                --config "$conflict_config")
            
            # Apply resolved data
            psql "$SUPABASE_URL" -c "
                UPDATE ${client_name}.${table}
                SET data = '$resolved'
                WHERE id = '${row.id}'
            "
            
            # Log resolution
            log_conflict_resolution "$client_name" "$table" "$row.id" "$strategy"
        else
            # No conflict - insert normally
            psql "$SUPABASE_URL" -c "
                INSERT INTO ${client_name}.${table}
                VALUES ('$row')
            "
        fi
    done
    
    # Commit SQLite transaction
    sqlite3 "$SQLITE_PATH" "COMMIT;"
}
```

### Deployment with HA:

```bash
# deploy-sync-cluster.sh
#!/bin/bash

# Create Docker secrets for database credentials
echo "Creating secure database credentials..."

# Generate restricted sync user password
SYNC_PASSWORD=$(openssl rand -base64 32)

# Store in Docker secrets
echo "$SYNC_PASSWORD" | docker secret create db_sync_password -

# Create sync user in Supabase
psql "$SUPABASE_ADMIN_URL" <<EOF
CREATE ROLE sync_service WITH LOGIN ENCRYPTED PASSWORD '$SYNC_PASSWORD';
GRANT USAGE ON SCHEMA sync_metadata TO sync_service;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA sync_metadata TO sync_service;
EOF

# Deploy HA sync containers
docker-compose -f docker-compose.sync-ha.yml up -d

# Wait for leader election
sleep 10

# Verify cluster health
curl -f http://localhost:9443/health || exit 1
curl -f http://localhost:9444/health || exit 1

echo "✅ HA Sync cluster deployed successfully"
```

### Client Manager Integration Updates:

```bash
# Modifications to client-manager.sh

# New menu option for sync configuration
sync_configuration_menu() {
    clear
    echo "╔════════════════════════════════════════╗"
    echo "║      Database Sync Configuration       ║"
    echo "╚════════════════════════════════════════╝"
    echo
    
    # Check sync cluster health
    local primary_health=$(curl -s http://localhost:9443/health)
    local secondary_health=$(curl -s http://localhost:9444/health)
    
    echo "Sync Cluster Status:"
    echo "  Primary:   $(echo $primary_health | jq -r .status)"
    echo "  Secondary: $(echo $secondary_health | jq -r .status)"
    echo "  Leader:    $(echo $primary_health | jq -r .leader_id)"
    echo
    
    echo "1) View sync status for deployment"
    echo "2) Configure sync interval"
    echo "3) Trigger manual sync"
    echo "4) View conflict log"
    echo "5) Configure conflict resolution"
    echo "6) Test sync cluster failover"
    echo "7) Return to main menu"
    echo
    echo -n "Select option (1-7): "
    read option
    
    case "$option" in
        4)
            view_conflict_log
            ;;
        5)
            configure_conflict_resolution
            ;;
        6)
            test_failover
            ;;
        # ... other options
    esac
}

view_conflict_log() {
    local client_name=$1
    
    echo "Recent conflicts for $client_name:"
    echo
    
    # Query Supabase for recent conflicts
    psql "$SUPABASE_URL" -c "
        SELECT 
            detected_at,
            table_name,
            conflict_type,
            resolution_strategy,
            resolved_by
        FROM sync_metadata.conflict_log
        WHERE client_id = '$client_name'
        ORDER BY detected_at DESC
        LIMIT 20
    "
    
    echo
    echo "Press Enter to continue..."
    read
}

configure_conflict_resolution() {
    local client_name=$1
    
    echo "Conflict Resolution Strategy for $client_name"
    echo
    echo "Current configuration:"
    cat "/sync-data/config/${client_name}-conflicts.json" | jq .
    echo
    echo "Available strategies:"
    echo "  1) newest_wins    - Use most recent updated_at"
    echo "  2) source_wins    - Always use SQLite version"
    echo "  3) target_wins    - Always use Supabase version"
    echo "  4) merge          - Merge changes (configurable)"
    echo "  5) manual         - Flag for manual review"
    echo
    echo -n "Select default strategy (1-5): "
    read strategy_choice
    
    # Update configuration
    update_conflict_config "$client_name" "$strategy_choice"
}

test_failover() {
    echo "Testing sync cluster failover..."
    echo
    echo "Current leader: $(curl -s http://localhost:9443/health | jq -r .leader_id)"
    echo
    echo "Stopping primary container to trigger failover..."
    docker stop openwebui-sync-primary
    
    echo "Waiting for failover (30 seconds)..."
    sleep 30
    
    echo "New leader: $(curl -s http://localhost:9444/health | jq -r .leader_id)"
    echo
    echo "Restarting primary container..."
    docker start openwebui-sync-primary
    
    echo "Failover test complete!"
    echo
    echo "Press Enter to continue..."
    read
}
```

### Monitoring Configuration:

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'sync-cluster'
    static_configs:
      - targets: 
        - 'localhost:9443'
        - 'localhost:9444'
    metrics_path: '/metrics'

  - job_name: 'openwebui-containers'
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        filters:
          - name: label
            values: ["openwebui-*"]
```

### Metrics Exposed by Sync Containers:

```python
# Prometheus metrics in sync container
from prometheus_client import Counter, Gauge, Histogram, Summary

# Sync metrics
sync_operations_total = Counter(
    'sync_operations_total',
    'Total number of sync operations',
    ['client', 'status']
)

sync_duration_seconds = Histogram(
    'sync_duration_seconds',
    'Sync operation duration',
    ['client'],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600]
)

sync_rows_processed = Counter(
    'sync_rows_processed_total',
    'Total rows synchronized',
    ['client', 'table']
)

# Conflict metrics
conflicts_detected = Counter(
    'conflicts_detected_total',
    'Total conflicts detected',
    ['client', 'table', 'type']
)

conflicts_resolved = Counter(
    'conflicts_resolved_total',
    'Total conflicts resolved',
    ['client', 'strategy']
)

# HA metrics
leader_elections = Counter(
    'leader_elections_total',
    'Total leader elections',
    ['result']
)

is_leader = Gauge(
    'sync_container_is_leader',
    'Whether this container is currently leader',
    ['node_id']
)

# State management metrics
cache_hits = Counter(
    'state_cache_hits_total',
    'Cache hit count'
)

cache_misses = Counter(
    'state_cache_misses_total',
    'Cache miss count'
)

state_sync_lag_seconds = Gauge(
    'state_sync_lag_seconds',
    'Time since last state sync with Supabase'
)
```

## EXAMPLES:

The following code should be studied and adapted:

### Database Migration System (Reference):
- `mt/client-manager.sh` - Extend with sync configuration menu

### Key Phase 1 Requirements:

**DO NOT use service role keys** - Use restricted sync_service role
**DO NOT maintain dual state** - Supabase is authoritative, cache is temporary
**DO NOT run single sync container** - Always deploy primary/secondary pair
**DO NOT skip conflict detection** - Every sync operation checks for conflicts
**DO implement cache invalidation** - Ensure consistency across cluster
**DO implement health checks** - Both containers expose health endpoints
**DO log all conflicts** - Maintain audit trail for manual review

## Testing Strategy:

### Phase 1 Tests:

**1. HA Failover Test:**
```bash
# Kill primary, verify secondary takes over
docker stop openwebui-sync-primary
sleep 35  # Wait for lease expiration
curl http://localhost:9444/health | grep '"is_leader":true'

# Restart primary, verify it becomes follower
docker start openwebui-sync-primary
sleep 10
curl http://localhost:9443/health | grep '"is_leader":false'
```

**2. Conflict Resolution Test:**
```bash
# Create conflicting changes
# In SQLite: UPDATE chat SET title='Local' WHERE id=1
# In Supabase: UPDATE chat SET title='Remote' WHERE id=1
# Run sync and verify resolution strategy applied
```

**3. State Authority Test:**
```bash
# Update state via API
curl -X PUT http://localhost:9443/api/v1/state \
  -d '{"client":"test","status":"migrating"}'

# Verify Supabase updated first
psql $SUPABASE_URL -c "SELECT * FROM sync_metadata.client_deployments"

# Kill primary and verify secondary reads correct state
docker stop openwebui-sync-primary
curl http://localhost:9444/api/v1/state | grep '"status":"migrating"'
```

**4. Security Validation:**
```bash
# Attempt unauthorized operations with sync role
psql -U sync_service $SUPABASE_URL -c "DELETE FROM sync_metadata.hosts"
# Should fail with permission denied

psql -U sync_service $SUPABASE_URL -c "DROP SCHEMA client_test"
# Should fail with permission denied
```

## Success Criteria:

**Phase 1 (Revised):**
- [ ] Supabase is authoritative state source with local caching
- [ ] HA sync containers with automatic failover
- [ ] Restricted database roles (no service keys)
- [ ] Automated conflict resolution with logging
- [ ] One-way sync operational (SQLite → Supabase)
- [ ] Comprehensive monitoring with Prometheus metrics
- [ ] All tests passing
- [ ] Documentation complete

**Phase 2 (Future):**
- [ ] Cross-host migration
- [ ] Bidirectional sync
- [ ] DNS provider abstraction
- [ ] SSL automation

**Phase 3 (Future):**
- [ ] mTLS authentication
- [ ] AI-driven optimization
- [ ] Auto-scaling
- [ ] Multi-region support