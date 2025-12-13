#!/bin/bash
# Unified Log Viewer for OpenWebUI and Redis/RQ Workers
# This script shows logs from both the main application and worker processes

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}OpenWebUI + Redis/RQ Worker Log Viewer${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Determine log locations
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR/backend"

# Log file locations
MAIN_APP_LOG="${MAIN_APP_LOG:-/tmp/openwebui.log}"
WORKER_LOG="${WORKER_LOG:-/tmp/rq-worker.log}"
REDIS_LOG="${REDIS_LOG:-/var/log/redis/redis-server.log}"

# Check if running in Docker
if [ -f /.dockerenv ] || [ -n "$DOCKER_CONTAINER" ]; then
    echo -e "${YELLOW}Running in Docker container${NC}"
    # In Docker, logs go to stdout/stderr, check if redirected
    if [ -n "$LOG_FILE" ]; then
        MAIN_APP_LOG="$LOG_FILE"
    fi
    # Worker logs might be in /tmp or stdout
    WORKER_LOG="${WORKER_LOG:-/tmp/rq-worker.log}"
fi

# Check if using Kubernetes
if [ -n "$POD_NAME" ] || [ -n "$KUBERNETES_SERVICE_HOST" ]; then
    echo -e "${YELLOW}Running in Kubernetes${NC}"
    echo -e "${BLUE}To view logs in Kubernetes, use:${NC}"
    echo -e "  ${GREEN}kubectl logs -f <pod-name>${NC} (for main app)"
    echo -e "  ${GREEN}kubectl logs -f <worker-pod-name>${NC} (for worker)"
    echo -e "  ${GREEN}kubectl logs -f <redis-pod-name>${NC} (for Redis)"
    echo ""
    echo -e "${BLUE}Or view all logs together:${NC}"
    echo -e "  ${GREEN}kubectl logs -f -l app=open-webui${NC}"
    echo ""
fi

echo -e "${BLUE}Log File Locations:${NC}"
echo -e "  Main App: ${GREEN}${MAIN_APP_LOG}${NC}"
echo -e "  Worker:   ${GREEN}${WORKER_LOG}${NC}"
echo -e "  Redis:    ${GREEN}${REDIS_LOG}${NC}"
echo ""

# Function to check if file exists and is readable
check_log_file() {
    local file=$1
    local name=$2
    if [ -f "$file" ] && [ -r "$file" ]; then
        echo -e "${GREEN}✓${NC} $name log file exists: $file"
        return 0
    else
        echo -e "${RED}✗${NC} $name log file not found: $file"
        return 1
    fi
}

# Check log files
MAIN_EXISTS=false
WORKER_EXISTS=false
REDIS_EXISTS=false

if check_log_file "$MAIN_APP_LOG" "Main App"; then
    MAIN_EXISTS=true
fi

if check_log_file "$WORKER_LOG" "Worker"; then
    WORKER_EXISTS=true
fi

if check_log_file "$REDIS_LOG" "Redis"; then
    REDIS_EXISTS=true
fi

echo ""

# If no log files found, show how to find logs
if [ "$MAIN_EXISTS" = false ] && [ "$WORKER_EXISTS" = false ] && [ "$REDIS_EXISTS" = false ]; then
    echo -e "${YELLOW}No log files found at expected locations.${NC}"
    echo ""
    echo -e "${BLUE}Where to find logs:${NC}"
    echo ""
    echo -e "${CYAN}1. Main Application Logs:${NC}"
    echo -e "   - If running with uvicorn: Check stdout/stderr"
    echo -e "   - If using systemd: ${GREEN}journalctl -u open-webui -f${NC}"
    echo -e "   - If using Docker: ${GREEN}docker logs -f <container-name>${NC}"
    echo -e "   - If using Kubernetes: ${GREEN}kubectl logs -f <pod-name>${NC}"
    echo ""
    echo -e "${CYAN}2. Worker Logs:${NC}"
    echo -e "   - Worker stdout/stderr (usually redirected to /tmp/rq-worker.log)"
    echo -e "   - If using systemd: ${GREEN}journalctl -u rq-worker -f${NC}"
    echo -e "   - If using Docker: ${GREEN}docker logs -f <worker-container-name>${NC}"
    echo -e "   - If using Kubernetes: ${GREEN}kubectl logs -f <worker-pod-name>${NC}"
    echo ""
    echo -e "${CYAN}3. Redis Logs:${NC}"
    echo -e "   - Default: ${GREEN}/var/log/redis/redis-server.log${NC}"
    echo -e "   - If using Docker: ${GREEN}docker logs -f <redis-container-name>${NC}"
    echo -e "   - If using Kubernetes: ${GREEN}kubectl logs -f <redis-pod-name>${NC}"
    echo ""
    echo -e "${BLUE}To set custom log locations, set environment variables:${NC}"
    echo -e "   ${GREEN}export MAIN_APP_LOG=/path/to/main.log${NC}"
    echo -e "   ${GREEN}export WORKER_LOG=/path/to/worker.log${NC}"
    echo -e "   ${GREEN}export REDIS_LOG=/path/to/redis.log${NC}"
    echo ""
    exit 1
fi

# Function to tail log file with color coding
tail_log() {
    local file=$1
    local name=$2
    local color=$3
    
    if [ -f "$file" ] && [ -r "$file" ]; then
        echo -e "${color}=== $name Logs ===${NC}"
        tail -f "$file" | while IFS= read -r line; do
            # Color code by log level
            if echo "$line" | grep -q "ERROR\|CRITICAL\|❌"; then
                echo -e "${RED}$line${NC}"
            elif echo "$line" | grep -q "WARNING\|⚠️"; then
                echo -e "${YELLOW}$line${NC}"
            elif echo "$line" | grep -q "INFO\|✅\|[STEP]"; then
                echo -e "${GREEN}$line${NC}"
            elif echo "$line" | grep -q "DEBUG"; then
                echo -e "${CYAN}$line${NC}"
            else
                echo "$line"
            fi
        done
    fi
}

# Menu for viewing logs
show_menu() {
    echo -e "${CYAN}Select log view:${NC}"
    echo -e "  ${GREEN}1${NC}) Main App only"
    echo -e "  ${GREEN}2${NC}) Worker only"
    echo -e "  ${GREEN}3${NC}) Redis only"
    echo -e "  ${GREEN}4${NC}) All logs (interleaved)"
    echo -e "  ${GREEN}5${NC}) Main App + Worker (combined)"
    echo -e "  ${GREEN}6${NC}) Show last 100 lines of each"
    echo -e "  ${GREEN}q${NC}) Quit"
    echo ""
    read -p "Choice [1-6, q]: " choice
    
    case $choice in
        1)
            if [ "$MAIN_EXISTS" = true ]; then
                tail -f "$MAIN_APP_LOG"
            else
                echo -e "${RED}Main app log not found${NC}"
            fi
            ;;
        2)
            if [ "$WORKER_EXISTS" = true ]; then
                tail -f "$WORKER_LOG"
            else
                echo -e "${RED}Worker log not found${NC}"
            fi
            ;;
        3)
            if [ "$REDIS_EXISTS" = true ]; then
                tail -f "$REDIS_LOG"
            else
                echo -e "${RED}Redis log not found${NC}"
            fi
            ;;
        4)
            # Use multitail if available, otherwise use simple tail
            if command -v multitail >/dev/null 2>&1; then
                MULTITAIL_CMD="multitail"
                if [ "$MAIN_EXISTS" = true ]; then
                    MULTITAIL_CMD="$MULTITAIL_CMD -ci green $MAIN_APP_LOG"
                fi
                if [ "$WORKER_EXISTS" = true ]; then
                    MULTITAIL_CMD="$MULTITAIL_CMD -ci yellow $WORKER_LOG"
                fi
                if [ "$REDIS_EXISTS" = true ]; then
                    MULTITAIL_CMD="$MULTITAIL_CMD -ci cyan $REDIS_LOG"
                fi
                eval $MULTITAIL_CMD
            else
                echo -e "${YELLOW}multitail not installed. Showing logs sequentially.${NC}"
                echo -e "${BLUE}Install multitail for better experience: ${GREEN}brew install multitail${NC} (macOS) or ${GREEN}apt-get install multitail${NC} (Linux)"
                echo ""
                # Simple approach: tail all files
                if [ "$MAIN_EXISTS" = true ] && [ "$WORKER_EXISTS" = true ] && [ "$REDIS_EXISTS" = true ]; then
                    tail -f "$MAIN_APP_LOG" "$WORKER_LOG" "$REDIS_LOG"
                elif [ "$MAIN_EXISTS" = true ] && [ "$WORKER_EXISTS" = true ]; then
                    tail -f "$MAIN_APP_LOG" "$WORKER_LOG"
                elif [ "$MAIN_EXISTS" = true ]; then
                    tail -f "$MAIN_APP_LOG"
                elif [ "$WORKER_EXISTS" = true ]; then
                    tail -f "$WORKER_LOG"
                fi
            fi
            ;;
        5)
            if [ "$MAIN_EXISTS" = true ] && [ "$WORKER_EXISTS" = true ]; then
                # Combine logs with prefixes
                (tail -f "$MAIN_APP_LOG" | sed 's/^/[MAIN] /' &) &
                (tail -f "$WORKER_LOG" | sed 's/^/[WORKER] /' &) &
                wait
            elif [ "$MAIN_EXISTS" = true ]; then
                tail -f "$MAIN_APP_LOG"
            elif [ "$WORKER_EXISTS" = true ]; then
                tail -f "$WORKER_LOG"
            else
                echo -e "${RED}Main app or worker logs not found${NC}"
            fi
            ;;
        6)
            echo -e "${CYAN}=== Last 100 lines of Main App ===${NC}"
            if [ "$MAIN_EXISTS" = true ]; then
                tail -n 100 "$MAIN_APP_LOG"
            else
                echo -e "${RED}Main app log not found${NC}"
            fi
            echo ""
            echo -e "${CYAN}=== Last 100 lines of Worker ===${NC}"
            if [ "$WORKER_EXISTS" = true ]; then
                tail -n 100 "$WORKER_LOG"
            else
                echo -e "${RED}Worker log not found${NC}"
            fi
            echo ""
            echo -e "${CYAN}=== Last 100 lines of Redis ===${NC}"
            if [ "$REDIS_EXISTS" = true ]; then
                tail -n 100 "$REDIS_LOG"
            else
                echo -e "${RED}Redis log not found${NC}"
            fi
            ;;
        q|Q)
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice${NC}"
            show_menu
            ;;
    esac
}

# If argument provided, use it
if [ "$1" = "main" ]; then
    if [ "$MAIN_EXISTS" = true ]; then
        tail -f "$MAIN_APP_LOG"
    else
        echo -e "${RED}Main app log not found: $MAIN_APP_LOG${NC}"
        exit 1
    fi
elif [ "$1" = "worker" ]; then
    if [ "$WORKER_EXISTS" = true ]; then
        tail -f "$WORKER_LOG"
    else
        echo -e "${RED}Worker log not found: $WORKER_LOG${NC}"
        exit 1
    fi
elif [ "$1" = "redis" ]; then
    if [ "$REDIS_EXISTS" = true ]; then
        tail -f "$REDIS_LOG"
    else
        echo -e "${RED}Redis log not found: $REDIS_LOG${NC}"
        exit 1
    fi
elif [ "$1" = "all" ]; then
    if [ "$MAIN_EXISTS" = true ] && [ "$WORKER_EXISTS" = true ] && [ "$REDIS_EXISTS" = true ]; then
        tail -f "$MAIN_APP_LOG" "$WORKER_LOG" "$REDIS_LOG"
    elif [ "$MAIN_EXISTS" = true ] && [ "$WORKER_EXISTS" = true ]; then
        tail -f "$MAIN_APP_LOG" "$WORKER_LOG"
    else
        echo -e "${RED}Required log files not found${NC}"
        exit 1
    fi
elif [ "$1" = "combined" ]; then
    if [ "$MAIN_EXISTS" = true ] && [ "$WORKER_EXISTS" = true ]; then
        (tail -f "$MAIN_APP_LOG" | sed 's/^/[MAIN] /' &) &
        (tail -f "$WORKER_LOG" | sed 's/^/[WORKER] /' &) &
        wait
    else
        echo -e "${RED}Main app or worker logs not found${NC}"
        exit 1
    fi
elif [ -n "$1" ]; then
    echo -e "${RED}Unknown option: $1${NC}"
    echo "Usage: $0 [main|worker|redis|all|combined]"
    exit 1
else
    # Interactive menu
    show_menu
fi

