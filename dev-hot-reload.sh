#!/bin/bash

# mAI Development Script - Two-Container Hot Reload Architecture
# This script manages the development environment with separate frontend and backend containers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if .env.dev exists
check_env_file() {
    if [ ! -f ".env.dev" ]; then
        print_warning ".env.dev not found. Generating..."
        if [ -f "generate_client_env_dev.py" ]; then
            python3 generate_client_env_dev.py
            print_success ".env.dev generated successfully"
        else
            print_error "generate_client_env_dev.py not found. Please create .env.dev manually."
            exit 1
        fi
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  up, start     Start the development environment"
    echo "  down, stop    Stop the development environment"
    echo "  restart       Restart the development environment"
    echo "  logs          Show logs from all services"
    echo "  logs-fe       Show frontend logs only"
    echo "  logs-be       Show backend logs only"
    echo "  build         Rebuild containers without cache"
    echo "  clean         Stop containers and remove volumes"
    echo "  status        Show container status"
    echo "  shell-fe      Open shell in frontend container"
    echo "  shell-be      Open shell in backend container"
    echo "  help          Show this help message"
    echo ""
    echo "Development URLs:"
    echo "  Frontend (Vite): http://localhost:5173"
    echo "  Backend API:     http://localhost:8080"
    echo "  Health Check:    http://localhost:8080/health"
}

# Function to start development environment
start_dev() {
    print_info "Starting mAI Development Environment (Hot Reload)"
    check_env_file
    
    print_info "Building and starting containers..."
    docker-compose -f docker-compose.dev.yml up -d
    
    print_info "Waiting for services to be ready..."
    sleep 5
    
    print_info "Checking service health..."
    if docker-compose -f docker-compose.dev.yml ps | grep -q "mai-frontend-dev.*Up"; then
        print_success "Frontend service is running"
    else
        print_error "Frontend service failed to start"
    fi
    
    if docker-compose -f docker-compose.dev.yml ps | grep -q "mai-backend-dev.*Up"; then
        print_success "Backend service is running"
    else
        print_error "Backend service failed to start"
    fi
    
    print_success "Development environment started!"
    echo ""
    echo "📱 Frontend (Vite HMR): http://localhost:5173"
    echo "🔧 Backend API:         http://localhost:8080"
    echo "💚 Health Check:        http://localhost:8080/health"
    echo ""
    echo "Use 'docker-compose -f docker-compose.dev.yml logs -f' to see logs"
}

# Function to stop development environment
stop_dev() {
    print_info "Stopping mAI Development Environment"
    docker-compose -f docker-compose.dev.yml down
    print_success "Development environment stopped"
}

# Function to restart development environment
restart_dev() {
    print_info "Restarting mAI Development Environment"
    stop_dev
    start_dev
}

# Function to show logs
show_logs() {
    docker-compose -f docker-compose.dev.yml logs -f
}

# Function to show frontend logs
show_logs_frontend() {
    docker-compose -f docker-compose.dev.yml logs -f frontend-dev
}

# Function to show backend logs
show_logs_backend() {
    docker-compose -f docker-compose.dev.yml logs -f backend-dev
}

# Function to rebuild containers
rebuild_containers() {
    print_info "Rebuilding containers without cache"
    docker-compose -f docker-compose.dev.yml build --no-cache
    print_success "Containers rebuilt successfully"
}

# Function to clean environment
clean_env() {
    print_warning "This will stop containers and remove volumes. Are you sure? (y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        print_info "Cleaning development environment"
        docker-compose -f docker-compose.dev.yml down -v
        docker volume prune -f
        print_success "Environment cleaned"
    else
        print_info "Clean operation cancelled"
    fi
}

# Function to show container status
show_status() {
    print_info "Container Status:"
    docker-compose -f docker-compose.dev.yml ps
}

# Function to open shell in frontend container
shell_frontend() {
    print_info "Opening shell in frontend container"
    docker-compose -f docker-compose.dev.yml exec frontend-dev sh
}

# Function to open shell in backend container
shell_backend() {
    print_info "Opening shell in backend container"
    docker-compose -f docker-compose.dev.yml exec backend-dev bash
}

# Main script logic
case "${1:-help}" in
    up|start)
        start_dev
        ;;
    down|stop)
        stop_dev
        ;;
    restart)
        restart_dev
        ;;
    logs)
        show_logs
        ;;
    logs-fe)
        show_logs_frontend
        ;;
    logs-be)
        show_logs_backend
        ;;
    build)
        rebuild_containers
        ;;
    clean)
        clean_env
        ;;
    status)
        show_status
        ;;
    shell-fe)
        shell_frontend
        ;;
    shell-be)
        shell_backend
        ;;
    help|*)
        show_usage
        ;;
esac