# Archon Tasks ↔ PRP Implementation Mapping

**Project**: SQLite + Supabase Sync System (Phase 1)
**Archon Project ID**: `038661b1-7e1c-40d0-b4f9-950db24c2a3f`
**PRP Document**: `PRPs/sqlite_supabase_migration_with_sync/prp-phase1.md`
**Last Updated**: 2025-10-08

---

## Overview

This document maps the **19 Archon tasks** (project management) to the **19 PRP implementation tasks** (detailed blueprint). Use this to understand:
- Which PRP section provides implementation details for each Archon task
- Current status of each task
- Dependencies between tasks

**Key Principle**:
- **Archon** = What needs to be done (project tracking)
- **PRP** = How to do it (implementation guide with pseudocode, validation, external docs)

---

## Task Mapping Table

| Archon Task Order | Archon Task Title | PRP Task # | PRP Section | Status | Notes |
|-------------------|-------------------|------------|-------------|--------|-------|
| 118 (highest) | Create project directory structure | Task 1 | Implementation Blueprint | ✅ Done | mt/SYNC/ created with subdirs |
| 112 | Implement Supabase schema | Task 1 | Implementation Blueprint | ⏳ Ready | SQL already written, needs deployment |
| 106 | Create restricted sync_service role | Task 2 | Implementation Blueprint | 📝 Todo | SQL script to create |
| 100 | Build Python StateManager | Task 4 | Implementation Blueprint | 📝 Todo | Cache-aside pattern |
| 94 | Implement LeaderElection class | Task 5 | Implementation Blueprint | 📝 Todo | PostgreSQL atomic ops |
| 88 | Build ConflictResolver | Task 6 | Implementation Blueprint | 📝 Todo | 5 strategies |
| 82 | Create FastAPI sync service | Task 7 | Implementation Blueprint | 📝 Todo | Main application |
| 76 | Write sync-client-to-supabase.sh | Task 8 | Implementation Blueprint | 📝 Todo | Bash sync engine |
| 70 | Create Docker image | Task 9 | Implementation Blueprint | 📝 Todo | Dockerfile + entrypoint |
| 64 | Write docker-compose.sync-ha.yml | Task 10 | Implementation Blueprint | 📝 Todo | HA cluster config |
| 58 | Add Prometheus metrics | Task 11 | Implementation Blueprint | 📝 Todo | Metrics module |
| 52 | Integrate with client-manager.sh | Task 12 | Implementation Blueprint | 📝 Todo | Sync config menu |
| 46 | Create deploy-sync-cluster.sh | Task 13 | Implementation Blueprint | 📝 Todo | Deployment automation |
| 40 | Write HA failover tests | Task 14 | Implementation Blueprint | 📝 Todo | Test scripts |
| 34 | Write conflict resolution tests | Task 15 | Implementation Blueprint | 📝 Todo | Test scripts |
| 28 | Write state authority tests | Task 16 | Implementation Blueprint | 📝 Todo | Test scripts |
| 22 | Write security validation tests | Task 17 | Implementation Blueprint | 📝 Todo | Test scripts |
| 16 | Create comprehensive documentation | Task 18 | Implementation Blueprint | ✅ Done | README.md created |
| 10 (lowest) | Run all Phase 1 validation tests | Task 19 | Implementation Blueprint | 📝 Todo | Final validation |

---

## Detailed Task Correspondence

### Infrastructure Tasks

#### Archon #118 → PRP Task 1 (Part 1)
**Archon**: Create project directory structure
**PRP**: Task 1 - Deploy Sync Metadata Schema
**Status**: ✅ COMPLETED
**What Was Done**:
```bash
mt/SYNC/
├── README.md                 ✅ Created
├── config/                   ✅ Created
├── docker/                   ✅ Created
├── python/                   ✅ Created
├── scripts/                  ✅ Created
│   └── 01-init-sync-schema.sql  ✅ Created (507 lines)
├── tests/                    ✅ Created
└── logs/                     ✅ Created
```

**Next Step**: Deploy schema to Supabase

---

### Database Tasks

#### Archon #112 → PRP Task 1 (Part 2)
**Archon**: Implement Supabase schema for sync metadata
**PRP**: Task 1 - Deploy Sync Metadata Schema to Supabase
**Status**: ⏳ READY TO DEPLOY
**File**: `mt/SYNC/scripts/01-init-sync-schema.sql`
**What's Ready**:
- ✅ sync_metadata schema
- ✅ 7 tables: hosts, client_deployments, leader_election, conflict_log, cache_events, sync_jobs, sync_progress
- ✅ 3 monitoring views
- ✅ Indexes and constraints
- ✅ Automatic timestamp triggers

**PRP Implementation Guide** (Lines 160-223):
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
```

**Next Step**: Execute in Supabase SQL Editor

---

#### Archon #106 → PRP Task 2
**Archon**: Create restricted sync_service database role
**PRP**: Task 2 - Create Restricted Database Role
**Status**: 📝 TODO
**File to Create**: `mt/SYNC/scripts/02-create-sync-role.sql`

**PRP Implementation Guide** (Lines 225-255):
- Create role with LOGIN only
- Grant SELECT, INSERT, UPDATE on sync_metadata (NO DELETE)
- Grant per-client schema permissions
- Validation: Test unauthorized DELETE (should fail)

**Dependencies**: Task 1 must be completed first

---

#### Archon #N/A → PRP Task 3
**Archon**: *(No direct mapping - implied in security task)*
**PRP**: Task 3 - Enable Row Level Security Policies
**Status**: 📝 TODO
**File to Create**: `mt/SYNC/scripts/03-enable-rls.sql`

**PRP Implementation Guide** (Lines 257-280):
- Enable RLS on sync_metadata tables
- Create isolation policies per host
- Validation: Test cross-host access (should fail)

**Note**: This is a sub-task that should be added to Archon

---

### Python Implementation Tasks

#### Archon #100 → PRP Task 4
**Archon**: Build Python StateManager with cache-aside pattern
**PRP**: Task 4 - Build StateManager Class
**Status**: 📝 TODO
**File to Create**: `mt/SYNC/python/state_manager.py`

**PRP Implementation Guide** (Lines 282-356):
- Cache-aside pattern with 5-minute TTL
- Async operations with asyncpg
- Supabase as authoritative source
- Cache invalidation across cluster

**Dependencies**: Tasks 1-3 (database setup)

**Key Code Pattern**:
```python
async def get_state(self, key: str) -> dict:
    # Check cache first
    if self._is_cache_valid(key):
        return self.cache[key]

    # Cache miss - fetch from Supabase (authoritative)
    state = await self._fetch_from_supabase(key)
    self._update_cache(key, state)
    return state
```

**Validation**: `pytest tests/test_state_manager.py -v`

---

#### Archon #94 → PRP Task 5
**Archon**: Implement LeaderElection class with Supabase atomic operations
**PRP**: Task 5 - Implement LeaderElection Class
**Status**: 📝 TODO
**File to Create**: `mt/SYNC/python/leader_election.py`

**PRP Implementation Guide** (Lines 358-435):
- PostgreSQL advisory locks + heartbeat
- 60-second lease duration, 30-second heartbeat
- Atomic INSERT...ON CONFLICT for leader acquisition
- Automatic failover on lease expiration

**Dependencies**: Tasks 1-3 (database setup)

**Key Code Pattern**:
```python
query = """
INSERT INTO sync_metadata.leader_election
    (cluster_name, leader_id, acquired_at, expires_at)
VALUES ($1, $2, NOW(), NOW() + INTERVAL '60 seconds')
ON CONFLICT (cluster_name) DO UPDATE
SET leader_id = EXCLUDED.leader_id, ...
WHERE leader_election.expires_at < NOW()
      OR leader_election.leader_id = EXCLUDED.leader_id
RETURNING leader_id = $2 as is_leader;
"""
```

**Validation**: `pytest tests/test_leader_election.py -v`

---

#### Archon #88 → PRP Task 6
**Archon**: Build ConflictResolver with configurable strategies
**PRP**: Task 6 - Build ConflictResolver Engine
**Status**: 📝 TODO
**File to Create**: `mt/SYNC/python/conflict_resolver.py`

**PRP Implementation Guide** (Lines 437-524):
- 5 strategies: newest_wins, source_wins, target_wins, merge, manual
- Strategy pattern with JSON configuration
- Conflict logging to sync_metadata.conflict_log

**Dependencies**: Tasks 1-3 (database setup)

**Config File**: `mt/SYNC/config/conflict-resolution-default.json` (see PRP Task 18)

**Validation**: `pytest tests/test_conflict_resolver.py -v`

---

#### Archon #82 → PRP Task 7
**Archon**: Create FastAPI sync container service
**PRP**: Task 7 - Create FastAPI Sync Container Service
**Status**: 📝 TODO
**File to Create**: `mt/SYNC/python/main.py`

**PRP Implementation Guide** (Lines 526-625):
- FastAPI with lifespan events
- Endpoints: /health, /api/v1/state, /api/v1/sync/trigger
- Background tasks for sync operations
- Integrate StateManager, LeaderElection, ConflictResolver

**Dependencies**: Tasks 4-6 (Python modules)

**Key Endpoints**:
```python
@app.get("/health")  # Health check with leader status
@app.get("/api/v1/state/{key}")  # Get state (cache-aside)
@app.put("/api/v1/state/{key}")  # Update state (Supabase first)
@app.post("/api/v1/sync/trigger/{client}")  # Manual sync (leader only)
```

**Validation**: Start service, test endpoints with curl

---

### Scripts & Automation Tasks

#### Archon #76 → PRP Task 8
**Archon**: Write sync-client-to-supabase.sh with conflict resolution
**PRP**: Task 8 - Write Sync Engine Script
**Status**: 📝 TODO
**File to Create**: `mt/SYNC/scripts/sync-client-to-supabase.sh`

**PRP Implementation Guide** (Lines 627-740):
- WAL checkpoint for consistent snapshot
- Incremental sync by updated_at
- Conflict detection per row
- Batch processing (1000 rows)
- Integration with ConflictResolver

**Dependencies**: Tasks 1-7 (database, Python modules, API)

**Key Pattern**:
```bash
# Checkpoint WAL
docker exec "$CONTAINER" sqlite3 "$DB" "PRAGMA wal_checkpoint(TRUNCATE);"

# Begin transaction
docker exec "$CONTAINER" sqlite3 "$DB" "BEGIN IMMEDIATE TRANSACTION;"

# Sync tables
for table in $TABLES; do
    # Get changes since last sync
    # Check for conflicts in Supabase
    # Resolve conflicts via Python resolver
    # Apply resolved data
done
```

**Validation**: Test sync with dummy client

---

### Containerization Tasks

#### Archon #70 → PRP Task 9
**Archon**: Create Docker image for openwebui-sync container
**PRP**: Task 9 - Create Docker Image for Sync Container
**Status**: 📝 TODO
**Files to Create**:
- `mt/SYNC/docker/Dockerfile`
- `mt/SYNC/docker/entrypoint.sh`

**PRP Implementation Guide** (Lines 742-787):
- Python 3.11-slim base
- Install: sqlite3, curl, asyncpg, fastapi, uvicorn
- Copy Python modules and scripts
- Health check on /health endpoint
- Entrypoint validates required env vars

**Dependencies**: Tasks 7-8 (Python app, sync script)

**Validation**: Build and test run with sample env vars

---

#### Archon #64 → PRP Task 10
**Archon**: Write docker-compose.sync-ha.yml for HA cluster
**PRP**: Task 10 - Write Docker Compose for HA Cluster
**Status**: 📝 TODO
**File to Create**: `mt/SYNC/docker/docker-compose.sync-ha.yml`

**PRP Implementation Guide** (Lines 789-837):
- Primary container (port 9443)
- Secondary container (port 9444)
- Docker secrets for credentials
- Volume mounts for docker.sock
- Health checks and restart policies

**Dependencies**: Task 9 (Docker image)

**Validation**: Start cluster, verify both containers running

---

### Monitoring Tasks

#### Archon #58 → PRP Task 11
**Archon**: Add Prometheus metrics to sync container
**PRP**: Task 11 - Add Prometheus Metrics
**Status**: 📝 TODO
**File to Create**: `mt/SYNC/python/metrics.py`

**PRP Implementation Guide** (Lines 839-901):
- Metrics: sync_operations_total, sync_duration_seconds, conflicts_detected/resolved
- Leader election metrics
- Cache hit/miss metrics
- State sync lag
- Expose /metrics endpoint via prometheus-fastapi-instrumentator

**Dependencies**: Task 7 (FastAPI app)

**Validation**: `curl http://localhost:9443/metrics | grep sync_`

---

### Integration Tasks

#### Archon #52 → PRP Task 12
**Archon**: Integrate sync configuration menu into client-manager.sh
**PRP**: Task 12 - Integrate with Client Manager
**Status**: 📝 TODO
**File to Modify**: `mt/client-manager.sh`

**PRP Implementation Guide** (Lines 903-1027):
- Add configure_database_sync() function
- Menu options: view status, configure interval, manual trigger, view conflicts, test failover
- Check cluster health via API
- Query conflict log from Supabase

**Dependencies**: Tasks 10-11 (running cluster with API)

**Validation**: Navigate client-manager menu, test all options

---

### Deployment Tasks

#### Archon #46 → PRP Task 13
**Archon**: Create deploy-sync-cluster.sh deployment script
**PRP**: Task 13 - Create Deployment Script
**Status**: 📝 TODO
**File to Create**: `mt/SYNC/scripts/deploy-sync-cluster.sh`

**PRP Implementation Guide** (Lines 1029-1097):
- Collect Supabase credentials
- Generate sync_service password
- Create restricted role in Supabase
- Deploy HA containers
- Verify cluster health

**Dependencies**: Tasks 2-3 (SQL scripts), Task 10 (docker-compose)

**Validation**: Execute script, verify cluster deployed

---

### Testing Tasks

#### Archon #40 → PRP Task 14
**Archon**: Write comprehensive test suite for HA failover
**PRP**: Task 14 - Write Test Scripts (HA Failover)
**Status**: 📝 TODO
**File to Create**: `mt/SYNC/tests/test-ha-failover.sh`

**PRP Implementation Guide** (Lines 1099-1117):
- Test 1: Primary is leader on startup
- Test 2: Kill primary, verify secondary takeover <35s
- Test 3: Restart primary, becomes follower

**Dependencies**: Task 13 (deployed cluster)

**Validation**: Run test script, all tests pass

---

#### Archon #34 → PRP Task 15
**Archon**: Write conflict resolution test scenarios
**PRP**: Task 15 - Write Test Scripts (Conflict Resolution)
**Status**: 📝 TODO
**File to Create**: `mt/SYNC/tests/test-conflict-resolution.sh`

**PRP Implementation Guide** (Lines 1119-1131):
- Test newest_wins strategy
- Test source_wins strategy
- Test merge strategy with list appending

**Dependencies**: Task 13 (deployed cluster), Task 8 (sync script)

**Validation**: Run test script, verify strategies work

---

#### Archon #28 → PRP Task 16
**Archon**: Write state authority test
**PRP**: Task 16 - Write Test Scripts (State Authority)
**Status**: 📝 TODO
**File to Create**: `mt/SYNC/tests/test-state-authority.sh`

**PRP Implementation Guide** (Lines 1133-1147):
- Test: Update via API
- Verify Supabase updated first
- Kill primary, verify secondary reads correct state
- Validate cache invalidation

**Dependencies**: Task 13 (deployed cluster)

**Validation**: Run test script, verify Supabase authority

---

#### Archon #22 → PRP Task 17
**Archon**: Write security validation tests for sync_service role
**PRP**: Task 17 - Write Test Scripts (Security)
**Status**: 📝 TODO
**File to Create**: `mt/SYNC/tests/test-security.sh`

**PRP Implementation Guide** (Lines 1149-1177):
- Test: sync_service cannot DELETE (should fail)
- Test: sync_service cannot DROP schema (should fail)
- Verify RLS policies work

**Dependencies**: Tasks 2-3 (restricted role, RLS)

**Validation**: Run test script, verify all unauthorized ops fail

---

### Documentation Tasks

#### Archon #16 → PRP Task 18
**Archon**: Create comprehensive documentation for Phase 1
**PRP**: Task 18 - Create Configuration Files
**Status**: ✅ COMPLETED (README.md), 📝 TODO (config files)

**What's Done**:
- ✅ `mt/SYNC/README.md` - Architecture, API, monitoring, troubleshooting

**Still Needed** (PRP Lines 1179-1230):
- 📝 `mt/SYNC/config/conflict-resolution-default.json` - Default strategies
- 📝 `mt/SYNC/config/sync-config-template.env` - Environment template
- 📝 `mt/SYNC/python/requirements.txt` - Python dependencies

**Dependencies**: None (can be done anytime)

---

### Validation Tasks

#### Archon #10 → PRP Task 19
**Archon**: Run all Phase 1 validation tests
**PRP**: Task 19 - Run Full Validation Suite
**Status**: 📝 TODO

**PRP Implementation Guide** (Lines 1232-1298):
- Run all test scripts (Tasks 14-17)
- Verify infrastructure checklist
- Verify database checklist
- Verify functionality checklist
- Verify HA checklist
- Verify security checklist
- Verify monitoring checklist
- Verify integration checklist
- Verify performance checklist

**Dependencies**: ALL previous tasks (1-18)

**Success Criteria**:
- All tests passing
- Zero data loss during failover
- Sync latency <60s at p95
- Failover time <35s
- Cache hit rate >80%
- 100% security validation pass

---

## Missing Tasks (PRP has, Archon doesn't)

### PRP Task 3 - Enable Row Level Security
**Status**: Not explicitly tracked in Archon
**Recommendation**: Add as new Archon task or fold into Task #106 (security role)

**Suggested Archon Task**:
```yaml
Title: Enable Row Level Security policies for sync_metadata
Description: Create and apply RLS policies to sync_metadata tables for host isolation. Verify sync_service can only access its own host's data.
Feature: security
Task Order: 103 (between 106 and 100)
```

---

## Task Dependencies Graph

```
Task 1 (Schema) ──┬──> Task 2 (Security Role) ──┐
                  │                               │
                  └──> Task 3 (RLS) ─────────────┤
                                                  │
                                                  ├──> Task 4 (StateManager)
                                                  ├──> Task 5 (LeaderElection)
                                                  └──> Task 6 (ConflictResolver)
                                                           │
                                                           ├──> Task 7 (FastAPI)
                                                           │         │
                                                           │         └──> Task 8 (Sync Script)
                                                           │                   │
                                                           └───────────────────┤
                                                                               │
                                                                               ├──> Task 9 (Docker Image)
                                                                               │         │
                                                                               │         └──> Task 10 (Compose)
                                                                               │                   │
                                                                               └───────────────────┤
                                                                                                   │
                        Task 11 (Metrics) ─────────────────────────────────────────────────────────┤
                                                                                                   │
                        Task 12 (Client Manager) ──────────────────────────────────────────────────┤
                                                                                                   │
                        Task 13 (Deploy Script) ───────────────────────────────────────────────────┤
                                                                                                   │
                                                                                                   ├──> Task 14 (HA Tests)
                                                                                                   ├──> Task 15 (Conflict Tests)
                                                                                                   ├──> Task 16 (State Tests)
                                                                                                   └──> Task 17 (Security Tests)
                                                                                                             │
        Task 18 (Config Files) ────────────────────────────────────────────────────────────────────────────┤
                                                                                                             │
                                                                                                             └──> Task 19 (Final Validation)
```

---

## How to Use This Mapping

### For Project Managers
1. **Track progress** in Archon (task status updates)
2. **Refer to PRP** for implementation details when needed
3. **Use this mapping** to understand dependencies

### For Developers/AI Agents
1. **Start with Archon task** (what to do)
2. **Jump to PRP section** via this mapping (how to do it)
3. **Follow PRP pseudocode** for implementation
4. **Update Archon status** when task complete

### For Reviews
1. **Check Archon** for high-level progress
2. **Check PRP** for implementation quality
3. **Use mapping** to verify alignment

---

## Status Summary

| Status | Count | Tasks |
|--------|-------|-------|
| ✅ Done | 2 | Directory structure, Documentation |
| ⏳ Ready | 1 | Schema deployment (SQL written) |
| 📝 Todo | 16 | All other implementation tasks |

**Next Immediate Steps**:
1. Deploy schema (Task 1 / Archon #112)
2. Create security role (Task 2 / Archon #106)
3. Enable RLS (Task 3 / New task needed)
4. Start Python implementations (Tasks 4-6 / Archon #100, #94, #88)

---

## References

- **Archon Project**: https://archon.mcp/projects/038661b1-7e1c-40d0-b4f9-950db24c2a3f
- **PRP Document**: `PRPs/sqlite_supabase_migration_with_sync/prp-phase1.md`
- **Project Status**: `PRPs/sqlite_supabase_migration_with_sync/README.md`
- **Implementation Code**: `mt/SYNC/`

---

**Document Version**: 1.0
**Last Updated**: 2025-10-08
**Maintained By**: Development Team
