#!/bin/bash
# Comprehensive VPS Deployment Script for Open WebUI
# Usage: bash deploy-vps.sh [--production] [--skip-frontend]
# Run from project root directory

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PRODUCTION=false
SKIP_FRONTEND=false
INSTALL_DIR="/opt/open-webui"
PYTHON_VERSION="3.11"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --production)
            PRODUCTION=true
            shift
            ;;
        --skip-frontend)
            SKIP_FRONTEND=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Open WebUI VPS Deployment Script       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# 1. Check prerequisites
log_info "Phase 1/6: Checking prerequisites..."

if ! command -v node &> /dev/null; then
    log_error "Node.js not found. Install Node.js >= 18.13.0"
    exit 1
fi
log_success "Node.js $(node -v) found"

if ! command -v npm &> /dev/null; then
    log_error "npm not found."
    exit 1
fi
log_success "npm $(npm -v) found"

if ! command -v python3 &> /dev/null; then
    log_error "Python3 not found. Install Python >= 3.11"
    exit 1
fi
log_success "Python3 $(python3 -V) found"

if ! command -v git &> /dev/null; then
    log_error "Git not found."
    exit 1
fi
log_success "Git found"

# 2. Build frontend
if [ "$SKIP_FRONTEND" = false ]; then
    log_info "Phase 2/6: Building frontend..."
    
    if [ ! -f "package.json" ]; then
        log_error "package.json not found. Run from project root."
        exit 1
    fi
    
    log_info "Installing npm dependencies (npm ci)..."
    npm ci || { log_error "npm ci failed"; exit 1; }
    log_success "npm dependencies installed"
    
    # Increase Node.js heap size to prevent out-of-memory errors during build
    export NODE_OPTIONS="--max-old-space-size=4096"
    log_info "Building frontend (npm run build)..."
    npm run build || { log_error "Frontend build failed"; exit 1; }
    log_success "Frontend build complete"
else
    log_warning "Skipping frontend build"
fi

# 3. Setup Python environment
log_info "Phase 3/6: Setting up Python virtual environment..."

if [ ! -d "venv" ]; then
    python3 -m venv venv || { log_error "Failed to create venv"; exit 1; }
    log_success "Virtual environment created"
else
    log_warning "Virtual environment already exists"
fi

# Activate venv
source venv/bin/activate || { log_error "Failed to activate venv"; exit 1; }
log_success "Virtual environment activated"

# 4. Install Python dependencies
log_info "Phase 4/6: Installing Python dependencies..."

log_info "Upgrading pip, setuptools, wheel..."
pip install --upgrade pip setuptools wheel > /dev/null 2>&1 || {
    log_error "Failed to upgrade pip"
    exit 1
}
log_success "pip, setuptools, wheel upgraded"

if [ ! -f "backend/requirements.txt" ]; then
    log_error "backend/requirements.txt not found."
    exit 1
fi

log_info "Installing backend requirements..."
pip install -r backend/requirements.txt || { log_error "Failed to install requirements"; exit 1; }
log_success "Python dependencies installed"

# 5. Setup Georgian font support
log_info "Phase 5/6: Setting up Georgian font support..."

if [ -f "scripts/fonts/NotoSansGeorgian-Bold.ttf" ]; then
    log_success "Georgian font already in repo"
elif [ -f "scripts/download_noto_georgian.sh" ]; then
    log_warning "Downloading Georgian font..."
    bash scripts/download_noto_georgian.sh || log_warning "Font download failed, continuing anyway"
else
    log_warning "Could not find font downloader script"
fi

# 6. Environment and final checks
log_info "Phase 6/6: Final configuration..."

if [ -f ".env" ]; then
    log_success ".env file exists (update as needed)"
else
    if [ -f ".env.example" ]; then
        log_warning "Copying .env.example to .env"
        cp .env.example .env
        log_warning "⚠️  IMPORTANT: Edit .env with your production settings!"
    fi
fi

# Summary
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Deployment Complete!                   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""

if [ "$PRODUCTION" = true ]; then
    echo -e "${YELLOW}Production Mode:${NC}"
    echo "1. Deactivate venv: deactivate"
    echo "2. Edit .env with production settings"
    echo "3. Configure Nginx/reverse proxy"
    echo "4. Setup systemd service (see DEPLOYMENT.md)"
    echo "5. Use gunicorn: pip install gunicorn"
    echo "   gunicorn -w 4 -k uvicorn.workers.UvicornWorker open_webui.main:app --bind 0.0.0.0:8080"
else
    echo -e "${YELLOW}Development Mode:${NC}"
    echo "1. Activate venv: source venv/bin/activate"
    echo "2. Start backend: cd backend && uvicorn open_webui.main:app --host 0.0.0.0 --port 8080"
    echo "3. In another terminal, serve frontend: cd build && python -m http.server 5173"
fi

echo ""
echo "For detailed setup instructions, see: DEPLOYMENT.md"
echo ""
