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

### Step 3: Deploy Client Instance on Single Hetzner Server

Deploy client's Docker instance on your centralized Hetzner server:

#### Hetzner Server Specifications
```bash
# Single server for all 20 clients
# CPU: 16-32 vCPUs, RAM: 64-128GB, Storage: 1TB+ SSD
# Location: Nuremberg (closest to Poland)
# Estimated resource per client: ~1-2 vCPU, 2-4GB RAM
```

#### Multi-Client Docker Deployment
```bash
# SSH into your main Hetzner server
ssh root@mai-production.hetzner-server.com

# Create client-specific deployment directory
mkdir -p /opt/clients/mai-companyabc
cd /opt/clients/mai-companyabc

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
      - "8001:8080"  # Unique port per client (8001, 8002, 8003...)
    volumes:
      - ./data:/app/backend/data
      - ./backups:/app/backups
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G

networks:
  default:
    name: mai-network
    external: true
EOF

# Start the client's instance
docker-compose up -d

# Verify deployment
docker-compose logs -f mai-companyabc
```

#### Port Management Strategy
```bash
# Client port assignments on single server
mai-client1:    8001:8080
mai-client2:    8002:8080  
mai-client3:    8003:8080
...
mai-client20:   8020:8080

# Reverse proxy configuration (Nginx/Caddy)
client1.mai-production.com → localhost:8001
client2.mai-production.com → localhost:8002
client3.mai-production.com → localhost:8003
```

Once the Docker instance is running, provide the client administrator with access:

#### Admin Account Setup (Client Administrator)
Provide the designated client administrator with:
- **Server URL**: `https://companyabc.mai-production.com` (via reverse proxy)
- **Direct Port Access**: `http://mai-production.hetzner-server.com:8001` (if no proxy)
- **OpenRouter API Key**: `sk-or-v1-abc123def456789...`
- **Instructions**: First person to register becomes admin automatically

#### Step-by-Step Admin Setup
1. **Access Instance**: Navigate to provided server URL
2. **Create Admin Account**: 
   - **Sign Up** as first user (automatically becomes admin)
   - System **auto-disables** signup after first user
   - Admin gains **full instance control**

3. **Configure OpenRouter API Key**:
   - Go to **Settings → Connections**
   - Enter provided API key: `sk-or-v1-abc123def456789...`
   - Set **OpenAI API Base URL**: `https://openrouter.ai/api/v1`
   - **Save Settings** → Auto-sync triggers organization setup

4. **Create Company User Accounts**:
   - Navigate to **Admin Panel** (sidebar menu)
   - Go to **Users** tab
   - **Add User** for each employee (4-19 users):
     - **Name**: Employee full name
     - **Email**: employee@company.com
     - **Password**: Generate secure password
     - **Role**: **user** (not admin)
   - **Distribute credentials** to employees

#### System Auto-Configuration (Automatic)
When admin saves API key:
- **Organization record** created in database
- **Admin user mapping** established
- **Usage tracking** initialized
- **External user** auto-learned on first API call

#### User Management Capabilities
Admin can:
- **Manage all users** (create, edit, delete, change roles)
- **Monitor usage** in Settings → Usage (live dashboard)
- **Configure permissions** for regular users
- **View chat activity** and system analytics
- **Control instance settings** and features

#### Regular Employee Access
Each employee receives:
- **Login credentials** from admin
- **Server URL** access
- **Standard user role** (no admin privileges)
- **Cannot**: create users, access admin panel, change settings

## ✅ Automated Features (Per Client Instance)

### Single-Tenant Architecture
- **Dedicated Instance**: Each client has isolated mAI instance on Hetzner
- **Isolated Database**: Dedicated SQLite database per client
- **Complete Data Separation**: No data sharing between client instances
- **Independent Usage Tracking**: Per-organization tracking with multiple users

### Admin-First User Model
- **First Registration**: Automatically becomes admin (Open WebUI feature)
- **Signup Auto-Disable**: Public signup disabled after first user
- **Admin Control**: Full user management through web interface
- **User Creation**: Admin creates 4-19 employee accounts via Admin → Users

### API Key Auto-Sync
- **Admin Configuration**: Admin enters API key in Settings → Connections
- **Organization Setup**: System creates organization record automatically
- **User Mapping**: All users mapped to single organization
- **No Manual Database Work**: Complete automation

### External User Auto-Learning (Per User)
- **Individual Learning**: Each user gets unique external_user from OpenRouter
- **First API Call Trigger**: System captures external_user from response
- **Database Update**: Automatic mapping update per user
- **Usage Tracking**: Immediate per-user tracking under shared API key

### Real-Time Usage Dashboard
- **Admin View**: Combined usage for all organization users
- **Live Updates**: 30-second refresh cycles
- **Per-User Breakdown**: Individual user usage analytics
- **Historical Data**: Daily and monthly usage summaries

## Client Management Structure

### Single Organization, Multiple Users
```
Company ABC (Hetzner Instance)
├── Admin User (john.admin@companyabc.com)
│   ├── Manages OpenRouter API key
│   ├── Creates employee accounts
│   ├── Monitors usage dashboard
│   └── Controls instance settings
└── Regular Users (4-19 employees)
    ├── employee1@companyabc.com
    ├── employee2@companyabc.com
    ├── employee3@companyabc.com
    └── employee4@companyabc.com
```

### External User Mapping
```
Shared API Key: sk-or-v1-abc123...
├── Admin: external_user "openrouter_admin_uuid_123"
├── Employee 1: external_user "openrouter_emp1_uuid_456"
├── Employee 2: external_user "openrouter_emp2_uuid_789"
├── Employee 3: external_user "openrouter_emp3_uuid_012"
└── Employee 4: external_user "openrouter_emp4_uuid_345"
```

### For You (Service Provider)
- **Single Hetzner Server**: 20 Docker instances on one powerful server
- **Resource Efficiency**: Shared server resources with per-client limits
- **OpenRouter Dashboard**: Aggregate view of all client API keys
- **Per-Client Billing**: Individual usage tracking for accurate invoicing
- **Centralized Management**: All instances managed from single server
- **Client Self-Service**: Clients manage their own users through admin interface

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
- **Port conflicts**: Verify unique ports per client (8001-8020)
- **Memory issues**: Monitor server resources (2-4GB RAM per client)
- **Network conflicts**: Ensure mai-network exists (`docker network create mai-network`)

### API Key Configuration
- **Wrong API key**: Verify key starts with `sk-or-v1-`
- **Base URL missing**: Ensure `https://openrouter.ai/api/v1` is set
- **Spending limits**: Check if client has exceeded monthly limit

### Usage Tracking Issues  
- **Auto-learning**: Check logs with `docker logs mai-[client] | grep "Auto-learning"`
- **Database init**: Verify client made first API call after key entry
- **Admin access**: Ensure user has admin permissions for usage tab

### Client Access Problems
- **Port access**: Verify correct port assignment and no conflicts
- **Reverse proxy**: Check proxy configuration points to correct port
- **Container status**: Check with `docker ps` that specific client container is running
- **Resource limits**: Monitor if client hitting CPU/memory limits

### Multi-Client Management
- **Container naming**: Use consistent naming: `mai-[client-name]`
- **Port tracking**: Document port assignments (8001-8020)
- **Resource monitoring**: Monitor overall server resource usage
- **Backup strategy**: Individual client data backups from `/opt/clients/[client]/data`

## Scaling Considerations

### Single Server Resource Planning
- **Total Server**: 16-32 vCPU, 64-128GB RAM, 1-2TB SSD
- **Per Client**: ~1-2 vCPU, 2-4GB RAM, 20-50GB storage
- **Location**: Nuremberg datacenter (closest to Poland)
- **Network**: High-bandwidth connection for 20 concurrent instances

### Management at Scale (20 Clients on One Server)
- **Container Orchestration**: Docker Compose per client with resource limits
- **Port Management**: Systematic port allocation (8001-8020)
- **Reverse Proxy**: Nginx/Caddy for domain-based routing
- **Monitoring**: Aggregate monitoring of all containers on single server
- **Backups**: Automated backup strategy for all client data directories
- **Updates**: Coordinated update process across all instances
- **Resource Monitoring**: Server-wide resource usage tracking

### Infrastructure Benefits
- **Cost Efficiency**: Single server vs 20 separate servers
- **Simplified Management**: Centralized administration
- **Resource Optimization**: Better utilization of server resources
- **Network Efficiency**: Shared bandwidth and infrastructure