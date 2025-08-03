#!/bin/bash
#
# Docker Daily Batch Processing Script
# Runs the daily batch processor inside Docker containers
# 
# Usage:
#   ./docker_daily_batch.sh                    # Process all containers
#   ./docker_daily_batch.sh container_name     # Process specific container
#

set -e

# Configuration
DOCKER_COMPOSE_DIR="/Users/patpil/Documents/Projects/mAI"
LOG_DIR="$DOCKER_COMPOSE_DIR/logs"
DEFAULT_CONTAINERS=("open-webui-dev" "open-webui-customization")

# Create log directory
mkdir -p "$LOG_DIR"

# Function to run batch processing in a container
run_batch_in_container() {
    local container_name="$1"
    local log_file="$LOG_DIR/daily_batch_${container_name}_$(date +%Y%m%d_%H%M%S).log"
    
    echo "🕰️ Running daily batch processing in container: $container_name"
    echo "📝 Log file: $log_file"
    
    # Check if container is running
    if ! docker ps --format "table {{.Names}}" | grep -q "^${container_name}$"; then
        echo "❌ Container $container_name is not running"
        return 1
    fi
    
    # Run the batch processor
    echo "Starting batch processing..." | tee "$log_file"
    if docker exec "$container_name" python -m open_webui.utils.daily_batch_processor >> "$log_file" 2>&1; then
        echo "✅ Batch processing completed successfully for $container_name"
        
        # Extract summary from log
        if grep -q "✅ Daily batch processing completed" "$log_file"; then
            duration=$(grep "Daily batch processing completed" "$log_file" | sed -n 's/.*in \([0-9.]*\)s.*/\1/p')
            echo "⏱️ Processing time: ${duration}s"
        fi
        
        return 0
    else
        echo "❌ Batch processing failed for $container_name"
        echo "📋 Last 10 lines of log:"
        tail -10 "$log_file"
        return 1
    fi
}

# Function to setup cron job for Docker environment
setup_cron() {
    local container_name="$1"
    
    echo "🕰️ Setting up cron job for container: $container_name"
    
    # Create cron job inside container
    docker exec "$container_name" bash -c "
        # Create cron job for daily execution at 00:00
        echo '0 0 * * * python -m open_webui.utils.daily_batch_processor >> /app/logs/daily_batch_\$(date +\\%Y\\%m\\%d).log 2>&1' | crontab -
        
        # Verify cron job was created
        echo 'Current cron jobs:'
        crontab -l
        
        # Start cron service if not running (for containers that support it)
        if command -v service >/dev/null 2>&1; then
            service cron start 2>/dev/null || true
        fi
    " 2>/dev/null || {
        echo "⚠️ Could not setup cron in container $container_name (may not support cron)"
        echo "💡 Consider using host-level cron to execute: docker exec $container_name python -m open_webui.utils.daily_batch_processor"
    }
}

# Main execution
main() {
    local target_container="$1"
    
    echo "🚀 mAI Daily Batch Processing Script"
    echo "===================================="
    echo "📅 Date: $(date)"
    echo ""
    
    if [ -n "$target_container" ]; then
        # Process specific container
        if [ "$target_container" = "--setup-cron" ]; then
            # Setup cron for all default containers
            for container in "${DEFAULT_CONTAINERS[@]}"; do
                if docker ps --format "table {{.Names}}" | grep -q "^${container}$"; then
                    setup_cron "$container"
                else
                    echo "⚠️ Container $container is not running, skipping cron setup"
                fi
            done
        else
            run_batch_in_container "$target_container"
        fi
    else
        # Process all default containers
        local successful=0
        local total=0
        
        for container in "${DEFAULT_CONTAINERS[@]}"; do
            total=$((total + 1))
            
            if docker ps --format "table {{.Names}}" | grep -q "^${container}$"; then
                if run_batch_in_container "$container"; then
                    successful=$((successful + 1))
                fi
            else
                echo "⚠️ Container $container is not running, skipping"
            fi
            
            echo ""
        done
        
        echo "📊 Summary: $successful/$total containers processed successfully"
        
        if [ "$successful" -lt "$total" ]; then
            exit 1
        fi
    fi
}

# Help function
show_help() {
    echo "Usage: $0 [CONTAINER_NAME|--setup-cron]"
    echo ""
    echo "Options:"
    echo "  CONTAINER_NAME    Process specific container"
    echo "  --setup-cron      Setup cron jobs in all containers"
    echo "  (no args)         Process all default containers"
    echo ""
    echo "Examples:"
    echo "  $0                          # Process all containers"
    echo "  $0 open-webui-dev           # Process dev container only"
    echo "  $0 --setup-cron             # Setup cron jobs"
    echo ""
    echo "Default containers: ${DEFAULT_CONTAINERS[*]}"
}

# Check arguments
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    *)
        main "$1"
        ;;
esac