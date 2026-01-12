# AI UI Deployment Guide

This guide explains how to deploy AI UI to Hetzner Cloud for shared development.

## Cost

| Resource | Monthly Cost |
|----------|-------------|
| Hetzner CX22 VPS (2 vCPU, 4GB RAM) | ~€3.49 (~$4) |
| Optional: Snapshots | ~€0.01/GB |
| **Total** | **~€4/month** |

## Prerequisites

- [Hetzner Cloud account](https://console.hetzner.cloud/)
- [hcloud CLI](https://github.com/hetznercloud/cli) installed
- SSH key pair on your machine

## Quick Start

### 1. Install Hetzner CLI

```bash
# macOS
brew install hcloud

# Linux (download from GitHub releases)
# https://github.com/hetznercloud/cli/releases
```

### 2. Configure Hetzner CLI

1. Create API token in Hetzner Console: **Security → API Tokens → Generate API Token** (Read & Write)
2. Configure CLI:

```bash
hcloud context create ai-ui-deploy
# Paste your API token when prompted
```

### 3. Provision Server

```bash
./scripts/hetzner-setup.sh
```

This creates:
- SSH key in Hetzner (from your local key)
- Firewall with ports 22, 80, 443, 3100
- CX22 server with Docker pre-installed

### 4. Deploy AI UI

SSH into the server and deploy:

```bash
# Get server IP
SERVER_IP=$(hcloud server ip ai-ui-dev)

# SSH in
ssh root@$SERVER_IP

# Clone repository
git clone https://github.com/<your-org>/ai_ui.git
cd ai_ui
git checkout testy

# Configure environment
cp .env.production.example .env
nano .env  # Add your WEBUI_SECRET_KEY and API keys

# Deploy
docker compose -f docker-compose.prod.yaml up -d
```

### 5. Access AI UI

Open in browser: `http://<SERVER_IP>:3100`

## Team Access

Add SSH keys for all developers:

```bash
ssh root@$SERVER_IP
echo "ssh-rsa AAAA... developer@email.com" >> /root/.ssh/authorized_keys
```

## Management Commands

### Update Deployment

```bash
ssh root@$(hcloud server ip ai-ui-dev)
cd /root/ai_ui
./scripts/deploy.sh
```

### Stop Server (Save Costs)

```bash
# Power off (data preserved, no charge while off)
hcloud server poweroff ai-ui-dev

# Power on
hcloud server poweron ai-ui-dev
ssh root@$(hcloud server ip ai-ui-dev) "cd /root/ai_ui && docker compose -f docker-compose.prod.yaml up -d"
```

### Delete Server

```bash
# Warning: This deletes all data!
hcloud server delete ai-ui-dev
```

### View Logs

```bash
ssh root@$(hcloud server ip ai-ui-dev)
cd /root/ai_ui
docker compose -f docker-compose.prod.yaml logs -f
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `WEBUI_SECRET_KEY` | Yes | Session encryption key. Generate with `openssl rand -hex 32` |
| `OPENAI_API_KEY` | No | OpenAI API key for GPT models |
| `ANTHROPIC_API_KEY` | No | Anthropic API key for Claude models |
| `AZURE_OPENAI_API_KEY` | No | Azure OpenAI API key |
| `OLLAMA_BASE_URL` | No | URL of external Ollama server |
| `OPEN_WEBUI_PORT` | No | Port for web interface (default: 3100) |

## Troubleshooting

### Cannot SSH into server

```bash
# Check server status
hcloud server describe ai-ui-dev

# Check your SSH key
hcloud ssh-key list
```

### Container not starting

```bash
ssh root@$(hcloud server ip ai-ui-dev)
cd /root/ai_ui
docker compose -f docker-compose.prod.yaml logs
```

### Check disk space

```bash
ssh root@$(hcloud server ip ai-ui-dev) "df -h"
```

## Architecture

```
┌─────────────────────────────────────────┐
│           Hetzner Cloud VPS             │
│           (ai-ui-dev)                   │
│  ┌────────────────────────────────────┐ │
│  │         Docker Container           │ │
│  │         (ai-ui)                    │ │
│  │  ┌──────────────────────────────┐  │ │
│  │  │       Open WebUI Fork        │  │ │
│  │  │       Port 8080 internal     │  │ │
│  │  └──────────────────────────────┘  │ │
│  └────────────────────────────────────┘ │
│                   │                     │
│  ┌────────────────┴────────────────┐    │
│  │    Volume: ai-ui-data           │    │
│  │    /app/backend/data            │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
              │
    Port 3100 exposed
              │
              ▼
    http://<SERVER_IP>:3100
```
