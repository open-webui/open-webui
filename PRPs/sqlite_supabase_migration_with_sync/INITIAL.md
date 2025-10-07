## FEATURE:

**SQLite + Supabase Bidirectional Sync System for Multi-Tenant Open WebUI Deployments**

- Replace direct Supabase migration with SQLite-primary + Supabase-sync architecture
- Each Open WebUI deployment uses local SQLite for instant performance
- Configurable sync intervals (1-minute, 5-minute, hourly, daily) per deployment
- Multi-tenant Supabase schema design (one schema per client: `imc_quantabase_io`, `acme_quantabase_io`, `chat_clientdomain_xyz` etc.)
- Bidirectional sync: SQLite → Supabase (backup/analytics) and Supabase → SQLite (restore/migration)
- On-demand sync triggers for real-time integration scenarios
- Deployment portability: restore any client from Supabase schema to new host
- Integration with existing `client-manager.sh` deployment lifecycle

### Core Components:

1. **Sync Engine** (`sync-client-to-supabase.sh`)
   - Incremental sync (only changed rows since last sync based on `updated_at` columns)
   - Full sync mode for initial setup or recovery
   - Change detection and conflict resolution
   - Schema creation and management per client
   - Progress tracking and error handling

2. **Sync Scheduler** (`sync-scheduler.sh`)
   - Per-client sync configuration stored in JSON
   - Systemd timer or cron integration
   - Concurrent sync support (multiple clients syncing in parallel)
   - Sync history and monitoring

3. **Restore Tool** (`restore-client-from-supabase.sh`)
   - Pull specific client schema from Supabase
   - Initialize new SQLite database on target host
   - Validate data integrity post-restore
   - Container deployment on new host

4. **Client Manager Integration**
   - Menu option: "Configure database sync"
   - View sync status (last sync time, pending changes, errors)
   - Manual sync trigger
   - Change sync interval
   - Enable/disable sync per deployment

### Architecture Changes from Existing Migration:

**Current (from `MIGRATION_IMPLEMENTATION_SUMMARY.md`):**
- One-way migration: SQLite → PostgreSQL (permanent switch)
- Container uses DATABASE_URL pointing to remote Supabase
- `db-migration-helper.sh` handles schema init, data migration, container recreation
- No ongoing sync, data lives in Supabase only after migration
- **Problem identified**: Remote PostgreSQL causes 100x slower token streaming (psycopg2 blocks async event loop)

**New Architecture:**
- **Primary database**: SQLite (stays in container for performance)
- **Secondary database**: Supabase (backup, analytics, cross-host portability)
- **Sync process**: Bidirectional, scheduled, incremental
- Container NEVER uses DATABASE_URL for Supabase (no performance degradation)
- Sync runs as background process outside container
- Each client gets dedicated Supabase schema for tenant isolation

### Multi-Tenant Schema Design:

```
Supabase Database (postgres)
├── schema: imc_quantabase_io
│   ├── chat
│   ├── user
│   ├── message
│   └── [all Open WebUI tables]
├── schema: chat_quantabase_io
│   ├── chat
│   ├── user
│   ├── message
│   └── [all Open WebUI tables]
└── schema: sync_metadata
    ├── owui_sync_log (tracks sync history per client)
    └── client_config (stores sync intervals, last sync times)
```

### Sync Interval Tiers:

- **Real-time** (1-5 min): Clients with backend integrations consuming chat data
- **Frequent** (hourly): Standard production deployments
- **Daily** (overnight): Test environments, development instances
- **On-demand**: Manual trigger only (no scheduled sync)

### Deployment Lifecycle Integration:

**Creating New Deployment:**
```bash
./start-template.sh chat_quantabase_io 8082
# Or via client-manager.sh → "1) Create New Deployment"
# Prompts:
#   - Enable Supabase sync? (Y/n)
#   - Sync interval: (realtime/frequent/daily/manual)
# Creates:
#   - Container with SQLite
#   - Supabase schema: chat_quantabase_io
#   - Sync configuration in ~/.openwebui-sync/chat-quantabase-io.json
```

**Managing Existing Deployment:**
```bash
./client-manager.sh → "3) Manage Existing Deployment" → Select client → "11) Database Sync Configuration"
# Options:
#   - View sync status
#   - Trigger manual sync now
#   - Change sync interval
#   - Enable/disable sync
#   - View sync history
```

**Migrating Deployment to New Host:**
```bash
# On new host:
./restore-client-from-supabase.sh chat_quantabase_io
# Prompts for Supabase credentials
# Downloads schema: client_acme
# Creates SQLite database
# Deploys container
# Configures sync to resume
```

**Converting Existing SQLite Deployment (No Sync):**
```bash
./client-manager.sh → "3) Manage Existing Deployment" → Select client → "11) Database Sync Configuration"
# Option: "Enable Supabase sync for this deployment"
# Prompts:
#   - Supabase connection details
#   - Sync interval
# Performs:
#   - Creates schema in Supabase
#   - Initial full sync (SQLite → Supabase)
#   - Enables scheduled sync
```

## EXAMPLES:

The following existing code should be studied to understand patterns and integration points:

### Database Migration System (Existing):
- `mt/db-migration-helper.sh` (593 lines) - Study schema initialization, connection handling, backup strategies
  - `get_supabase_config()` - Adapt for sync configuration
  - `test_supabase_connection()` - Reuse for sync validation
  - `backup_sqlite_database()` - Use before first sync
  - `initialize_postgresql_schema()` - Adapt for per-client schema creation

- `mt/client-manager.sh` (1165 lines) - Study menu integration, deployment management
  - Lines 268-279: FQDN extraction - reuse for sync metadata
  - Lines 281-295: Database type detection - adapt for sync status detection
  - Lines 673-830: Migration workflow - pattern for sync configuration workflow

### Key Patterns to Follow:
- Color-coded output (GREEN/RED/YELLOW/BLUE)
- User confirmation prompts with warnings
- Screen clearing between workflow steps
- Progress indicators during long operations
- Comprehensive error handling with actionable messages
- Automatic rollback on failure
- Docker-based operations (no system dependencies)

### Differences from Existing Migration:
- **DO NOT recreate container** - sync operates externally
- **DO NOT modify DATABASE_URL** - container stays on SQLite
- **DO NOT use temporary containers** - sync process uses persistent connection
- **DO create per-client schemas** - not single database switch
- **DO track sync state** - last sync time, pending changes

## DOCUMENTATION:

### Open WebUI:
- Database structure: https://github.com/open-webui/open-webui/blob/main/backend/open_webui/internal/db.py
- SQLAlchemy models: Study table definitions for sync requirements
- Migration tool reference: https://github.com/taylorwilsdon/open-webui-postgres-migration

### Supabase:
- PostgreSQL schemas: https://www.postgresql.org/docs/current/ddl-schemas.html
- Row-level security: https://supabase.com/docs/guides/auth/row-level-security
- Connection pooling: https://supabase.com/docs/guides/database/connecting-to-postgres

### Sync Strategy References:
- Change data capture (CDC) patterns
- Incremental sync using timestamps
- Conflict resolution strategies
- SQLite Write-Ahead Logging (WAL) for concurrent reads during sync

## OTHER CONSIDERATIONS:

### Technical Requirements:

**1. Change Detection Strategy:**
- Rely on Open WebUI's `updated_at` timestamps in tables
- Track last successful sync timestamp per client
- Query: `SELECT * FROM table WHERE updated_at > last_sync_timestamp`
- Handle tables without `updated_at` (full sync or use rowid)

**2. Sync Process Architecture:**
```
sync-client-to-supabase.sh <client_name> <mode>
├── Read sync config (~/.openwebui-sync/<client>.json)
├── Connect to container SQLite (docker exec or volume mount)
├── Connect to Supabase (schema: client_<name>)
├── Determine changes since last sync
├── Apply changes to Supabase (batch inserts/updates)
├── Update sync metadata (last_sync_time, row counts)
└── Log results to sync history
```

**3. Schema Creation:**
```sql
-- Create client schema
CREATE SCHEMA IF NOT EXISTS imc_quantabase_io;

-- Set search path and create tables
SET search_path TO imc_quantabase_io;

-- Replicate Open WebUI table structure
-- (Use Open WebUI container to generate schema via SQLAlchemy)
-- OR extract from existing PostgreSQL migration
```

**4. Conflict Resolution:**
- **Assumption**: Supabase is read-only for external systems
- If Supabase changes detected: Log warning, prefer SQLite (source of truth)
- Future enhancement: Bidirectional merge strategies

**5. Performance Considerations:**
- Sync in batches (1000 rows per transaction)
- Use PostgreSQL COPY for bulk inserts
- Create indexes on `updated_at` columns
- Parallel sync if multiple tables have changes

**6. Error Handling:**
- Transactional sync (rollback if any table fails)
- Retry logic with exponential backoff
- Alert on repeated failures
- Continue container operation even if sync fails (non-blocking)

**7. Security:**
- Store Supabase credentials encrypted in sync config
- Use Supabase service role key (not user JWT)
- Implement Supabase Row Level Security (RLS) per schema
- Restrict access to sync_metadata schema

**8. Monitoring & Observability:**
- Sync history table: timestamp, client, duration, rows_synced, errors
- Prometheus metrics endpoint (optional)
- Slack/email alerts on sync failure
- Dashboard showing sync status across all clients

### Integration with Existing Systems:

**1. Modify `client-manager.sh`:**
- Add menu option 11: "Database Sync Configuration"
- Show sync status in deployment info (last sync, pending changes)
- Add sync status indicator in deployment list

**2. Modify `start-template.sh`:**
- Add optional parameter: `--enable-sync`
- Prompt for sync configuration during deployment
- Create initial sync config file

**3. New Configuration Files:**
```
~/.openwebui-sync/
├── config.json (global: Supabase connection, default intervals)
├── imc.json (per-client: sync interval, last sync, schema name)
├── acme.json
└── sync-history/
    ├── imc-quantabase-io-2025-10-07.log
    └── acme-quantabase-io-2025-10-07.log
```

**4. Scheduler Setup:**
```bash
# Install sync scheduler
./install-sync-scheduler.sh
# Creates systemd timer or cron jobs based on OS
# Runs sync-scheduler.sh every minute
# Scheduler checks client configs and triggers syncs when due
```

### Migration Path from Existing System:

**For deployments already migrated to Supabase (having issues):**
```bash
./rollback-to-sqlite-with-sync.sh <imc_quantabase_io>
# 1. Restores SQLite from Supabase (reverse migration)
# 2. Recreates container without DATABASE_URL
# 3. Enables sync configuration
# 4. Performs initial sync to verify
```

**For new deployments:**
- Default to SQLite + sync enabled
- Prompt for sync interval during creation

### Testing Strategy:

**1. Unit Tests (Sync Functions):**
- Test change detection algorithm
- Test batch insert/update logic
- Test schema creation
- Test conflict detection

**2. Integration Tests:**
- Create test deployment
- Add test data to SQLite
- Trigger sync
- Verify data in Supabase schema
- Modify Supabase data
- Sync back to SQLite
- Verify round-trip integrity

**3. Performance Tests:**
- Large database (10K+ chats)
- Measure sync duration
- Verify no container performance impact during sync
- Test concurrent syncs (multiple clients)

**4. Failure Tests:**
- Network interruption during sync
- Supabase connection timeout
- Schema creation failure
- Verify rollback and retry logic

### Documentation Deliverables:

**1. User Guide (mt/README.md section):**
- "Database Sync with Supabase" section
- How to enable sync for existing deployment
- How to change sync intervals
- How to migrate deployment using Supabase backup
- Troubleshooting sync issues

**2. Architecture Documentation (PRPs/ARCHITECTURE.md):**
- System diagram
- Data flow diagrams
- Schema design rationale
- Sync algorithm explanation

**3. Operator Guide (PRPs/OPERATIONS.md):**
- Monitoring sync health
- Responding to sync failures
- Backup and restore procedures
- Scaling considerations

### Success Criteria:

- [ ] New deployments can enable Supabase sync during creation
- [ ] Existing SQLite deployments can add sync without downtime
- [ ] Each client syncs to dedicated Supabase schema
- [ ] Sync intervals configurable per client (realtime/frequent/daily/manual)
- [ ] Manual sync trigger works from client-manager menu
- [ ] Sync status visible in deployment info
- [ ] Deployment can be restored from Supabase to new host
- [ ] Sync failures do not affect container operation
- [ ] Sync history is logged and viewable
- [ ] Token streaming remains fast (SQLite performance)
- [ ] No DATABASE_URL in container environment (no psycopg2 blocking)
- [ ] Scheduler runs automatically after installation
- [ ] Schema creation is automatic and isolated per client
- [ ] Conflict detection logs warnings but doesn't block sync
- [ ] Integration with existing client-manager.sh is seamless
