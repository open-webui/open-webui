# Secure Deployment User Setup

This directory contains tools for creating a secure, dedicated deployment user (`qbmgr`) on your Digital Ocean droplet instead of using root for deployments.

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

## Quick Setup (One Command) ⭐

This is the simplest and most reliable method. Just login as root and run a single command.

### Steps

1. **Get your SSH public key** on your local machine:

   ```bash
   cat ~/.ssh/id_rsa.pub
   # or
   cat ~/.ssh/id_ed25519.pub
   ```

   Copy the entire output (starts with `ssh-rsa` or `ssh-ed25519`)

2. **Create Digital Ocean Droplet**

   - Go to Digital Ocean → Create → Droplets
   - Choose **Docker 20.04** one-click image
   - Select size (minimum 2GB RAM)
   - Create droplet

3. **SSH as root and run setup**

   ```bash
   ssh root@YOUR_DROPLET_IP

   # Run the setup script with your SSH key
   curl -fsSL https://raw.githubusercontent.com/imagicrafter/open-webui/main/mt/setup/quick-setup.sh | bash -s -- "YOUR_SSH_PUBLIC_KEY"
   ```

   Replace `YOUR_SSH_PUBLIC_KEY` with your actual public key from step 1.

   **Example:**
   ```bash
   curl -fsSL https://raw.githubusercontent.com/imagicrafter/open-webui/main/mt/setup/quick-setup.sh | bash -s -- "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ... user@host"
   ```

4. **Exit and SSH as qbmgr**

   ```bash
   exit  # Exit root session
   ssh qbmgr@YOUR_DROPLET_IP
   ```

5. **Start deploying**

   ```bash
   cat ~/WELCOME.txt  # Read welcome message
   cd ~/open-webui/mt/nginx-container
   ./deploy-nginx-container.sh
   ```

### What Gets Set Up

The script automatically:
- ✅ Creates `qbmgr` user with sudo and docker access
- ✅ Configures passwordless sudo for convenience
- ✅ Adds your SSH key for authentication
- ✅ Clones the Open WebUI repository to `/home/qbmgr/open-webui`
- ✅ Creates `/opt/openwebui-nginx` directory
- ✅ Installs useful packages (certbot, jq, htop, tree, net-tools)
- ✅ Tests Docker access

### User Configuration

**Username:** `qbmgr`

**Permissions:**
- Member of `sudo` group (can run commands as root when needed)
- Member of `docker` group (can run Docker without sudo)
- Passwordless sudo enabled (convenient for automation)

**Home Directory:** `/home/qbmgr/`

**Repository Location:** `/home/qbmgr/open-webui/`

### Directory Structure After Setup

```
/home/qbmgr/
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

## Security Recommendations

### 1. Disable Root SSH Login ⭐ Important

After confirming the qbmgr user works, disable root SSH access:

```bash
sudo sed -i 's/^PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl reload sshd
```

**IMPORTANT:** Test qbmgr access first before disabling root SSH!

### 2. Use SSH Keys (Not Passwords)

The setup script configures SSH key authentication. Never use password authentication for production servers.

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

The qbmgr user has Docker access (no sudo required). This is necessary for deployment but means:
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
sudo cat /home/qbmgr/.bash_history

# View Docker events
docker events --since 24h

# Check sudo usage
sudo cat /var/log/auth.log | grep sudo
```

## Comparison: Root vs qbmgr User

| Aspect | Root User | qbmgr User |
|--------|-----------|---------------|
| **Security** | ❌ High risk | ✅ Lower risk |
| **Privilege** | Unlimited | Limited to sudo/docker |
| **Audit Trail** | Harder to track | Clear user attribution |
| **Recovery** | If compromised, rebuild | Disable user, system intact |
| **Best Practice** | ❌ Not recommended | ✅ Industry standard |
| **Team Use** | ❌ No accountability | ✅ Per-user accounts |
| **SSH Access** | Should be disabled | ✅ Allowed |

## Troubleshooting

### Can't SSH as qbmgr

**Check SSH key:**
```bash
# On your local machine
ssh-add -l

# On the server (as root)
cat /home/qbmgr/.ssh/authorized_keys
```

Ensure they match.

**Check permissions:**
```bash
# As root
ls -la /home/qbmgr/.ssh/
# Should be: drwx------ (700)

ls -la /home/qbmgr/.ssh/authorized_keys
# Should be: -rw------- (600)
```

### Docker permission denied

The qbmgr user needs to logout and login again (or run `newgrp docker`):

```bash
# Test Docker access
docker ps

# If permission denied:
newgrp docker
# Then test again
docker ps
```

### Script fails with "Invalid SSH key format"

Make sure you copied your **public** key (not private key) and it starts with `ssh-rsa`, `ssh-ed25519`, or `ecdsa-sha2-nistp256`.

### Repository already exists

If you run the script multiple times, it will pull the latest changes if the repo already exists.

## Integration with Deployment Scripts

All deployment scripts work seamlessly with the qbmgr user:

```bash
# As qbmgr user
cd ~/open-webui/mt/nginx-container
./deploy-nginx-container.sh  # Works without sudo

cd ~/open-webui/mt
./client-manager.sh  # Interactive menu works

# Scripts automatically detect user and adjust paths
```

Scripts use `sudo` internally only when needed (e.g., copying nginx configs to `/opt/`).

## Quick Reference

### After Setup

**Login:**
```bash
ssh qbmgr@YOUR_DROPLET_IP
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

- **`quick-setup.sh`** - Non-interactive setup script (one command)
- **`QUICKSTART.md`** - Quick reference guide with copy/paste commands
- **`README.md`** - This file (full documentation)

## Additional Resources

- [Digital Ocean Docker Droplets](https://www.digitalocean.com/community/tutorials/how-to-use-the-digitalocean-docker-application)
- [Docker Post-Install Steps](https://docs.docker.com/engine/install/linux-postinstall/)
- [SSH Key Authentication](https://www.digitalocean.com/community/tutorials/how-to-set-up-ssh-keys-2)
- [Ubuntu Server Security](https://ubuntu.com/server/docs/security-introduction)

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify SSH key configuration
3. Check Docker group membership: `groups qbmgr`
4. Review script output for error messages

---

**For the fastest setup:** See `QUICKSTART.md` for a simplified copy/paste guide.
