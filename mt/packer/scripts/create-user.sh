#!/bin/bash
# Create deployment user and set up Open WebUI repository
# Called by Packer during image build

set -euo pipefail

echo "=== Creating deployment user: $DEPLOY_USER ==="

# Create user if doesn't exist
if ! id "$DEPLOY_USER" &>/dev/null; then
    useradd -m -s /bin/bash "$DEPLOY_USER"
    echo "User $DEPLOY_USER created"
else
    echo "User $DEPLOY_USER already exists"
fi

# Add to groups
usermod -aG sudo "$DEPLOY_USER"
usermod -aG docker "$DEPLOY_USER"
echo "Added to sudo and docker groups"

# Configure passwordless sudo
echo "$DEPLOY_USER ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/$DEPLOY_USER"
chmod 0440 "/etc/sudoers.d/$DEPLOY_USER"
echo "Passwordless sudo configured"

# Create .ssh directory (SSH keys added per-droplet)
mkdir -p "/home/$DEPLOY_USER/.ssh"
chmod 700 "/home/$DEPLOY_USER/.ssh"
chown -R "$DEPLOY_USER:$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh"
echo "SSH directory created (keys added per-droplet)"

# Clone Open WebUI repository
echo "=== Cloning Open WebUI repository ==="
REPO_PATH="/home/$DEPLOY_USER/open-webui"

if [ -d "$REPO_PATH" ]; then
    echo "Repository already exists at $REPO_PATH"
    sudo -u "$DEPLOY_USER" git -C "$REPO_PATH" pull
else
    sudo -u "$DEPLOY_USER" git clone -b "${REPO_BRANCH:-main}" "$REPO_URL" "$REPO_PATH"
    echo "Repository cloned to $REPO_PATH"
fi

# Create common directories
echo "=== Creating common directories ==="
mkdir -p /opt/openwebui-nginx
chown -R "$DEPLOY_USER:$DEPLOY_USER" /opt/openwebui-nginx
echo "Created /opt/openwebui-nginx"

# Create welcome message
cat > "/home/$DEPLOY_USER/WELCOME.txt" << EOF
╔════════════════════════════════════════════════════════════╗
║          Open WebUI Deployment Server Ready                ║
╚════════════════════════════════════════════════════════════╝

Your server is configured and ready for Open WebUI deployment!

This is a golden image - SSH key needs to be added on first boot.

Quick Start:
1. Add your SSH key (as root):
   echo "YOUR_SSH_PUBLIC_KEY" > /home/$DEPLOY_USER/.ssh/authorized_keys
   chown $DEPLOY_USER:$DEPLOY_USER /home/$DEPLOY_USER/.ssh/authorized_keys
   chmod 600 /home/$DEPLOY_USER/.ssh/authorized_keys

2. SSH as $DEPLOY_USER: ssh $DEPLOY_USER@YOUR_DROPLET_IP

3. Deploy nginx: cd ~/open-webui/mt/nginx-container
   ./deploy-nginx-container.sh

4. Create client: cd ~/open-webui/mt && ./client-manager.sh

Repository: ~/open-webui
User: $DEPLOY_USER (sudo + docker access)
nginx: Pre-deployed (openwebui-nginx container)

Documentation:
- Quick Start: ~/open-webui/mt/QUICKSTART-FRESH-DEPLOYMENT.md
- nginx Setup: ~/open-webui/mt/nginx-container/README.md

Image Info: cat /etc/open-webui-image-info.txt
EOF

chown "$DEPLOY_USER:$DEPLOY_USER" "/home/$DEPLOY_USER/WELCOME.txt"
echo "Welcome message created"

# Test Docker access
echo "=== Testing Docker access ==="
if sudo -u "$DEPLOY_USER" docker ps > /dev/null 2>&1; then
    echo "Docker access verified for $DEPLOY_USER"
else
    echo "WARNING: Docker access not working, may need reboot"
fi

echo "=== User setup complete ==="
