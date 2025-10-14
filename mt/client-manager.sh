#!/bin/bash

# Multi-Client Management Script

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

show_help() {
    echo "Multi-Client Open WebUI Management"
    echo "=================================="
    echo
    echo "Start Clients:"
    echo "  ./start-acme-corp.sh       - Start ACME Corp instance (port 8081)"
    echo "  ./start-beta-client.sh     - Start Beta Client instance (port 8082)"
    echo "  ./start-template.sh NAME PORT DOMAIN - Start custom client"
    echo
    echo "Manage All Clients:"
    echo "  ./client-manager.sh list   - List all Open WebUI containers"
    echo "  ./client-manager.sh stop   - Stop all Open WebUI containers"
    echo "  ./client-manager.sh start  - Start all Open WebUI containers"
    echo "  ./client-manager.sh logs CLIENT_NAME - Show logs for specific client"
    echo
    echo "Individual Client Commands:"
    echo "  docker stop openwebui-CLIENT_NAME"
    echo "  docker start openwebui-CLIENT_NAME"
    echo "  docker logs -f openwebui-CLIENT_NAME"
    echo
}

show_main_menu() {
    clear
    echo "╔════════════════════════════════════════╗"
    echo "║       Open WebUI Client Manager        ║"
    echo "╚════════════════════════════════════════╝"
    echo
    echo "1) View Deployment Status"
    echo "2) Create New Deployment"
    echo "3) Manage Existing Deployment"
    echo "4) Generate nginx Configuration"
    echo "5) Exit"
    echo
    echo -n "Please select an option (1-5): "
}

# Detect container type (sync-node vs client)
detect_container_type() {
    local client_name="$1"

    # Check if this is a sync node
    if [[ "$client_name" == "sync-node-a" ]] || [[ "$client_name" == "sync-node-b" ]]; then
        echo "sync-node"
    else
        echo "client"
    fi
}

get_next_available_port() {
    local start_port=8081
    local max_port=8099

    for ((port=$start_port; port<=$max_port; port++)); do
        # Check if port is used by Docker containers
        if ! docker ps --format "{{.Ports}}" | grep -q ":${port}->"; then
            # Check if port is in use by any process (without sudo)
            if ! lsof -i :$port >/dev/null 2>&1; then
                # Double-check with netstat as backup
                if ! netstat -ln 2>/dev/null | grep -q ":${port} "; then
                    echo $port
                    return 0
                fi
            fi
        fi
    done

    echo "No available ports in range 8081-8099"
    return 1
}

create_new_deployment() {
    clear
    echo "╔════════════════════════════════════════╗"
    echo "║         Create New Deployment          ║"
    echo "╚════════════════════════════════════════╝"
    echo

    # Get client name
    echo -n "Enter client name (lowercase, no spaces): "
    read client_name

    if [[ ! "$client_name" =~ ^[a-z0-9-]+$ ]]; then
        echo "❌ Invalid client name. Use only lowercase letters, numbers, and hyphens."
        echo "Press Enter to continue..."
        read
        return 1
    fi

    # Check if client already exists
    if docker ps -a --filter "name=openwebui-${client_name}" --format "{{.Names}}" | grep -q "openwebui-${client_name}"; then
        echo "❌ Client '${client_name}' already exists!"
        echo "Press Enter to continue..."
        read
        return 1
    fi

    # Get next available port
    echo "Finding next available port..."
    port=$(get_next_available_port)
    if [ $? -ne 0 ]; then
        echo "❌ $port"
        echo "Press Enter to continue..."
        read
        return 1
    fi
    echo "✅ Port $port is available"

    # Determine what auto-detect would use (for display in prompt)
    if [ -f "/etc/hostname" ] && grep -q "droplet\|server\|prod\|ubuntu\|digital" /etc/hostname 2>/dev/null; then
        # Production environment
        default_domain="${client_name}.quantabase.io"
    # Check for other production indicators
    elif [ -d "/etc/nginx/sites-available" ] && [ -f "/etc/nginx/sites-available/quantabase" ]; then
        # Has nginx and quantabase config = production server
        default_domain="${client_name}.quantabase.io"
    # Check for cloud provider metadata
    elif curl -s --max-time 2 http://169.254.169.254/metadata/v1/ >/dev/null 2>&1; then
        # Digital Ocean metadata service available = cloud server
        default_domain="${client_name}.quantabase.io"
    else
        # Development environment
        default_domain="localhost:${port}"
    fi

    # Get domain (optional - auto-detect if empty)
    echo -n "Enter domain (press Enter for '${default_domain}'): "
    read domain

    # Resolve domain for display
    if [[ -z "$domain" ]]; then
        # Use the default we calculated above
        resolved_domain="$default_domain"
        domain="auto-detect"

        # Set redirect URI and environment based on domain type
        if [[ "$resolved_domain" == localhost* ]] || [[ "$resolved_domain" == 127.0.0.1* ]]; then
            redirect_uri="http://127.0.0.1:${port}/oauth/google/callback"
            environment="development"
        else
            redirect_uri="https://${resolved_domain}/oauth/google/callback"
            environment="production"
        fi
    else
        resolved_domain="$domain"
        if [[ "$domain" == localhost* ]] || [[ "$domain" == 127.0.0.1* ]]; then
            redirect_uri="http://${domain}/oauth/google/callback"
            environment="development"
        else
            redirect_uri="https://${domain}/oauth/google/callback"
            environment="production"
        fi
    fi

    # Show configuration summary
    echo
    echo "╔════════════════════════════════════════╗"
    echo "║         Deployment Summary             ║"
    echo "╚════════════════════════════════════════╝"
    echo "Client Name:   $client_name"
    echo "Container:     openwebui-$client_name"
    echo "Port:          $port"
    echo "Domain:        $resolved_domain"
    echo "Environment:   $environment"
    echo "Redirect URI:  $redirect_uri"
    echo "Volume:        openwebui-${client_name}-data"
    echo
    echo -n "Create this deployment? (y/N): "
    read confirm

    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        echo
        echo "Creating deployment..."

        # Create the deployment using the template script
        if [ "$domain" = "auto-detect" ]; then
            "${SCRIPT_DIR}/start-template.sh" "$client_name" "$port"
        else
            "${SCRIPT_DIR}/start-template.sh" "$client_name" "$port" "$domain"
        fi

        if [ $? -eq 0 ]; then
            echo "✅ Deployment created successfully!"
            echo
            echo "Next steps:"
            echo "1. Add nginx configuration for domain: $resolved_domain"
            echo "2. Update Google OAuth redirect URI: $redirect_uri"
            echo "3. Configure DNS for: $resolved_domain"
            echo
            echo "Access at: http://localhost:$port"
        else
            echo "❌ Failed to create deployment"
        fi
    else
        echo "Deployment cancelled."
    fi

    echo
    echo "Press Enter to continue..."
    read
}

# Sync-node management menu
manage_sync_node() {
    local client_name="$1"
    local container_name="openwebui-${client_name}"

    # Determine API port based on node (a=9443, b=9444)
    local api_port
    if [[ "$client_name" == "sync-node-a" ]]; then
        api_port=9443
    else
        api_port=9444
    fi

    while true; do
        clear
        echo "╔════════════════════════════════════════╗"
        # Calculate padding for client name to align properly
        local title="   Managing Sync Node: $client_name"
        local padding=$((38 - ${#title}))
        printf "║%s%*s║\n" "$title" $padding ""
        echo "╚════════════════════════════════════════╝"
        echo

        # Show status
        local status=$(docker ps -a --filter "name=$container_name" --format "{{.Status}}")
        local ports=$(docker ps -a --filter "name=$container_name" --format "{{.Ports}}")

        echo "Status:   $status"
        echo "Ports:    $ports"
        echo "API Port: $api_port"
        echo

        echo "1) View Cluster Status"
        echo "2) View Health Check"
        echo "3) View Container Logs (last 50 lines)"
        echo "4) View Live Logs (follow mode)"
        echo "5) Restart Sync Node"
        echo "6) Stop Sync Node"
        echo "7) Update Sync Node (instructions)"
        echo "8) Return to Deployment List"
        echo
        echo -n "Select action (1-8): "
        read action

        case "$action" in
            1)
                # View Cluster Status
                clear
                echo "╔════════════════════════════════════════╗"
                echo "║          Cluster Status                ║"
                echo "╚════════════════════════════════════════╝"
                echo
                echo "Fetching cluster status from http://localhost:${api_port}/api/v1/cluster/status..."
                echo

                if curl -s -f "http://localhost:${api_port}/api/v1/cluster/status" > /tmp/cluster_status.json 2>/dev/null; then
                    # Pretty print the JSON
                    if command -v jq &> /dev/null; then
                        cat /tmp/cluster_status.json | jq '.'
                    else
                        cat /tmp/cluster_status.json
                        echo
                        echo "(Install 'jq' for formatted output)"
                    fi
                    rm -f /tmp/cluster_status.json
                else
                    echo "❌ Failed to fetch cluster status"
                    echo "Possible reasons:"
                    echo "  - Sync node is not running"
                    echo "  - API port $api_port is not accessible"
                    echo "  - Network connectivity issues"
                fi
                echo
                echo "Press Enter to continue..."
                read
                ;;
            2)
                # View Health Check
                clear
                echo "╔════════════════════════════════════════╗"
                echo "║           Health Check                 ║"
                echo "╚════════════════════════════════════════╝"
                echo
                echo "Fetching health status from http://localhost:${api_port}/health..."
                echo

                if curl -s -f "http://localhost:${api_port}/health" > /tmp/health_check.json 2>/dev/null; then
                    # Pretty print the JSON
                    if command -v jq &> /dev/null; then
                        cat /tmp/health_check.json | jq '.'
                    else
                        cat /tmp/health_check.json
                        echo
                        echo "(Install 'jq' for formatted output)"
                    fi
                    rm -f /tmp/health_check.json
                else
                    echo "❌ Failed to fetch health status"
                    echo "Possible reasons:"
                    echo "  - Sync node is not running"
                    echo "  - API port $api_port is not accessible"
                fi
                echo
                echo "Press Enter to continue..."
                read
                ;;
            3)
                # View Container Logs (last 50 lines)
                clear
                echo "╔════════════════════════════════════════╗"
                echo "║      Container Logs (last 50 lines)    ║"
                echo "╚════════════════════════════════════════╝"
                echo
                docker logs --tail 50 "$container_name"
                echo
                echo "Press Enter to continue..."
                read
                ;;
            4)
                # View Live Logs
                echo
                echo "Starting live log stream for $container_name..."
                echo "(Press Ctrl+C to exit)"
                echo
                sleep 2
                docker logs -f "$container_name"
                ;;
            5)
                # Restart Sync Node
                clear
                echo "╔════════════════════════════════════════╗"
                echo "║         Restart Sync Node              ║"
                echo "╚════════════════════════════════════════╝"
                echo
                echo "⚠️  WARNING: Restarting sync node will temporarily affect sync operations"
                echo
                echo "This sync node will:"
                echo "  - Stop processing sync jobs"
                echo "  - Lose leader status (if it's the current leader)"
                echo "  - Rejoin the cluster and participate in leader election after restart"
                echo
                echo "The other sync node will continue serving requests during the restart."
                echo
                echo -n "Continue with restart? (y/N): "
                read confirm

                if [[ "$confirm" =~ ^[Yy]$ ]]; then
                    echo
                    echo "Restarting $container_name..."
                    docker restart "$container_name"
                    echo "✅ Sync node restarted successfully"
                    echo
                    echo "Waiting 5 seconds for startup..."
                    sleep 5

                    # Check health after restart
                    if curl -s -f "http://localhost:${api_port}/health" > /dev/null 2>&1; then
                        echo "✅ Health check passed - sync node is responding"
                    else
                        echo "⚠️  Health check failed - sync node may still be starting up"
                    fi
                else
                    echo "Restart cancelled."
                fi
                echo
                echo "Press Enter to continue..."
                read
                ;;
            6)
                # Stop Sync Node
                clear
                echo "╔════════════════════════════════════════╗"
                echo "║          Stop Sync Node                ║"
                echo "╚════════════════════════════════════════╝"
                echo
                echo "⚠️  CRITICAL WARNING: Stopping this sync node will affect sync operations"
                echo
                echo "Impact:"
                echo "  - This sync node will stop processing sync jobs"
                echo "  - If this is the current leader, leadership will transfer to the other node"
                echo "  - Only one sync node will remain active"
                echo "  - Reduced high availability until both nodes are running"
                echo
                echo "Only stop this node if:"
                echo "  - You need to perform maintenance"
                echo "  - You are troubleshooting an issue"
                echo "  - The other sync node is confirmed healthy and running"
                echo
                echo -n "Type 'STOP' to confirm: "
                read confirm

                if [[ "$confirm" == "STOP" ]]; then
                    echo
                    echo "Stopping $container_name..."
                    docker stop "$container_name"
                    echo "✅ Sync node stopped"
                    echo
                    echo "To restart later, use option 5 (Restart Sync Node) or:"
                    echo "  docker start $container_name"
                else
                    echo "Stop cancelled."
                fi
                echo
                echo "Press Enter to continue..."
                read
                ;;
            7)
                # Update Sync Node
                clear
                echo "╔════════════════════════════════════════╗"
                echo "║         Update Sync Node               ║"
                echo "╚════════════════════════════════════════╝"
                echo
                echo "To update the sync node to the latest version:"
                echo
                echo "1. Navigate to the SYNC directory:"
                echo "   cd ${SCRIPT_DIR}/SYNC"
                echo
                echo "2. Run the deployment script (it will update existing nodes):"
                echo "   ./scripts/deploy-sync-cluster.sh"
                echo
                echo "3. The script will:"
                echo "   - Pull the latest Docker image"
                echo "   - Recreate sync node containers"
                echo "   - Preserve all configuration and data"
                echo "   - Maintain cluster registration in Supabase"
                echo
                echo "⚠️  NOTE: Updates should be done during maintenance windows"
                echo "to minimize disruption to sync operations."
                echo
                echo "For more details, see:"
                echo "  ${SCRIPT_DIR}/SYNC/README.md"
                echo "  ${SCRIPT_DIR}/SYNC/TECHNICAL_REFERENCE.md"
                echo
                echo "Press Enter to continue..."
                read
                ;;
            8)
                # Return to Deployment List
                return
                ;;
            *)
                echo "Invalid selection. Press Enter to continue..."
                read
                ;;
        esac
    done
}

# Sync Management submenu for client deployments
sync_management_menu() {
    local client_name="$1"
    local container_name="openwebui-${client_name}"

    while true; do
        clear
        echo "╔════════════════════════════════════════╗"
        local title="   Sync Management: $client_name"
        local padding=$((38 - ${#title}))
        printf "║%s%*s║\n" "$title" $padding ""
        echo "╚════════════════════════════════════════╝"
        echo

        echo "1) Register Client for Sync"
        echo "2) Start/Resume Sync"
        echo "3) Pause Sync"
        echo "4) Manual Sync (Full)"
        echo "5) Manual Sync (Incremental)"
        echo "6) View Sync Status"
        echo "7) View Recent Sync Jobs"
        echo "8) Deregister Client"
        echo "9) Help (View Scripts Reference)"
        echo "10) Return to Client Menu"
        echo
        echo -n "Select action (1-10): "
        read action

        case "$action" in
            1)
                # Register Client for Sync
                clear
                echo "╔════════════════════════════════════════╗"
                echo "║        Register Client for Sync        ║"
                echo "╚════════════════════════════════════════╝"
                echo
                echo "This will register '$client_name' with the sync system."
                echo
                echo "What will happen:"
                echo "  - Create Supabase schema for this client"
                echo "  - Initialize Open WebUI tables in Supabase"
                echo "  - Enable automatic syncing"
                echo
                echo -n "Continue? (y/N): "
                read confirm

                if [[ "$confirm" =~ ^[Yy]$ ]]; then
                    echo
                    "${SCRIPT_DIR}/SYNC/scripts/register-sync-client-to-supabase.sh" "$client_name" "$container_name"
                else
                    echo "Registration cancelled."
                fi
                echo
                echo "Press Enter to continue..."
                read
                ;;
            2)
                # Start/Resume Sync
                clear
                echo "╔════════════════════════════════════════╗"
                echo "║          Start/Resume Sync             ║"
                echo "╚════════════════════════════════════════╝"
                echo
                echo "This will enable automatic syncing for '$client_name'."
                echo
                echo -n "Continue? (y/N): "
                read confirm

                if [[ "$confirm" =~ ^[Yy]$ ]]; then
                    echo
                    "${SCRIPT_DIR}/SYNC/scripts/start-sync.sh" "$client_name"
                else
                    echo "Operation cancelled."
                fi
                echo
                echo "Press Enter to continue..."
                read
                ;;
            3)
                # Pause Sync
                clear
                echo "╔════════════════════════════════════════╗"
                echo "║            Pause Sync                  ║"
                echo "╚════════════════════════════════════════╝"
                echo
                echo "This will temporarily stop automatic syncing for '$client_name'."
                echo "Data and registration will be preserved."
                echo
                echo -n "Continue? (y/N): "
                read confirm

                if [[ "$confirm" =~ ^[Yy]$ ]]; then
                    echo
                    "${SCRIPT_DIR}/SYNC/scripts/pause-sync.sh" "$client_name"
                else
                    echo "Operation cancelled."
                fi
                echo
                echo "Press Enter to continue..."
                read
                ;;
            4)
                # Manual Sync (Full)
                clear
                echo "╔════════════════════════════════════════╗"
                echo "║        Manual Full Sync                ║"
                echo "╚════════════════════════════════════════╝"
                echo
                echo "This will perform a complete sync of all data from SQLite to Supabase."
                echo
                echo -n "Continue? (y/N): "
                read confirm

                if [[ "$confirm" =~ ^[Yy]$ ]]; then
                    echo
                    cd "${SCRIPT_DIR}/SYNC"
                    source .credentials
                    export DATABASE_URL="$SYNC_URL"
                    ./scripts/sync-client-to-supabase.sh "$client_name" "manual-console" --full
                else
                    echo "Operation cancelled."
                fi
                echo
                echo "Press Enter to continue..."
                read
                ;;
            5)
                # Manual Sync (Incremental)
                clear
                echo "╔════════════════════════════════════════╗"
                echo "║      Manual Incremental Sync           ║"
                echo "╚════════════════════════════════════════╝"
                echo
                echo "This will sync only recent changes from SQLite to Supabase."
                echo
                echo -n "Continue? (y/N): "
                read confirm

                if [[ "$confirm" =~ ^[Yy]$ ]]; then
                    echo
                    cd "${SCRIPT_DIR}/SYNC"
                    source .credentials
                    export DATABASE_URL="$SYNC_URL"
                    ./scripts/sync-client-to-supabase.sh "$client_name" "manual-console"
                else
                    echo "Operation cancelled."
                fi
                echo
                echo "Press Enter to continue..."
                read
                ;;
            6)
                # View Sync Status
                clear
                echo "╔════════════════════════════════════════╗"
                echo "║           Sync Status                  ║"
                echo "╚════════════════════════════════════════╝"
                echo

                docker exec -i openwebui-sync-node-a python3 << EOF
import asyncpg, asyncio, os, sys

async def check_status():
    try:
        conn = await asyncpg.connect(os.getenv('ADMIN_URL'))
        row = await conn.fetchrow('''
            SELECT sync_enabled, status, sync_interval, last_sync_at, last_sync_status
            FROM sync_metadata.client_deployments
            WHERE client_name = \$1
        ''', '$client_name')

        if row:
            print(f"Client: $client_name")
            print(f"  Sync Enabled: {row['sync_enabled']}")
            print(f"  Status: {row['status']}")
            print(f"  Interval: {row['sync_interval']}s")
            print(f"  Last Sync: {row['last_sync_at']}")
            print(f"  Last Status: {row['last_sync_status']}")
        else:
            print(f"❌ Client '$client_name' not found in sync system")
            print(f"   Use option 1 to register this client for sync")

        await conn.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

asyncio.run(check_status())
EOF
                echo
                echo "Press Enter to continue..."
                read
                ;;
            7)
                # View Recent Sync Jobs
                clear
                echo "╔════════════════════════════════════════╗"
                echo "║        Recent Sync Jobs                ║"
                echo "╚════════════════════════════════════════╝"
                echo

                docker exec -i openwebui-sync-node-a python3 << 'EOF'
import asyncpg, asyncio, os, sys

async def show_jobs():
    try:
        conn = await asyncpg.connect(os.getenv('ADMIN_URL'))
        rows = await conn.fetch('''
            SELECT job_id, started_at, status, sync_type, triggered_by,
                   rows_synced, duration_seconds
            FROM sync_metadata.sync_jobs
            WHERE client_name = $1
            ORDER BY started_at DESC
            LIMIT 10
        ''', '$client_name')

        if rows:
            print(f"{'Started':<20} {'Status':<10} {'Type':<6} {'By':<15} {'Rows':<8} {'Duration':<8}")
            print("-" * 85)

            for row in rows:
                duration = f"{row['duration_seconds']:.1f}s" if row['duration_seconds'] else "-"
                rows_synced = row['rows_synced'] or 0
                print(f"{str(row['started_at']):<20} {row['status']:<10} {row['sync_type']:<6} "
                      f"{row['triggered_by']:<15} {rows_synced:<8} {duration:<8}")
        else:
            print(f"No sync jobs found for client: $client_name")

        await conn.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

asyncio.run(show_jobs())
EOF
                echo
                echo "Press Enter to continue..."
                read
                ;;
            8)
                # Deregister Client
                clear
                echo "╔════════════════════════════════════════╗"
                echo "║         Deregister Client              ║"
                echo "╚════════════════════════════════════════╝"
                echo
                echo "⚠️  WARNING: This will remove '$client_name' from the sync system"
                echo
                echo "Choose removal option:"
                echo "  1) Keep Supabase data (remove from sync only)"
                echo "  2) DELETE all Supabase data (cannot be undone)"
                echo "  3) Cancel"
                echo
                echo -n "Select option (1-3): "
                read deregister_option

                case "$deregister_option" in
                    1)
                        echo
                        echo "Deregistering client (keeping data)..."
                        "${SCRIPT_DIR}/SYNC/scripts/deregister-client.sh" "$client_name"
                        ;;
                    2)
                        echo
                        echo "⚠️  CRITICAL WARNING: This will DELETE ALL DATA for '$client_name' in Supabase!"
                        echo -n "Type 'DELETE' to confirm: "
                        read confirm
                        if [[ "$confirm" == "DELETE" ]]; then
                            "${SCRIPT_DIR}/SYNC/scripts/deregister-client.sh" "$client_name" --drop-schema
                        else
                            echo "Deletion cancelled."
                        fi
                        ;;
                    3)
                        echo "Deregistration cancelled."
                        ;;
                    *)
                        echo "Invalid selection."
                        ;;
                esac
                echo
                echo "Press Enter to continue..."
                read
                ;;
            9)
                # Help - Display SCRIPTS_REFERENCE.md
                clear
                if [ -f "${SCRIPT_DIR}/SYNC/SCRIPTS_REFERENCE.md" ]; then
                    less "${SCRIPT_DIR}/SYNC/SCRIPTS_REFERENCE.md"
                else
                    echo "❌ Scripts reference file not found:"
                    echo "   ${SCRIPT_DIR}/SYNC/SCRIPTS_REFERENCE.md"
                    echo
                    echo "Press Enter to continue..."
                    read
                fi
                ;;
            10)
                # Return to Client Menu
                return
                ;;
            *)
                echo "Invalid selection. Press Enter to continue..."
                read
                ;;
        esac
    done
}

manage_deployment_menu() {
    while true; do
        clear
        echo "╔════════════════════════════════════════╗"
        echo "║        Manage Deployment Menu          ║"
        echo "╚════════════════════════════════════════╝"
        echo

        # List available clients
        echo "Available deployments:"
        clients=($(docker ps -a --filter "name=openwebui-" --format "{{.Names}}" | sed 's/openwebui-//'))

        if [ ${#clients[@]} -eq 0 ]; then
            echo "No deployments found."
            echo
            echo "Press Enter to return to main menu..."
            read
            return
        fi

        for i in "${!clients[@]}"; do
            status=$(docker ps -a --filter "name=openwebui-${clients[$i]}" --format "{{.Status}}")
            container_type=$(detect_container_type "${clients[$i]}")

            # Try to get the redirect URI from container environment to extract domain
            redirect_uri=$(docker exec "openwebui-${clients[$i]}" env 2>/dev/null | grep "GOOGLE_REDIRECT_URI=" | cut -d'=' -f2- 2>/dev/null || echo "")

            if [[ "$container_type" == "sync-node" ]]; then
                # Sync node - show with [SYNC NODE] indicator
                echo "$((i+1))) ${clients[$i]} [SYNC NODE] ($status)"
            elif [[ -n "$redirect_uri" ]]; then
                # Extract domain from redirect URI (remove http/https and /oauth/google/callback)
                domain=$(echo "$redirect_uri" | sed -E 's|https?://||' | sed 's|/oauth/google/callback||')
                echo "$((i+1))) ${clients[$i]} [CLIENT] → $domain ($status)"
            else
                # Fallback if we can't get the redirect URI
                echo "$((i+1))) ${clients[$i]} [CLIENT] ($status)"
            fi
        done

        echo "$((${#clients[@]}+1))) Return to main menu"
        echo
        echo -n "Select deployment to manage (1-$((${#clients[@]}+1))): "
        read selection

        if [[ "$selection" =~ ^[0-9]+$ ]] && [ "$selection" -gt 0 ] && [ "$selection" -le ${#clients[@]} ]; then
            manage_single_deployment "${clients[$((selection-1))]}"
        elif [[ "$selection" =~ ^[0-9]+$ ]] && [ "$selection" -eq $((${#clients[@]}+1)) ]; then
            return
        else
            echo "Invalid selection. Press Enter to continue..."
            read
        fi
    done
}

manage_single_deployment() {
    local client_name="$1"
    local container_name="openwebui-${client_name}"

    # Detect container type and route to appropriate menu
    local container_type=$(detect_container_type "$client_name")

    if [[ "$container_type" == "sync-node" ]]; then
        # Route to sync-node management menu
        manage_sync_node "$client_name"
        return
    fi

    # Continue with client deployment menu for non-sync-node containers
    # Color codes for output
    local RED='\033[0;31m'
    local GREEN='\033[0;32m'
    local YELLOW='\033[1;33m'
    local NC='\033[0m'

    while true; do
        clear
        echo "╔════════════════════════════════════════╗"
        # Calculate padding for client name to align properly
        local title="     Managing: $client_name"
        local padding=$((38 - ${#title}))
        printf "║%s%*s║\n" "$title" $padding ""
        echo "╚════════════════════════════════════════╝"
        echo

        # Show status
        local status=$(docker ps -a --filter "name=$container_name" --format "{{.Status}}")
        local ports=$(docker ps -a --filter "name=$container_name" --format "{{.Ports}}")

        # Get FQDN from redirect URI
        local redirect_uri=$(docker exec "$container_name" env 2>/dev/null | grep "GOOGLE_REDIRECT_URI=" | cut -d'=' -f2- 2>/dev/null || echo "")
        local fqdn=""
        if [[ -n "$redirect_uri" ]]; then
            fqdn=$(echo "$redirect_uri" | sed -E 's|https?://||' | sed 's|/oauth/google/callback||')
        fi

        echo "Status: $status"
        echo "Ports:  $ports"
        if [[ -n "$fqdn" ]]; then
            echo "Domain: $fqdn"
        fi

        # Detect and display database configuration
        local database_url=$(docker exec "$container_name" env 2>/dev/null | grep "DATABASE_URL=" | cut -d'=' -f2- 2>/dev/null || echo "")

        if [[ -n "$database_url" ]]; then
            # PostgreSQL detected
            local db_host=$(echo "$database_url" | sed 's|postgresql://[^@]*@||' | cut -d':' -f1)
            local db_port=$(echo "$database_url" | sed 's|.*:||' | cut -d'/' -f1)
            local db_name=$(echo "$database_url" | sed 's|.*/||')
            echo "Database: PostgreSQL"
            echo "  Host: $db_host:$db_port"
            echo "  Name: $db_name"
        else
            # SQLite (default)
            echo "Database: SQLite (default)"
        fi

        echo

        echo "1) Start deployment"
        echo "2) Stop deployment"
        echo "3) Restart deployment"
        echo "4) View logs"
        echo "5) Show Cloudflare DNS configuration"
        echo "6) Update OAuth allowed domains"
        echo "7) Change domain/client (preserve data)"
        echo "8) Sync Management"

        # Show database option based on current database type
        if [[ -n "$database_url" ]]; then
            echo "9) View database configuration (includes rollback)"
        else
            echo "9) Migrate to Supabase/PostgreSQL"
        fi

        echo "10) Remove deployment (DANGER)"
        echo "11) Return to deployment list"
        echo
        echo -n "Select action (1-11): "
        read action

        case "$action" in
            1)
                echo "Starting $container_name..."
                docker start "$container_name"
                echo "Press Enter to continue..."
                read
                ;;
            2)
                echo "Stopping $container_name..."
                docker stop "$container_name"
                echo "Press Enter to continue..."
                read
                ;;
            3)
                echo "Restarting $container_name..."
                docker restart "$container_name"
                echo "Press Enter to continue..."
                read
                ;;
            4)
                echo "Showing logs for $container_name (Ctrl+C to exit)..."
                echo "Press Enter to continue..."
                read
                docker logs -f "$container_name"
                ;;
            5)
                # Show Cloudflare configuration
                # Get domain from container environment
                redirect_uri=$(docker exec "$container_name" env 2>/dev/null | grep "GOOGLE_REDIRECT_URI=" | cut -d'=' -f2- 2>/dev/null || echo "")
                if [[ -n "$redirect_uri" ]]; then
                    domain=$(echo "$redirect_uri" | sed -E 's|https?://||' | sed 's|/oauth/google/callback||')
                    subdomain=$(echo "$domain" | cut -d'.' -f1)
                    base_domain=$(echo "$domain" | cut -d'.' -f2-)
                    server_ip=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_SERVER_IP")

                    echo
                    echo "╔════════════════════════════════════════╗"
                    echo "║      Cloudflare DNS Configuration      ║"
                    echo "╚════════════════════════════════════════╝"
                    echo
                    echo "Domain: $domain"
                    echo "Server IP: $server_ip"
                    echo
                    echo "1. Go to Cloudflare Dashboard"
                    echo "   → Select domain: $base_domain"
                    echo "   → Go to DNS → Records"
                    echo
                    echo "2. Create DNS Record:"
                    echo "   Type: A"
                    echo "   Name: $subdomain"
                    echo "   IPv4 address: $server_ip"
                    echo "   Proxy status: Proxied (orange cloud) ✓"
                    echo
                    echo "3. SSL/TLS Configuration:"
                    echo "   → Go to SSL/TLS → Overview"
                    echo "   → Set encryption mode: Full (strict)"
                    echo
                    echo "4. Wait for DNS propagation (1-5 minutes)"
                    echo "   Test with: nslookup $domain"
                    echo
                else
                    echo "❌ Could not determine domain for this deployment"
                fi
                echo "Press Enter to continue..."
                read
                ;;
            6)
                # Update OAuth allowed domains
                echo
                echo "╔════════════════════════════════════════╗"
                echo "║       Update OAuth Allowed Domains     ║"
                echo "╚════════════════════════════════════════╝"
                echo

                # Get current domains from container
                current_domains=$(docker exec "$container_name" env 2>/dev/null | grep "OAUTH_ALLOWED_DOMAINS=" | cut -d'=' -f2- 2>/dev/null || echo "")
                if [[ -n "$current_domains" ]]; then
                    echo "Current allowed domains: $current_domains"
                else
                    echo "Current allowed domains: Not set"
                fi
                echo

                echo "Enter new allowed domains (comma-separated, e.g., martins.net,example.com):"
                echo -n "New domains: "
                read new_domains

                if [[ -z "$new_domains" ]]; then
                    echo "❌ No domains provided. Operation cancelled."
                    echo "Press Enter to continue..."
                    read
                    continue
                fi

                echo
                echo "⚠️  This will recreate the container with new domain settings."
                echo "All data will be preserved (volumes are maintained)."
                echo "New allowed domains: $new_domains"
                echo
                echo -n "Continue? (y/N): "
                read confirm

                if [[ "$confirm" =~ ^[Yy]$ ]]; then
                    echo
                    echo "Updating allowed domains..."

                    # Get current container configuration BEFORE stopping
                    port=$(docker ps -a --filter "name=$container_name" --format "{{.Ports}}" | grep -o '0.0.0.0:[0-9]*' | cut -d: -f2)
                    redirect_uri=$(docker exec "$container_name" env 2>/dev/null | grep "GOOGLE_REDIRECT_URI=" | cut -d'=' -f2- 2>/dev/null || echo "")
                    webui_name=$(docker exec "$container_name" env 2>/dev/null | grep "WEBUI_NAME=" | cut -d'=' -f2- 2>/dev/null || echo "QuantaBase - $client_name")

                    if [[ -z "$port" ]] || [[ -z "$redirect_uri" ]]; then
                        echo "❌ Could not retrieve container configuration. Please recreate manually."
                        echo "Press Enter to continue..."
                        read
                        continue
                    fi

                    echo "Current configuration:"
                    echo "  Port: $port"
                    echo "  Redirect URI: $redirect_uri"
                    echo "  WebUI Name: $webui_name"
                    echo

                    # Verify port is available before proceeding
                    echo "Checking port availability..."
                    if netstat -ln 2>/dev/null | grep -q ":${port} " && ! docker ps --format "{{.Ports}}" | grep -q ":${port}->"; then
                        echo "❌ Port $port is in use by another process. Cannot safely recreate container."
                        echo "Please resolve port conflict manually."
                        echo "Press Enter to continue..."
                        read
                        continue
                    fi

                    # Stop and remove old container (preserve volume)
                    echo "Stopping container..."
                    docker stop "$container_name" 2>/dev/null
                    echo "Removing old container..."
                    docker rm "$container_name" 2>/dev/null

                    # Double-check port is still available after container removal
                    if netstat -ln 2>/dev/null | grep -q ":${port} "; then
                        echo "❌ Port $port is still in use after container removal. Aborting recreation."
                        echo "Press Enter to continue..."
                        read
                        continue
                    fi

                    # Recreate container with new domains
                    echo "Creating new container with updated domains..."
                    volume_name="openwebui-${client_name}-data"

                    docker run -d \
                        --name "$container_name" \
                        -p "${port}:8080" \
                        -e GOOGLE_CLIENT_ID=1063776054060-2fa0vn14b7ahi1tmfk49cuio44goosc1.apps.googleusercontent.com \
                        -e GOOGLE_CLIENT_SECRET=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 \
                        -e GOOGLE_REDIRECT_URI="$redirect_uri" \
                        -e ENABLE_OAUTH_SIGNUP=true \
                        -e OAUTH_ALLOWED_DOMAINS="$new_domains" \
                        -e OPENID_PROVIDER_URL=https://accounts.google.com/.well-known/openid-configuration \
                        -e WEBUI_NAME="$webui_name" \
                        -e USER_PERMISSIONS_CHAT_CONTROLS=false \
                        -v "${volume_name}:/app/backend/data" \
                        --restart unless-stopped \
                        ghcr.io/imagicrafter/open-webui:main

                    if [ $? -eq 0 ]; then
                        echo "✅ Container recreated successfully with new allowed domains!"
                        echo "New allowed domains: $new_domains"
                    else
                        echo "❌ Failed to recreate container. Check Docker logs."
                    fi
                else
                    echo "Operation cancelled."
                fi

                echo "Press Enter to continue..."
                read
                ;;
            7)
                # Change domain/client while preserving data
                echo
                echo "╔════════════════════════════════════════╗"
                echo "║  Change Domain/Client (Preserve Data)  ║"
                echo "╚════════════════════════════════════════╝"
                echo

                # Get current configuration
                current_redirect_uri=$(docker exec "$container_name" env 2>/dev/null | grep "GOOGLE_REDIRECT_URI=" | cut -d'=' -f2- 2>/dev/null || echo "")
                current_webui_name=$(docker exec "$container_name" env 2>/dev/null | grep "WEBUI_NAME=" | cut -d'=' -f2- 2>/dev/null || echo "")
                current_port=$(docker ps -a --filter "name=$container_name" --format "{{.Ports}}" | grep -o '0.0.0.0:[0-9]*' | cut -d: -f2)

                if [[ -n "$current_redirect_uri" ]]; then
                    current_domain=$(echo "$current_redirect_uri" | sed -E 's|https?://||' | sed 's|/oauth/google/callback||')
                    echo "Current domain: $current_domain"
                else
                    echo "Current domain: Unable to determine"
                fi
                echo "Current port: $current_port"
                echo "Current WebUI name: $current_webui_name"
                echo

                # Get new client name
                echo -n "Enter new client name (lowercase, no spaces): "
                read new_client_name

                if [[ ! "$new_client_name" =~ ^[a-z0-9-]+$ ]]; then
                    echo "❌ Invalid client name. Use only lowercase letters, numbers, and hyphens."
                    echo "Press Enter to continue..."
                    read
                    continue
                fi

                # Check if new client name conflicts with existing deployments
                if docker ps -a --filter "name=openwebui-${new_client_name}" --format "{{.Names}}" | grep -q "openwebui-${new_client_name}"; then
                    echo "❌ Client '${new_client_name}' already exists!"
                    echo "Press Enter to continue..."
                    read
                    continue
                fi

                # Get new domain
                default_domain="${new_client_name}.quantabase.io"
                echo -n "Enter new domain (press Enter for '${default_domain}'): "
                read new_domain

                if [[ -z "$new_domain" ]]; then
                    new_domain="$default_domain"
                fi

                # Set new redirect URI based on domain type
                if [[ "$new_domain" == localhost* ]] || [[ "$new_domain" == 127.0.0.1* ]]; then
                    new_redirect_uri="http://${new_domain}/oauth/google/callback"
                    environment="development"
                else
                    new_redirect_uri="https://${new_domain}/oauth/google/callback"
                    environment="production"
                fi

                new_webui_name="QuantaBase - ${new_client_name}"

                echo
                echo "╔════════════════════════════════════════╗"
                echo "║            Change Summary              ║"
                echo "╚════════════════════════════════════════╝"
                echo "Old client: $client_name"
                echo "New client: $new_client_name"
                echo "Old domain: $current_domain"
                echo "New domain: $new_domain"
                echo "New redirect URI: $new_redirect_uri"
                echo "New WebUI name: $new_webui_name"
                echo "Port: $current_port (unchanged)"
                echo
                echo "⚠️  IMPORTANT: After this change you will need to:"
                echo "   1. Update nginx configuration for the new domain"
                echo "   2. Update Google OAuth redirect URI"
                echo "   3. Configure DNS for the new domain"
                echo
                echo "⚠️  This will:"
                echo "   - Rename the container to: openwebui-${new_client_name}"
                echo "   - Rename the volume to: openwebui-${new_client_name}-data"
                echo "   - Preserve ALL chat data and settings"
                echo "   - Remove old nginx configs (you'll need to recreate)"
                echo
                echo -n "Continue with domain/client change? (y/N): "
                read confirm

                if [[ "$confirm" =~ ^[Yy]$ ]]; then
                    echo
                    echo "Changing domain/client..."

                    # Get current allowed domains
                    current_allowed_domains=$(docker exec "$container_name" env 2>/dev/null | grep "OAUTH_ALLOWED_DOMAINS=" | cut -d'=' -f2- 2>/dev/null || echo "martins.net")

                    # Stop and remove old container
                    echo "Stopping old container..."
                    docker stop "$container_name" 2>/dev/null
                    echo "Removing old container..."
                    docker rm "$container_name" 2>/dev/null

                    # Rename volume to new client name
                    old_volume_name="openwebui-${client_name}-data"
                    new_volume_name="openwebui-${new_client_name}-data"
                    new_container_name="openwebui-${new_client_name}"

                    echo "Renaming data volume..."
                    # Create temporary container to rename volume
                    docker run --rm -v "${old_volume_name}:/old_data" -v "${new_volume_name}:/new_data" alpine sh -c "cp -a /old_data/. /new_data/" 2>/dev/null
                    if [ $? -eq 0 ]; then
                        echo "✅ Data volume copied successfully"
                        # Remove old volume after successful copy
                        docker volume rm "${old_volume_name}" 2>/dev/null || echo "Note: Old volume cleanup may require manual removal"
                    else
                        echo "❌ Volume copy failed. Creating new container with original volume name..."
                        new_volume_name="$old_volume_name"
                    fi

                    # Create new container with new name and domain
                    echo "Creating new container: $new_container_name"
                    docker run -d \
                        --name "$new_container_name" \
                        -p "${current_port}:8080" \
                        -e GOOGLE_CLIENT_ID=1063776054060-2fa0vn14b7ahi1tmfk49cuio44goosc1.apps.googleusercontent.com \
                        -e GOOGLE_CLIENT_SECRET=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 \
                        -e GOOGLE_REDIRECT_URI="$new_redirect_uri" \
                        -e ENABLE_OAUTH_SIGNUP=true \
                        -e OAUTH_ALLOWED_DOMAINS="$current_allowed_domains" \
                        -e OPENID_PROVIDER_URL=https://accounts.google.com/.well-known/openid-configuration \
                        -e WEBUI_NAME="$new_webui_name" \
                        -e USER_PERMISSIONS_CHAT_CONTROLS=false \
                        -v "${new_volume_name}:/app/backend/data" \
                        --restart unless-stopped \
                        ghcr.io/imagicrafter/open-webui:main

                    if [ $? -eq 0 ]; then
                        echo "✅ Container recreated successfully!"
                        echo
                        echo "╔════════════════════════════════════════╗"
                        echo "║             Next Steps                 ║"
                        echo "╚════════════════════════════════════════╝"
                        echo "1. Generate new nginx config:"
                        echo "   Use option 4 (Generate nginx Configuration)"
                        echo
                        echo "2. Update Google OAuth Console:"
                        echo "   New redirect URI: $new_redirect_uri"
                        echo
                        echo "3. Configure DNS:"
                        echo "   Point $new_domain to this server"
                        echo
                        echo "4. Remove old nginx config if it exists:"
                        echo "   sudo rm /etc/nginx/sites-enabled/$current_domain"
                        echo "   sudo rm /etc/nginx/sites-available/$current_domain"
                        echo
                        echo "The deployment is now accessible as '$new_client_name' in the menu."
                        echo "All your chat data and settings have been preserved!"

                        # Since we changed the client name, we need to exit this menu
                        # as the container name has changed
                        echo
                        echo "Press Enter to return to main menu..."
                        read
                        return
                    else
                        echo "❌ Failed to create new container. Check Docker logs."
                    fi
                else
                    echo "Domain/client change cancelled."
                fi

                echo "Press Enter to continue..."
                read
                ;;
            8)
                # Sync Management
                sync_management_menu "$client_name"
                ;;
            9)
                # Database Migration / Configuration Viewer
                if [[ -n "$database_url" ]]; then
                    # PostgreSQL - Show configuration
                    clear
                    source "${SCRIPT_DIR}/DB_MIGRATION/db-migration-helper.sh"
                    display_postgres_config "$container_name"
                else
                    # SQLite - Offer migration
                    clear
                    echo "╔════════════════════════════════════════╗"
                    echo "║     Migrate to Supabase/PostgreSQL     ║"
                    echo "╚════════════════════════════════════════╝"
                    echo
                    echo "⚠️  WARNING: Database migration is a critical operation"
                    echo
                    echo "What will happen:"
                    echo "  1. Backup your current SQLite database"
                    echo "  2. Initialize PostgreSQL schema on Supabase"
                    echo "  3. Migrate all data to PostgreSQL"
                    echo "  4. Recreate container with PostgreSQL configuration"
                    echo
                    echo "Requirements:"
                    echo "  - Supabase account and project set up"
                    echo "  - pgvector extension enabled (recommended)"
                    echo "  - Stable internet connection"
                    echo
                    echo "Estimated time: 15-30 minutes"
                    echo "The service will be temporarily unavailable during migration"
                    echo
                    echo -n "Continue with migration? (y/N): "
                    read confirm

                    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
                        echo "Migration cancelled."
                        echo "Press Enter to continue..."
                        read
                        continue
                    fi

                    # Source the helper script
                    source "${SCRIPT_DIR}/DB_MIGRATION/db-migration-helper.sh"

                    # Step 1: Get Supabase configuration
                    clear
                    if ! get_supabase_config; then
                        echo
                        echo "❌ Failed to configure Supabase connection"
                        echo "Press Enter to continue..."
                        read
                        continue
                    fi

                    # Step 2: Test connection
                    clear
                    if ! test_supabase_connection "$DATABASE_URL"; then
                        echo
                        echo "❌ Cannot connect to Supabase. Please check your credentials."
                        echo "Press Enter to continue..."
                        read
                        continue
                    fi

                    # Step 3: Check pgvector extension
                    clear
                    if ! check_pgvector_extension "$DATABASE_URL"; then
                        echo "Migration cancelled."
                        echo "Press Enter to continue..."
                        read
                        continue
                    fi

                    # Step 4: Backup SQLite database
                    clear
                    # Use FQDN for backup naming, fall back to client_name if not available
                    local backup_identifier="${fqdn:-$client_name}"
                    backup_path=$(backup_sqlite_database "$container_name" "$backup_identifier")

                    if [[ -z "$backup_path" ]]; then
                        echo
                        echo "❌ Failed to create backup. Migration aborted."
                        echo "Press Enter to continue..."
                        read
                        continue
                    fi

                    # Step 5: Get port for initialization
                    current_port=$(echo "$ports" | grep -o '0.0.0.0:[0-9]*' | head -1 | cut -d: -f2)
                    if [[ -z "$current_port" ]]; then
                        current_port=8080
                    fi

                    # Step 6: Initialize PostgreSQL schema
                    clear
                    if ! initialize_postgresql_schema "$container_name" "$DATABASE_URL" "$current_port"; then
                        echo
                        echo "❌ Failed to initialize PostgreSQL schema. Migration aborted."
                        echo "Press Enter to continue..."
                        read
                        continue
                    fi

                    # Step 7: Run migration tool
                    clear
                    echo "╔════════════════════════════════════════╗"
                    echo "║        Running Migration Tool          ║"
                    echo "╚════════════════════════════════════════╝"
                    echo
                    echo "The migration tool will now run interactively."
                    echo "When prompted for the SQLite database path, enter:"
                    echo "  $backup_path"
                    echo
                    echo "Press Enter to start migration..."
                    read

                    # Use FQDN for log file naming, fall back to client_name if not available
                    local migration_identifier="${fqdn:-$client_name}"

                    if ! run_migration_tool "$backup_path" "$DATABASE_URL" "$migration_identifier"; then
                        echo
                        echo "❌ Migration failed. Starting rollback..."
                        rollback_to_sqlite "$client_name" "$backup_path" "$current_port"
                        echo
                        echo "Press Enter to continue..."
                        read
                        continue
                    fi

                    # Step 8: Fix null byte issue
                    clear
                    fix_null_bytes "$DATABASE_URL"

                    # Step 9: Recreate container with PostgreSQL
                    clear
                    if ! recreate_container_with_postgres "$client_name" "$DATABASE_URL" "$current_port"; then
                        echo
                        echo "❌ Failed to recreate container. Starting rollback..."
                        rollback_to_sqlite "$client_name" "$backup_path" "$current_port"
                        echo
                        echo "Press Enter to continue..."
                        read
                        continue
                    fi

                    # Step 10: Success message
                    clear
                    echo "╔════════════════════════════════════════╗"
                    echo "║     Migration Completed Successfully!  ║"
                    echo "╚════════════════════════════════════════╝"
                    echo
                    echo "✅ Your deployment is now using PostgreSQL/Supabase"
                    echo
                    echo "Next steps:"
                    echo "  1. Test web access: http://localhost:$current_port"
                    echo "  2. Verify chat history and user data"
                    echo "  3. Monitor container logs for any errors"
                    echo "  4. SQLite backup saved at: $backup_path"
                    echo "  5. Keep backup for 2-4 weeks before deleting"
                    echo
                    echo "If you encounter any issues, you can rollback to SQLite"
                    echo "by using option 8 again and selecting rollback."
                fi

                echo
                echo "Press Enter to continue..."
                read
                ;;
            10)
                # Remove deployment
                echo "⚠️  WARNING: This will permanently remove the deployment!"
                echo "Data volume will be preserved but container will be deleted."
                echo -n "Type 'DELETE' to confirm: "
                read confirm
                if [ "$confirm" = "DELETE" ]; then
                    echo "Removing $container_name..."
                    docker stop "$container_name" 2>/dev/null
                    docker rm "$container_name"
                    echo "Deployment removed. Data volume preserved."
                    echo "Press Enter to continue..."
                    read
                    return
                else
                    echo "Removal cancelled."
                    echo "Press Enter to continue..."
                    read
                fi
                ;;
            11)
                # Return to deployment list
                return
                ;;
            *)
                echo "Invalid selection. Press Enter to continue..."
                read
                ;;
        esac
    done
}

generate_nginx_config() {
    clear
    echo "╔════════════════════════════════════════╗"
    echo "║      Generate nginx Configuration      ║"
    echo "╚════════════════════════════════════════╝"
    echo

    # List available clients
    echo "Available deployments:"
    clients=($(docker ps -a --filter "name=openwebui-" --format "{{.Names}}" | sed 's/openwebui-//'))

    if [ ${#clients[@]} -eq 0 ]; then
        echo "No deployments found. Create a deployment first."
        echo "Press Enter to continue..."
        read
        return
    fi

    for i in "${!clients[@]}"; do
        ports=$(docker ps -a --filter "name=openwebui-${clients[$i]}" --format "{{.Ports}}" | grep -o '0.0.0.0:[0-9]*' | cut -d: -f2)

        # Try to get the redirect URI from container environment to extract domain
        redirect_uri=$(docker exec "openwebui-${clients[$i]}" env 2>/dev/null | grep "GOOGLE_REDIRECT_URI=" | cut -d'=' -f2- 2>/dev/null || echo "")

        # Check if nginx configuration exists
        # TODO: This section currently assumes nginx is not containerized.
        # Future enhancement needed to support dockerized nginx deployments.
        nginx_status="❌ Not configured"

        # Extract domain for config filename check
        config_domain=""
        if [[ -n "$redirect_uri" ]]; then
            config_domain=$(echo "$redirect_uri" | sed -E 's|https?://||' | sed 's|/oauth/google/callback||')
        fi

        if [[ -n "$config_domain" ]] && [ -f "/etc/nginx/sites-available/${config_domain}" ]; then
            nginx_status="✅ Configured"
        elif [[ -n "$config_domain" ]] && [ -f "${SCRIPT_DIR}/nginx/sites-available/${config_domain}" ]; then
            nginx_status="🔧 Local config"
        fi

        if [[ -n "$redirect_uri" ]]; then
            # Extract domain from redirect URI
            domain=$(echo "$redirect_uri" | sed -E 's|https?://||' | sed 's|/oauth/google/callback||')
            echo "$((i+1))) ${clients[$i]} → $domain (port: $ports) [$nginx_status]"
        else
            # Fallback if we can't get the redirect URI
            echo "$((i+1))) ${clients[$i]} (port: $ports) [$nginx_status]"
        fi
    done

    echo "$((${#clients[@]}+1))) Return to main menu"
    echo
    echo -n "Select client for nginx config (1-$((${#clients[@]}+1))): "
    read selection

    if [[ "$selection" =~ ^[0-9]+$ ]] && [ "$selection" -gt 0 ] && [ "$selection" -le ${#clients[@]} ]; then
        local client_name="${clients[$((selection-1))]}"
        local port=$(docker ps -a --filter "name=openwebui-${client_name}" --format "{{.Ports}}" | grep -o '0.0.0.0:[0-9]*' | cut -d: -f2)

        echo
        echo
        echo "Select configuration type:"
        echo "1) Production (HTTPS with Let's Encrypt)"
        echo "2) Local Testing (HTTP with Docker nginx)"
        echo
        echo -n "Choose option (1-2): "
        read config_type

        case "$config_type" in
            1)
                # Auto-detect production domain
                default_production_domain="${client_name}.quantabase.io"
                echo -n "Production domain (press Enter for '${default_production_domain}'): "
                read domain
                if [[ -z "$domain" ]]; then
                    domain="$default_production_domain"
                fi
                template_file="${SCRIPT_DIR}/nginx-template.conf"
                config_file="/tmp/${domain}-nginx.conf"
                setup_type="production"
                ;;
            2)
                echo -n "Enter local domain (press Enter for 'localhost'): "
                read domain
                if [[ -z "$domain" ]]; then
                    domain="localhost"
                fi
                template_file="${SCRIPT_DIR}/nginx-template-local.conf"
                config_file="${SCRIPT_DIR}/nginx/sites-available/${domain}"
                setup_type="local"
                ;;
            *)
                echo "Invalid selection. Press Enter to continue..."
                read
                return
                ;;
        esac

        # Generate nginx config
        sed "s/{{CLIENT_NAME}}/${client_name}/g; s/{{DOMAIN}}/${domain}/g; s/{{PORT}}/${port}/g" \
            "$template_file" > "$config_file"

        echo
        echo "✅ nginx configuration generated: $config_file"
        echo

        if [ "$setup_type" = "production" ]; then
            # Auto-detect current server info
            # TODO: This section provides both local and remote deployment options.
            # Future enhancement: Auto-detect deployment context and show only relevant commands.
            current_user=$(whoami)
            current_hostname=$(hostname)

            echo "╔════════════════════════════════════════╗"
            echo "║         Production Setup Steps         ║"
            echo "╚════════════════════════════════════════╝"
            echo
            echo "1. Copy config to server:"
            echo "   # For local deployment (script running on production server):"
            echo "   sudo cp $config_file /etc/nginx/sites-available/${domain}"
            echo
            echo "   # For remote deployment (script running on local machine):"
            echo "   scp -o PreferredAuthentications=password $config_file ${current_user}@${current_hostname}:/etc/nginx/sites-available/${domain}"
            echo "   # OR with SSH keys: scp $config_file ${current_user}@${current_hostname}:/etc/nginx/sites-available/${domain}"
            echo
            echo "2. Enable the site:"
            echo "   sudo ln -s /etc/nginx/sites-available/${domain} /etc/nginx/sites-enabled/"
            echo
            echo "3. Configure DNS (Cloudflare):"
            echo "   - Create A record: ${domain} → $(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_SERVER_IP')"
            echo "   - Wait for DNS propagation (1-5 minutes)"
            echo
            echo "4. Test nginx config:"
            echo "   sudo nginx -t"
            echo
            echo "5. Generate SSL certificate:"
            echo "   sudo certbot --nginx -d ${domain}"
            echo "   (Certbot will automatically modify nginx config for HTTPS)"
            echo
            echo "6. Reload nginx configuration:"
            echo "   sudo systemctl reload nginx"
            echo
            echo "7. Update Google OAuth with redirect URI:"
            echo "   https://${domain}/oauth/google/callback"
        else
            echo "╔════════════════════════════════════════╗"
            echo "║          Local Testing Steps           ║"
            echo "╚════════════════════════════════════════╝"
            echo
            echo "1. Enable the site:"
            echo "   cp ${SCRIPT_DIR}/nginx/sites-available/${domain} ${SCRIPT_DIR}/nginx/sites-enabled/"
            echo
            echo "2. Start nginx container:"
            echo "   docker-compose -f docker-compose.nginx.yml up -d"
            echo
            echo "3. Test configuration:"
            echo "   docker exec local-nginx nginx -t"
            echo
            echo "4. Access your client:"
            echo "   http://localhost (nginx will proxy to port ${port})"
            echo
            echo "5. Update Google OAuth with redirect URI:"
            echo "   http://localhost/oauth/google/callback"
            echo
            echo "6. Stop nginx when done:"
            echo "   docker-compose -f docker-compose.nginx.yml down"
        fi
        echo

        echo "Press Enter to view the generated config..."
        read
        echo "Generated nginx configuration:"
        echo "============================="
        cat "$config_file"

    elif [ "$selection" -eq $((${#clients[@]}+1)) ]; then
        return
    else
        echo "Invalid selection. Press Enter to continue..."
        read
    fi

    echo
    echo "Press Enter to continue..."
    read
}

list_clients() {
    echo "Open WebUI Client Containers:"
    echo "============================="

    # Get all openwebui containers
    containers=($(docker ps -a --filter "name=openwebui-" --format "{{.Names}}"))

    if [ ${#containers[@]} -eq 0 ]; then
        echo "No Open WebUI deployments found."
        return
    fi

    # Header
    printf "%-25s %-30s %-20s %s\n" "CLIENT" "DOMAIN" "STATUS" "PORTS"
    printf "%-25s %-30s %-20s %s\n" "------" "------" "------" "-----"

    for container in "${containers[@]}"; do
        client_name=$(echo "$container" | sed 's/openwebui-//')
        status=$(docker ps -a --filter "name=${container}" --format "{{.Status}}")
        ports=$(docker ps -a --filter "name=${container}" --format "{{.Ports}}")

        # Try to get the redirect URI from container environment to extract domain
        redirect_uri=$(docker exec "$container" env 2>/dev/null | grep "GOOGLE_REDIRECT_URI=" | cut -d'=' -f2- 2>/dev/null || echo "")

        if [[ -n "$redirect_uri" ]]; then
            # Extract domain from redirect URI
            domain=$(echo "$redirect_uri" | sed -E 's|https?://||' | sed 's|/oauth/google/callback||')
        else
            domain="unknown"
        fi

        printf "%-25s %-30s %-20s %s\n" "$client_name" "$domain" "$status" "$ports"
    done
}

stop_all() {
    echo "Stopping all Open WebUI clients..."
    docker ps --filter "name=openwebui-" --format "{{.Names}}" | xargs -r docker stop
}

start_all() {
    echo "Starting all Open WebUI clients..."
    docker ps -a --filter "name=openwebui-" --filter "status=exited" --format "{{.Names}}" | xargs -r docker start
}

show_logs() {
    if [ -z "$2" ]; then
        echo "Usage: $0 logs CLIENT_NAME"
        echo "Available clients:"
        docker ps -a --filter "name=openwebui-" --format "{{.Names}}" | sed 's/openwebui-/  /'
        exit 1
    fi
    docker logs -f "openwebui-$2"
}

# Main execution logic
if [ $# -eq 0 ]; then
    # Interactive menu mode
    while true; do
        show_main_menu
        read choice

        case "$choice" in
            1)
                clear
                list_clients
                echo
                echo "Press Enter to continue..."
                read
                ;;
            2)
                create_new_deployment
                ;;
            3)
                manage_deployment_menu
                ;;
            4)
                generate_nginx_config
                ;;
            5)
                echo "Goodbye!"
                exit 0
                ;;
            *)
                echo "Invalid choice. Press Enter to continue..."
                read
                ;;
        esac
    done
else
    # Command line mode (preserve original functionality)
    case "$1" in
        "help"|"-h"|"--help")
            show_help
            ;;
        "list")
            list_clients
            ;;
        "stop")
            stop_all
            ;;
        "start")
            start_all
            ;;
        "logs")
            show_logs "$@"
            ;;
        *)
            echo "Unknown command: $1"
            echo "Run './client-manager.sh help' for available commands"
            exit 1
            ;;
    esac
fi
