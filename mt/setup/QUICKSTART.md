# Quick Droplet Setup - One Command

This is the fastest way to set up a new Digital Ocean droplet with the `qbmgr` user and Open WebUI repository.

## Step 1: Get Your SSH Key

On your local machine:

```bash
cat ~/.ssh/id_rsa.pub
```

Copy the entire output (it should start with `ssh-rsa` or `ssh-ed25519`)

## Step 2: Create Droplet

1. Go to Digital Ocean and create a new droplet
2. Choose **Docker 20.04** one-click image
3. Select your size (minimum 2GB RAM recommended)
4. Create the droplet

## Step 3: Run Setup Command

SSH to your droplet as root and run this ONE command:

```bash
curl -fsSL https://raw.githubusercontent.com/imagicrafter/open-webui/main/mt/setup/quick-setup.sh | bash -s -- "YOUR_SSH_PUBLIC_KEY_HERE"
```

**Replace `YOUR_SSH_PUBLIC_KEY_HERE` with your actual SSH public key from Step 1.**

Example:
```bash
curl -fsSL https://raw.githubusercontent.com/imagicrafter/open-webui/main/mt/setup/quick-setup.sh | bash -s -- "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDl77XDmQLqSPiMynr48sBbEn95w7wse+Y4MYCEyfnkhUAnr3BaJFw34C92F0uJBUDa9PaTKIAkhJhuQtM+st7zkUkeSp9/CPrNVhwkQVWny+B7+kuBGBIgZfdO00W4AUp9O6NF69ABz1WYwpdCpaUKI2FgMv0HKxq7JJ/zXpjDNiTtA2MYSd6yLJ9lmdYscs6RJbUWrOQ3ILcXOn+1CYJvfSdGAaBiHbgMnU4dE1H6V8f/YrJYxDljhhktlm2/H4NZKtG9QX4R7R2hh3PKwDK1cQ8DoQ09B6oZuRbj5sk+kUulOFZz/CCG2JHX+/7ujl322P5BEPloFsFH84TI90egBIu0Of0FLtTzPSnILRcAWx02EDFH65UN7HT+Eb6JtxrkBv+kbPLa5i3v2a3YdeDyZtPbBg5LBBQteGk+ijKQLvhrXhj4VhjBeTD7IyYlSBzfg583nY/XC7zAj2Qkq+xTxNq3Juu8S9zmOjmUbluYcEkGFg8DGp17HYfLCadf/Pc= justinmartin@Justins-MacBook-Pro.local"
```

## Step 4: Exit and SSH as qbmgr

```bash
exit  # Exit root session
ssh qbmgr@YOUR_DROPLET_IP
```

## Step 5: Deploy!

```bash
# Read welcome message
cat ~/WELCOME.txt

# Deploy nginx reverse proxy
cd ~/open-webui/mt/nginx-container
./deploy-nginx-container.sh

# Create/manage clients
cd ~/open-webui/mt
./client-manager.sh
```

## What Gets Set Up

The script automatically:
- ✅ Creates `qbmgr` user with sudo and docker access
- ✅ Adds your SSH key for authentication
- ✅ Clones the Open WebUI repository to `/home/qbmgr/open-webui`
- ✅ Installs useful packages (certbot, jq, htop, tree)
- ✅ Creates `/opt/openwebui-nginx` directory for nginx configs
- ✅ Tests Docker access

## Security Note

Root SSH is still enabled after setup. After you verify qbmgr access works, disable it:

```bash
sudo sed -i 's/^PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl reload sshd
```

## Troubleshooting

### Script fails with "Invalid SSH key format"

Make sure you copied your **public** key (not private key) and it starts with `ssh-rsa` or `ssh-ed25519`.

### Can't SSH as qbmgr

1. Check the key was added correctly:
   ```bash
   # As root
   cat /home/qbmgr/.ssh/authorized_keys
   ```

2. Check permissions:
   ```bash
   ls -la /home/qbmgr/.ssh/
   ```
   Should show `drwx------` (700) for directory and `-rw-------` (600) for authorized_keys

### Docker permission denied

Logout and login again, or run:
```bash
newgrp docker
docker ps
```

## Full Documentation

See `mt/setup/README.md` for detailed documentation on all setup methods and configuration options.
