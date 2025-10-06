#!/bin/bash

# Database Migration Helper for Open WebUI
# Handles SQLite to Supabase/PostgreSQL migration

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory for locating helper files
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Global variables for Supabase configuration
SUPABASE_PROJECT_REF=""
SUPABASE_PASSWORD=""
SUPABASE_REGION=""
DATABASE_URL=""

#######################################
# Get Supabase configuration from user
# Globals:
#   SUPABASE_PROJECT_REF, SUPABASE_PASSWORD, SUPABASE_REGION, DATABASE_URL
# Returns:
#   0 on success, 1 on failure
#######################################
get_supabase_config() {
    echo
    echo "╔════════════════════════════════════════╗"
    echo "║   Supabase PostgreSQL Configuration   ║"
    echo "╚════════════════════════════════════════╝"
    echo
    echo "Please provide your Supabase connection details."
    echo
    echo "📍 Where to find this information:"
    echo "   1. Go to your Supabase project dashboard"
    echo "   2. Navigate to: Project Settings → Database"
    echo "   3. Scroll to 'Connection String' section"
    echo
    echo "Supabase provides two connection modes:"
    echo
    echo "┌─────────────────────────────────────────────────────────────┐"
    echo "│ Session Mode (Port 5432) - RECOMMENDED                     │"
    echo "├─────────────────────────────────────────────────────────────┤"
    echo "│ ✅ Supports prepared statements                             │"
    echo "│ ✅ Better for long-lived connections                        │"
    echo "│ ✅ More stable for Open WebUI                               │"
    echo "│ ✅ Available on all Supabase plans                          │"
    echo "│                                                             │"
    echo "│ Connection format:                                          │"
    echo "│ postgres://postgres.PROJECT:PASS@REGION.pooler....:5432     │"
    echo "└─────────────────────────────────────────────────────────────┘"
    echo
    echo "┌─────────────────────────────────────────────────────────────┐"
    echo "│ Transaction Mode (Port 6543)                                │"
    echo "├─────────────────────────────────────────────────────────────┤"
    echo "│ ⚡ Optimized for serverless/edge functions                  │"
    echo "│ ⚡ Better for many short-lived connections                  │"
    echo "│ ⚠️  No prepared statements support                          │"
    echo "│ ⚠️  May not be available on free tier                       │"
    echo "│                                                             │"
    echo "│ Connection format:                                          │"
    echo "│ postgres://postgres:PASS@db.PROJECT.supabase.co:6543        │"
    echo "└─────────────────────────────────────────────────────────────┘"
    echo
    echo "💡 Recommendation: Use Session Mode unless you have specific"
    echo "   serverless requirements. Both work for migration."
    echo
    echo -n "Which mode do you want to use? (session/transaction) [session]: "
    read -r connection_mode
    connection_mode=${connection_mode:-session}

    if [[ "$connection_mode" =~ ^[Tt] ]]; then
        # Transaction Mode - Direct connection format
        echo
        echo "Using Transaction Mode (Port 6543)"
        echo
        echo "📦 Project Reference:"
        echo "   Found in connection string: db.PROJECT.supabase.co"
        echo "   Example: 'dgjvrkoxxmbndvtxvqjv'"
        echo
        echo -n "Enter Project Reference: "
        read -r SUPABASE_PROJECT_REF

        if [[ -z "$SUPABASE_PROJECT_REF" ]]; then
            echo -e "${RED}❌ Project reference is required${NC}"
            return 1
        fi

        echo
        echo "🔑 Database Password:"
        echo "   The password you set when creating your Supabase project"
        echo
        echo -n "Enter Database Password: "
        read -rs SUPABASE_PASSWORD
        echo

        if [[ -z "$SUPABASE_PASSWORD" ]]; then
            echo -e "${RED}❌ Password is required${NC}"
            return 1
        fi

        # URL-encode the password
        local encoded_password=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$SUPABASE_PASSWORD', safe=''))" 2>/dev/null)

        if [[ -z "$encoded_password" ]]; then
            echo -e "${YELLOW}⚠️  Warning: Could not URL-encode password. Using as-is.${NC}"
            encoded_password="$SUPABASE_PASSWORD"
        fi

        # Transaction Mode format
        DATABASE_URL="postgresql://postgres:${encoded_password}@db.${SUPABASE_PROJECT_REF}.supabase.co:6543/postgres"

        echo
        echo "Connection string built (password hidden):"
        echo "  postgresql://postgres:****@db.${SUPABASE_PROJECT_REF}.supabase.co:6543/postgres"

    else
        # Session Mode - Pooler connection format
        echo
        echo "Using Session Mode (Port 5432)"
        echo
        echo "📦 Project Reference:"
        echo "   The part after 'postgres.' and before the ':'"
        echo "   Example: In 'postgres.abcxyz123:pass@...', it's 'abcxyz123'"
        echo
        echo -n "Enter Project Reference: "
        read -r SUPABASE_PROJECT_REF

        if [[ -z "$SUPABASE_PROJECT_REF" ]]; then
            echo -e "${RED}❌ Project reference is required${NC}"
            return 1
        fi

        echo
        echo "🔑 Database Password:"
        echo "   The password you set when creating your Supabase project"
        echo
        echo -n "Enter Database Password: "
        read -rs SUPABASE_PASSWORD
        echo

        if [[ -z "$SUPABASE_PASSWORD" ]]; then
            echo -e "${RED}❌ Password is required${NC}"
            return 1
        fi

        echo
        echo "🌍 Region:"
        echo "   The part after '@' and before '.pooler.supabase.com'"
        echo "   Example: In '@aws-1-us-east-2.pooler...', it's 'aws-1-us-east-2'"
        echo
        echo "   Common regions:"
        echo "   • aws-0-us-east-1 / aws-1-us-east-2 (US East)"
        echo "   • aws-0-us-west-1 / aws-1-us-west-2 (US West)"
        echo "   • aws-0-eu-west-1 (Europe - Ireland)"
        echo "   • aws-0-eu-central-1 (Europe - Frankfurt)"
        echo "   • aws-0-ap-southeast-1 (Asia Pacific)"
        echo
        echo -n "Enter Region: "
        read -r SUPABASE_REGION

        if [[ -z "$SUPABASE_REGION" ]]; then
            echo -e "${RED}❌ Region is required${NC}"
            return 1
        fi

        # URL-encode the password
        local encoded_password=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$SUPABASE_PASSWORD', safe=''))" 2>/dev/null)

        if [[ -z "$encoded_password" ]]; then
            echo -e "${YELLOW}⚠️  Warning: Could not URL-encode password. Using as-is.${NC}"
            encoded_password="$SUPABASE_PASSWORD"
        fi

        # Session Mode format
        DATABASE_URL="postgresql://postgres.${SUPABASE_PROJECT_REF}:${encoded_password}@${SUPABASE_REGION}.pooler.supabase.com:5432/postgres"

        echo
        echo "Connection string built (password hidden):"
        echo "  postgresql://postgres.${SUPABASE_PROJECT_REF}:****@${SUPABASE_REGION}.pooler.supabase.com:5432/postgres"
    fi

    echo
    echo -e "${GREEN}Configuration complete!${NC}"
    return 0
}

#######################################
# Test Supabase PostgreSQL connection
# Arguments:
#   $1 - Database URL
# Returns:
#   0 on success, 1 on failure
#######################################
test_supabase_connection() {
    local db_url="$1"

    echo
    echo "Testing Supabase connection..."
    echo "(Using temporary Docker container - no impact on production)"
    echo

    # Use a temporary Docker container with Open WebUI image (has psycopg2 built-in)
    # The --rm flag ensures the container is deleted immediately after the test
    # Pass DATABASE_URL as environment variable to avoid bash escaping issues
    local test_output=$(docker run --rm -e DATABASE_URL="$db_url" ghcr.io/imagicrafter/open-webui:main python3 -c "
import psycopg2
import sys
import os
try:
    db_url = os.environ['DATABASE_URL']
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute('SELECT version();')
    version = cur.fetchone()[0]
    print(f'Connected successfully')
    print(f'PostgreSQL version: {version.split(\",\")[0]}')
    cur.close()
    conn.close()
    sys.exit(0)
except Exception as e:
    print(f'Connection failed: {e}')
    sys.exit(1)
" 2>&1)

    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ Connection successful!${NC}"
        echo
        echo "$test_output" | grep -E "(Connected|PostgreSQL version)"
        return 0
    else
        echo -e "${RED}❌ Connection failed!${NC}"
        echo
        echo "Error details:"
        echo "$test_output"
        echo
        echo "Common issues:"
        echo "  • Check that password special characters are entered correctly"
        echo "  • Verify project reference matches your Supabase project"
        echo "  • Ensure region is correct (e.g., aws-1-us-east-2)"
        echo "  • Check that you selected the right connection mode (session/transaction)"
        echo
        echo "Please verify your credentials and try again."
        return 1
    fi
}

#######################################
# Check if pgvector extension is enabled
# Arguments:
#   $1 - Database URL
# Returns:
#   0 if enabled, 1 if not enabled
#######################################
check_pgvector_extension() {
    local db_url="$1"

    echo
    echo "Checking pgvector extension..."
    echo "(Using temporary Docker container)"
    echo

    # Use temporary Docker container to check for pgvector extension
    # Pass DATABASE_URL as environment variable to avoid bash escaping issues
    local check_output=$(docker run --rm -e DATABASE_URL="$db_url" ghcr.io/imagicrafter/open-webui:main python3 -c "
import psycopg2
import sys
import os
try:
    db_url = os.environ['DATABASE_URL']
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute(\"SELECT 1 FROM pg_extension WHERE extname='vector'\")
    result = cur.fetchone()
    cur.close()
    conn.close()
    if result:
        print('1')
        sys.exit(0)
    else:
        print('0')
        sys.exit(0)
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
" 2>&1)

    if [[ "$check_output" == "1" ]]; then
        echo -e "${GREEN}✅ pgvector extension is enabled${NC}"
        return 0
    elif [[ "$check_output" == "0" ]]; then
        echo -e "${YELLOW}⚠️  pgvector extension is NOT enabled${NC}"
        echo
        echo "To enable pgvector:"
        echo "1. Go to your Supabase project dashboard"
        echo "2. Navigate to Database → Extensions"
        echo "3. Search for 'vector' and enable it"
        echo
        echo "Or run this SQL in the SQL Editor:"
        echo "  CREATE EXTENSION IF NOT EXISTS vector;"
        echo
        echo "Note: pgvector is required for RAG/document search features."
        echo "      Open WebUI will work without it, but with limited functionality."
        echo
        echo -n "Continue without pgvector? (y/N): "
        read -r confirm

        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            echo "Continuing without pgvector (RAG features may not work optimally)"
            return 0
        else
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️  Could not check pgvector extension${NC}"
        echo "Error: $check_output"
        echo
        echo -n "Continue anyway? (y/N): "
        read -r confirm

        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            return 0
        else
            return 1
        fi
    fi
}

#######################################
# Backup SQLite database
# Arguments:
#   $1 - Container name
#   $2 - Client identifier (FQDN or client name for backup file naming)
# Returns:
#   Backup path on stdout, or empty on failure
#######################################
backup_sqlite_database() {
    local container_name="$1"
    local client_identifier="$2"

    # Sanitize client_identifier for use in filename (replace invalid chars)
    local safe_identifier=$(echo "$client_identifier" | sed 's/:/_/g; s/\//_/g; s/ /_/g')

    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_filename="webui-backup-${safe_identifier}-${timestamp}.db"
    local container_backup_path="/app/backend/data/${backup_filename}"
    local host_backup_path="/tmp/${backup_filename}"

    echo >&2
    echo "Backing up SQLite database for ${client_identifier}..." >&2

    # Create backup inside container
    if docker exec "$container_name" cp /app/backend/data/webui.db "$container_backup_path" 2>/dev/null; then
        echo -e "${GREEN}✅ Created backup in container: ${container_backup_path}${NC}" >&2
    else
        echo -e "${RED}❌ Failed to create backup in container${NC}" >&2
        return 1
    fi

    # Copy backup to host
    if docker cp "${container_name}:${container_backup_path}" "$host_backup_path" 2>/dev/null; then
        echo -e "${GREEN}✅ Copied backup to host: ${host_backup_path}${NC}" >&2
        echo "$host_backup_path"
        return 0
    else
        echo -e "${RED}❌ Failed to copy backup to host${NC}" >&2
        return 1
    fi
}

#######################################
# Initialize PostgreSQL schema
# Arguments:
#   $1 - Container name
#   $2 - Database URL
#   $3 - Port
# Returns:
#   0 on success, 1 on failure
#######################################
initialize_postgresql_schema() {
    local container_name="$1"
    local database_url="$2"
    local port="$3"
    local init_container="${container_name}-schema-init"

    # Use a temporary port (original port + 10000) to avoid conflicts
    local temp_port=$((port + 10000))

    echo
    echo "╔════════════════════════════════════════╗"
    echo "║    Initializing PostgreSQL Schema     ║"
    echo "╚════════════════════════════════════════╝"
    echo
    echo "This will start Open WebUI temporarily to create database tables."
    echo "This process takes about 30-60 seconds..."
    echo
    echo "Using temporary port: $temp_port"
    echo

    # Start temporary container with PostgreSQL configuration
    echo "Starting initialization container..."

    # First, ensure no leftover container with this name exists
    docker rm -f "$init_container" > /dev/null 2>&1

    # Create and start container
    local container_id=$(docker run -d \
        --name "$init_container" \
        -p "${temp_port}:8080" \
        -e DATABASE_URL="$database_url" \
        -e VECTOR_DB="pgvector" \
        ghcr.io/imagicrafter/open-webui:main 2>&1)

    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to create initialization container${NC}"
        echo
        echo "Error details:"
        echo "$container_id"
        echo

        # Check if port is in use
        if echo "$container_id" | grep -q "port is already allocated"; then
            echo "Port $port is already in use. Please stop the container using this port."
        fi

        return 1
    fi

    # Wait a moment for container to start
    sleep 2

    # Verify container is actually running
    local container_state=$(docker inspect --format='{{.State.Status}}' "$init_container" 2>/dev/null)

    if [ "$container_state" != "running" ]; then
        echo -e "${RED}❌ Container created but failed to start${NC}"
        echo
        echo "Container state: $container_state"
        echo
        echo "Error logs:"
        docker logs "$init_container" 2>&1
        echo

        # Get more details about why it didn't start
        local error_msg=$(docker inspect --format='{{.State.Error}}' "$init_container" 2>/dev/null)
        if [ -n "$error_msg" ]; then
            echo "Error message: $error_msg"
            echo
        fi

        docker rm -f "$init_container" > /dev/null 2>&1
        return 1
    fi

    echo "Container started successfully (ID: ${container_id:0:12})"

    # Wait for schema initialization
    echo "Waiting for schema initialization..."
    local max_wait=180
    local waited=0
    local initialized=false

    while [ $waited -lt $max_wait ]; do
        local logs=$(docker logs "$init_container" 2>&1)

        # Check for successful startup indicators
        if echo "$logs" | grep -q "Application startup complete"; then
            echo -e "${GREEN}✅ Schema initialized successfully${NC}"
            initialized=true
            break
        fi

        # Alternative success indicators
        if echo "$logs" | grep -q "Uvicorn running on"; then
            echo -e "${GREEN}✅ Schema initialized successfully (Uvicorn started)${NC}"
            initialized=true
            break
        fi

        # Server process started - means migrations completed successfully
        if echo "$logs" | grep -q "Started server process"; then
            echo -e "${GREEN}✅ Schema initialized successfully (Server started)${NC}"
            initialized=true
            break
        fi

        # Database migrations completed - schema is initialized
        if echo "$logs" | grep -q "Dropping unique index" && echo "$logs" | grep -q "Waiting for application startup"; then
            echo -e "${GREEN}✅ Schema initialized successfully (Migrations complete)${NC}"
            initialized=true
            break
        fi

        # Check for fatal errors only (ignore warnings)
        if echo "$logs" | grep -qi "fatal\|critical\|cannot connect"; then
            echo -e "${RED}❌ Fatal error detected during initialization${NC}"
            echo "Last logs:"
            docker logs --tail 20 "$init_container"
            break
        fi

        echo -n "."
        sleep 3
        waited=$((waited + 3))
    done

    echo

    # If not initialized, show logs before cleanup
    if [ "$initialized" != true ]; then
        echo -e "${RED}❌ Schema initialization timed out or failed${NC}"
        echo
        echo "Container logs (last 30 lines):"
        echo "================================"
        docker logs --tail 30 "$init_container" 2>&1
        echo "================================"
        echo
    fi

    # Stop and remove temporary container
    echo "Cleaning up initialization container..."
    docker stop "$init_container" > /dev/null 2>&1
    docker rm "$init_container" > /dev/null 2>&1

    if [ "$initialized" = true ]; then
        return 0
    else
        return 1
    fi
}

#######################################
# Run migration tool
# Arguments:
#   $1 - SQLite backup path
#   $2 - PostgreSQL connection string
#   $3 - Client identifier (FQDN or client name for log file naming)
# Returns:
#   0 on success, 1 on failure
#######################################
run_migration_tool() {
    local sqlite_path="$1"
    local postgres_url="$2"
    local client_identifier="$3"

    echo
    echo "╔════════════════════════════════════════╗"
    echo "║      Running Database Migration       ║"
    echo "╚════════════════════════════════════════╝"
    echo
    echo "This process may take 15-30 minutes for large databases..."
    echo

    echo "SQLite backup file: $sqlite_path"
    echo "PostgreSQL target: ${postgres_url%%:*}://***@${postgres_url##*@}"
    echo

    # Use custom non-interactive migration script
    echo "Running custom migration script..."
    echo

    # Run migration in Docker container (has psycopg2 pre-installed)
    # Copy our migration script and SQLite backup into container
    local container_name="migration-temp-$$"

    echo "Creating temporary migration container..."
    docker run -d --name "$container_name" \
        -v "$(dirname "$sqlite_path"):/backup" \
        ghcr.io/imagicrafter/open-webui:main sleep 3600 > /dev/null 2>&1

    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to create migration container${NC}"
        return 1
    fi

    # Copy migration script into container
    docker cp "${SCRIPT_DIR}/migrate-db.py" "${container_name}:/tmp/migrate-db.py" > /dev/null 2>&1

    # Run migration
    echo "Migrating data..."
    echo

    docker exec "$container_name" python3 /tmp/migrate-db.py \
        "/backup/$(basename "$sqlite_path")" \
        "$postgres_url" \
        "$client_identifier"

    local exit_code=$?

    # PAUSE before cleanup to let user read output
    echo
    echo "============================================================"
    echo "IMPORTANT: Press Enter to continue and save migration log..."
    echo "============================================================"
    read

    # Copy migration log file out of container before cleanup
    echo
    echo "Retrieving migration log..."

    # Find any migration log in the container (use wildcard to catch all)
    local log_file=$(docker exec "$container_name" ls -t /tmp/migration-*.log 2>&1)

    echo "DEBUG: ls result: $log_file"

    if [[ -n "$log_file" && ! "$log_file" =~ "No such file" ]]; then
        local first_log=$(echo "$log_file" | head -1)
        echo "Found log file: $first_log"
        echo "Executing: docker cp ${container_name}:${first_log} /tmp/"

        if docker cp "${container_name}:${first_log}" /tmp/ 2>&1; then
            echo -e "${GREEN}✅ Migration log saved to: /tmp/$(basename "$first_log")${NC}"
            echo "You can view it with: cat /tmp/$(basename "$first_log")"
        else
            echo -e "${RED}⚠ Warning: Failed to copy log file${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ Warning: No migration log file found in container${NC}"
        echo "Container contents:"
        docker exec "$container_name" ls -la /tmp/ 2>&1 | grep migration
    fi

    # Cleanup
    echo
    echo "Cleaning up migration container..."
    docker stop "$container_name" > /dev/null 2>&1
    docker rm "$container_name" > /dev/null 2>&1

    if [ $exit_code -eq 0 ]; then
        echo
        echo -e "${GREEN}✅ Migration completed successfully${NC}"
        return 0
    else
        echo
        echo -e "${RED}❌ Migration failed with exit code: $exit_code${NC}"
        echo
        echo "Common issues:"
        echo "  • Verify the backup file exists: $sqlite_path"
        echo "  • Check PostgreSQL connection is still active"
        echo "  • Ensure sufficient disk space on Supabase"
        echo "  • Review migration output above for specific errors"
        return 1
    fi
}

#######################################
# Fix null byte issue in PostgreSQL
# Arguments:
#   $1 - Database URL
# Returns:
#   0 on success, 1 on failure
#######################################
fix_null_bytes() {
    local db_url="$1"

    echo
    echo "Fixing null byte issue in PostgreSQL..."
    echo "This is required for proper search functionality."
    echo "(Using temporary Docker container)"
    echo

    # Use temporary Docker container to fix null bytes
    # Pass DATABASE_URL as environment variable to avoid bash escaping issues
    local fix_output=$(docker run --rm -e DATABASE_URL="$db_url" ghcr.io/imagicrafter/open-webui:main python3 -c "
import psycopg2
import sys
import os
try:
    db_url = os.environ['DATABASE_URL']
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    # Check if chat table exists
    cur.execute(\"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'chat')\")
    table_exists = cur.fetchone()[0]

    if table_exists:
        # Fix null bytes in chat table
        cur.execute(\"UPDATE chat SET chat = REPLACE(chat::TEXT, E'\\\\\\\\u0000', '')::JSONB WHERE chat::TEXT LIKE '%\\\\\\\\u0000%'\")
        rows_affected = cur.rowcount
        conn.commit()
        print(f'Fixed {rows_affected} rows with null bytes')
        sys.exit(0)
    else:
        print('Chat table does not exist yet')
        sys.exit(0)
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
finally:
    if cur:
        cur.close()
    if conn:
        conn.close()
" 2>&1)

    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ Null byte fix completed${NC}"
        echo "$fix_output"
        return 0
    else
        echo -e "${YELLOW}⚠️  Could not fix null bytes${NC}"
        echo "Error: $fix_output"
        echo
        echo "This is not critical - you can fix it manually later with:"
        echo "  UPDATE chat SET chat = REPLACE(chat::TEXT, E'\\\\u0000', '')::JSONB WHERE chat::TEXT LIKE '%\\\\u0000%';"
        return 0  # Don't fail migration for this
    fi
}

#######################################
# Recreate container with PostgreSQL configuration
# Arguments:
#   $1 - Client name
#   $2 - Database URL
#   $3 - Port
# Returns:
#   0 on success, 1 on failure
#######################################
recreate_container_with_postgres() {
    local client_name="$1"
    local database_url="$2"
    local port="$3"
    local container_name="openwebui-${client_name}"
    local volume_name="openwebui-${client_name}-data"

    echo
    echo "╔════════════════════════════════════════╗"
    echo "║   Recreating Container with PostgreSQL ║"
    echo "╚════════════════════════════════════════╝"
    echo

    # Get existing environment variables using docker inspect (works on running or stopped containers)
    local redirect_uri=$(docker inspect --format='{{range .Config.Env}}{{println .}}{{end}}' "$container_name" 2>/dev/null | grep "^GOOGLE_REDIRECT_URI=" | cut -d'=' -f2- 2>/dev/null || echo "")
    local allowed_domains=$(docker inspect --format='{{range .Config.Env}}{{println .}}{{end}}' "$container_name" 2>/dev/null | grep "^OAUTH_ALLOWED_DOMAINS=" | cut -d'=' -f2- 2>/dev/null || echo "martins.net")
    local webui_name=$(docker inspect --format='{{range .Config.Env}}{{println .}}{{end}}' "$container_name" 2>/dev/null | grep "^WEBUI_NAME=" | cut -d'=' -f2- 2>/dev/null || echo "QuantaBase")

    # Stop and remove existing container
    echo "Stopping existing container..."
    docker stop "$container_name" > /dev/null 2>&1

    echo "Removing existing container..."
    docker rm "$container_name" > /dev/null 2>&1

    # Create new container with PostgreSQL
    echo "Creating new container with PostgreSQL configuration..."

    local docker_cmd="docker run -d \
        --name \"$container_name\" \
        -p \"${port}:8080\" \
        -e DATABASE_URL=\"$database_url\" \
        -e VECTOR_DB=\"pgvector\" \
        -e GOOGLE_CLIENT_ID=1063776054060-2fa0vn14b7ahi1tmfk49cuio44goosc1.apps.googleusercontent.com \
        -e GOOGLE_CLIENT_SECRET=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 \
        -e ENABLE_OAUTH_SIGNUP=true \
        -e OAUTH_ALLOWED_DOMAINS=\"$allowed_domains\" \
        -e OPENID_PROVIDER_URL=https://accounts.google.com/.well-known/openid-configuration \
        -e USER_PERMISSIONS_CHAT_CONTROLS=false \
        -v \"${volume_name}:/app/backend/data\" \
        --restart unless-stopped"

    # Add redirect URI if it exists
    if [[ -n "$redirect_uri" ]]; then
        docker_cmd="$docker_cmd -e GOOGLE_REDIRECT_URI=\"$redirect_uri\""
    fi

    # Add WEBUI_NAME if it exists
    if [[ -n "$webui_name" ]]; then
        docker_cmd="$docker_cmd -e WEBUI_NAME=\"$webui_name\""
    fi

    docker_cmd="$docker_cmd ghcr.io/imagicrafter/open-webui:main"

    # Execute docker run
    if eval "$docker_cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Container recreated successfully${NC}"

        # Wait for container to be healthy
        echo "Waiting for container to start..."
        sleep 5

        if docker ps | grep -q "$container_name"; then
            echo -e "${GREEN}✅ Container is running${NC}"
            return 0
        else
            echo -e "${RED}❌ Container failed to start${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ Failed to create container${NC}"
        return 1
    fi
}

#######################################
# Rollback to SQLite
# Arguments:
#   $1 - Client name
#   $2 - Backup path
#   $3 - Port
# Returns:
#   0 on success, 1 on failure
#######################################
rollback_to_sqlite() {
    local client_name="$1"
    local backup_path="$2"
    local port="$3"
    local container_name="openwebui-${client_name}"
    local volume_name="openwebui-${client_name}-data"

    echo
    echo "╔════════════════════════════════════════╗"
    echo "║        Rolling Back to SQLite          ║"
    echo "╚════════════════════════════════════════╝"
    echo

    # Get existing environment variables using docker inspect (works on running or stopped containers)
    local redirect_uri=$(docker inspect --format='{{range .Config.Env}}{{println .}}{{end}}' "$container_name" 2>/dev/null | grep "^GOOGLE_REDIRECT_URI=" | cut -d'=' -f2- 2>/dev/null || echo "")
    local allowed_domains=$(docker inspect --format='{{range .Config.Env}}{{println .}}{{end}}' "$container_name" 2>/dev/null | grep "^OAUTH_ALLOWED_DOMAINS=" | cut -d'=' -f2- 2>/dev/null || echo "martins.net")
    local webui_name=$(docker inspect --format='{{range .Config.Env}}{{println .}}{{end}}' "$container_name" 2>/dev/null | grep "^WEBUI_NAME=" | cut -d'=' -f2- 2>/dev/null || echo "QuantaBase")

    # Stop and remove PostgreSQL container
    echo "Stopping PostgreSQL container..."
    docker stop "$container_name" > /dev/null 2>&1
    docker rm "$container_name" > /dev/null 2>&1

    # Restore SQLite backup
    if [[ -f "$backup_path" ]]; then
        echo "Restoring SQLite backup..."

        # Create temporary container to restore backup
        docker run -d --name "${container_name}-restore-temp" \
            -v "${volume_name}:/app/backend/data" \
            ghcr.io/imagicrafter/open-webui:main sleep 3600 > /dev/null 2>&1

        docker cp "$backup_path" "${container_name}-restore-temp:/app/backend/data/webui.db"

        docker stop "${container_name}-restore-temp" > /dev/null 2>&1
        docker rm "${container_name}-restore-temp" > /dev/null 2>&1

        echo -e "${GREEN}✅ SQLite backup restored${NC}"
    else
        echo -e "${YELLOW}⚠️  Backup not found, proceeding without restore${NC}"
    fi

    # Recreate container without DATABASE_URL (SQLite)
    echo "Creating container with SQLite configuration..."

    local docker_cmd="docker run -d \
        --name \"$container_name\" \
        -p \"${port}:8080\" \
        -e GOOGLE_CLIENT_ID=1063776054060-2fa0vn14b7ahi1tmfk49cuio44goosc1.apps.googleusercontent.com \
        -e GOOGLE_CLIENT_SECRET=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 \
        -e ENABLE_OAUTH_SIGNUP=true \
        -e OAUTH_ALLOWED_DOMAINS=\"$allowed_domains\" \
        -e OPENID_PROVIDER_URL=https://accounts.google.com/.well-known/openid-configuration \
        -e USER_PERMISSIONS_CHAT_CONTROLS=false \
        -v \"${volume_name}:/app/backend/data\" \
        --restart unless-stopped"

    # Add redirect URI if it exists
    if [[ -n "$redirect_uri" ]]; then
        docker_cmd="$docker_cmd -e GOOGLE_REDIRECT_URI=\"$redirect_uri\""
    fi

    # Add WEBUI_NAME if it exists
    if [[ -n "$webui_name" ]]; then
        docker_cmd="$docker_cmd -e WEBUI_NAME=\"$webui_name\""
    fi

    docker_cmd="$docker_cmd ghcr.io/imagicrafter/open-webui:main"

    # Execute docker run
    if eval "$docker_cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Rollback successful - Container running with SQLite${NC}"
        return 0
    else
        echo -e "${RED}❌ Rollback failed${NC}"
        return 1
    fi
}

#######################################
# Display PostgreSQL configuration
# Arguments:
#   $1 - Container name
# Returns:
#   0 on success
#######################################
display_postgres_config() {
    local container_name="$1"

    # Get DATABASE_URL from container using docker inspect
    local database_url=$(docker inspect --format='{{range .Config.Env}}{{println .}}{{end}}' "$container_name" 2>/dev/null | grep "^DATABASE_URL=" | cut -d'=' -f2- 2>/dev/null)

    if [[ -z "$database_url" ]]; then
        echo -e "${RED}❌ No PostgreSQL configuration found${NC}"
        return 1
    fi

    # Get FQDN from redirect URI for backup filtering
    local redirect_uri=$(docker inspect --format='{{range .Config.Env}}{{println .}}{{end}}' "$container_name" 2>/dev/null | grep "^GOOGLE_REDIRECT_URI=" | cut -d'=' -f2- 2>/dev/null)
    local fqdn=""
    if [[ -n "$redirect_uri" ]]; then
        fqdn=$(echo "$redirect_uri" | sed -E 's|https?://||' | sed 's|/oauth/google/callback||')
    fi

    # Use container name as fallback if no FQDN
    local client_identifier="${fqdn:-${container_name#openwebui-}}"
    # Sanitize for filename matching
    local safe_identifier=$(echo "$client_identifier" | sed 's/:/_/g; s/\//_/g; s/ /_/g')

    # Parse connection details
    local db_host=$(echo "$database_url" | sed 's|postgresql://[^@]*@||' | cut -d':' -f1)
    local db_port=$(echo "$database_url" | sed 's|.*:||' | cut -d'/' -f1)
    local db_name=$(echo "$database_url" | sed 's|.*/||')
    local db_user=$(echo "$database_url" | sed 's|postgresql://||' | cut -d':' -f1)

    # Mask password
    local masked_url=$(echo "$database_url" | sed 's|:[^:@]*@|:****@|')

    echo
    echo "╔════════════════════════════════════════╗"
    echo "║    PostgreSQL Database Configuration   ║"
    echo "╚════════════════════════════════════════╝"
    echo
    echo "Database Type:  PostgreSQL (Supabase)"
    echo "Host:           $db_host:$db_port"
    echo "Database:       $db_name"
    echo "User:           $db_user"
    echo "Connection:     $masked_url"
    echo
    echo "─────────────────────────────────────────"
    echo
    echo "1) Test connection"
    echo "2) Rollback to SQLite database"
    echo "3) Return to manage menu"
    echo
    echo -n "Select option (1-3): "
    read option

    case "$option" in
        1)
            # Test connection
            echo
            echo -n "Testing connection... "
            if test_supabase_connection "$database_url"; then
                echo -e "${GREEN}✅ Connected successfully${NC}"
            else
                echo -e "${RED}❌ Connection failed${NC}"
            fi
            echo
            echo "Press Enter to continue..."
            read
            # Re-display menu
            display_postgres_config "$container_name"
            ;;
        2)
            # Rollback to SQLite
            clear
            echo "╔════════════════════════════════════════╗"
            echo "║     Rollback to SQLite Database        ║"
            echo "╚════════════════════════════════════════╝"
            echo
            echo "⚠️  WARNING: This will revert to SQLite database"
            echo
            echo "What will happen:"
            echo "  1. Stop the current PostgreSQL deployment"
            echo "  2. Restore the latest SQLite backup (if available)"
            echo "  3. Recreate container with SQLite configuration"
            echo "  4. PostgreSQL data will remain in Supabase (not deleted)"
            echo
            echo "Latest backups available for ${client_identifier}:"
            ls -lh /tmp/webui-backup-${safe_identifier}-*.db 2>/dev/null | tail -5 | awk '{print "  " $9 " (" $5 " - " $6 " " $7 ")"}'
            echo
            echo -n "Continue with rollback? (yes/NO): "
            read confirm

            if [[ "$confirm" == "yes" ]]; then
                # Find most recent backup for this client
                local latest_backup=$(ls -t /tmp/webui-backup-${safe_identifier}-*.db 2>/dev/null | head -1)

                # Fallback: If no client-specific backup found, try any backup
                if [[ -z "$latest_backup" ]]; then
                    echo
                    echo -e "${YELLOW}⚠ No backup found with client identifier, searching for any backup...${NC}"
                    latest_backup=$(ls -t /tmp/webui-backup-*.db 2>/dev/null | head -1)
                fi

                if [[ -z "$latest_backup" ]]; then
                    echo
                    echo -e "${RED}❌ No backup found in /tmp/${NC}"
                    echo "Cannot proceed with rollback without a backup."
                else
                    echo
                    echo "Using backup: $latest_backup"

                    # Extract client name from container name
                    local client_name="${container_name#openwebui-}"

                    # Get current port
                    local current_port=$(docker inspect --format='{{range $p, $conf := .NetworkSettings.Ports}}{{(index $conf 0).HostPort}}{{end}}' "$container_name" 2>/dev/null)
                    if [[ -z "$current_port" ]]; then
                        current_port=8080
                    fi

                    # Perform rollback
                    rollback_to_sqlite "$client_name" "$latest_backup" "$current_port"
                fi
            else
                echo "Rollback cancelled."
            fi
            ;;
        3)
            # Return to menu
            return 0
            ;;
        *)
            echo "Invalid selection."
            ;;
    esac

    return 0
}
