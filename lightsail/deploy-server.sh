#!/bin/bash

# Next.js Deployment Script for Ubuntu 24.04 (LightSail)
# This script automates the deployment of a Next.js app using Nginx + PM2
# Usage: ./deploy-nextjs.sh <repository-url> [app-name] [server-name] [port] [--packages "package1 package2"]

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to show usage
show_usage() {
    echo -e "${YELLOW}Usage: $0 <repository-url> [app-name] [server-name] [port] [--packages \"package1 package2\"]${NC}"
    echo ""
    echo -e "${BLUE}Examples:${NC}"
    echo -e "  $0 https://github.com/user/my-nextjs-app.git"
    echo -e "  $0 git@github.com:user/my-nextjs-app.git"
    echo -e "  $0 https://github.com/user/my-nextjs-app.git my-custom-app"
    echo -e "  $0 git@github.com:user/my-nextjs-app.git my-custom-app 4321"
    echo -e "  $0 git@github.com:user/my-nextjs-app.git complaints 4321 --packages \"lodash axios\""
    echo ""
    echo -e "${BLUE}Arguments:${NC}"
    echo -e "  repository-url  : Git repository URL - HTTP/HTTPS or SSH (required)"
    echo -e "  app-name       : Name for PM2 process (optional, default: nextjs-app)"
    echo -e "  port           : Port number for the app (optional, default: 3000)"
    echo -e "  --packages     : Additional npm packages to install (optional)"
    exit 1
}

# Initialize variables
REPO_URL=""
APP_NAME="nextjs-app"
SERVER_NAME="_"
PORT="3000"
ADDITIONAL_PACKAGES=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --packages)
            ADDITIONAL_PACKAGES="$2"
            shift 2
            ;;
        *)
            if [ -z "$REPO_URL" ]; then
                REPO_URL="$1"
            elif [ "$APP_NAME" = "nextjs-app" ]; then
                APP_NAME="$1"
            elif [ "$SERVER_NAME" = "_" ]; then
                SERVER_NAME="$1"
            elif [ "$PORT" = "3000" ]; then
                PORT="$1"
            fi
            shift
            ;;
    esac
done

# Check if repository URL is provided
if [ -z "$REPO_URL" ]; then
    print_error "Repository URL is required!"
    echo ""
    show_usage
fi

# Validate repository URL format (support both HTTP/HTTPS and SSH)
if [[ ! "$REPO_URL" =~ ^(https?://|git@) ]]; then
    print_error "Invalid repository URL format. Please use HTTP/HTTPS or SSH URL."
    echo ""
    show_usage
fi

# Validate port number
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -lt 1024 ] || [ "$PORT" -gt 65535 ]; then
    print_error "Invalid port number. Please use a port between 1024 and 65535."
    echo ""
    show_usage
fi

print_status "Starting Next.js deployment on Ubuntu 24.04..."
print_status "Repository: $REPO_URL"
print_status "App Name: $APP_NAME"
print_status "Port: $PORT"
if [ -n "$ADDITIONAL_PACKAGES" ]; then
    print_status "Additional Packages: $ADDITIONAL_PACKAGES"
fi

# Step 1: System + Nginx Setup
print_status "Step 1: Updating system and installing Nginx + Git..."
sudo apt update
sudo apt install -y nginx git

print_success "System packages installed successfully"

# Step 2: Nginx Reverse Proxy Config
print_status "Step 2: Configuring Nginx reverse proxy..."

# Create Nginx configuration with dynamic port
# sudo tee /etc/nginx/sites-available/nextjs > /dev/null <<EOF
# server {
#     listen 80;
#     server_name $SERVER_NAME;

#     location / {
#         proxy_pass http://localhost:$PORT;
#         proxy_http_version 1.1;

#         proxy_set_header Upgrade \$http_upgrade;
#         proxy_set_header Connection 'upgrade';
#         proxy_set_header Host \$host;
#         proxy_cache_bypass \$http_upgrade;
#     }
# }
# EOF

sudo tee /etc/nginx/sites-available/nextjs > /dev/null <<'EOF'
# :80 — keep for ACME + redirect
server {
  listen 80;
  listen [::]:80;
  server_name origin.dev.customer-service.app.bio-rad.com;

  # let certbot http-01 work
  location ^~ /.well-known/acme-challenge/ { allow all; }

  # everything else -> https
  return 301 https://$host$request_uri;
}

# :443 — proxy to your app
server {
  listen 443 ssl http2;
  listen [::]:443 ssl http2;
  server_name origin.dev.customer-service.app.bio-rad.com;

  ssl_certificate     /etc/letsencrypt/live/origin.dev.customer-service.app.bio-rad.com/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/origin.dev.customer-service.app.bio-rad.com/privkey.pem;
  include /etc/letsencrypt/options-ssl-nginx.conf;
  ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

  # (optional) only if you set the same header in CloudFront
  # if ($http_x_origin_key != "YOUR_SECRET") { return 403; }

  location / {
    proxy_pass http://127.0.0.1:3000;
    
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    
    # SNI/cert safety + real viewer host/proto to the app
    proxy_set_header Host origin.customer-service.app.bio-rad.com;
    proxy_set_header X-Forwarded-Host $http_x_forwarded_host;
    proxy_set_header X-Forwarded-Proto $http_cloudfront_forwarded_proto;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    
    proxy_cache_bypass $http_upgrade;
  }
}
EOF

# Install Certbot for SSL
print_status "Installing Certbot for SSL..."
if ! command -v certbot >/dev/null 2>&1; then
    sudo snap install core; sudo snap refresh core
    sudo snap install --classic certbot
    sudo ln -s /snap/bin/certbot /usr/bin/certbot
    sudo ufw allow 'Nginx Full' || true
else
    print_warning "Certbot is already installed"
fi

# Check if SSL certificate exists, if not generate it
if [ ! -f "/etc/letsencrypt/live/origin.dev.customer-service.app.bio-rad.com/fullchain.pem" ]; then
    print_status "Generating SSL certificate..."
    sudo ufw allow 'Nginx Full' || true
    sudo certbot --nginx -d origin.dev.customer-service.app.bio-rad.com --redirect --agree-tos -m james_malin@bio-rad.com -n
    print_success "SSL certificate obtained successfully"
else
    print_warning "SSL certificate already exists"
fi

# Enable the site and reload Nginx
sudo ln -sf /etc/nginx/sites-available/nextjs /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

print_success "Nginx configured and reloaded successfully"

# Step 3: Node.js + PM2 Setup
print_status "Step 3: Installing Node.js and PM2..."

# Install NVM if not already installed
if [ ! -d "$HOME/.nvm" ]; then
    print_status "Installing NVM..."
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
    
    # Load NVM immediately
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
else
    print_warning "NVM is already installed"
fi

# Ensure NVM is loaded
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Source NVM before using Node.js commands
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Install LTS version of Node.js
print_status "Installing Node.js LTS version..."
nvm install --lts
nvm use --lts

# Verify Node.js installation
NODE_VERSION=$(node --version)
print_success "Node.js $NODE_VERSION installed successfully"

# Install PM2 globally (source NVM again to ensure npm is available)
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
npm install -g pm2

print_success "Node.js and PM2 installed successfully"

# Step 4: Clone & Start Next.js App
print_status "Step 4: Cloning and setting up your Next.js app..."

# Extract repository name for directory
REPO_NAME=$(basename "$REPO_URL" .git)

# Remove existing directory if it exists
if [ -d "$REPO_NAME" ]; then
    print_warning "Directory $REPO_NAME already exists. Removing it..."
    rm -rf "$REPO_NAME"
fi

# Clone the repository
git clone "$REPO_URL"
cd "$REPO_NAME"

# Install dependencies and build
print_status "Installing dependencies..."
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
npm install

# Install additional packages if specified
if [ -n "$ADDITIONAL_PACKAGES" ]; then
    print_status "Installing additional packages: $ADDITIONAL_PACKAGES"
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    npm install $ADDITIONAL_PACKAGES
    print_success "Additional packages installed successfully"
fi

# Build the app
print_status "Building the app..."
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
npm run build

# Stop existing PM2 process if it exists
if pm2 list | grep -q "$APP_NAME"; then
    print_warning "Stopping existing PM2 process: $APP_NAME"
    pm2 delete "$APP_NAME"
fi

# Start the app with PM2
print_status "Starting the app with PM2..."
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
PORT=$PORT pm2 start npm --name "$APP_NAME" -- start

print_success "Next.js app started successfully with PM2"

# Step 5: Make PM2 Persistent
print_status "Step 5: Making PM2 persistent across reboots..."

# Generate startup script
STARTUP_CMD=$(pm2 startup | tail -n 1)
if [[ $STARTUP_CMD == sudo* ]]; then
    print_status "Executing PM2 startup command..."
    eval "$STARTUP_CMD"
else
    print_warning "Please run the following command manually:"
    echo "$STARTUP_CMD"
fi

# Save PM2 configuration
pm2 save

print_success "PM2 configured for auto-startup"

# Final status check
print_status "Checking deployment status..."

# Check if Nginx is running
if systemctl is-active --quiet nginx; then
    print_success "✓ Nginx is running"
else
    print_error "✗ Nginx is not running"
fi

# Check if PM2 process is running
if pm2 list | grep -q "$APP_NAME.*online"; then
    print_success "✓ $APP_NAME is running via PM2"
else
    print_error "✗ $APP_NAME is not running"
fi

# Get server IP
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "Unable to detect IP")

echo ""
echo "=========================================="
print_success "🎉 DEPLOYMENT COMPLETED SUCCESSFULLY! 🎉"
echo "=========================================="
echo ""
echo -e "${GREEN}Your Next.js app is now deployed and running!${NC}"
echo ""
echo -e "${BLUE}Access your app at:${NC}"
if [ "$SERVER_IP" != "Unable to detect IP" ]; then
    echo -e "  🌐 http://$SERVER_IP"
else
    echo -e "  🌐 http://YOUR_SERVER_IP"
fi
echo ""
echo -e "${BLUE}App Details:${NC}"
echo -e "  📱 App Name: ${YELLOW}$APP_NAME${NC}"
echo -e "  🔌 Port: ${YELLOW}$PORT${NC}"
echo -e "  📁 Directory: ${YELLOW}$(pwd)${NC}"
if [ -n "$ADDITIONAL_PACKAGES" ]; then
    echo -e "  📦 Additional Packages: ${YELLOW}$ADDITIONAL_PACKAGES${NC}"
fi
echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo -e "  📊 View PM2 processes: ${YELLOW}pm2 list${NC}"
echo -e "  📋 View app logs: ${YELLOW}pm2 logs $APP_NAME${NC}"
echo -e "  🔄 Restart app: ${YELLOW}pm2 restart $APP_NAME${NC}"
echo -e "  🛑 Stop app: ${YELLOW}pm2 stop $APP_NAME${NC}"
echo ""
echo -e "${BLUE}Nginx commands:${NC}"
echo -e "  📊 Check status: ${YELLOW}sudo systemctl status nginx${NC}"
echo -e "  🔄 Reload config: ${YELLOW}sudo systemctl reload nginx${NC}"
echo ""
