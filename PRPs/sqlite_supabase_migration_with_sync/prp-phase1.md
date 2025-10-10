name: "SQLite + Supabase Sync System - Phase 1 (High Availability Foundation)"
version: "1.0"
created: "2025-10-08"
confidence_score: 8/10
archon_project_id: "038661b1-7e1c-40d0-b4f9-950db24c2a3f"
task_mapping: "PRPs/sqlite_supabase_migration_with_sync/archon-prp-task-mapping.md"

---

# Product Requirement Prompt: SQLite + Supabase Sync System (Phase 1)

> **🔗 Project Management**: This PRP is tracked in Archon MCP (Project ID: `038661b1-7e1c-40d0-b4f9-950db24c2a3f`)
> **📋 Task Mapping**: See `archon-prp-task-mapping.md` for correspondence between Archon tasks and PRP implementation steps

## Goal

Build a high-availability database synchronization system for multi-tenant Open WebUI deployments that maintains SQLite as the primary database (for performance) while using Supabase PostgreSQL as the authoritative state source with automated conflict resolution and failover capabilities.

**Phase 1 Deliverable**: Foundation infrastructure with HA sync containers, state management, conflict resolution, and one-way sync (SQLite → Supabase).

## Why

### Business Value
- **Data Protection**: Client databases automatically backed up to Supabase with every sync operation
- **High Availability**: Dual sync container architecture prevents single point of failure
- **Migration Enablement**: Phase 1 lays foundation for Phase 2 cross-host migrations
- **Performance**: SQLite remains primary database (eliminates 100x latency from current Supabase-only approach)
- **Scalability**: Enables future multi-host, multi-region deployments

### User Impact
- **Clients**: Zero data loss with automatic failover, improved performance with local SQLite
- **Operators**: Simple deployment via client-manager.sh, comprehensive monitoring
- **Developers**: Clear separation of concerns, extensible architecture for Phases 2-3

### Problems This Solves
1. **Current Issue**: No automated database backup for SQLite deployments
2. **Current Issue**: Single sync container = single point of failure
3. **Current Issue**: Manual intervention required for conflict resolution
4. **Current Issue**: No authoritative state source across potential future multi-host deployments
5. **Future-proofing**: Enables Phase 2 host-to-host migrations

## What

### User-Visible Behavior

**Client Manager Integration**:
```bash
./client-manager.sh
# Select "3) Manage Existing Deployment" → Pick client
# Option: "Configure Database Sync"
  ├─ View sync status
  ├─ Configure sync interval (1m, 5m, hourly, daily)
  ├─ Trigger manual sync
  ├─ View conflict log
  ├─ Configure conflict resolution strategies
  └─ Test sync cluster failover
```

**Sync Cluster Status**:
```
Sync Cluster Status:
  Primary:   ✅ Running (Leader)
  Secondary: ✅ Running (Standby)
  Last Sync: 2 minutes ago
  Conflicts: 0
```

### Technical Requirements

#### Phase 1 Scope (This PRP)
- ✅ Supabase as authoritative state source with local caching
- ✅ HA sync containers (primary/secondary) with leader election
- ✅ Restricted database roles (no service keys in containers)
- ✅ Automated conflict resolution with configurable strategies
- ✅ One-way sync operational (SQLite → Supabase)
- ✅ Comprehensive monitoring with Prometheus metrics
- ✅ Full test suite (HA, conflicts, state authority, security)

#### Out of Scope (Future Phases)
- ❌ Bidirectional sync (Supabase → SQLite restore) - Phase 2
- ❌ Cross-host migration orchestration - Phase 2
- ❌ DNS automation - Phase 2
- ❌ mTLS authentication - Phase 3
- ❌ AI-driven sync scheduling - Phase 3

### Success Criteria
- [ ] Dual sync containers deployed with automatic failover <35 seconds
- [ ] Leader election verified with PostgreSQL atomic operations
- [ ] State cache consistency maintained across cluster
- [ ] All conflict resolution strategies functional (newest_wins, source_wins, target_wins, merge, manual)
- [ ] Sync operations complete in <60 seconds at p95
- [ ] Zero data loss during failover scenarios
- [ ] All security validations passing (no DELETE permissions, RLS policies active)
- [ ] Prometheus metrics exposed and dashboards functional
- [ ] Client-manager integration complete with all menu options working

---

## All Needed Context

### Project Management Integration

**Archon MCP Project**:
- **Project ID**: `038661b1-7e1c-40d0-b4f9-950db24c2a3f`
- **Project Title**: SQLite + Supabase Sync System (Phase 1)
- **Total Tasks**: 19 tasks tracked in Archon
- **Task Mapping**: See `archon-prp-task-mapping.md` for complete correspondence between Archon tasks and PRP implementation steps

**How to Use**:
1. **Track Progress**: Update Archon task status as you complete work
2. **Get Implementation Details**: Use this PRP for pseudocode, validation steps, and external docs
3. **Understand Dependencies**: Refer to task mapping document for dependency graph

**Archon Task Status**:
- ✅ Completed: 2 tasks (directory structure, documentation)
- ⏳ Ready: 1 task (schema deployment - SQL written, needs execution)
- 📝 Todo: 16 tasks (implementation work)

### CRITICAL: Must-Read Files from Existing Codebase

```yaml
# Existing Database Migration System (Study the Patterns!)
- file: mt/DB_MIGRATION/README.md
  why: Comprehensive migration patterns, security posture, rollback procedures
  critical: "Understand why Open WebUI uses public schema WITHOUT RLS"

- file: mt/DB_MIGRATION/db-migration-helper.sh
  why: Shell script patterns for Docker-based PostgreSQL operations
  critical: "Study backup_sqlite_database() and test_supabase_connection() functions"

- file: mt/client-manager.sh
  why: Integration point for sync configuration menu
  critical: "Function manage_single_deployment() shows menu integration pattern (lines 250-875)"

# Multi-Tenant Architecture
- file: mt/README.md
  why: Client naming conventions, container patterns, volume management
  critical: "Container naming: openwebui-CLIENT_NAME, volumes: openwebui-CLIENT_NAME-data"

# Current Sync Implementation Progress
- file: mt/SYNC/README.md
  why: Architecture overview, API reference, monitoring setup
  critical: "Already created - read to understand overall architecture"

- file: mt/SYNC/scripts/01-init-sync-schema.sql
  why: Database schema with 7 tables already designed
  critical: "Schema is ready - just needs deployment to Supabase"
```

### External Documentation & API References

```yaml
# PostgreSQL Leader Election (2025 Best Practices)
- url: https://tedkim.dev/posts/leader-election-with-postgresql/
  section: "Advisory Locks for Leader Election"
  critical: "pg_try_advisory_lock() provides atomic lock acquisition"

- url: https://ramitmittal.com/blog/general/leader-election-advisory-locks
  section: "Implementation Patterns"
  critical: "Advisory locks auto-release on session disconnect - use for heartbeat"

- url: https://github.com/janbjorge/notifelect
  section: "Python asyncio + PostgreSQL NOTIFY"
  critical: "Reference implementation for leader election with asyncio"

# SQLite WAL Mode (Official Docs)
- url: https://www.sqlite.org/wal.html
  section: "WAL Mode and Concurrent Readers/Writers"
  critical: "WAL provides more concurrency - readers don't block writers"

- url: https://sqlite.work/ensuring-consistent-backups-in-sqlite-wal-mode-without-disrupting-writers/
  section: "Consistent Backups Without Disrupting Writers"
  critical: "Use PRAGMA wal_checkpoint(TRUNCATE) before backup"

# FastAPI State Management (2025)
- url: https://pypi.org/project/fastapi-state/
  section: "State Management Utilities"
  critical: "New July 2025 package - decorator-based state injection"

- url: https://dev.to/sivakumarmanoharan/caching-in-fastapi-unlocking-high-performance-development-20ej
  section: "Cache-Aside Pattern Implementation"
  critical: "Load data into cache only on demand - exactly our StateManager pattern"

# Prometheus Metrics (2025 Best Practices)
- url: https://github.com/trallnag/prometheus-fastapi-instrumentator
  section: "FastAPI Instrumentation"
  critical: "Most popular library - auto-exposes /metrics endpoint"

- url: https://blog.greeden.me/en/2025/10/07/operations-friendly-observability-a-fastapi-implementation-guide-for-logs-metrics-and-traces-request-id-json-logs-prometheus-opentelemetry-and-dashboard-design/
  section: "Three Pillars of Observability (Oct 2025)"
  critical: "Request ID + JSON logs + RED metrics (latency/throughput/errors)"
```

### Known Gotchas & Library Quirks

```python
# CRITICAL: Supabase Connection Modes
# ⚠️ Session Mode (port 5432) vs Transaction Mode (port 6543)
# Session Mode: Supports prepared statements, better for long-lived connections
# Transaction Mode: Optimized for serverless, may not support all features
# CHOICE: Use Session Mode for sync containers (long-lived connections)
DATABASE_URL = "postgresql://postgres.PROJECT:PASS@REGION.pooler.supabase.com:5432/postgres"

# CRITICAL: PostgreSQL Row Level Security
# Open WebUI tables in public schema WITHOUT RLS (by design!)
# Create sync_metadata schema WITH RLS for sync system state
# DO NOT enable RLS on public.* tables - breaks Open WebUI authentication

# CRITICAL: Docker Container Patterns
# All PostgreSQL operations must use temporary Docker containers
# Reason: Host may not have psql/psycopg2 installed (see db-migration-helper.sh)
# Pattern:
docker run --rm -e DATABASE_URL="$url" ghcr.io/imagicrafter/open-webui:main python3 -c "..."

# CRITICAL: SQLite WAL Checkpointing
# Must checkpoint before consistent snapshot:
sqlite3 "$DB_PATH" "PRAGMA wal_checkpoint(TRUNCATE);"
# Then start IMMEDIATE transaction for consistent read

# CRITICAL: Python asyncio + PostgreSQL
# Use asyncpg (not psycopg2) for async operations
# psycopg2 is sync-only - blocks event loop
import asyncpg  # ✅ Async native
import psycopg2  # ❌ Sync only - don't use in async functions

# CRITICAL: Prometheus Metric Naming
# Must follow naming convention: subsystem_name_unit
# Examples:
#   sync_operations_total (Counter)
#   sync_duration_seconds (Histogram)
#   sync_container_is_leader (Gauge)
```

---

## Current Codebase Tree

```bash
open-webui/
├── backend/
│   └── open_webui/
│       ├── config.py              # OAuth and database configuration
│       ├── utils/oauth.py         # OAuth implementation
│       └── models/                # SQLAlchemy models
│           ├── users.py
│           ├── chats.py
│           └── oauth_sessions.py
├── mt/                            # Multi-tenant system
│   ├── README.md                  # Architecture docs
│   ├── client-manager.sh          # Main management script (1179 lines)
│   ├── start-template.sh          # Client deployment template
│   ├── DB_MIGRATION/              # Existing migration system
│   │   ├── README.md
│   │   ├── db-migration-helper.sh # Shell helper functions
│   │   └── migrate-db.py          # Python migration script
│   └── SYNC/                      # NEW - This PRP's output
│       ├── README.md              # ✅ Already created
│       ├── config/                # ⏳ To be populated
│       ├── docker/                # ⏳ Dockerfile, docker-compose
│       ├── python/                # ⏳ FastAPI service
│       ├── scripts/               # ⏳ Sync engine, deployment
│       │   └── 01-init-sync-schema.sql  # ✅ Already created
│       ├── tests/                 # ⏳ Test scripts
│       └── logs/                  # Runtime logs
└── PRPs/
    └── sqlite_supabase_migration_with_sync/
        ├── INITIALv2.md          # Original feature spec
        ├── README.md              # Project status tracker
        └── prp-phase1.md          # ← This PRP document
```

### Desired Codebase Tree (After This PRP)

```bash
mt/SYNC/
├── README.md                              # ✅ Already exists
├── config/
│   ├── conflict-resolution-default.json   # Default conflict strategies
│   └── sync-config-template.env           # Environment template
├── docker/
│   ├── Dockerfile                         # Sync container image
│   ├── entrypoint.sh                      # Container startup script
│   └── docker-compose.sync-ha.yml         # HA cluster deployment
├── python/
│   ├── __init__.py
│   ├── main.py                            # FastAPI application
│   ├── state_manager.py                   # Cache-aside state management
│   ├── leader_election.py                 # PostgreSQL-based leader election
│   ├── conflict_resolver.py               # Conflict resolution engine
│   ├── metrics.py                         # Prometheus metrics
│   └── requirements.txt                   # Python dependencies
├── scripts/
│   ├── 01-init-sync-schema.sql            # ✅ Already exists
│   ├── 02-create-sync-role.sql            # Restricted sync_service role
│   ├── 03-enable-rls.sql                  # Row-level security policies
│   ├── sync-client-to-supabase.sh         # Sync engine (WAL-aware)
│   └── deploy-sync-cluster.sh             # Deployment automation
├── tests/
│   ├── test-ha-failover.sh                # Leader election tests
│   ├── test-conflict-resolution.sh        # Conflict strategy tests
│   ├── test-state-authority.sh            # State consistency tests
│   └── test-security.sh                   # Permission validation tests
└── logs/                                   # Created at runtime
```

---

## Implementation Blueprint

### Phase 1 Task List (Execution Order)

```yaml
Task 1: Deploy Sync Metadata Schema to Supabase
  STATUS: Ready to execute (SQL already written)
  FILE: mt/SYNC/scripts/01-init-sync-schema.sql
  ACTION:
    - Login to Supabase project SQL Editor
    - Copy/paste 01-init-sync-schema.sql
    - Execute to create sync_metadata schema
    - Verify 7 tables + 3 views created
  VALIDATION: |
    SELECT count(*) FROM information_schema.tables
    WHERE table_schema = 'sync_metadata';
    -- Should return 7

Task 2: Create Restricted Database Role
  STATUS: Create SQL script
  FILE: mt/SYNC/scripts/02-create-sync-role.sql
  PSEUDOCODE: |
    -- Create role with LOGIN only
    CREATE ROLE sync_service WITH LOGIN ENCRYPTED PASSWORD 'generate-strong-password';

    -- Grant minimal permissions on sync_metadata
    GRANT USAGE ON SCHEMA sync_metadata TO sync_service;
    GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA sync_metadata TO sync_service;
    -- IMPORTANT: NO DELETE permission

    -- Grant permissions for each client schema (executed per client)
    GRANT USAGE ON SCHEMA {client_name} TO sync_service;
    GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA {client_name} TO sync_service;
    -- IMPORTANT: NO DELETE, NO DROP, NO CREATE permissions
  VALIDATION: |
    \du sync_service  -- Verify role exists
    -- Try unauthorized operation (should fail):
    DELETE FROM sync_metadata.hosts WHERE host_id = 'test';

Task 3: Enable Row Level Security Policies
  STATUS: Create SQL script
  FILE: mt/SYNC/scripts/03-enable-rls.sql
  PSEUDOCODE: |
    -- Enable RLS on sync_metadata tables
    ALTER TABLE sync_metadata.hosts ENABLE ROW LEVEL SECURITY;
    ALTER TABLE sync_metadata.client_deployments ENABLE ROW LEVEL SECURITY;

    -- Policy: Sync service can only see/modify its own host's data
    CREATE POLICY sync_host_isolation ON sync_metadata.hosts
        FOR ALL TO sync_service
        USING (host_id = current_setting('app.current_host_id'));

    -- Policy: Deployment isolation per host
    CREATE POLICY sync_deployment_isolation ON sync_metadata.client_deployments
        FOR ALL TO sync_service
        USING (host_id = current_setting('app.current_host_id'));
  VALIDATION: |
    -- As sync_service, attempt to read another host's data (should return 0 rows)
    SET app.current_host_id = 'host-1';
    SELECT * FROM sync_metadata.hosts WHERE host_id = 'host-2';

Task 4: Build StateManager Class (Python)
  STATUS: Create Python module
  FILE: mt/SYNC/python/state_manager.py
  DEPENDENCIES: asyncpg, asyncio
  PATTERN: Cache-aside with 5-minute TTL
  PSEUDOCODE: |
    import asyncio
    import time
    from typing import Dict, Optional
    import asyncpg

    class StateManager:
        def __init__(self, db_url: str, ttl: int = 300):
            self.db_url = db_url
            self.cache: Dict[str, dict] = {}
            self.cache_expiry: Dict[str, float] = {}
            self.ttl = ttl  # 5 minutes default
            self.pool: Optional[asyncpg.Pool] = None

        async def initialize(self):
            """Create connection pool"""
            self.pool = await asyncpg.create_pool(self.db_url, min_size=2, max_size=10)

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
            # CRITICAL: Update authoritative source first
            success = await self._update_supabase(key, state)

            if success:
                # Invalidate local cache to force refresh
                self._invalidate_cache(key)
                # Notify secondary container via Supabase event
                await self._notify_cluster(key, 'invalidate')

            return success

        def _is_cache_valid(self, key: str) -> bool:
            if key not in self.cache:
                return False
            return time.time() < self.cache_expiry[key]

        async def _fetch_from_supabase(self, key: str) -> dict:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT data FROM sync_metadata.state_cache WHERE key = $1", key
                )
                return row['data'] if row else {}

        async def _update_supabase(self, key: str, state: dict) -> bool:
            try:
                async with self.pool.acquire() as conn:
                    await conn.execute(
                        """INSERT INTO sync_metadata.state_cache (key, data, updated_at)
                           VALUES ($1, $2, NOW())
                           ON CONFLICT (key) DO UPDATE
                           SET data = EXCLUDED.data, updated_at = NOW()""",
                        key, state
                    )
                return True
            except Exception as e:
                print(f"State update failed: {e}")
                return False

        async def _notify_cluster(self, key: str, action: str):
            """Notify other nodes via cache_events table"""
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO sync_metadata.cache_events (cache_key, action)
                       VALUES ($1, $2)""",
                    key, action
                )
  VALIDATION: |
    pytest tests/test_state_manager.py -v
    # Test cases:
    # - test_cache_hit_avoids_db_query
    # - test_cache_miss_fetches_from_db
    # - test_update_invalidates_cache
    # - test_cache_expiry_after_ttl

Task 5: Implement LeaderElection Class (Python)
  STATUS: Create Python module
  FILE: mt/SYNC/python/leader_election.py
  DEPENDENCIES: asyncpg, asyncio
  PATTERN: PostgreSQL advisory locks + heartbeat
  PSEUDOCODE: |
    import asyncio
    import asyncpg
    from typing import Optional
    import logging

    logger = logging.getLogger(__name__)

    class LeaderElection:
        def __init__(self, cluster_name: str, node_id: str, db_url: str):
            self.cluster_name = cluster_name
            self.node_id = node_id
            self.db_url = db_url
            self.is_leader = False
            self.lease_duration = 60  # seconds
            self.pool: Optional[asyncpg.Pool] = None

        async def initialize(self):
            self.pool = await asyncpg.create_pool(self.db_url, min_size=1, max_size=3)

        async def participate(self):
            """Participate in leader election (run as background task)"""
            while True:
                try:
                    # Attempt to acquire or renew leadership
                    acquired = await self._try_acquire_leadership()

                    if acquired:
                        if not self.is_leader:
                            logger.info(f"Node {self.node_id} became LEADER")
                        self.is_leader = True
                        await self._perform_leader_duties()
                    else:
                        if self.is_leader:
                            logger.info(f"Node {self.node_id} lost leadership, now FOLLOWER")
                        self.is_leader = False
                        await self._perform_follower_duties()

                    # Sleep half the lease duration (renew before expiry)
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

            async with self.pool.acquire() as conn:
                result = await conn.fetchval(query, self.cluster_name, self.node_id)
                return result if result is not None else False

        async def _perform_leader_duties(self):
            """Leader-specific tasks"""
            # Process sync jobs from queue
            # Update metrics
            pass

        async def _perform_follower_duties(self):
            """Follower-specific tasks"""
            # Monitor leader health
            # Update local metrics
            pass
  VALIDATION: |
    pytest tests/test_leader_election.py -v
    # Test cases:
    # - test_first_node_becomes_leader
    # - test_second_node_becomes_follower
    # - test_leader_renewal_prevents_takeover
    # - test_follower_takes_over_after_lease_expiry

Task 6: Build ConflictResolver Engine (Python)
  STATUS: Create Python module
  FILE: mt/SYNC/python/conflict_resolver.py
  DEPENDENCIES: json, datetime
  PATTERN: Strategy pattern with configurable rules
  PSEUDOCODE: |
    import json
    from datetime import datetime
    from typing import Dict, Callable
    import asyncpg

    class ConflictResolver:
        def __init__(self, config_path: str, db_url: str):
            with open(config_path) as f:
                self.config = json.load(f)

            self.db_url = db_url
            self.strategies: Dict[str, Callable] = {
                'newest_wins': self._resolve_newest_wins,
                'source_wins': self._resolve_source_wins,
                'target_wins': self._resolve_target_wins,
                'merge': self._resolve_merge,
                'manual': self._flag_manual_resolution
            }

        async def resolve_conflict(self, table: str, source_row: dict,
                                   target_row: dict, client_id: str) -> dict:
            """Resolve conflict based on configured strategy"""
            strategy = self._get_strategy(table)

            # Log conflict detection
            await self._log_conflict(client_id, table, source_row, target_row, strategy)

            # Apply resolution strategy
            resolved = self.strategies[strategy](source_row, target_row, table)

            # Log resolution
            await self._log_resolution(client_id, table, resolved, strategy)

            return resolved

        def _get_strategy(self, table: str) -> str:
            """Get strategy for table, fall back to default"""
            table_config = self.config['conflict_resolution']['table_strategies']
            if table in table_config:
                return table_config[table]['strategy']
            return self.config['conflict_resolution']['default_strategy']

        def _resolve_newest_wins(self, source: dict, target: dict, table: str) -> dict:
            """Resolution: Use the row with most recent updated_at"""
            compare_field = self.config['conflict_resolution']['table_strategies'].get(
                table, {}
            ).get('compare_field', 'updated_at')

            source_time = datetime.fromisoformat(str(source[compare_field]))
            target_time = datetime.fromisoformat(str(target[compare_field]))

            return source if source_time > target_time else target

        def _resolve_source_wins(self, source: dict, target: dict, table: str) -> dict:
            """Resolution: Always use source (SQLite)"""
            return source

        def _resolve_target_wins(self, source: dict, target: dict, table: str) -> dict:
            """Resolution: Always use target (Supabase)"""
            return target

        def _resolve_merge(self, source: dict, target: dict, table: str) -> dict:
            """Resolution: Merge based on configured rules"""
            merge_rules = self.config['conflict_resolution']['table_strategies'][table]['merge_rules']
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
                    merged[field] = list(set(target.get(field, [])) | set(source.get(field, [])))

            return merged

        def _flag_manual_resolution(self, source: dict, target: dict, table: str) -> dict:
            """Resolution: Flag for manual review, keep target"""
            # Log with notify=true flag
            return target  # Keep existing until manual review

        async def _log_conflict(self, client_id: str, table: str, source: dict,
                                target: dict, strategy: str):
            """Log conflict to sync_metadata.conflict_log"""
            pool = await asyncpg.create_pool(self.db_url)
            async with pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO sync_metadata.conflict_log
                       (client_id, table_name, conflict_type, source_data, target_data,
                        resolution_strategy, detected_at)
                       VALUES ($1, $2, $3, $4, $5, $6, NOW())""",
                    client_id, table, 'update', json.dumps(source),
                    json.dumps(target), strategy
                )
            await pool.close()

        async def _log_resolution(self, client_id: str, table: str,
                                  resolved: dict, strategy: str):
            """Update conflict log with resolution"""
            # Update most recent conflict log entry with resolved_data
            pass
  VALIDATION: |
    pytest tests/test_conflict_resolver.py -v
    # Test cases:
    # - test_newest_wins_selects_correct_row
    # - test_source_wins_always_uses_sqlite
    # - test_merge_appends_lists
    # - test_manual_flags_for_review

Task 7: Create FastAPI Sync Container Service (Python)
  STATUS: Create Python application
  FILE: mt/SYNC/python/main.py
  DEPENDENCIES: fastapi, uvicorn, asyncpg
  PATTERN: FastAPI with background tasks
  PSEUDOCODE: |
    from fastapi import FastAPI, BackgroundTasks
    from contextlib import asynccontextmanager
    import asyncio

    from state_manager import StateManager
    from leader_election import LeaderElection
    from conflict_resolver import ConflictResolver
    from metrics import setup_metrics
    import os

    # Configuration from environment
    ROLE = os.getenv('ROLE', 'primary')  # primary or secondary
    CLUSTER_NAME = os.getenv('CLUSTER_NAME', 'default')
    NODE_ID = f"{CLUSTER_NAME}-{ROLE}"
    DATABASE_URL = os.getenv('DATABASE_URL')
    API_PORT = int(os.getenv('API_PORT', '9443'))

    # Global instances
    state_mgr: StateManager = None
    leader_election: LeaderElection = None
    conflict_resolver: ConflictResolver = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Startup and shutdown tasks"""
        global state_mgr, leader_election, conflict_resolver

        # Initialize components
        state_mgr = StateManager(DATABASE_URL)
        await state_mgr.initialize()

        leader_election = LeaderElection(CLUSTER_NAME, NODE_ID, DATABASE_URL)
        await leader_election.initialize()

        conflict_resolver = ConflictResolver('/app/config/conflict-resolution.json', DATABASE_URL)

        # Start leader election in background
        asyncio.create_task(leader_election.participate())

        yield  # App runs here

        # Cleanup on shutdown
        await state_mgr.pool.close()
        await leader_election.pool.close()

    app = FastAPI(lifespan=lifespan)

    # Setup Prometheus metrics
    setup_metrics(app)

    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "node_id": NODE_ID,
            "is_leader": leader_election.is_leader if leader_election else False,
            "role": ROLE
        }

    @app.get("/api/v1/state/{key}")
    async def get_state(key: str):
        """Get state from cache or Supabase"""
        state = await state_mgr.get_state(key)
        return {"key": key, "state": state}

    @app.put("/api/v1/state/{key}")
    async def update_state(key: str, state: dict):
        """Update state (writes to Supabase first, then invalidates cache)"""
        success = await state_mgr.update_state(key, state)
        return {"success": success}

    @app.post("/api/v1/sync/trigger/{client_name}")
    async def trigger_manual_sync(client_name: str, background_tasks: BackgroundTasks):
        """Trigger manual sync for a client (leader only)"""
        if not leader_election.is_leader:
            return {"error": "Only leader can trigger sync", "current_leader": "unknown"}

        # Add sync job to queue
        background_tasks.add_task(trigger_sync_job, client_name)
        return {"status": "queued", "client": client_name}

    async def trigger_sync_job(client_name: str):
        """Background task to trigger sync"""
        # Call sync-client-to-supabase.sh via subprocess
        import subprocess
        result = subprocess.run(
            ['/app/scripts/sync-client-to-supabase.sh', client_name],
            capture_output=True,
            text=True
        )
        # Log result
        pass

    if __name__ == "__main__":
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=API_PORT)
  VALIDATION: |
    # Start service
    python3 main.py
    # Test endpoints
    curl http://localhost:9443/health
    curl http://localhost:9443/api/v1/state/test-key
    curl -X PUT http://localhost:9443/api/v1/state/test-key -d '{"data":"value"}'

Task 8: Write Sync Engine Script (Bash)
  STATUS: Create shell script
  FILE: mt/SYNC/scripts/sync-client-to-supabase.sh
  DEPENDENCIES: sqlite3, docker, python3
  PATTERN: WAL checkpoint → read snapshot → batch insert with conflict resolution
  PSEUDOCODE: |
    #!/bin/bash

    # Usage: ./sync-client-to-supabase.sh CLIENT_NAME

    CLIENT_NAME=$1
    CONTAINER_NAME="openwebui-${CLIENT_NAME}"
    SQLITE_PATH="/app/backend/data/webui.db"

    # Get Supabase URL from environment (passed via sync container)
    SUPABASE_URL=$DATABASE_URL

    # Get last sync timestamp for this client from Supabase
    get_last_sync_timestamp() {
        docker exec "$CONTAINER_NAME" python3 -c "
    import asyncpg
    import asyncio

    async def get_timestamp():
        conn = await asyncpg.connect('$SUPABASE_URL')
        result = await conn.fetchval(
            'SELECT last_sync_at FROM sync_metadata.client_deployments WHERE client_id = \$1',
            '$CLIENT_NAME'
        )
        await conn.close()
        return result if result else '1970-01-01 00:00:00'

    print(asyncio.run(get_timestamp()))
    "
    }

    LAST_SYNC=$(get_last_sync_timestamp)

    # Checkpoint WAL for consistent snapshot
    docker exec "$CONTAINER_NAME" sqlite3 "$SQLITE_PATH" "PRAGMA wal_checkpoint(TRUNCATE);"

    # Begin IMMEDIATE transaction for consistent read
    docker exec "$CONTAINER_NAME" sqlite3 "$SQLITE_PATH" "BEGIN IMMEDIATE TRANSACTION;"

    # Get list of tables to sync
    TABLES="user auth tag config chat oauth_session function message"

    for table in $TABLES; do
        echo "Syncing table: $table"

        # Get changes since last sync
        changes=$(docker exec "$CONTAINER_NAME" sqlite3 -json "$SQLITE_PATH" "
            SELECT * FROM $table
            WHERE updated_at > '$LAST_SYNC'
        ")

        # Process each row with conflict detection
        echo "$changes" | jq -c '.[]' | while read -r row; do
            # Extract ID
            row_id=$(echo "$row" | jq -r '.id')

            # Check if row exists in Supabase (conflict detection)
            existing=$(docker run --rm -e DATABASE_URL="$SUPABASE_URL" \
                ghcr.io/imagicrafter/open-webui:main python3 -c "
    import asyncpg
    import asyncio
    import json

    async def check_exists():
        conn = await asyncpg.connect('$SUPABASE_URL')
        result = await conn.fetchrow(
            'SELECT * FROM ${CLIENT_NAME}.${table} WHERE id = \$1',
            '$row_id'
        )
        await conn.close()
        return json.dumps(dict(result)) if result else None

    print(asyncio.run(check_exists()))
    ")

            if [[ -n "$existing" ]]; then
                # Conflict detected - use conflict resolver
                resolved=$(python3 /app/python/conflict_resolver.py \
                    --table "$table" \
                    --source "$row" \
                    --target "$existing" \
                    --config "/app/config/conflict-resolution.json")

                # Apply resolved data
                echo "Conflict resolved for $table:$row_id"
                # INSERT resolved data to Supabase
            else
                # No conflict - insert normally
                echo "No conflict for $table:$row_id - inserting"
                # INSERT row to Supabase
            fi
        done
    done

    # Commit SQLite transaction
    docker exec "$CONTAINER_NAME" sqlite3 "$SQLITE_PATH" "COMMIT;"

    # Update last_sync_at timestamp in Supabase
    docker run --rm -e DATABASE_URL="$SUPABASE_URL" \
        ghcr.io/imagicrafter/open-webui:main python3 -c "
    import asyncpg
    import asyncio

    async def update_sync():
        conn = await asyncpg.connect('$SUPABASE_URL')
        await conn.execute(
            '''UPDATE sync_metadata.client_deployments
               SET last_sync_at = NOW()
               WHERE client_id = \$1''',
            '$CLIENT_NAME'
        )
        await conn.close()

    asyncio.run(update_sync())
    "

    echo "✅ Sync complete for $CLIENT_NAME"
  VALIDATION: |
    # Test sync with dummy client
    ./sync-client-to-supabase.sh test-client
    # Verify data in Supabase
    # Check conflict_log for any detected conflicts

Task 9: Create Docker Image for Sync Container
  STATUS: Create Dockerfile
  FILE: mt/SYNC/docker/Dockerfile
  DEPENDENCIES: Python 3.11, FastAPI, asyncpg
  PSEUDOCODE: |
    FROM python:3.11-slim

    # Install system dependencies
    RUN apt-get update && apt-get install -y \
        sqlite3 \
        curl \
        && rm -rf /var/lib/apt/lists/*

    # Install Python dependencies
    WORKDIR /app
    COPY python/requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt

    # Copy application code
    COPY python/ /app/python/
    COPY scripts/ /app/scripts/
    COPY config/ /app/config/

    # Make scripts executable
    RUN chmod +x /app/scripts/*.sh

    # Expose API port
    EXPOSE 9443

    # Health check
    HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
        CMD curl -f http://localhost:9443/health || exit 1

    # Entry point
    COPY docker/entrypoint.sh /entrypoint.sh
    RUN chmod +x /entrypoint.sh
    ENTRYPOINT ["/entrypoint.sh"]

  FILE: mt/SYNC/docker/entrypoint.sh
  PSEUDOCODE: |
    #!/bin/bash
    set -e

    # Validate required environment variables
    : ${DATABASE_URL:?ERROR: DATABASE_URL not set}
    : ${ROLE:?ERROR: ROLE not set (primary or secondary)}
    : ${CLUSTER_NAME:?ERROR: CLUSTER_NAME not set}

    echo "Starting sync container..."
    echo "Role: $ROLE"
    echo "Cluster: $CLUSTER_NAME"
    echo "Node ID: ${CLUSTER_NAME}-${ROLE}"

    # Start FastAPI application
    exec python3 /app/python/main.py
  VALIDATION: |
    # Build image
    docker build -t ghcr.io/imagicrafter/openwebui-sync:latest .
    # Test run
    docker run --rm -e DATABASE_URL=postgresql://... -e ROLE=primary \
        -e CLUSTER_NAME=test ghcr.io/imagicrafter/openwebui-sync:latest

Task 10: Write Docker Compose for HA Cluster
  STATUS: Create docker-compose file
  FILE: mt/SYNC/docker/docker-compose.sync-ha.yml
  PSEUDOCODE: |
    version: '3.8'

    services:
      sync-primary:
        image: ghcr.io/imagicrafter/openwebui-sync:latest
        container_name: openwebui-sync-primary
        environment:
          - ROLE=primary
          - API_PORT=9443
          - CLUSTER_NAME=${HOST_NAME:-prod-host-1}
          - HEARTBEAT_INTERVAL=30
          - DATABASE_URL=${SUPABASE_URL}
        volumes:
          - /var/run/docker.sock:/var/run/docker.sock:ro
          - ./config:/app/config:ro
          - ./logs:/app/logs
        ports:
          - "9443:9443"
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
          - CLUSTER_NAME=${HOST_NAME:-prod-host-1}
          - HEARTBEAT_INTERVAL=30
          - DATABASE_URL=${SUPABASE_URL}
        volumes:
          - /var/run/docker.sock:/var/run/docker.sock:ro
          - ./config:/app/config:ro
          - ./logs:/app/logs
        ports:
          - "9444:9444"
        restart: unless-stopped
        depends_on:
          - sync-primary
  VALIDATION: |
    # Start cluster
    docker-compose -f docker-compose.sync-ha.yml up -d
    # Verify both containers running
    docker ps | grep openwebui-sync
    # Check leader election
    curl http://localhost:9443/health
    curl http://localhost:9444/health

Task 11: Add Prometheus Metrics
  STATUS: Create metrics module
  FILE: mt/SYNC/python/metrics.py
  DEPENDENCIES: prometheus-fastapi-instrumentator
  PSEUDOCODE: |
    from prometheus_client import Counter, Gauge, Histogram
    from prometheus_fastapi_instrumentator import Instrumentator

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
    cache_hits = Counter('state_cache_hits_total', 'Cache hit count')
    cache_misses = Counter('state_cache_misses_total', 'Cache miss count')
    state_sync_lag_seconds = Gauge(
        'state_sync_lag_seconds',
        'Time since last state sync with Supabase'
    )

    def setup_metrics(app):
        """Setup Prometheus metrics for FastAPI app"""
        Instrumentator().instrument(app).expose(app, endpoint="/metrics")
  VALIDATION: |
    # Start service and check metrics endpoint
    curl http://localhost:9443/metrics
    # Should see all defined metrics in Prometheus format

Task 12: Integrate with Client Manager
  STATUS: Modify existing script
  FILE: mt/client-manager.sh
  ACTION: Add sync configuration menu to manage_single_deployment()
  PSEUDOCODE: |
    # Add new menu option after line 318 (database migration option)
    # New option: "9) Configure Database Sync"

    configure_database_sync() {
        local client_name="$1"

        while true; do
            clear
            echo "╔════════════════════════════════════════╗"
            echo "║      Database Sync Configuration       ║"
            echo "╚════════════════════════════════════════╝"
            echo

            # Check sync cluster health
            local primary_health=$(curl -s http://localhost:9443/health 2>/dev/null || echo '{"status":"unavailable"}')
            local secondary_health=$(curl -s http://localhost:9444/health 2>/dev/null || echo '{"status":"unavailable"}')

            echo "Sync Cluster Status:"
            echo "  Primary:   $(echo $primary_health | jq -r .status)"
            echo "  Secondary: $(echo $secondary_health | jq -r .status)"
            echo "  Leader:    $(echo $primary_health | jq -r .node_id)"
            echo

            echo "1) View sync status for deployment"
            echo "2) Configure sync interval"
            echo "3) Trigger manual sync"
            echo "4) View conflict log"
            echo "5) Configure conflict resolution"
            echo "6) Test sync cluster failover"
            echo "7) Return to deployment menu"
            echo
            echo -n "Select option (1-7): "
            read option

            case "$option" in
                1) view_sync_status "$client_name" ;;
                2) configure_sync_interval "$client_name" ;;
                3) trigger_manual_sync_via_api "$client_name" ;;
                4) view_conflict_log "$client_name" ;;
                5) configure_conflict_resolution "$client_name" ;;
                6) test_sync_failover ;;
                7) return ;;
            esac
        done
    }

    view_conflict_log() {
        local client_name=$1

        echo "Recent conflicts for $client_name:"
        echo

        # Query Supabase via Docker container
        docker run --rm -e DATABASE_URL="$SUPABASE_URL" \
            ghcr.io/imagicrafter/open-webui:main python3 -c "
    import asyncpg
    import asyncio

    async def get_conflicts():
        conn = await asyncpg.connect('$DATABASE_URL')
        rows = await conn.fetch('''
            SELECT detected_at, table_name, conflict_type,
                   resolution_strategy, resolved_by
            FROM sync_metadata.conflict_log
            WHERE client_id = \$1
            ORDER BY detected_at DESC
            LIMIT 20
        ''', '$client_name')
        await conn.close()

        for row in rows:
            print(f\"{row['detected_at']} | {row['table_name']} | {row['resolution_strategy']}\")

    asyncio.run(get_conflicts())
    "

        echo
        echo "Press Enter to continue..."
        read
    }

    test_sync_failover() {
        echo "Testing sync cluster failover..."
        echo
        echo "Current leader: $(curl -s http://localhost:9443/health | jq -r .node_id)"
        echo
        echo "Stopping primary container to trigger failover..."
        docker stop openwebui-sync-primary

        echo "Waiting for failover (35 seconds)..."
        sleep 35

        echo "New leader: $(curl -s http://localhost:9444/health | jq -r .node_id)"
        echo
        echo "Restarting primary container..."
        docker start openwebui-sync-primary

        echo "Failover test complete!"
        echo
        echo "Press Enter to continue..."
        read
    }
  VALIDATION: |
    ./client-manager.sh
    # Navigate to deployment → Option 9: Configure Database Sync
    # Test all sub-menu options

Task 13: Create Deployment Script
  STATUS: Create shell script
  FILE: mt/SYNC/scripts/deploy-sync-cluster.sh
  PSEUDOCODE: |
    #!/bin/bash

    # Deploy HA Sync Cluster

    echo "╔════════════════════════════════════════╗"
    echo "║    Deploy Sync Cluster (HA Mode)      ║"
    echo "╚════════════════════════════════════════╝"
    echo

    # Get Supabase configuration
    echo "Enter Supabase connection details:"
    echo -n "Project Reference: "
    read PROJECT_REF

    echo -n "Database Password: "
    read -s PASSWORD
    echo

    echo -n "Region (e.g., aws-1-us-east-2): "
    read REGION

    # Build DATABASE_URL
    DATABASE_URL="postgresql://postgres.${PROJECT_REF}:${PASSWORD}@${REGION}.pooler.supabase.com:5432/postgres"

    # Generate sync_service password
    SYNC_PASSWORD=$(openssl rand -base64 32)

    # Create sync_service role in Supabase
    echo
    echo "Creating sync_service database role..."
    docker run --rm -e DATABASE_URL="$DATABASE_URL" \
        ghcr.io/imagicrafter/open-webui:main python3 -c "
    import asyncpg
    import asyncio

    async def create_role():
        conn = await asyncpg.connect('$DATABASE_URL')
        await conn.execute('''
            CREATE ROLE sync_service WITH LOGIN ENCRYPTED PASSWORD '$SYNC_PASSWORD'
        ''')
        await conn.execute('''
            GRANT USAGE ON SCHEMA sync_metadata TO sync_service;
            GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA sync_metadata TO sync_service;
        ''')
        await conn.close()
        print('✅ sync_service role created')

    asyncio.run(create_role())
    "

    # Update DATABASE_URL to use sync_service
    SYNC_DATABASE_URL="postgresql://sync_service:${SYNC_PASSWORD}@${REGION}.pooler.supabase.com:5432/postgres"

    # Export environment variables
    export SUPABASE_URL="$SYNC_DATABASE_URL"
    export HOST_NAME=$(hostname)

    # Deploy HA containers
    echo
    echo "Deploying sync cluster..."
    cd "$(dirname "$0")/../docker"
    docker-compose -f docker-compose.sync-ha.yml up -d

    # Wait for leader election
    echo "Waiting for leader election (10 seconds)..."
    sleep 10

    # Verify cluster health
    echo
    echo "Verifying cluster health..."
    curl -f http://localhost:9443/health || { echo "❌ Primary unhealthy"; exit 1; }
    curl -f http://localhost:9444/health || { echo "❌ Secondary unhealthy"; exit 1; }

    echo
    echo "✅ HA Sync cluster deployed successfully"
    echo
    echo "Cluster endpoints:"
    echo "  Primary:   http://localhost:9443/health"
    echo "  Secondary: http://localhost:9444/health"
    echo "  Metrics:   http://localhost:9443/metrics"
  VALIDATION: |
    ./deploy-sync-cluster.sh
    # Enter Supabase credentials when prompted
    # Verify both containers running
    # Check leader election worked

Task 14-17: Write Test Scripts
  STATUS: Create test scripts

  FILE: mt/SYNC/tests/test-ha-failover.sh
  PSEUDOCODE: |
    #!/bin/bash
    # HA Failover Test

    echo "Test 1: Primary is leader on startup"
    primary_leader=$(curl -s http://localhost:9443/health | jq -r .is_leader)
    [[ "$primary_leader" == "true" ]] || { echo "❌ FAIL"; exit 1; }
    echo "✅ PASS"

    echo "Test 2: Kill primary, verify secondary takes over"
    docker stop openwebui-sync-primary
    sleep 35  # Wait for lease expiration
    secondary_leader=$(curl -s http://localhost:9444/health | jq -r .is_leader)
    [[ "$secondary_leader" == "true" ]] || { echo "❌ FAIL"; exit 1; }
    echo "✅ PASS"

    echo "Test 3: Restart primary, verify it becomes follower"
    docker start openwebui-sync-primary
    sleep 10
    primary_leader=$(curl -s http://localhost:9443/health | jq -r .is_leader)
    [[ "$primary_leader" == "false" ]] || { echo "❌ FAIL"; exit 1; }
    echo "✅ PASS"

    echo "All HA failover tests passed! ✅"

  FILE: mt/SYNC/tests/test-conflict-resolution.sh
  PSEUDOCODE: |
    #!/bin/bash
    # Conflict Resolution Test

    # Test newest_wins strategy
    echo "Test: newest_wins strategy"
    # Create conflicting rows with different updated_at
    # Run sync, verify newest row wins

    # Test source_wins strategy
    echo "Test: source_wins strategy"
    # Update config to use source_wins for test table
    # Create conflict, verify SQLite version wins

    # Test merge strategy
    echo "Test: merge strategy"
    # Configure merge rules for test table
    # Create conflict with list fields
    # Verify lists appended correctly

  FILE: mt/SYNC/tests/test-state-authority.sh
  PSEUDOCODE: |
    #!/bin/bash
    # State Authority Test

    echo "Test: Supabase is authoritative source"
    # Update state via API
    curl -X PUT http://localhost:9443/api/v1/state/test-key \
      -d '{"data":"from-api"}'

    # Verify Supabase updated first
    # (Query Supabase directly, check value)

    # Kill primary, verify secondary reads correct state
    docker stop openwebui-sync-primary
    sleep 5
    state=$(curl -s http://localhost:9444/api/v1/state/test-key | jq -r .state.data)
    [[ "$state" == "from-api" ]] || { echo "❌ FAIL"; exit 1; }
    echo "✅ PASS: Secondary has correct state from Supabase"

  FILE: mt/SYNC/tests/test-security.sh
  PSEUDOCODE: |
    #!/bin/bash
    # Security Validation Test

    # Test 1: sync_service cannot DELETE
    echo "Test: sync_service DELETE should fail"
    docker run --rm -e DATABASE_URL="$SYNC_URL" \
        ghcr.io/imagicrafter/open-webui:main python3 -c "
    import asyncpg
    import asyncio

    async def test_delete():
        try:
            conn = await asyncpg.connect('$SYNC_URL')
            await conn.execute('DELETE FROM sync_metadata.hosts WHERE host_id = \\'test\\'')
            print('❌ FAIL: DELETE succeeded (should have failed)')
        except Exception as e:
            if 'permission denied' in str(e):
                print('✅ PASS: DELETE denied as expected')
            else:
                print(f'❌ FAIL: Wrong error: {e}')

    asyncio.run(test_delete())
    "

    # Test 2: sync_service cannot DROP schema
    echo "Test: sync_service DROP should fail"
    # Similar test for DROP SCHEMA

  VALIDATION: |
    # Run all tests
    cd mt/SYNC/tests
    ./test-ha-failover.sh
    ./test-conflict-resolution.sh
    ./test-state-authority.sh
    ./test-security.sh

Task 18: Create Configuration Files
  STATUS: Create config files

  FILE: mt/SYNC/config/conflict-resolution-default.json
  PSEUDOCODE: |
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

  FILE: mt/SYNC/config/sync-config-template.env
  PSEUDOCODE: |
    # Supabase Connection
    DATABASE_URL=postgresql://sync_service:PASSWORD@REGION.pooler.supabase.com:5432/postgres

    # Cluster Configuration
    HOST_NAME=prod-host-1
    CLUSTER_NAME=prod-host-1

    # Sync Settings
    DEFAULT_SYNC_INTERVAL=300  # 5 minutes
    BATCH_SIZE=1000

    # HA Settings
    HEARTBEAT_INTERVAL=30
    LEASE_DURATION=60

    # Monitoring
    ENABLE_METRICS=true
    METRICS_PORT=9443

Task 19: Run Full Validation Suite
  STATUS: Final validation
  CHECKLIST: |
    Infrastructure:
    - [ ] Both sync containers running
    - [ ] Leader election functional
    - [ ] Primary has API on port 9443
    - [ ] Secondary has health check on port 9444

    Database:
    - [ ] sync_metadata schema created (7 tables)
    - [ ] sync_service role created with restricted permissions
    - [ ] RLS policies enabled and functional
    - [ ] No DELETE permission on any schema

    Functionality:
    - [ ] Manual sync triggered via API works
    - [ ] Conflict resolution strategies functional
    - [ ] State management cache-aside pattern working
    - [ ] Cache invalidation across cluster verified

    High Availability:
    - [ ] Primary failure triggers secondary takeover <35s
    - [ ] Primary restart becomes follower
    - [ ] No data loss during failover

    Security:
    - [ ] sync_service cannot DELETE rows
    - [ ] sync_service cannot DROP schemas
    - [ ] RLS prevents cross-host data access
    - [ ] No service role keys in containers

    Monitoring:
    - [ ] Prometheus /metrics endpoint responding
    - [ ] All defined metrics present
    - [ ] Grafana dashboard showing metrics (manual setup)

    Integration:
    - [ ] Client-manager.sh sync menu functional
    - [ ] All menu options working
    - [ ] Conflict log viewer working
    - [ ] Manual sync trigger working

  COMMANDS: |
    # Full test suite
    cd mt/SYNC/tests
    ./test-ha-failover.sh && \
    ./test-conflict-resolution.sh && \
    ./test-state-authority.sh && \
    ./test-security.sh

    # Check metrics
    curl http://localhost:9443/metrics | grep sync_

    # Verify client-manager integration
    ./mt/client-manager.sh
    # Navigate to: Manage Deployment → Configure Database Sync
```

---

## Validation Loop

### Level 1: Syntax & Type Checking

```bash
# Python syntax and type checking (run before each commit)
cd mt/SYNC/python

# Syntax check
python3 -m py_compile *.py

# Type checking (requires mypy)
pip install mypy
mypy --strict main.py state_manager.py leader_election.py conflict_resolver.py

# Expected: No errors
```

### Level 2: Unit Tests

```python
# Create comprehensive unit tests
# mt/SYNC/tests/test_state_manager_unit.py

import pytest
import asyncio
from python.state_manager import StateManager

@pytest.mark.asyncio
async def test_cache_hit_avoids_db_query():
    """Cache hit should not query database"""
    mgr = StateManager("postgresql://test")
    await mgr.initialize()

    # Prime cache
    await mgr.update_state("key1", {"value": "test"})

    # Should use cache (no DB query)
    result = await mgr.get_state("key1")
    assert result == {"value": "test"}

@pytest.mark.asyncio
async def test_cache_expiry_forces_refresh():
    """Expired cache should refresh from DB"""
    mgr = StateManager("postgresql://test", ttl=1)  # 1 second TTL
    await mgr.initialize()

    # Prime cache
    await mgr.update_state("key1", {"value": "old"})

    # Wait for expiry
    await asyncio.sleep(2)

    # Should refresh from DB
    result = await mgr.get_state("key1")
    # Verify DB was queried

@pytest.mark.asyncio
async def test_update_invalidates_cache():
    """Update should invalidate cache"""
    mgr = StateManager("postgresql://test")
    await mgr.initialize()

    # Prime cache
    await mgr.get_state("key1")

    # Update should invalidate
    await mgr.update_state("key1", {"value": "new"})

    # Next get should fetch from DB
    result = await mgr.get_state("key1")
    assert result == {"value": "new"}

# Run tests
# pytest mt/SYNC/tests/ -v --asyncio-mode=auto
```

### Level 3: Integration Tests

```bash
# Full integration test with real Supabase instance

# 1. Start test environment
cd mt/SYNC
export TEST_DATABASE_URL="postgresql://postgres:testpass@localhost:5432/postgres"
docker-compose -f docker/docker-compose.sync-ha.yml up -d

# 2. Deploy schema
psql "$TEST_DATABASE_URL" < scripts/01-init-sync-schema.sql
psql "$TEST_DATABASE_URL" < scripts/02-create-sync-role.sql
psql "$TEST_DATABASE_URL" < scripts/03-enable-rls.sql

# 3. Run integration tests
./tests/test-ha-failover.sh
./tests/test-conflict-resolution.sh
./tests/test-state-authority.sh
./tests/test-security.sh

# 4. Verify metrics
curl http://localhost:9443/metrics | grep -E "(sync_|conflict_|leader_)"

# Expected: All tests pass, metrics present
```

### Level 4: End-to-End Test

```bash
# Real-world scenario test

# 1. Create test client deployment
cd mt
./start-template.sh test-sync-client 8091

# 2. Add some test data
docker exec openwebui-test-sync-client sqlite3 /app/backend/data/webui.db <<EOF
INSERT INTO user (id, name, email, created_at, updated_at)
VALUES ('test-1', 'Test User', 'test@example.com', datetime('now'), datetime('now'));

INSERT INTO chat (id, user_id, title, created_at, updated_at)
VALUES ('chat-1', 'test-1', 'Test Chat', datetime('now'), datetime('now'));
EOF

# 3. Trigger manual sync via API
curl -X POST http://localhost:9443/api/v1/sync/trigger/test-sync-client

# 4. Verify data in Supabase
psql "$SUPABASE_URL" -c "SELECT * FROM test_sync_client.user WHERE id = 'test-1';"
# Expected: User row present

# 5. Test failover scenario
docker stop openwebui-sync-primary
sleep 35
# Secondary should be leader now
curl http://localhost:9444/health | jq .is_leader
# Expected: true

# 6. Trigger sync from secondary
curl -X POST http://localhost:9444/api/v1/sync/trigger/test-sync-client
# Expected: Sync works from secondary

# 7. Cleanup
docker start openwebui-sync-primary
docker stop openwebui-test-sync-client
docker rm openwebui-test-sync-client
```

---

## Final Validation Checklist

Before marking Phase 1 complete, verify:

### Infrastructure ✅
- [ ] Dual sync containers deployed and healthy
- [ ] Leader election working with PostgreSQL atomic ops
- [ ] Primary API accessible on port 9443
- [ ] Secondary health check on port 9444
- [ ] Docker image built and pushed to ghcr.io

### Database ✅
- [ ] `sync_metadata` schema with 7 tables created
- [ ] `sync_service` role with restricted permissions
- [ ] RLS policies enabled and functional
- [ ] Test: sync_service cannot DELETE (permission denied)
- [ ] Test: sync_service cannot DROP schema (permission denied)

### Core Functionality ✅
- [ ] State management cache-aside pattern working
- [ ] Cache invalidation across cluster verified
- [ ] Conflict resolution all 5 strategies functional
- [ ] Manual sync trigger via API working
- [ ] Sync engine handles WAL checkpointing correctly

### High Availability ✅
- [ ] Failover time <35 seconds verified
- [ ] Secondary takes over when primary fails
- [ ] Primary becomes follower when restarted
- [ ] Zero data loss during failover scenarios
- [ ] Leader election logs showing correct behavior

### Security ✅
- [ ] No service role keys in containers (using sync_service)
- [ ] RLS prevents cross-host data access
- [ ] All unauthorized operations fail correctly
- [ ] Credentials encrypted in Docker secrets
- [ ] Audit trail in conflict_log functional

### Monitoring ✅
- [ ] Prometheus /metrics endpoint accessible
- [ ] All defined metrics present (sync_, conflict_, leader_, cache_)
- [ ] RED metrics functional (latency, throughput, errors)
- [ ] Health check endpoints returning correct status
- [ ] Grafana dashboard (manual setup - not in PRP scope)

### Integration ✅
- [ ] client-manager.sh integration complete
- [ ] Sync configuration menu accessible
- [ ] All sub-menu options working
- [ ] Conflict log viewer functional
- [ ] Failover test option working

### Performance ✅
- [ ] Sync operations <60s at p95
- [ ] Cache hit rate >80% for state queries
- [ ] Leader election latency <5s
- [ ] No memory leaks during 24h test

---

## Anti-Patterns to Avoid

```python
# ❌ Don't use psycopg2 in async context
import psycopg2  # Blocks event loop!
async def bad_query():
    conn = psycopg2.connect(url)  # ❌ Sync call in async function

# ✅ Do use asyncpg
import asyncpg
async def good_query():
    conn = await asyncpg.connect(url)  # ✅ Async native

# ❌ Don't enable RLS on Open WebUI public schema tables
ALTER TABLE public.user ENABLE ROW LEVEL SECURITY;  # ❌ Breaks authentication!

# ✅ Do enable RLS on sync_metadata schema only
ALTER TABLE sync_metadata.hosts ENABLE ROW LEVEL SECURITY;  # ✅ Correct

# ❌ Don't use service role keys in containers
DATABASE_URL="postgresql://postgres.PROJECT:SERVICE_ROLE_KEY@..."  # ❌ Too powerful!

# ✅ Do use restricted sync_service role
DATABASE_URL="postgresql://sync_service:RESTRICTED_PASS@..."  # ✅ Limited permissions

# ❌ Don't skip WAL checkpoint before snapshot
rows = sqlite3.execute("SELECT * FROM user")  # ❌ May read inconsistent data

# ✅ Do checkpoint first
sqlite3.execute("PRAGMA wal_checkpoint(TRUNCATE);")
sqlite3.execute("BEGIN IMMEDIATE TRANSACTION;")
rows = sqlite3.execute("SELECT * FROM user")  # ✅ Consistent snapshot
```

---

## Dependencies & Requirements

### Python Requirements (mt/SYNC/python/requirements.txt)
```txt
fastapi==0.115.0
uvicorn[standard]==0.32.0
asyncpg==0.30.0
prometheus-client==0.21.0
prometheus-fastapi-instrumentator==7.0.0
pydantic==2.9.2
python-dotenv==1.0.1
```

### System Requirements
- Docker Engine 24.0+
- Docker Compose 2.20+
- Python 3.11+
- SQLite 3.40+ (with WAL mode support)
- PostgreSQL 15+ (Supabase)
- Bash 4.0+

### Supabase Requirements
- Supabase project (free tier acceptable for Phase 1)
- pgvector extension enabled (recommended)
- Connection pooling enabled (Session Mode)
- At least 500MB storage (free tier)

---

## Success Metrics

### Phase 1 Completion Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| Sync Latency (p95) | <60 seconds | Prometheus histogram |
| Failover Time | <35 seconds | Manual test |
| Cache Hit Rate | >80% | Prometheus counter ratio |
| Conflict Resolution Success | >95% | Conflicts resolved automatically |
| Zero Data Loss | 100% | No data loss in failover scenarios |
| Security Validation | 100% pass | All permission tests passing |
| Test Suite Pass Rate | 100% | All tests green |

---

## PRP Confidence Score: 8/10

### Strengths (+)
- Comprehensive context from existing codebase (DB_MIGRATION patterns)
- Clear task breakdown with pseudocode for all components
- Executable validation gates at every level
- External research included (2025 best practices)
- Security considerations deeply integrated
- HA patterns proven in production systems

### Risks & Mitigations (-)
- **Risk**: Leader election race conditions
  - **Mitigation**: PostgreSQL atomic operations guarantee correctness
- **Risk**: Cache inconsistency across cluster
  - **Mitigation**: Cache invalidation events in sync_metadata.cache_events
- **Risk**: SQLite WAL checkpoint blocking writers
  - **Mitigation**: TRUNCATE mode releases locks immediately
- **Score reduction**: Some test scripts need real environment (can't dry-run)
  - **Mitigation**: Integration tests provide comprehensive coverage

### Estimated Implementation Time
- **Experienced Developer**: 3-4 weeks (following this PRP)
- **AI Agent (Claude)**: 6-8 hours of active coding sessions
- **Testing & Validation**: 1-2 days

---

## Next Steps After Phase 1

Once Phase 1 is complete and validated, Phase 2 will add:

1. **Bidirectional Sync** (Supabase → SQLite restore)
2. **Cross-Host Migration Orchestration**
3. **DNS Automation** (provider abstraction for Cloudflare/Route53)
4. **SSL Certificate Management** (Let's Encrypt automation)
5. **Blue-Green Deployment Support**

Phase 2 PRP will be generated separately after Phase 1 validation.

---

## References & Resources

### Official Documentation
- [PostgreSQL 18 Documentation](https://www.postgresql.org/docs/current/)
- [SQLite WAL Mode](https://www.sqlite.org/wal.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [asyncpg Documentation](https://magicstack.github.io/asyncpg/current/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)

### GitHub Repositories
- [prometheus-fastapi-instrumentator](https://github.com/trallnag/prometheus-fastapi-instrumentator)
- [notifelect - Python Leader Election](https://github.com/janbjorge/notifelect)

### Articles (2025)
- [Leader Election with PostgreSQL](https://tedkim.dev/posts/leader-election-with-postgresql/)
- [FastAPI Observability Guide (Oct 2025)](https://blog.greeden.me/en/2025/10/07/operations-friendly-observability-a-fastapi-implementation-guide-for-logs-metrics-and-traces-request-id-json-logs-prometheus-opentelemetry-and-dashboard-design/)
- [SQLite Consistent Backups in WAL Mode](https://sqlite.work/ensuring-consistent-backups-in-sqlite-wal-mode-without-disrupting-writers/)

---

## Project Management & Task Tracking

### Archon MCP Integration

This PRP is fully integrated with Archon MCP for project management:

**Project Details**:
- **Archon Project ID**: `038661b1-7e1c-40d0-b4f9-950db24c2a3f`
- **Project Title**: SQLite + Supabase Sync System (Phase 1)
- **GitHub Repo**: https://github.com/imagicrafter/open-webui
- **Total Tasks**: 19 tasks

**Task Status Summary**:
- ✅ **Completed**: 2 tasks
  - Directory structure created (`mt/SYNC/`)
  - Documentation created (`mt/SYNC/README.md`)
- ⏳ **Ready to Deploy**: 1 task
  - Schema SQL written (`scripts/01-init-sync-schema.sql`)
- 📝 **Todo**: 16 implementation tasks

**How to Use Archon + PRP Together**:

1. **Find Your Next Task**:
   ```bash
   # Via Archon MCP
   find_tasks(project_id="038661b1-7e1c-40d0-b4f9-950db24c2a3f",
              filter_by="status", filter_value="todo")
   ```

2. **Get Implementation Details**:
   - Look up task in `archon-prp-task-mapping.md`
   - Jump to corresponding PRP Task section
   - Follow pseudocode and validation steps

3. **Update Progress**:
   ```bash
   # Mark task as doing
   manage_task("update", task_id="...", status="doing")

   # Mark task as done when complete
   manage_task("update", task_id="...", status="done")
   ```

4. **Track Dependencies**:
   - Refer to dependency graph in task mapping document
   - Complete prerequisite tasks before starting dependent ones

**Key Documents**:
- **This PRP**: Implementation blueprint with pseudocode and context
- **Task Mapping**: `archon-prp-task-mapping.md` - Archon ↔ PRP correspondence
- **Project Status**: `README.md` - High-level progress tracking
- **Archon Dashboard**: Access via Archon MCP tools

### Next Immediate Steps

Based on current progress, the next steps are:

1. **Deploy Schema** (Archon #112, PRP Task 1)
   - Open Supabase SQL Editor
   - Execute `mt/SYNC/scripts/01-init-sync-schema.sql`
   - Validate 7 tables + 3 views created
   - Update Archon task status to "done"

2. **Create Security Role** (Archon #106, PRP Task 2)
   - Write `scripts/02-create-sync-role.sql`
   - Create sync_service role with restricted permissions
   - Test unauthorized operations fail

3. **Enable RLS** (New task, PRP Task 3)
   - Write `scripts/03-enable-rls.sql`
   - Apply host isolation policies
   - Validate cross-host access denied

4. **Start Python Development** (Archon #100, #94, #88)
   - Implement StateManager (Task 4)
   - Implement LeaderElection (Task 5)
   - Implement ConflictResolver (Task 6)

---

**PRP Version**: 1.0
**Created**: 2025-10-08
**Last Updated**: 2025-10-08
**Status**: Ready for Implementation
**Archon Project**: `038661b1-7e1c-40d0-b4f9-950db24c2a3f`
**Task Mapping**: `archon-prp-task-mapping.md`
**Estimated Implementation Time**: 3-4 weeks (experienced developer) | 6-8 hours (AI agent)
