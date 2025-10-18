# CLI Automation for Client Deployments

Complete command-line automation for deploying Open WebUI instances for clients across multiple Digital Ocean accounts - **no console access required**.

## Overview

This workflow allows you to:
- ✅ Build golden images via CLI
- ✅ Deploy droplets programmatically
- ✅ Configure client instances remotely
- ✅ Manage multiple Digital Ocean accounts
- ✅ Complete deployments in under 5 minutes
- ✅ Zero manual console clicks

## Prerequisites

### 1. Install Tools

```bash
# On macOS
brew install hashicorp/tap/packer
brew install doctl

# Verify installations
packer version
doctl version
```

### 2. Authenticate Digital Ocean CLI

```bash
# For primary account
doctl auth init
# Paste your DO API token

# For multiple accounts (use contexts)
doctl auth init --context client-account-1
doctl auth init --context client-account-2

# Switch between accounts
doctl auth switch --context client-account-1
```

### 3. Add SSH Keys to Digital Ocean

```bash
# List your local SSH keys
ls -la ~/.ssh/*.pub

# Add to Digital Ocean
doctl compute ssh-key import my-key --public-key-file ~/.ssh/id_rsa.pub

# Verify
doctl compute ssh-key list
```

## Workflow

### Step 1: Build Golden Image (One Time Per Account)

Build the golden image in your Digital Ocean account:

```bash
cd ~/github/open-webui/mt/packer

# Interactive mode (prompts for settings)
./build.sh

# Or fully automated
export DIGITALOCEAN_TOKEN="your-token"
./build.sh <<EOF


s-2vcpu-4gb
main
Y
EOF
```

**Build time:** ~8-10 minutes

**Result:** Custom image `open-webui-multitenant-YYYY-MM-DD-HHMM` appears in your account

**For multiple DO accounts:**
```bash
# Build in Account 1
doctl auth switch --context account-1
./build.sh

# Build in Account 2
doctl auth switch --context account-2
./build.sh

# Build in Account 3
doctl auth switch --context account-3
./build.sh
```

Each account now has an identical golden image!

### Step 2: Deploy Clients (Automated)

Three deployment options depending on your needs:

#### Option A: Full Automation (Recommended)

**One command to create droplet + deploy Open WebUI:**

```bash
# Basic deployment
./full-client-setup.sh acme-corp chat.acme.com

# With custom size and region
./full-client-setup.sh beta-client beta.example.com s-4vcpu-8gb sfo3
```

**What this does:**
1. Creates droplet from golden image
2. Waits for boot + SSH ready
3. Deploys Open WebUI container
4. Configures nginx reverse proxy
5. Saves deployment info

**Time:** ~3-4 minutes

**Output:**
```
✅ CLIENT SETUP COMPLETE!

Droplet Information:
  Name:      webui-acme-corp
  IP:        167.99.123.45
  Domain:    chat.acme.com

Next Steps:
  1. Point DNS: chat.acme.com → 167.99.123.45
  2. Setup SSL (after DNS propagates)
```

#### Option B: Droplet Creation Only

**Just create the droplet, deploy containers manually:**

```bash
./deploy-from-image.sh acme-corp
```

Interactive prompts for size, region, SSH keys.

Then SSH in and deploy:
```bash
ssh qbmgr@DROPLET_IP
cd ~/open-webui/mt
./client-manager.sh
```

#### Option C: Manual doctl Commands

**Full control with raw doctl:**

```bash
# 1. Find image ID
doctl compute image list --public=false | grep open-webui-multitenant

# 2. Get SSH key IDs
doctl compute ssh-key list

# 3. Create droplet
doctl compute droplet create webui-client1 \
  --image 123456789 \
  --size s-2vcpu-4gb \
  --region nyc3 \
  --ssh-keys 12345,67890 \
  --tag-name openwebui \
  --wait

# 4. Get IP address
doctl compute droplet list webui-client1

# 5. Deploy via SSH
ssh qbmgr@DROPLET_IP 'cd ~/open-webui/mt && ./start-template.sh "client1" "chat.client1.com"'
```

### Step 3: SSL Setup (Semi-Manual)

After DNS propagates, setup SSL:

```bash
# Method 1: SSH and use menu
ssh qbmgr@DROPLET_IP
cd ~/open-webui/mt
./client-manager.sh
# Select: Setup SSL Certificate → Enter domain

# Method 2: Remote command
ssh qbmgr@DROPLET_IP 'docker exec openwebui-nginx certbot --nginx -d chat.acme.com --non-interactive --agree-tos --email admin@acme.com'
```

## Multi-Account Client Deployments

### Scenario: Deploy for 3 different clients, each in their own DO account

```bash
# Client 1: ACME Corp (Account A)
doctl auth switch --context acme-corp-account
./full-client-setup.sh acme-corp chat.acme.com

# Client 2: Beta Industries (Account B)
doctl auth switch --context beta-account
./full-client-setup.sh beta-industries chat.beta.com s-4vcpu-8gb

# Client 3: Gamma LLC (Account C)
doctl auth switch --context gamma-account
./full-client-setup.sh gamma-llc gamma.example.com
```

**Total time:** ~12-15 minutes for all 3 clients!

## Deployment Tracking

All deployments are automatically tracked in `deployments/` directory:

```bash
# View deployment info
cat deployments/acme-corp.txt

# List all deployments
ls -la deployments/

# Get droplet IP
grep "IP Address" deployments/acme-corp.txt
```

Example deployment file:
```
Client: acme-corp
Domain: chat.acme.com
Droplet Name: webui-acme-corp
Droplet ID: 123456789
IP Address: 167.99.123.45
Image: open-webui-multitenant-2025-10-17-0315
Size: s-2vcpu-4gb
Region: nyc3
Created: Thu Oct 17 15:32:10 UTC 2025

Next Steps:
  1. Point DNS: chat.acme.com -> 167.99.123.45
  2. Setup SSL: ssh qbmgr@167.99.123.45 'cd ~/open-webui/mt && ./client-manager.sh'
```

## Managing Multiple Digital Ocean Accounts

### Setup Named Contexts

```bash
# Add accounts with descriptive names
doctl auth init --context personal
doctl auth init --context acme-corp
doctl auth init --context beta-client
doctl auth init --context gamma-llc

# List contexts
doctl auth list

# Switch between accounts
doctl auth switch --context acme-corp

# Check current account
doctl account get
```

### Build Images in All Accounts

```bash
#!/bin/bash
# build-all-accounts.sh

ACCOUNTS=("personal" "acme-corp" "beta-client" "gamma-llc")

for account in "${ACCOUNTS[@]}"; do
  echo "Building image for: $account"
  doctl auth switch --context $account

  cd ~/github/open-webui/mt/packer
  ./build.sh <<EOF


s-2vcpu-2gb
main
Y
EOF

  echo "✓ Image built for $account"
  echo
done

echo "✅ All accounts have golden images!"
```

## Advanced Automation

### Bulk Client Deployment Script

```bash
#!/bin/bash
# deploy-multiple-clients.sh

# clients.csv format: account_context,client_name,domain,size,region
# Example:
# acme-account,acme-corp,chat.acme.com,s-2vcpu-4gb,nyc3
# beta-account,beta-ind,beta.example.com,s-4vcpu-8gb,sfo3

while IFS=',' read -r context client domain size region; do
  echo "Deploying: $client"

  doctl auth switch --context "$context"

  cd ~/github/open-webui/mt/packer
  ./full-client-setup.sh "$client" "$domain" "$size" "$region" <<EOF
Y
EOF

  echo "✓ $client deployed"
  echo "---"
done < clients.csv

echo "✅ All clients deployed!"
```

Usage:
```bash
# Create clients.csv
cat > clients.csv <<EOF
acme-account,acme-corp,chat.acme.com,s-2vcpu-4gb,nyc3
beta-account,beta-ind,beta.example.com,s-4vcpu-8gb,sfo3
gamma-account,gamma-llc,gamma.chat.io,s-2vcpu-4gb,lon1
EOF

# Deploy all at once
./deploy-multiple-clients.sh
```

### Monitoring and Management

```bash
# List all Open WebUI droplets across all accounts
for context in $(doctl auth list --format Account --no-header); do
  echo "=== $context ==="
  doctl auth switch --context $context
  doctl compute droplet list --tag-name openwebui
  echo
done

# Get resource usage summary
doctl compute droplet list --tag-name openwebui --format Name,Memory,Disk,VCPUs,Region,Status

# Check specific client
doctl compute droplet get webui-acme-corp
```

### Backup and Snapshots

```bash
# Create snapshot of a client deployment
doctl compute droplet-action snapshot DROPLET_ID \
  --snapshot-name "acme-corp-backup-$(date +%Y%m%d)"

# List snapshots
doctl compute snapshot list

# Restore from snapshot
doctl compute droplet create webui-acme-corp-restored \
  --image SNAPSHOT_ID \
  --size s-2vcpu-4gb \
  --region nyc3
```

## Troubleshooting

### SSH Connection Issues

```bash
# Test SSH connectivity
ssh -o ConnectTimeout=10 qbmgr@DROPLET_IP "echo 'Connected'"

# Check droplet status
doctl compute droplet get DROPLET_ID

# View droplet console (emergency access)
# This opens browser - only option for console access
doctl compute droplet console DROPLET_ID
```

### Deployment Failures

```bash
# Check container status remotely
ssh qbmgr@DROPLET_IP 'docker ps -a'

# View container logs
ssh qbmgr@DROPLET_IP 'docker logs openwebui-CONTAINER_NAME'

# Check nginx status
ssh qbmgr@DROPLET_IP 'docker logs openwebui-nginx'

# Re-run deployment
ssh qbmgr@DROPLET_IP 'cd ~/open-webui/mt && ./start-template.sh "client-name" "domain.com"'
```

### Cleanup Failed Deployments

```bash
# Delete droplet
doctl compute droplet delete DROPLET_ID

# Or by name
doctl compute droplet delete webui-client-name

# Delete with volumes
doctl compute droplet delete DROPLET_ID --delete-volumes
```

## Cost Optimization

### Right-Sizing Droplets

```bash
# Start small, resize later if needed
./full-client-setup.sh client1 chat.client1.com s-1vcpu-2gb

# Resize later (requires droplet power-off)
doctl compute droplet-action power-off DROPLET_ID
doctl compute droplet-action resize DROPLET_ID --size s-2vcpu-4gb
doctl compute droplet-action power-on DROPLET_ID
```

### Region Selection for Cost

```bash
# View pricing by region (all regions same price, but check transfer costs)
doctl compute region list

# Deploy to cheapest region with good connectivity to client
./full-client-setup.sh client1 chat.client1.com s-2vcpu-4gb tor1  # Toronto
./full-client-setup.sh client2 chat.client2.com s-2vcpu-4gb sfo3  # San Francisco
```

## Security Best Practices

### 1. Separate API Tokens Per Client Account

```bash
# Create restricted token per account
# Give only required permissions:
# - droplet (read/write)
# - image (read)
# - ssh_key (read)
# - tag (read/write)

# Use token only for that account
doctl auth init --context client1 --access-token CLIENT1_TOKEN
```

### 2. Rotate SSH Keys Regularly

```bash
# Generate new key for client
ssh-keygen -t ed25519 -f ~/.ssh/client1_key -C "client1@example.com"

# Add to DO
doctl compute ssh-key import client1-key --public-key-file ~/.ssh/client1_key.pub

# Deploy with specific key
doctl compute droplet create ... --ssh-keys $(doctl compute ssh-key list --format ID --no-header | grep client1)
```

### 3. Enable Firewall Rules

```bash
# Create firewall
doctl compute firewall create \
  --name openwebui-firewall \
  --inbound-rules "protocol:tcp,ports:22,sources:addresses:YOUR_IP protocol:tcp,ports:80,sources:addresses:0.0.0.0/0,::/0 protocol:tcp,ports:443,sources:addresses:0.0.0.0/0,::/0" \
  --outbound-rules "protocol:tcp,ports:all,destinations:addresses:0.0.0.0/0,::/0"

# Apply to droplets
doctl compute firewall add-droplets FIREWALL_ID --droplet-ids DROPLET_ID
```

## Complete Example: New Client Onboarding

```bash
#!/bin/bash
# Complete client onboarding workflow

CLIENT="acme-corp"
DOMAIN="chat.acme.com"
ACCOUNT_CONTEXT="acme-do-account"
SIZE="s-2vcpu-4gb"
REGION="nyc3"

echo "🚀 Onboarding new client: $CLIENT"

# 1. Switch to client's DO account
echo "Switching to client account..."
doctl auth switch --context $ACCOUNT_CONTEXT

# 2. Check if golden image exists, build if not
if ! doctl compute image list --public=false | grep -q "open-webui-multitenant"; then
  echo "Building golden image..."
  cd ~/github/open-webui/mt/packer
  ./build.sh <<EOF


$SIZE
main
Y
EOF
fi

# 3. Deploy complete setup
echo "Deploying infrastructure..."
./full-client-setup.sh "$CLIENT" "$DOMAIN" "$SIZE" "$REGION" <<EOF
Y
EOF

# 4. Get droplet IP
DROPLET_IP=$(doctl compute droplet list webui-$CLIENT --format PublicIPv4 --no-header)

# 5. Send client setup instructions
cat > "client-instructions-${CLIENT}.txt" <<EOF
Welcome to Your Open WebUI Instance!

Your server is ready at: $DROPLET_IP

Next Steps:
1. Configure DNS:
   Add an A record for $DOMAIN pointing to $DROPLET_IP

2. After DNS propagates (check with: dig $DOMAIN), email us to setup SSL

3. Once SSL is configured, access your instance:
   https://$DOMAIN

Support: support@yourcompany.com
EOF

echo "✅ Client onboarding complete!"
echo "📧 Client instructions: client-instructions-${CLIENT}.txt"
echo "📊 Deployment details: deployments/${CLIENT}.txt"
```

Save as `onboard-client.sh`, make executable, and use:
```bash
./onboard-client.sh
```

---

**You now have complete CLI automation for client deployments - zero console clicks required!** 🎉
