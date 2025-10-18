# Packer template for Open WebUI Multi-Tenant Golden Image
# Builds a Digital Ocean custom image that can be used across multiple accounts
#
# Usage:
#   export DIGITALOCEAN_TOKEN="your-do-api-token"
#   packer build open-webui-image.pkr.hcl
#
# Or with variables:
#   packer build -var "do_token=YOUR_TOKEN" -var "image_name=my-custom-name" open-webui-image.pkr.hcl

packer {
  required_plugins {
    digitalocean = {
      version = ">= 1.0.0"
      source  = "github.com/digitalocean/digitalocean"
    }
  }
}

# Variables
variable "do_token" {
  type        = string
  description = "DigitalOcean API Token"
  default     = env("DIGITALOCEAN_TOKEN")
  sensitive   = true
}

variable "image_name" {
  type        = string
  description = "Name for the output image"
  default     = "open-webui-multitenant"
}

variable "region" {
  type        = string
  description = "DigitalOcean region to build in"
  default     = "nyc3"
}

variable "size" {
  type        = string
  description = "Droplet size for building (recommend at least 2GB RAM)"
  default     = "s-2vcpu-2gb"
}

variable "repo_url" {
  type        = string
  description = "Open WebUI repository URL"
  default     = "https://github.com/imagicrafter/open-webui.git"
}

variable "repo_branch" {
  type        = string
  description = "Branch to clone"
  default     = "main"
}

# Source: DigitalOcean Docker 20.04 base image
source "digitalocean" "open-webui" {
  api_token     = var.do_token
  image         = "docker-20-04"
  region        = var.region
  size          = var.size
  snapshot_name = "${var.image_name}-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
  ssh_username  = "root"

  # Droplet settings
  droplet_name = "packer-build-open-webui-${formatdate("YYYYMMDDhhmmss", timestamp())}"

  # Tags for organization
  tags = ["packer", "open-webui", "golden-image"]
}

# Build
build {
  name    = "open-webui-golden-image"
  sources = ["source.digitalocean.open-webui"]

  # Wait for cloud-init to finish
  provisioner "shell" {
    inline = [
      "echo 'Waiting for cloud-init to complete...'",
      "cloud-init status --wait || true",
      "sleep 10"
    ]
  }

  # Update system and install base packages
  provisioner "shell" {
    inline = [
      "echo '=== Updating system packages ==='",
      "export DEBIAN_FRONTEND=noninteractive",
      "apt-get update -qq",
      "apt-get upgrade -y -qq",
      "apt-get install -y -qq git curl wget certbot jq htop tree net-tools",
      "echo '=== Base packages installed ==='",
    ]
  }

  # Create qbmgr user
  provisioner "shell" {
    script = "${path.root}/scripts/create-user.sh"
    environment_vars = [
      "DEPLOY_USER=qbmgr",
      "REPO_URL=${var.repo_url}",
      "REPO_BRANCH=${var.repo_branch}"
    ]
  }

  # Deploy nginx container
  provisioner "shell" {
    script = "${path.root}/scripts/deploy-nginx.sh"
    environment_vars = [
      "DEPLOY_USER=qbmgr"
    ]
  }

  # Clean up for imaging
  provisioner "shell" {
    script = "${path.root}/scripts/cleanup.sh"
  }

  # Create manifest file with build info
  provisioner "shell" {
    inline = [
      "cat > /etc/open-webui-image-info.txt << 'EOF'",
      "Open WebUI Multi-Tenant Golden Image",
      "Built: ${formatdate("YYYY-MM-DD HH:mm:ss", timestamp())}",
      "Repository: ${var.repo_url}",
      "Branch: ${var.repo_branch}",
      "Packer Version: ${packer.version}",
      "",
      "Default User: qbmgr",
      "Repository Location: /home/qbmgr/open-webui",
      "nginx Container: Pre-deployed (openwebui-nginx)",
      "",
      "First Boot Instructions:",
      "1. SSH as root and add SSH key for qbmgr user",
      "2. SSH as qbmgr: ssh qbmgr@YOUR_IP",
      "3. Start deploying: cd ~/open-webui/mt && ./client-manager.sh",
      "EOF"
    ]
  }

  # Post-processor: Output image information
  post-processor "manifest" {
    output     = "manifest.json"
    strip_path = true
  }
}
