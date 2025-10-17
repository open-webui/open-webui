#!/bin/bash
# Create Deployment User for Open WebUI
# Run this as root on a fresh Digital Ocean droplet to set up a secure deployment user
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/imagicrafter/open-webui/main/mt/setup/create-deployment-user.sh | bash
#   OR
#   sudo ./create-deployment-user.sh

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
DEPLOY_USER="${DEPLOY_USER:-qbmgr}"
REPO_URL="https://github.com/imagicrafter/open-webui.git"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Open WebUI Deployment User Setup                      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ This script must be run as root${NC}"
    echo "Run with: sudo $0"
    exit 1
fi

# Check if user already exists
if id "$DEPLOY_USER" &>/dev/null; then
    echo -e "${YELLOW}⚠️  User '$DEPLOY_USER' already exists${NC}"
    echo -n "Do you want to continue and update the configuration? (y/N): "
    read confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "Exiting..."
        exit 0
    fi
    USER_EXISTS=true
else
    USER_EXISTS=false
fi

# Step 1: Create user if doesn't exist
if [ "$USER_EXISTS" = false ]; then
    echo -e "${BLUE}Step 1: Creating user '$DEPLOY_USER'${NC}"
    useradd -m -s /bin/bash "$DEPLOY_USER"
    echo -e "${GREEN}✅ User created${NC}"
else
    echo -e "${BLUE}Step 1: User already exists, skipping creation${NC}"
fi
echo

# Step 2: Add to sudo and docker groups
echo -e "${BLUE}Step 2: Adding user to sudo and docker groups${NC}"
usermod -aG sudo "$DEPLOY_USER"
usermod -aG docker "$DEPLOY_USER"
echo -e "${GREEN}✅ Groups configured${NC}"
echo

# Step 3: Configure sudo without password (optional but convenient)
echo -e "${BLUE}Step 3: Configure passwordless sudo${NC}"
echo -n "Allow $DEPLOY_USER to use sudo without password? (Y/n): "
read allow_nopasswd
if [[ ! "$allow_nopasswd" =~ ^[Nn]$ ]]; then
    echo "$DEPLOY_USER ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/$DEPLOY_USER"
    chmod 0440 "/etc/sudoers.d/$DEPLOY_USER"
    echo -e "${GREEN}✅ Passwordless sudo enabled${NC}"
else
    echo "Setting password for $DEPLOY_USER"
    passwd "$DEPLOY_USER"
fi
echo

# Step 4: Set up SSH key
echo -e "${BLUE}Step 4: Set up SSH key${NC}"
echo "Choose SSH key setup method:"
echo "1) Copy from root's authorized_keys (recommended if you SSH'd as root)"
echo "2) Manually paste your SSH public key"
echo "3) Skip (configure later)"
echo -n "Choice (1-3): "
read ssh_choice

case "$ssh_choice" in
    1)
        if [ -f /root/.ssh/authorized_keys ]; then
            mkdir -p "/home/$DEPLOY_USER/.ssh"
            cp /root/.ssh/authorized_keys "/home/$DEPLOY_USER/.ssh/authorized_keys"
            chown -R "$DEPLOY_USER:$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh"
            chmod 700 "/home/$DEPLOY_USER/.ssh"
            chmod 600 "/home/$DEPLOY_USER/.ssh/authorized_keys"
            echo -e "${GREEN}✅ SSH key copied from root${NC}"
        else
            echo -e "${YELLOW}⚠️  No authorized_keys found for root${NC}"
        fi
        ;;
    2)
        echo "Paste your SSH public key (starts with 'ssh-rsa' or 'ssh-ed25519'):"
        read ssh_key
        mkdir -p "/home/$DEPLOY_USER/.ssh"
        echo "$ssh_key" > "/home/$DEPLOY_USER/.ssh/authorized_keys"
        chown -R "$DEPLOY_USER:$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh"
        chmod 700 "/home/$DEPLOY_USER/.ssh"
        chmod 600 "/home/$DEPLOY_USER/.ssh/authorized_keys"
        echo -e "${GREEN}✅ SSH key configured${NC}"
        ;;
    3)
        echo "Skipping SSH key setup"
        ;;
esac
echo

# Step 5: Clone Open WebUI repository
echo -e "${BLUE}Step 5: Clone Open WebUI repository${NC}"
REPO_PATH="/home/$DEPLOY_USER/open-webui"
if [ -d "$REPO_PATH" ]; then
    echo -e "${YELLOW}⚠️  Repository already exists at $REPO_PATH${NC}"
    echo -n "Pull latest changes? (Y/n): "
    read pull_confirm
    if [[ ! "$pull_confirm" =~ ^[Nn]$ ]]; then
        sudo -u "$DEPLOY_USER" git -C "$REPO_PATH" pull
        echo -e "${GREEN}✅ Repository updated${NC}"
    fi
else
    sudo -u "$DEPLOY_USER" git clone "$REPO_URL" "$REPO_PATH"
    echo -e "${GREEN}✅ Repository cloned to $REPO_PATH${NC}"
fi
echo

# Step 6: Create common directories
echo -e "${BLUE}Step 6: Create common directories${NC}"
mkdir -p /opt/openwebui-nginx
chown -R "$DEPLOY_USER:$DEPLOY_USER" /opt/openwebui-nginx
echo -e "${GREEN}✅ Created /opt/openwebui-nginx${NC}"
echo

# Step 7: Install additional packages
echo -e "${BLUE}Step 7: Install useful packages${NC}"
echo -n "Install certbot, jq, htop, tree? (Y/n): "
read install_packages
if [[ ! "$install_packages" =~ ^[Nn]$ ]]; then
    apt-get update -qq
    apt-get install -y certbot jq htop tree net-tools > /dev/null 2>&1
    echo -e "${GREEN}✅ Packages installed${NC}"
else
    echo "Skipping package installation"
fi
echo

# Step 8: Create welcome message
echo -e "${BLUE}Step 8: Create welcome message${NC}"
cat > "/home/$DEPLOY_USER/WELCOME.txt" << EOF
╔════════════════════════════════════════════════════════════╗
║          Open WebUI Deployment Server Ready                ║
╚════════════════════════════════════════════════════════════╝

Your server is configured and ready for Open WebUI deployment!

Quick Start:
1. Navigate to repo: cd ~/open-webui/mt/nginx-container
2. Deploy nginx: ./deploy-nginx-container.sh
3. Create client: cd ~/open-webui/mt && ./client-manager.sh

Repository location: ~/open-webui
User: $DEPLOY_USER (has sudo and docker access)

Documentation:
- Quick Start: ~/open-webui/mt/QUICKSTART-FRESH-DEPLOYMENT.md
- nginx Setup: ~/open-webui/mt/nginx-container/README.md

Useful commands:
- Check Docker: docker ps
- Check nginx: docker ps --filter "name=openwebui-nginx"
- View deployments: cd ~/open-webui/mt && ./client-manager.sh

For security, consider disabling root SSH login after testing.
EOF

chown "$DEPLOY_USER:$DEPLOY_USER" "/home/$DEPLOY_USER/WELCOME.txt"
echo -e "${GREEN}✅ Welcome message created${NC}"
echo

# Step 9: Disable root SSH (optional)
echo -e "${BLUE}Step 9: Security hardening${NC}"
echo -e "${YELLOW}⚠️  For security, it's recommended to disable root SSH login${NC}"
echo "Test SSH as $DEPLOY_USER first, then disable root SSH"
echo
echo -n "Disable root SSH login now? (y/N): "
read disable_root
if [[ "$disable_root" =~ ^[Yy]$ ]]; then
    sed -i.bak 's/^PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
    systemctl reload sshd
    echo -e "${GREEN}✅ Root SSH login disabled${NC}"
    echo -e "${YELLOW}⚠️  Make sure you can SSH as $DEPLOY_USER before logging out!${NC}"
else
    echo "Skipping - you can disable later by editing /etc/ssh/sshd_config"
    echo "Set: PermitRootLogin no"
fi
echo

# Step 10: Test Docker access
echo -e "${BLUE}Step 10: Test Docker access${NC}"
sudo -u "$DEPLOY_USER" docker ps > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Docker access verified for $DEPLOY_USER${NC}"
else
    echo -e "${YELLOW}⚠️  Docker group may require logout/login to take effect${NC}"
    echo "Run: newgrp docker (or logout and login again)"
fi
echo

# Summary
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo
echo "Deployment user configured:"
echo "  User: $DEPLOY_USER"
echo "  Groups: sudo, docker"
echo "  Repository: /home/$DEPLOY_USER/open-webui"
echo "  Config directory: /opt/openwebui-nginx"
echo
echo "Next steps:"
echo "1. Test SSH access: ssh $DEPLOY_USER@YOUR_DROPLET_IP"
echo "2. Read welcome: cat ~/WELCOME.txt"
echo "3. Deploy nginx: cd ~/open-webui/mt/nginx-container && ./deploy-nginx-container.sh"
echo "4. Create client: cd ~/open-webui/mt && ./client-manager.sh"
echo
echo "Security reminder:"
if [[ "$disable_root" =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}✅ Root SSH login is disabled${NC}"
else
    echo -e "${YELLOW}⚠️  Root SSH is still enabled - disable after testing $DEPLOY_USER access${NC}"
fi
echo

# Option to switch to qbmgr and run client-manager
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Would you like to switch to $DEPLOY_USER and start client-manager now?${NC}"
echo -n "Start client-manager? (Y/n): "
read start_manager

if [[ ! "$start_manager" =~ ^[Nn]$ ]]; then
    echo
    echo -e "${GREEN}Switching to $DEPLOY_USER and starting client-manager...${NC}"
    echo
    sleep 1
    # Switch to qbmgr and run client manager
    exec sudo -u "$DEPLOY_USER" bash -c 'cd ~/open-webui/mt && ./client-manager.sh'
else
    echo
    echo -e "${GREEN}Setup complete! You can run client-manager later with:${NC}"
    echo "  sudo -u $DEPLOY_USER bash -c 'cd ~/open-webui/mt && ./client-manager.sh'"
    echo
fi
