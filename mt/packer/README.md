# Packer - Automated Golden Image Builder

This directory contains Packer templates for building **Digital Ocean custom images** that can be deployed across multiple accounts.

## What is This?

Creates a "golden image" that includes:
- ✅ Ubuntu 22.04 with Docker
- ✅ `qbmgr` user (sudo + docker access)
- ✅ Open WebUI repository pre-cloned
- ✅ nginx container pre-deployed
- ✅ All tools and packages installed
- ❌ **NO** SSH keys (added per-droplet)
- ❌ **NO** client deployments (added per-droplet)
- ❌ **NO** SSL certificates (added per-droplet)

**Result:** Deploy new droplets in **60 seconds** instead of 5+ minutes!

## Prerequisites

### 1. Install Packer

**macOS:**
```bash
brew tap hashicorp/tap
brew install hashicorp/tap/packer
```

**Linux:**
```bash
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
sudo apt-get update && sudo apt-get install packer
```

**Windows:**
```bash
choco install packer
```

**Verify installation:**
```bash
packer version
# Should show: Packer v1.9.x or newer
```

### 2. Get Digital Ocean API Token

1. Go to: https://cloud.digitalocean.com/account/api/tokens
2. Click **"Generate New Token"**
3. Name: `Packer Image Builder`
4. Scopes: **Read** and **Write**
5. Copy the token (you'll need it below)

## Quick Start

### Build Image in Your Account

```bash
# 1. Navigate to packer directory
cd mt/packer

# 2. Set your DO API token
export DIGITALOCEAN_TOKEN="your-token-here"

# 3. Build the image
packer build open-webui-image.pkr.hcl
```

**Build time:** 5-8 minutes

**Output:**
```
==> Builds finished. The artifacts of successful builds are:
--> digitalocean.open-webui: A snapshot was created: 'open-webui-multitenant-2025-10-18-0315' (ID: 123456789) in regions 'nyc3'
```

The custom image will appear in your Digital Ocean dashboard under **Images** → **Custom Images**.

### Build in Multiple Accounts

For each Digital Ocean account:

```bash
# Account A
export DIGITALOCEAN_TOKEN="account-a-token"
packer build open-webui-image.pkr.hcl

# Account B
export DIGITALOCEAN_TOKEN="account-b-token"
packer build open-webui-image.pkr.hcl

# Account C
export DIGITALOCEAN_TOKEN="account-c-token"
packer build open-webui-image.pkr.hcl
```

Each account gets an identical custom image!

## Configuration

### Using Variables

Create `variables.auto.pkrvars.hcl` (not tracked in git):

```hcl
do_token    = "your-digital-ocean-token"
image_name  = "my-company-open-webui"
region      = "sfo3"
size        = "s-2vcpu-4gb"
repo_branch = "main"
```

Then build:
```bash
packer build open-webui-image.pkr.hcl
# Automatically loads variables.auto.pkrvars.hcl
```

### Available Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `do_token` | `$DIGITALOCEAN_TOKEN` | DO API token |
| `image_name` | `open-webui-multitenant` | Name prefix for image |
| `region` | `nyc3` | Build region |
| `size` | `s-2vcpu-2gb` | Build droplet size |
| `repo_url` | `https://github.com/imagicrafter/open-webui.git` | Repository URL |
| `repo_branch` | `main` | Branch to clone |

### Override Variables

```bash
# Build with different branch
packer build -var "repo_branch=develop" open-webui-image.pkr.hcl

# Custom image name
packer build -var "image_name=acme-corp-webui" open-webui-image.pkr.hcl

# Build in different region
packer build -var "region=sfo3" open-webui-image.pkr.hcl

# Combine multiple variables
packer build \
  -var "image_name=prod-webui" \
  -var "region=sfo3" \
  -var "size=s-2vcpu-4gb" \
  open-webui-image.pkr.hcl
```

## Using the Build Script

For easier builds:

```bash
# Make build script executable
chmod +x build.sh

# Build with prompts
./build.sh

# Or provide token directly
./build.sh YOUR_DO_TOKEN
```

## Validate Template

Check for syntax errors before building:

```bash
packer validate open-webui-image.pkr.hcl
```

## Deploy Droplets from Your Image

### Via Digital Ocean Dashboard

1. **Create** → **Droplets**
2. **Choose an image** → **Custom Images** tab
3. Select your `open-webui-multitenant-YYYY-MM-DD-hhmm` image
4. Choose size, region
5. **Authentication:**
   - Set root password
   - Add your SSH key
6. Create!

### First Boot Setup

```bash
# 1. SSH as root
ssh root@YOUR_DROPLET_IP

# 2. Add SSH key for qbmgr
echo "YOUR_SSH_PUBLIC_KEY" > /home/qbmgr/.ssh/authorized_keys
chown qbmgr:qbmgr /home/qbmgr/.ssh/authorized_keys
chmod 600 /home/qbmgr/.ssh/authorized_keys

# 3. Exit and SSH as qbmgr
exit
ssh qbmgr@YOUR_DROPLET_IP

# 4. Read welcome message
cat ~/WELCOME.txt

# 5. Check image info
cat /etc/open-webui-image-info.txt

# 6. Start deploying!
cd ~/open-webui/mt
./client-manager.sh
```

**That's it!** The nginx container is already running, repository is cloned, everything is ready.

## What Gets Installed

### System Packages
- git, curl, wget
- certbot (for SSL)
- jq (JSON processing)
- htop, tree, net-tools (utilities)

### Docker Components
- Docker Engine (from base image)
- Docker Compose (from base image)
- Custom network: `openwebui-network`
- nginx container: `openwebui-nginx` (pre-deployed)

### User Setup
- User: `qbmgr`
- Groups: `sudo`, `docker`
- Sudo: Passwordless
- Home: `/home/qbmgr`
- Repository: `/home/qbmgr/open-webui`

### Directory Structure
```
/home/qbmgr/
├── open-webui/              # Git repository
│   └── mt/
│       ├── client-manager.sh
│       ├── nginx-container/
│       └── ...
└── WELCOME.txt              # First boot instructions

/opt/openwebui-nginx/        # nginx container configs
├── conf.d/                  # Site configurations
├── nginx.conf               # Main config
└── webroot/                 # Let's Encrypt webroot
```

## Troubleshooting

### Build Fails

**Check Packer logs:**
```bash
PACKER_LOG=1 packer build open-webui-image.pkr.hcl
```

**Common issues:**
- Invalid DO token → Check token has read+write access
- Region unavailable → Try different region (`-var "region=sfo3"`)
- Droplet size too small → Use at least 2GB RAM

### Provisioning Errors

**View detailed output:**
```bash
packer build -debug open-webui-image.pkr.hcl
```

This pauses after each step, allowing you to SSH into the build droplet:
```bash
# Packer will show SSH command like:
ssh -i /tmp/packer-key root@TEMP_DROPLET_IP
```

**Check script logs:**
```bash
# During -debug mode, SSH in and check:
tail -f /var/log/cloud-init-output.log
journalctl -xe
docker logs openwebui-nginx
```

### Image Not Appearing

**Check build output:**
- Look for snapshot ID in output
- Check DO dashboard → Images → Snapshots
- May take 1-2 minutes to appear

**Verify build completed:**
```bash
cat manifest.json
# Should show snapshot ID and image details
```

## Updating the Image

### When to Rebuild

Rebuild when you:
- Update Open WebUI repository
- Change deployment scripts
- Update packages
- Modify nginx configuration
- Change user setup

### Versioning

Use semantic versioning in image names:

```bash
# Version 1.0
packer build -var "image_name=open-webui-v1.0" open-webui-image.pkr.hcl

# Version 1.1 (minor update)
packer build -var "image_name=open-webui-v1.1" open-webui-image.pkr.hcl

# Version 2.0 (major changes)
packer build -var "image_name=open-webui-v2.0" open-webui-image.pkr.hcl
```

**Keep old images** until you verify new ones work!

### Automated Builds

**CI/CD Integration (GitHub Actions example):**

```yaml
# .github/workflows/build-image.yml
name: Build Golden Image
on:
  push:
    branches: [main]
    paths:
      - 'mt/packer/**'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: hashicorp/setup-packer@main
      - name: Build Image
        env:
          DIGITALOCEAN_TOKEN: ${{ secrets.DO_TOKEN }}
        run: |
          cd mt/packer
          packer build open-webui-image.pkr.hcl
```

## Cost Considerations

### Build Costs
- **Temporary droplet:** ~$0.03/hour (s-2vcpu-2gb)
- **Build time:** ~8 minutes
- **Cost per build:** ~$0.004 (less than 1 cent!)

### Storage Costs
- **Image storage:** $0.05/GB/month
- **Typical image size:** ~2-3 GB
- **Monthly cost:** ~$0.10-0.15 per image

**Total cost:** Building weekly = **~$0.50/month**

Very affordable compared to manual setup time!

## Advanced Usage

### Custom Repository

Build from your own fork:

```bash
packer build \
  -var "repo_url=https://github.com/YOUR_USERNAME/open-webui.git" \
  -var "repo_branch=custom-branch" \
  open-webui-image.pkr.hcl
```

### Custom Provisioning

Edit `scripts/create-user.sh` to add your own setup steps:

```bash
# Add at end of create-user.sh
echo "Installing custom tools..."
apt-get install -y your-custom-package
```

### Multiple Regions

Build in multiple regions simultaneously:

```bash
# Create wrapper script
for region in nyc3 sfo3 lon1 fra1; do
  packer build -var "region=$region" open-webui-image.pkr.hcl &
done
wait
```

## Files in This Directory

- **`open-webui-image.pkr.hcl`** - Main Packer template
- **`scripts/create-user.sh`** - Creates qbmgr user and clones repo
- **`scripts/deploy-nginx.sh`** - Deploys nginx container
- **`scripts/cleanup.sh`** - Prepares image for deployment
- **`build.sh`** - Helper script for easy builds
- **`variables.auto.pkrvars.hcl.example`** - Example variables file
- **`README.md`** - This file
- **`.gitignore`** - Prevents committing sensitive files

## Support

For issues:
1. Check build logs with `PACKER_LOG=1`
2. Validate template: `packer validate open-webui-image.pkr.hcl`
3. Use `-debug` mode to inspect during build
4. Check Digital Ocean status: https://status.digitalocean.com/

## References

- [Packer Documentation](https://www.packer.io/docs)
- [DigitalOcean Builder](https://www.packer.io/plugins/builders/digitalocean)
- [Digital Ocean Custom Images](https://docs.digitalocean.com/products/images/custom-images/)
- [Packer Best Practices](https://www.packer.io/guides/hcl/best-practices)

---

**Pro Tip:** Build images on a schedule (weekly/monthly) to keep them updated with latest packages and security patches!
