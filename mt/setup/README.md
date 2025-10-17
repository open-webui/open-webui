# Secure Deployment User Setup

This directory contains tools for creating a secure, dedicated deployment user on your Digital Ocean droplet instead of using root for deployments.

## Why Use a Dedicated User?

### Security Best Practices

**Problems with using root:**
- ❌ Unlimited system privileges (violates principle of least privilege)
- ❌ If compromised, attacker has full system access
- ❌ Harder to audit and track actions
- ❌ Accidental commands can damage the entire system
- ❌ Many security guides recommend disabling root SSH entirely

**Benefits of dedicated deployment user:**
- ✅ Limited privileges (sudo only when needed)
- ✅ Better isolation and containment
- ✅ Clear audit trail of deployment actions
- ✅ Can be easily disabled/removed if compromised
- ✅ Follows industry best practices
- ✅ Safer for team environments

### Recommended for Production

For production deployments, **always use a dedicated user** with appropriate permissions rather than root.

## Setup Methods

### Method 1: Cloud-Init (Automated During Droplet Creation) ⭐ Recommended

Use this method when creating a **new** Digital Ocean droplet. The user is created automatically during first boot.

**Advantages:**
- Fully automated
- Zero manual steps after droplet creation
- Repository pre-cloned
- Root SSH automatically disabled
- Ready to deploy immediately

**Steps:**

1. **Prepare the cloud-init file**

   Edit `cloud-init-user-data.yaml` and replace `YOUR_SSH_PUBLIC_KEY_HERE` with your actual SSH public key:

   ```bash
   # Get your SSH public key
   cat ~/.ssh/id_rsa.pub  # or id_ed25519.pub
   ```

   Copy the output and paste it into the cloud-init file.

2. **Create Digital Ocean Droplet**

   - Go to Digital Ocean → Create → Droplets
   - Choose **Docker 20.04** one-click image
   - Select size (minimum 2GB RAM)
   - Scroll down to **Advanced Options**
   - Check **"Add Initialization scripts (free)"**
   - Paste the **entire contents** of `cloud-init-user-data.yaml`
   - Create droplet

3. **Wait for initialization** (2-3 minutes)

   Cloud-init runs on first boot. The droplet will:
   - Create user `deployer`
   - Add to sudo and docker groups
   - Clone Open WebUI repository
   - Install certbot, jq, htop, tree
   - Disable root SSH login

4. **SSH as deployer**

   ```bash
   ssh deployer@YOUR_DROPLET_IP
   ```

   You should see a welcome message. Root SSH is disabled for security.

5. **Start deploying**

   ```bash
   cat ~/WELCOME.txt  # Read welcome message
   cd ~/open-webui/mt/nginx-container
   ./deploy-nginx-container.sh
   ```

### Method 2: Manual Setup (For Existing Droplets)

Use this method if you already have a running droplet or prefer manual setup.

**Steps:**

1. **SSH as root**

   ```bash
   ssh root@YOUR_DROPLET_IP
   ```

2. **Download and run setup script**

   ```bash
   # Clone repository if not already done
   git clone https://github.com/imagicrafter/open-webui.git
   cd open-webui/mt/setup

   # Make script executable
   chmod +x create-deployment-user.sh

   # Run the setup script
   sudo ./create-deployment-user.sh
   ```

   Or download and run directly:

   ```bash
   curl -fsSL https://raw.githubusercontent.com/imagicrafter/open-webui/main/mt/setup/create-deployment-user.sh | sudo bash
   ```

3. **Follow interactive prompts**

   The script will ask:
   - Passwordless sudo? (Recommended: Yes)
   - SSH key setup method (Recommended: Copy from root)
   - Install packages? (Recommended: Yes)
   - Disable root SSH? (Recommended: Test first, then yes)

4. **Test SSH access**

   Open a **new terminal** (keep your root session open):

   ```bash
   ssh deployer@YOUR_DROPLET_IP
   ```

   Verify you can access the droplet and run Docker:

   ```bash
   docker ps
   cat ~/WELCOME.txt
   ```

5. **Disable root SSH** (if not done during setup)

   Once you've confirmed the deployer user works:

   ```bash
   # As root
   sudo sed -i 's/^PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
   sudo systemctl reload sshd
   ```

## User Configuration Details

### Created User

**Username:** `deployer` (configurable via `DEPLOY_USER` environment variable)

**Permissions:**
- Member of `sudo` group (can run commands as root when needed)
- Member of `docker` group (can run Docker without sudo)
- Optional: Passwordless sudo (convenient for automation)

**Home Directory:** `/home/deployer/`

**Repository Location:** `/home/deployer/open-webui/`

### Directory Structure

```
/home/deployer/
├── open-webui/              # Git repository
│   └── mt/
│       ├── nginx-container/
│       ├── client-manager.sh
│       └── ...
├── WELCOME.txt              # Quick reference guide
└── .ssh/
    └── authorized_keys      # Your SSH public key

/opt/openwebui-nginx/        # nginx container configs
├── conf.d/                  # Site configurations
├── nginx.conf               # Main nginx config
└── webroot/                 # Let's Encrypt webroot
```

## Customization

### Change Username

**Cloud-Init Method:**

Edit `cloud-init-user-data.yaml` and change:
```yaml
users:
  - name: myuser  # Change from 'deployer' to your preference
```

**Manual Method:**

Set environment variable before running:
```bash
DEPLOY_USER=myuser sudo -E ./create-deployment-user.sh
```

### Use Existing SSH Key

The cloud-init and manual scripts both support adding your SSH key so you can login immediately.

**Find your SSH public key:**
```bash
cat ~/.ssh/id_rsa.pub
# or
cat ~/.ssh/id_ed25519.pub
```

**Add to cloud-init:**
```yaml
ssh_authorized_keys:
  - ssh-rsa AAAAB3... your-email@example.com
```

**Add manually:**
```bash
# As root, after user is created
mkdir -p /home/deployer/.ssh
echo "ssh-rsa AAAAB3... your-email@example.com" > /home/deployer/.ssh/authorized_keys
chown -R deployer:deployer /home/deployer/.ssh
chmod 700 /home/deployer/.ssh
chmod 600 /home/deployer/.ssh/authorized_keys
```

## Security Recommendations

### 1. Disable Root SSH Login ⭐ Important

After confirming the deployer user works:

```bash
# Edit SSH config
sudo nano /etc/ssh/sshd_config

# Set this line:
PermitRootLogin no

# Reload SSH
sudo systemctl reload sshd
```

### 2. Use SSH Keys (Not Passwords)

Both setup methods configure SSH key authentication. Never use password authentication for production servers.

### 3. Configure Firewall

```bash
# Allow SSH, HTTP, HTTPS only
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

### 4. Keep System Updated

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

### 5. Monitor Docker Access

The deployer user has Docker access (no sudo required). This is necessary for deployment but means:
- User can run any container
- User can mount any host path into containers
- User effectively has root-equivalent access via Docker

**For multi-user environments:**
- Create separate deployment users per person
- Use Docker socket proxies for fine-grained access control
- Consider using Docker's authorization plugins

### 6. Audit Logs

Monitor deployment activity:

```bash
# View user's command history
sudo cat /home/deployer/.bash_history

# View Docker events
docker events --since 24h

# Check sudo usage
sudo cat /var/log/auth.log | grep sudo
```

## Comparison: Root vs Deployer User

| Aspect | Root User | Deployer User |
|--------|-----------|---------------|
| **Security** | ❌ High risk | ✅ Lower risk |
| **Privilege** | Unlimited | Limited to sudo/docker |
| **Audit Trail** | Harder to track | Clear user attribution |
| **Recovery** | If compromised, rebuild | Disable user, system intact |
| **Best Practice** | ❌ Not recommended | ✅ Industry standard |
| **Team Use** | ❌ No accountability | ✅ Per-user accounts |
| **SSH Access** | Should be disabled | ✅ Allowed |

## Troubleshooting

### Can't SSH as deployer

**Check SSH key:**
```bash
# On your local machine
ssh-add -l

# On the server (as root)
cat /home/deployer/.ssh/authorized_keys
```

Ensure they match.

**Check permissions:**
```bash
# As root
ls -la /home/deployer/.ssh/
# Should be: drwx------ (700)

ls -la /home/deployer/.ssh/authorized_keys
# Should be: -rw------- (600)
```

### Docker permission denied

The deployer user needs to logout and login again (or run `newgrp docker`):

```bash
# Test Docker access
docker ps

# If permission denied:
newgrp docker
# Then test again
docker ps
```

### Sudo requires password

If you chose not to enable passwordless sudo, you'll need to enter the deployer user's password.

To enable passwordless sudo later:
```bash
# As root
echo "deployer ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/deployer
chmod 0440 /etc/sudoers.d/deployer
```

## Integration with Deployment Scripts

All deployment scripts work seamlessly with the deployer user:

```bash
# As deployer user
cd ~/open-webui/mt/nginx-container
./deploy-nginx-container.sh  # Works without sudo

cd ~/open-webui/mt
./client-manager.sh  # Interactive menu works

# Scripts automatically detect user and adjust paths
```

Scripts use `sudo` internally only when needed (e.g., copying nginx configs to `/opt/`).

## Migration from Root to Deployer

If you've been using root and want to migrate:

1. **Create deployer user** (use Method 2 above)

2. **Copy Docker volumes** (optional - volumes are global)
   ```bash
   # No action needed - Docker volumes are system-wide
   ```

3. **Copy nginx configs**
   ```bash
   sudo cp -r /opt/openwebui-nginx /opt/openwebui-nginx.backup
   sudo chown -R deployer:deployer /opt/openwebui-nginx
   ```

4. **Update paths in documentation**
   ```bash
   # Change from:
   cd /root/open-webui

   # To:
   cd ~/open-webui
   # or
   cd /home/deployer/open-webui
   ```

5. **Test everything as deployer**

6. **Disable root SSH**

## Quick Reference

### After Setup

**Login:**
```bash
ssh deployer@YOUR_DROPLET_IP
```

**Deploy nginx:**
```bash
cd ~/open-webui/mt/nginx-container
./deploy-nginx-container.sh
```

**Create client:**
```bash
cd ~/open-webui/mt
./client-manager.sh
```

**Update repository:**
```bash
cd ~/open-webui
git pull
```

**View running containers:**
```bash
docker ps
```

**Check nginx logs:**
```bash
docker logs -f openwebui-nginx
```

## Files in This Directory

- **`cloud-init-user-data.yaml`** - Cloud-init script for automated setup during droplet creation
- **`create-deployment-user.sh`** - Interactive script for manual setup on existing droplets
- **`README.md`** - This file

## Additional Resources

- [Digital Ocean Cloud-Init Docs](https://docs.digitalocean.com/products/droplets/how-to/provide-user-data/)
- [Docker Post-Install Steps](https://docs.docker.com/engine/install/linux-postinstall/)
- [SSH Key Authentication](https://www.digitalocean.com/community/tutorials/how-to-set-up-ssh-keys-2)
- [Ubuntu Server Security](https://ubuntu.com/server/docs/security-introduction)

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify SSH key configuration
3. Check Docker group membership: `groups deployer`
4. Review cloud-init logs: `sudo cat /var/log/cloud-init-output.log`

---

**Recommendation:** Use Method 1 (Cloud-Init) for new deployments. It's fully automated and follows all security best practices out of the box.
