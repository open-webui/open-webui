# Client Organization Deployment Guide

This guide explains how to create API keys for client organizations and deploy dedicated mAI instances on Hetzner Cloud. Each client gets their own Docker instance with isolated database and usage tracking.

## Deployment Architecture

**One Docker Instance Per Client:**
- Each client gets a dedicated mAI instance on Hetzner Cloud
- Isolated database (SQLite) per client organization
- Single OpenRouter API key per client instance
- One admin account manages multiple company users
- Automatic usage tracking with external_user auto-learning

## Step-by-Step Process

### Step 1: Get Your OpenRouter Provisioning Key

1. Go to https://openrouter.ai/keys
2. Click "Create New Key" 
3. Select "Provisioning API Key"
4. Copy the key (starts with `sk-or-prov-`)

### Step 2: Create API Key for Client Organization

Run the client key creation script:

```bash
cd /Users/patpil/Documents/Projects/mAI
python3 create_client_key_option1.py
```

**Example Session:**
```
🚀 Option 1: Simple Client API Key Creator & Usage Checker
============================================================
Select mode:
1. Create new API key
2. Check usage of existing API key
Enter choice (1 or 2): 1

Enter your OpenRouter provisioning key: sk-or-prov-your-key-here
Enter client organization name: Company ABC
Enter monthly spending limit (USD, or press Enter to skip): 500

🔑 Creating API key for client: Company ABC
📡 Response status: 201
✅ API key created successfully!

📋 CLIENT DEPLOYMENT INFO:
{
  "client_name": "Company ABC",
  "api_key": "sk-or-v1-abc123def456789...",
  "key_id": "12345",
  "monthly_limit": 500.0,
  "created_at": "2025-07-24T16:00:00",
  "deployment": "Dedicated Docker instance with isolated database"
}

🎯 DEPLOYMENT INSTRUCTIONS:
1. Deploy dedicated Docker instance for Company ABC
2. Admin enters API key in Settings → Connections
3. System automatically configures usage tracking
4. External user ID is auto-learned on first API call

✅ Single-tenant deployment with full data isolation!
```

### Step 3: Deploy Dedicated Client Instance on Hetzner

Create a dedicated Hetzner Cloud server for each client:

#### Create Hetzner Server
```bash
# Example server specs for each client
# CPU: 2 vCPUs, RAM: 4GB, Storage: 40GB SSD
# Location: Nuremberg (closest to Poland)

# Server naming convention: mai-[client-name]
# Example: mai-companyabc
```

#### Docker Deployment on Hetzner
```bash
# SSH into client's Hetzner server
ssh root@[client-server-ip]

# Install Docker (if not already installed)
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Create client-specific deployment directory
mkdir /opt/mai-companyabc
cd /opt/mai-companyabc

# Create docker-compose.yml for client
cat > docker-compose.yml << EOF
version: '3.8'
services:
  mai-companyabc:
    image: mai-production:latest
    container_name: mai-companyabc
    environment:
      - WEBUI_NAME=mAI - Company ABC
      - ENABLE_SIGNUP=false
      - ENV=prod
    ports:
      - "80:8080"    # Direct port 80 for client access
      - "443:8080"   # HTTPS if SSL termination handled elsewhere
    volumes:
      - ./data:/app/backend/data
      - ./backups:/app/backups
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
EOF

# Start the client's dedicated instance
docker-compose up -d

# Verify deployment
docker-compose logs -f
```

Once the Docker instance is running, provide the client administrator with access:

#### Admin Account Creation
```bash
# Access the client's mAI instance
# URL: http://[client-server-ip] or https://[client-domain.com]

# First user to register automatically becomes admin
# Provide client with:
# - Server URL/domain
# - Instruction to create admin account
# - OpenRouter API key for configuration
```

#### Client Admin Configuration Steps
1. **Access Instance**: Navigate to `http://[client-server-ip]`
2. **Create Admin Account**: First registration becomes admin automatically
3. **Configure OpenRouter**: 
   - Go to Settings → Connections
   - Enter OpenRouter API key: `sk-or-v1-abc123def456789...`
   - Set OpenAI API Base URL: `https://openrouter.ai/api/v1`
4. **System Auto-Configuration**:
   - Usage tracking initializes automatically
   - External user ID learned on first API call
   - Organization database created automatically

#### User Management
The admin can now:
- Create user accounts for company employees (5-20 users per client)
- Manage user permissions through Admin Settings
- Monitor organization usage in Settings → Usage tab

## ✅ Automated Features (Per Client Instance)

### Single-Tenant Architecture
- Each client has completely isolated mAI instance
- Dedicated SQLite database per client
- Independent usage tracking per organization
- No data sharing between client instances

### API Key Auto-Sync
- Admin enters API key once in Settings → Connections
- System automatically configures organization database
- No manual database setup required

### External User Auto-Learning
- System learns OpenRouter external_user on first API call
- Automatic mapping between users and OpenRouter usage
- Immediate usage tracking activation

### Real-Time Usage Tracking
- Live usage monitoring with 30-second updates
- Historical usage data and trends
- Per-user and per-model usage breakdowns
- 1.3x markup pricing automatically applied

## Client Management

### For Each Client Organization
1. **Access**: Dedicated URL `http://[client-server-ip]`
2. **Admin Management**: One admin manages 5-20 company users
3. **Usage Monitoring**: Real-time usage dashboard in Settings → Usage
4. **Data Isolation**: Complete separation from other clients

### For You (Service Provider)
- **Individual Monitoring**: Each client has isolated usage tracking
- **OpenRouter Dashboard**: Aggregate view of all client API key usage
- **Server Management**: 20 separate Hetzner servers to maintain
- **Billing**: Per-client usage tracking for accurate invoicing

## Management Commands

### Create New Client
```bash
python3 create_client_key_option1.py
# Choose mode 1 (Create new API key)
```

### Check Client Usage  
```bash
python3 create_client_key_option1.py  
# Choose mode 2 (Check usage of existing API key)
```

## Best Practices for Multi-Instance Deployment

1. **Server Management**: 
   - Use consistent naming: `mai-[client-name]`
   - Document server IPs and client assignments
   - Regular backups of each client's data volume

2. **Security**:
   - Keep provisioning key secure (only you have access)
   - Each client has isolated database and users
   - No data sharing between client instances

3. **Monitoring**:
   - Set reasonable spending limits per client API key
   - Monitor aggregate usage through OpenRouter dashboard
   - Each client admin monitors their own usage

4. **Client Onboarding**:
   - Test each deployment before handover
   - Provide clear admin setup instructions
   - Document client API keys and server details

## Troubleshooting

### Server Deployment Issues
- **Docker installation**: Ensure Docker is properly installed on Hetzner server
- **Port conflicts**: Verify ports 80/443 are available
- **Memory issues**: Monitor server resources (4GB RAM minimum)

### API Key Configuration
- **Wrong API key**: Verify key starts with `sk-or-v1-`
- **Base URL missing**: Ensure `https://openrouter.ai/api/v1` is set
- **Spending limits**: Check if client has exceeded monthly limit

### Usage Tracking Issues  
- **Auto-learning**: Check logs with `docker logs mai-[client] | grep "Auto-learning"`
- **Database init**: Verify client made first API call after key entry
- **Admin access**: Ensure user has admin permissions for usage tab

### Client Access Problems
- **Network**: Verify Hetzner server firewall allows HTTP/HTTPS
- **DNS**: If using domain, check DNS points to correct server IP
- **Container status**: Check with `docker ps` that container is running

## Scaling Considerations

### Server Resources (Per Client)
- **Minimum**: 2 vCPU, 4GB RAM, 40GB storage
- **Recommended**: 4 vCPU, 8GB RAM, 80GB storage (for larger teams)
- **Location**: Nuremberg datacenter (closest to Poland)

### Management at Scale (20 Clients)
- **Automation**: Consider Terraform/Ansible for server provisioning
- **Monitoring**: Aggregate monitoring across all client servers
- **Backups**: Automated backup strategy for all client databases
- **Updates**: Coordinated update process across all instances