name: "SQLite to Supabase PostgreSQL Migration Integration"
description: |

## Purpose
Integrate automated database migration capability into the Open WebUI client management system, enabling seamless migration from SQLite to Supabase PostgreSQL with zero-downtime, comprehensive validation, and rollback capabilities.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Be sure to follow all rules in CLAUDE.md

---

## Goal
Add a database migration menu option to the existing `mt/client-manager.sh` script that:
- Detects the current database type (SQLite or PostgreSQL)
- Provides interactive migration from SQLite to Supabase PostgreSQL
- Maintains zero-downtime by using a parallel container approach
- Validates connectivity and data integrity before committing
- Supports rollback to SQLite if issues occur
- Displays database configuration status for existing PostgreSQL deployments

## Why
- **Business value**: Enables scalability from local SQLite to cloud PostgreSQL
- **Integration**: Seamlessly integrates with existing multi-tenant management workflow
- **Problems solved**:
  - Manual migration process is error-prone and risky
  - No built-in way to migrate production deployments safely
  - Users need remote database access for backup and scaling
  - Preparation for multi-instance deployments sharing a database

## What
A new menu option in the "Manage Existing Deployment" menu that:
- Shows current database configuration (SQLite or PostgreSQL details)
- For SQLite deployments: Offers "Migrate to Supabase/PostgreSQL" option
- For PostgreSQL deployments: Shows connection details and metrics
- Validates Supabase connectivity before migration
- Creates schema initialization in PostgreSQL
- Runs migration tool with progress tracking
- Switches container to PostgreSQL atomically
- Keeps SQLite as rollback option

### Success Criteria
- [ ] Menu displays current database type correctly
- [ ] SQLite deployments show migration option
- [ ] PostgreSQL deployments show configuration details
- [ ] Migration validates Supabase connectivity before proceeding
- [ ] Schema is initialized before data migration
- [ ] Data integrity verified post-migration
- [ ] Container switches to PostgreSQL without downtime
- [ ] Rollback to SQLite works if migration fails
- [ ] All environment variables properly configured
- [ ] Script follows existing client-manager.sh patterns

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://docs.openwebui.com/tutorials/database/
  why: Official Open WebUI database configuration and migration process

- url: https://docs.openwebui.com/getting-started/env-configuration/
  why: DATABASE_URL and VECTOR_DB environment variable configuration

- url: https://supabase.com/docs/guides/database/connecting-to-postgres
  why: Supabase connection string formats, pooling, SSL requirements
  section: Connection pooling (port 6543 vs 5432)
  critical: Use Transaction Mode (port 6543) for web applications

- url: https://github.com/taylorwilsdon/open-webui-postgres-migration
  why: Reference migration tool - patterns for data migration, integrity checking
  critical: Must initialize schema before running migration

- url: https://github.com/open-webui/open-webui/discussions/8116
  why: Null byte issue fix - PostgreSQL doesn't support \u0000
  critical: Must run: UPDATE chat SET chat = REPLACE(chat::TEXT, '\u0000', '')::JSONB;

- url: https://pypi.org/project/open-webui-postgres-migration/
  why: Installation and usage of migration package via uvx

- file: /Users/justinmartin/github/open-webui/mt/client-manager.sh
  why: Existing patterns for menu structure, container management, error handling
  section: Lines 250-663 - manage_single_deployment function
  critical: Follow existing menu pattern and container recreation logic

- file: /Users/justinmartin/github/open-webui-postgres-migration/migrate.py
  why: Reference implementation of migration logic
  section: Lines 73-94 - check_postgres_tables_exist function
  critical: Must verify PostgreSQL tables exist before migration

- file: /Users/justinmartin/github/open-webui/backend/open_webui/internal/db.py
  why: Understanding database configuration and connection handling
  section: Lines 55-80 - handle_peewee_migration function
  critical: DATABASE_URL format and special character encoding

- docfile: /Users/justinmartin/github/open-webui/PRPs/INITIAL_sqlite_supbase_migration.md
  why: Complete feature specification with all gotchas and edge cases
```

### Current Codebase tree (mt directory)
```bash
mt/
├── client-manager.sh          # Main management script (966 lines)
├── start-template.sh           # Template for creating new deployments
├── start-acme-corp.sh         # Pre-configured client example
├── start-beta-client.sh       # Pre-configured client example
├── nginx-template.conf        # Production nginx config template
├── nginx-template-local.conf  # Local testing nginx config
├── docker-compose.nginx.yml   # Local nginx setup
└── nginx/                     # Local nginx configurations
    ├── sites-available/
    └── sites-enabled/
```

### Desired Codebase tree with files to be added
```bash
mt/
├── client-manager.sh          # MODIFIED: Add database migration menu option
├── db-migration-helper.sh     # NEW: Database migration logic (isolation)
├── start-template.sh          # (unchanged)
├── start-acme-corp.sh         # (unchanged)
├── start-beta-client.sh       # (unchanged)
├── nginx-template.conf        # (unchanged)
└── README.md                  # MODIFIED: Add migration documentation
```

### Known Gotchas & Library Quirks
```bash
# CRITICAL: Migration tool must be installed or used via uvx
# Example: uvx open-webui-postgres-migration requires internet connection

# CRITICAL: Null byte issue - PostgreSQL doesn't support \u0000
# Must run after migration: UPDATE chat SET chat = REPLACE(chat::TEXT, '\u0000', '')::JSONB;

# CRITICAL: Connection string format matters
# Wrong: postgresql://...@...supabase.com:5432/postgres (Session Mode)
# Right: postgresql://...@...pooler.supabase.com:6543/postgres (Transaction Mode)

# CRITICAL: Schema initialization order
# 1. Start container with DATABASE_URL
# 2. Wait for schema creation
# 3. Stop container
# 4. Run migration
# 5. Start container with migrated data

# CRITICAL: Docker environment variables are NOT persistent
# Must use docker run -e flags when recreating container

# CRITICAL: Volume contains more than database
# Volume has uploads, documents - don't remove after migration

# CRITICAL: Container name must remain consistent for nginx
# Changing container name can break nginx proxy_pass

# CRITICAL: Special characters in passwords must be URL-encoded
# Example: password "p@ss" becomes "p%40ss" in DATABASE_URL

# GOTCHA: Migration can take 15-30 minutes for large databases
# Need progress indicator and user warnings about downtime

# GOTCHA: Supabase free tier limits - 500MB storage, 2GB bandwidth/month
# Check database size before migration

# GOTCHA: pgvector extension required for RAG features
# Must run: CREATE EXTENSION IF NOT EXISTS vector;
```

## Implementation Blueprint

### Data models and structure

```bash
# Environment variables to track in container
DATABASE_URL="postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
VECTOR_DB="pgvector"  # or keep as default ChromaDB
DATABASE_TYPE="postgresql"  # or "sqlite" for tracking

# Container configuration tracking
CONTAINER_NAME="openwebui-${client_name}"
VOLUME_NAME="openwebui-${client_name}-data"
DATABASE_BACKUP_PATH="/tmp/webui-backup-${client_name}-$(date +%Y%m%d-%H%M%S).db"
```

### List of tasks to be completed to fulfill the PRP in the order they should be completed

```yaml
Task 1: Detect Current Database Configuration
MODIFY mt/client-manager.sh:
  - FIND function: manage_single_deployment (line 250)
  - INJECT after: echo "Ports:  $ports" (line 266)
  - ADD: Database configuration detection and display
  - PATTERN: Similar to how container environment is read for domains
  - LOGIC:
    * Check if DATABASE_URL environment variable exists in container
    * If exists → PostgreSQL, extract host/port/dbname
    * If not exists → SQLite (default)
    * Display current database type and details

Task 2: Add Menu Option Based on Database Type
MODIFY mt/client-manager.sh:
  - FIND: Menu options in manage_single_deployment (lines 269-277)
  - INJECT: New option after "7) Change domain/client (preserve data)"
  - CONDITIONAL DISPLAY:
    * If SQLite detected: "8) Migrate to Supabase/PostgreSQL"
    * If PostgreSQL detected: "8) View Database Configuration"
  - RENUMBER: Existing options 8 and 9 become 9 and 10

Task 3: Create Database Migration Helper Script
CREATE mt/db-migration-helper.sh:
  - PATTERN: Standalone script with functions (like start-template.sh)
  - FUNCTIONS:
    * get_supabase_config() - Interactive Supabase connection setup
    * test_supabase_connection() - Validate connectivity
    * check_pgvector_extension() - Verify pgvector is enabled
    * initialize_postgresql_schema() - Create tables before migration
    * backup_sqlite_database() - Export current database
    * run_migration_tool() - Execute uvx migration with progress
    * fix_null_bytes() - Run PostgreSQL cleanup after migration
    * recreate_container_with_postgres() - Switch to PostgreSQL
  - ERROR HANDLING: Return codes and error messages
  - VALIDATION: All steps must succeed before proceeding

Task 4: Implement Migration Workflow
MODIFY mt/client-manager.sh:
  - FIND: case statement for menu actions (line 282)
  - INJECT: New case for option "8"
  - LOGIC:
    * Confirm user wants to migrate (show warnings)
    * Source db-migration-helper.sh
    * Get Supabase configuration interactively
    * Test Supabase connection
    * Verify pgvector extension
    * Backup SQLite database to container and host
    * Initialize PostgreSQL schema (start/stop container)
    * Run migration tool with progress display
    * Fix null byte issue in PostgreSQL
    * Recreate container with DATABASE_URL
    * Verify container is running
    * Test web access
    * Show success message with next steps

Task 5: Implement PostgreSQL Configuration Viewer
MODIFY mt/client-manager.sh:
  - FIND: Same case statement for menu actions
  - INJECT: Logic for when PostgreSQL already exists
  - DISPLAY:
    * Database URL (masked password)
    * Database host, port, name
    * Vector database type
    * Connection status (test connection)
    * Table count and schema info
  - PATTERN: Similar to Cloudflare DNS display (lines 308-346)

Task 6: Add Rollback Capability
MODIFY mt/db-migration-helper.sh:
  - ADD FUNCTION: rollback_to_sqlite()
  - LOGIC:
    * Stop PostgreSQL container
    * Restore SQLite backup
    * Recreate container without DATABASE_URL
    * Verify container starts successfully
  - TRIGGER: Automatic on migration failure, manual option in menu

Task 7: Update Documentation
MODIFY mt/README.md:
  - ADD SECTION: "Database Migration"
  - DOCUMENT:
    * When to migrate to PostgreSQL
    * Prerequisites (Supabase account, project setup)
    * Migration process overview
    * Rollback procedure
    * Troubleshooting common issues
  - PATTERN: Follow existing README structure
```

### Per task pseudocode

```bash
# Task 1: Database Detection (in manage_single_deployment)
detect_database_type() {
    local container_name="$1"

    # Try to get DATABASE_URL from container
    local database_url=$(docker exec "$container_name" env 2>/dev/null | grep "DATABASE_URL=" | cut -d'=' -f2- 2>/dev/null)

    if [[ -n "$database_url" ]]; then
        # PostgreSQL detected
        local db_type="PostgreSQL"
        local db_host=$(echo "$database_url" | sed 's|postgresql://[^@]*@||' | cut -d':' -f1)
        local db_port=$(echo "$database_url" | sed 's|.*:||' | cut -d'/' -f1)
        local db_name=$(echo "$database_url" | sed 's|.*/||')

        echo "Database:  $db_type"
        echo "Host:      $db_host"
        echo "Port:      $db_port"
        echo "Database:  $db_name"
    else
        # SQLite (default)
        echo "Database:  SQLite (default)"
        echo "Location:  /app/backend/data/webui.db"
    fi
}

# Task 3: Supabase Configuration (in db-migration-helper.sh)
get_supabase_config() {
    echo "╔════════════════════════════════════════╗"
    echo "║   Supabase PostgreSQL Configuration   ║"
    echo "╚════════════════════════════════════════╝"
    echo
    echo "Please provide your Supabase connection details:"
    echo

    # PATTERN: Similar to client-manager.sh domain prompts
    echo -n "Supabase Project Reference (e.g., abc123xyz): "
    read project_ref

    echo -n "Supabase Database Password: "
    read -s db_password
    echo

    echo -n "Supabase Region (e.g., aws-0-us-east-1): "
    read region

    # CRITICAL: Use Transaction Mode port 6543
    DATABASE_URL="postgresql://postgres.${project_ref}:${db_password}@${region}.pooler.supabase.com:6543/postgres"

    # Test connection before proceeding
    if ! test_connection "$DATABASE_URL"; then
        return 1
    fi

    export DATABASE_URL
    return 0
}

# Task 3: Schema Initialization (in db-migration-helper.sh)
initialize_postgresql_schema() {
    local container_name="$1"
    local database_url="$2"
    local port="$3"

    echo "Initializing PostgreSQL schema..."
    echo "This will start Open WebUI temporarily to create tables."
    echo

    # CRITICAL: Start container with DATABASE_URL to trigger schema creation
    docker run -d \
        --name "${container_name}-schema-init" \
        -p "${port}:8080" \
        -e DATABASE_URL="$database_url" \
        -e VECTOR_DB="pgvector" \
        ghcr.io/imagicrafter/open-webui:main

    # Wait for schema initialization (check logs)
    echo "Waiting for schema initialization..."
    local max_wait=60
    local waited=0

    while [ $waited -lt $max_wait ]; do
        if docker logs "${container_name}-schema-init" 2>&1 | grep -q "Application startup complete"; then
            echo "✅ Schema initialized successfully"
            break
        fi
        sleep 2
        waited=$((waited + 2))
    done

    # Stop and remove temporary container
    docker stop "${container_name}-schema-init" 2>/dev/null
    docker rm "${container_name}-schema-init" 2>/dev/null

    # CRITICAL: Verify tables were created
    # Use psql or python to check table existence
    # Expected tables: user, auth, chat, document, model, prompt, function, tool

    return 0
}

# Task 4: Migration Execution (in client-manager.sh)
execute_migration() {
    local client_name="$1"
    local container_name="openwebui-${client_name}"

    # PATTERN: Confirmation prompt like domain change (line 547)
    echo "⚠️  WARNING: Database migration is a critical operation"
    echo "Estimated time: 15-30 minutes"
    echo "The service will be temporarily unavailable during migration"
    echo
    echo -n "Continue with migration? (y/N): "
    read confirm

    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "Migration cancelled."
        return 1
    fi

    # Source the helper script
    source "${SCRIPT_DIR}/db-migration-helper.sh"

    # Step 1: Get Supabase configuration
    if ! get_supabase_config; then
        echo "❌ Failed to configure Supabase connection"
        return 1
    fi

    # Step 2: Backup SQLite database
    echo "Backing up SQLite database..."
    backup_path=$(backup_sqlite_database "$container_name")

    # Step 3: Initialize PostgreSQL schema
    echo "Initializing PostgreSQL schema..."
    port=$(docker ps -a --filter "name=$container_name" --format "{{.Ports}}" | grep -o '0.0.0.0:[0-9]*' | cut -d: -f2)
    initialize_postgresql_schema "$container_name" "$DATABASE_URL" "$port"

    # Step 4: Run migration tool
    echo "Running migration tool..."
    # CRITICAL: Must have internet connection for uvx
    if ! command -v uvx &> /dev/null; then
        echo "❌ uvx not found. Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        source $HOME/.cargo/env
    fi

    # Run migration with backup as source
    # GOTCHA: Migration tool is interactive, may need non-interactive mode
    uvx open-webui-postgres-migration || return 1

    # Step 5: Fix null byte issue
    echo "Fixing null byte issue in PostgreSQL..."
    fix_null_bytes "$DATABASE_URL"

    # Step 6: Recreate container with PostgreSQL
    echo "Recreating container with PostgreSQL configuration..."
    recreate_container_with_postgres "$client_name" "$DATABASE_URL" "$port"

    # Step 7: Verify migration
    echo "Verifying migration..."
    if docker ps | grep -q "$container_name"; then
        echo "✅ Migration completed successfully!"
        echo
        echo "Next steps:"
        echo "1. Test web access: http://localhost:$port"
        echo "2. Verify chat history and user data"
        echo "3. Monitor container logs for errors"
        echo "4. SQLite backup saved at: $backup_path"
        echo "5. Keep backup for 2-4 weeks before deleting"
    else
        echo "❌ Migration failed - container not running"
        echo "Starting rollback procedure..."
        rollback_to_sqlite "$client_name" "$backup_path"
    fi
}
```

### Integration Points
```yaml
DOCKER:
  - Container recreation with new environment variables
  - Volume preservation (contains uploads, not just database)
  - Port mapping unchanged
  - Container name unchanged (nginx compatibility)

ENVIRONMENT_VARIABLES:
  - DATABASE_URL: Full PostgreSQL connection string
  - VECTOR_DB: Set to "pgvector" (optional, can keep ChromaDB)
  - Other env vars: Preserved from existing container

DEPENDENCIES:
  - uvx: For running migration tool (install if missing)
  - psql: Optional, for manual database verification
  - docker: Required, already present
  - curl: For downloading uv installer if needed

SUPABASE_SETUP:
  - User must create Supabase project beforehand
  - pgvector extension must be enabled manually
  - Connection string provided by user
  - No automatic Supabase project creation

ROLLBACK_STRATEGY:
  - Keep SQLite backup in container volume
  - Keep SQLite backup on host filesystem
  - Rollback function recreates container without DATABASE_URL
  - Restores backup to original location
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
shellcheck mt/client-manager.sh           # Bash linting
shellcheck mt/db-migration-helper.sh      # Bash linting

# Expected: No errors or warnings
# If errors: Fix syntax issues, undefined variables, quoting problems
```

### Level 2: Manual Testing
```bash
# Test 1: Database Detection
# Start a test container with SQLite
./mt/start-template.sh test-client 8090
./mt/client-manager.sh
# Select "Manage Existing Deployment" → "test-client"
# Verify: Shows "Database: SQLite (default)"

# Test 2: Menu Option Display
# Verify: Shows "8) Migrate to Supabase/PostgreSQL" for SQLite deployments
# Verify: Option 9 is "Remove deployment"
# Verify: Option 10 is "Return to deployment list"

# Test 3: Supabase Configuration (Dry Run)
# Select migration option
# Verify: Prompts for Supabase credentials
# Verify: Tests connection before proceeding
# Verify: Rejects invalid credentials with clear error

# Test 4: Full Migration (with real Supabase project)
# Prerequisites:
#   - Create Supabase project
#   - Enable pgvector extension: CREATE EXTENSION IF NOT EXISTS vector;
#   - Note connection details
# Run migration
# Verify: Schema initialized
# Verify: Migration completes without errors
# Verify: Container restarts with PostgreSQL
# Verify: Web interface accessible
# Verify: Chat history preserved
# Verify: User login works

# Test 5: PostgreSQL Configuration Viewer
# After migration, return to manage menu
# Verify: Shows "8) View Database Configuration"
# Select option
# Verify: Displays database host, port, name
# Verify: Password is masked
# Verify: Shows connection status

# Test 6: Rollback (Destructive Test)
# Trigger rollback manually or via failed migration
# Verify: Container recreated with SQLite
# Verify: Data restored from backup
# Verify: Web interface accessible
# Verify: Original data present
```

### Level 3: Edge Cases Testing
```bash
# Edge Case 1: Special Characters in Password
# Test with password containing: @, #, !, %, &
# Verify: URL encoding handled correctly
# Verify: Connection succeeds

# Edge Case 2: Network Interruption
# Simulate network failure during migration
# Verify: Error message displayed
# Verify: Rollback initiated
# Verify: Original container restored

# Edge Case 3: Insufficient Supabase Storage
# Use Supabase project near 500MB limit
# Migrate large database (>450MB)
# Verify: Error detected and reported
# Verify: Migration aborted safely

# Edge Case 4: Missing uvx
# Remove uvx from system
# Run migration
# Verify: uvx installation attempted
# Verify: Migration continues after installation

# Edge Case 5: Container Port Conflict
# During migration, another service uses the port
# Verify: Error detected
# Verify: Clear error message
# Verify: Rollback works
```

## Final Validation Checklist
- [ ] All bash scripts pass shellcheck
- [ ] Database type detection works for SQLite
- [ ] Database type detection works for PostgreSQL
- [ ] Menu option shows correctly for SQLite
- [ ] Menu option shows correctly for PostgreSQL
- [ ] Supabase connection validation works
- [ ] Schema initialization creates all tables
- [ ] Migration tool runs successfully
- [ ] Null byte fix applied post-migration
- [ ] Container recreated with correct env vars
- [ ] Volume preserved (uploads still accessible)
- [ ] Port mapping unchanged
- [ ] Web interface accessible after migration
- [ ] Chat history preserved
- [ ] User authentication works
- [ ] PostgreSQL configuration viewer displays info
- [ ] Rollback restores SQLite successfully
- [ ] Error messages are clear and actionable
- [ ] Documentation updated in README.md

---

## Anti-Patterns to Avoid
- ❌ Don't hardcode Supabase credentials - always prompt user
- ❌ Don't skip connection testing before migration
- ❌ Don't forget to initialize schema before data migration
- ❌ Don't remove SQLite backup immediately after migration
- ❌ Don't change container name during migration (breaks nginx)
- ❌ Don't use Session Mode (port 5432) for Supabase - use Transaction Mode (port 6543)
- ❌ Don't forget to URL-encode special characters in passwords
- ❌ Don't skip null byte fix in PostgreSQL
- ❌ Don't assume uvx is installed - check and install if needed
- ❌ Don't proceed with migration if pgvector extension is missing
- ❌ Don't recreate container if port is already in use
- ❌ Don't lose existing environment variables during recreation

## Zero-Downtime Strategy

### Parallel Container Approach
```bash
# Instead of stopping existing container:
# 1. Keep existing container running (SQLite)
# 2. Create new container with PostgreSQL (different port)
# 3. Migrate data to PostgreSQL while SQLite container serves traffic
# 4. Test PostgreSQL container
# 5. Atomic switch: Update nginx to point to new container
# 6. Stop old SQLite container

# Benefits:
# - No downtime during migration
# - Easy rollback (just switch nginx back)
# - Users unaffected during migration
# - Can test PostgreSQL before committing

# Implementation Note:
# This is an ENHANCEMENT for future version
# Initial implementation can have brief downtime (5-10 minutes)
# Document this clearly in the migration prompt
```

## Confidence Score: 8/10

### High confidence due to:
- Clear reference implementation in migrate.py
- Well-documented Supabase connection patterns
- Existing client-manager.sh patterns to follow
- Comprehensive feature specification with all gotchas
- Bash scripting within team expertise

### Uncertainty areas:
- uvx installation reliability across different systems (7/10 confidence)
- Interactive migration tool integration into bash script (7/10 confidence)
- Network reliability during long migrations (8/10 confidence)
- Edge cases with special password characters (8/10 confidence)

### Risk Mitigation:
- Implement comprehensive error handling
- Add detailed logging at each step
- Keep SQLite backup in multiple locations
- Test rollback procedure thoroughly
- Provide clear user feedback at every stage
- Document all prerequisites and assumptions
