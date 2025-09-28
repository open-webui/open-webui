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
    echo "║       Open WebUI Client Manager       ║"
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

    # Get domain (optional - auto-detect if empty)
    echo -n "Enter domain (press Enter to auto-detect): "
    read domain

    # Resolve domain for display
    if [[ -z "$domain" ]]; then
        # Auto-detect environment logic (same as start-template.sh)
        if [ -f "/etc/hostname" ] && grep -q "droplet\|server\|prod" /etc/hostname 2>/dev/null; then
            # Production environment
            resolved_domain="${client_name}.yourdomain.com"
            redirect_uri="https://${resolved_domain}/oauth/google/callback"
            environment="production"
        else
            # Development environment
            resolved_domain="localhost:${port}"
            redirect_uri="http://127.0.0.1:${port}/oauth/google/callback"
            environment="development"
        fi
        domain="auto-detect"
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
            echo "1. Add nginx configuration for domain: $domain"
            echo "2. Update Google OAuth redirect URI: https://$domain/oauth/google/callback"
            echo "3. Configure DNS for: $domain"
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

manage_deployment_menu() {
    while true; do
        clear
        echo "╔════════════════════════════════════════╗"
        echo "║        Manage Deployment Menu         ║"
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
            echo "$((i+1))) ${clients[$i]} ($status)"
        done

        echo "$((${#clients[@]}+1))) Return to main menu"
        echo
        echo -n "Select deployment to manage (1-$((${#clients[@]}+1))): "
        read selection

        if [[ "$selection" =~ ^[0-9]+$ ]] && [ "$selection" -gt 0 ] && [ "$selection" -le ${#clients[@]} ]; then
            manage_single_deployment "${clients[$((selection-1))]}"
        elif [ "$selection" -eq $((${#clients[@]}+1)) ]; then
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

    while true; do
        clear
        echo "╔════════════════════════════════════════╗"
        echo "║     Managing: $client_name"
        printf "║%*s║\n" $((40-${#client_name}-15)) ""
        echo "╚════════════════════════════════════════╝"
        echo

        # Show status
        local status=$(docker ps -a --filter "name=$container_name" --format "{{.Status}}")
        local ports=$(docker ps -a --filter "name=$container_name" --format "{{.Ports}}")
        echo "Status: $status"
        echo "Ports:  $ports"
        echo

        echo "1) Start deployment"
        echo "2) Stop deployment"
        echo "3) Restart deployment"
        echo "4) View logs"
        echo "5) Remove deployment (DANGER)"
        echo "6) Return to deployment list"
        echo
        echo -n "Select action (1-6): "
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
            6)
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
    echo "║      Generate nginx Configuration     ║"
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
        echo "$((i+1))) ${clients[$i]} (port: $ports)"
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
                echo -n "Enter production domain (e.g., ${client_name}.yourdomain.com): "
                read domain
                if [[ -z "$domain" ]]; then
                    echo "❌ Domain cannot be empty."
                    echo "Press Enter to continue..."
                    read
                    return
                fi
                template_file="${SCRIPT_DIR}/nginx-template.conf"
                config_file="/tmp/${client_name}-nginx.conf"
                setup_type="production"
                ;;
            2)
                echo -n "Enter local domain (press Enter for 'localhost'): "
                read domain
                if [[ -z "$domain" ]]; then
                    domain="localhost"
                fi
                template_file="${SCRIPT_DIR}/nginx-template-local.conf"
                config_file="${SCRIPT_DIR}/nginx/sites-available/${client_name}"
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
            echo "╔════════════════════════════════════════╗"
            echo "║         Production Setup Steps        ║"
            echo "╚════════════════════════════════════════╝"
            echo
            echo "1. Copy config to server:"
            echo "   scp $config_file user@server:/etc/nginx/sites-available/${client_name}"
            echo
            echo "2. Enable the site:"
            echo "   sudo ln -s /etc/nginx/sites-available/${client_name} /etc/nginx/sites-enabled/"
            echo
            echo "3. Test nginx config:"
            echo "   sudo nginx -t"
            echo
            echo "4. Generate SSL certificate:"
            echo "   sudo certbot --nginx -d ${domain}"
            echo
            echo "5. Uncomment SSL lines in config file and restart:"
            echo "   sudo systemctl restart nginx"
            echo
            echo "6. Update Google OAuth with redirect URI:"
            echo "   https://${domain}/oauth/google/callback"
        else
            echo "╔════════════════════════════════════════╗"
            echo "║         Local Testing Steps           ║"
            echo "╚════════════════════════════════════════╝"
            echo
            echo "1. Enable the site:"
            echo "   cp ${SCRIPT_DIR}/nginx/sites-available/${client_name} ${SCRIPT_DIR}/nginx/sites-enabled/"
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
    docker ps -a --filter "name=openwebui-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
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