# Multi-Tenant Open WebUI

This directory contains scripts for running multiple isolated Open WebUI instances for different clients.

## Overview

Each client gets their own:
- 🔒 **Isolated container** with unique name
- 💾 **Dedicated data volume** (separate chat history, settings, etc.)
- 🌐 **Custom domain** and port
- 🏷️ **Branded interface** with client name
- 🔐 **Same OAuth configuration** (martins.net domain restriction)
- 🗄️ **Database choice** (SQLite local or PostgreSQL/Supabase cloud)

### Database Migration Feature

The client manager includes built-in database migration capabilities:
- **Automatic detection** of current database type (SQLite or PostgreSQL)
- **One-click migration** from SQLite to Supabase PostgreSQL
- **Zero data loss** with automatic backups and rollback
- **Configuration viewer** for PostgreSQL deployments

Perfect for scaling from local development to cloud-hosted production databases.

**📖 [Complete Migration Documentation →](DB_MIGRATION/README.md)**

The DB_MIGRATION folder contains comprehensive documentation covering:
- Step-by-step migration process
- Security posture explanation (why no RLS, public schema)
- Rollback procedures
- Troubleshooting guide
- Migration scripts and helper functions

### High Availability Sync System (NEW - Phase 1)

**⭐ NEW**: The `SYNC/` directory contains a production-ready **SQLite + Supabase Sync System** with high availability:

**Key Features**:
- **Dual sync containers** (primary/secondary) with automatic leader election
- **One-way sync** SQLite → Supabase (Phase 1)
- **Automated conflict resolution** with 5 configurable strategies
- **Supabase as authoritative state** with local caching (5-min TTL)
- **High availability** with automatic failover (<35 seconds)
- **Comprehensive monitoring** via Prometheus metrics
- **IPv6 auto-configuration** for optimal Supabase connectivity

**Architecture**:
- **Leader Election**: PostgreSQL atomic operations (no external dependencies)
- **State Management**: Cache-aside pattern with cluster synchronization
- **Security**: Restricted database roles, Row Level Security (RLS)
- **Deployment**: Automated with `deploy-sync-cluster.sh`

**📖 [Complete Sync System Documentation →](SYNC/README.md)**

The SYNC folder includes:
- Complete architectural overview and design patterns
- **Automatic IPv6 detection and configuration** (Digital Ocean supported)
- FastAPI application with REST API and health checks
- Deployment automation with pre-flight validation
- Conflict resolution strategies and configuration
- Monitoring and troubleshooting guides
- Phase 2 roadmap (bidirectional sync, cross-host migration)

**Quick Start**:
```bash
cd mt/SYNC
./scripts/deploy-sync-cluster.sh
```

See [SYNC/README.md](SYNC/README.md) for detailed documentation including IPv6 setup requirements.

## Testing & Certification

### Testing Suite

**Location**: `mt/tests/`

The testing suite validates all mt/ features before production release. Tests cover:
- **Security validation**: Permission and access control tests
- **HA failover testing**: High availability and leader election
- **Integration tests**: Component interaction validation
- **Performance tests**: Load and latency benchmarks

**📖 [Complete Testing Documentation →](tests/README.md)**

**Available Tests**:
- ✅ `sync-security-validation.py` - SYNC security validation (13 tests, all passing)
- ⏳ `sync-ha-failover.sh` - HA failover tests (manual testing complete, script pending)
- 🔲 `sync-conflict-resolution.sh` - Conflict resolution tests (planned)
- 🔲 `sync-state-authority.sh` - State management tests (planned)

**Quick Test Execution**:
```bash
# Run security validation tests
cd mt/tests
source ../SYNC/.credentials
docker exec -i -e SYNC_URL="$SYNC_URL" -e ADMIN_URL="$ADMIN_URL" \
    openwebui-sync-node-a python3 - < sync-security-validation.py
```

**Future: Automated Certification**
```bash
# Run full certification suite (future)
cd mt/tests
./run-certification.sh
```

This will validate all components before production deployment and generate comprehensive test reports.

## Monitoring & Observability

### Current State

The sync containers **already expose Prometheus metrics** on their `/metrics` endpoints:

- **Node A**: `http://localhost:9443/metrics`
- **Node B**: `http://localhost:9444/metrics`

**Available Metrics** (automatically instrumented):

| Category | Metrics | Description |
|----------|---------|-------------|
| **Leader Election** | `sync_is_leader`<br>`sync_leader_election_attempts_total`<br>`sync_leader_election_successes_total`<br>`sync_leader_lease_expires_timestamp` | Leadership status, election attempts, lease expiration |
| **Heartbeats** | `sync_heartbeat_failures_total`<br>`sync_container_uptime_seconds` | Heartbeat failures, container uptime |
| **Sync Operations** | `sync_operations_total{status}`<br>`sync_operation_duration_seconds`<br>`sync_rows_synced_total` | Sync job metrics, duration histograms, row counts |
| **Conflicts** | `sync_conflicts_detected_total`<br>`sync_conflicts_resolved_total{strategy}` | Conflict detection and resolution by strategy |
| **Failover** | `sync_failover_events_total` | Leadership change events |

### Centralized Monitoring Setup (Planned)

**Location**: `mt/monitoring/` (not yet implemented)

The centralized monitoring stack will track:
- ✅ All sync clusters across different hosts
- ✅ Client deployment health and status
- ✅ Future mt/ services (client-manager metrics, etc.)

**Planned Architecture**:
```
mt/monitoring/
├── docker-compose.yml          # Prometheus + Grafana stack
├── prometheus/
│   ├── prometheus.yml          # Multi-cluster scrape config
│   └── alerts.yml              # Alert rules for failures
└── grafana/
    └── dashboards/
        ├── sync-clusters.json  # Multi-cluster overview
        └── mt-overview.json    # Overall mt/ stack health
```

**Access** (when deployed):
- **Grafana**: `http://localhost:3000` (dashboards)
- **Prometheus**: `http://localhost:9090` (raw metrics)

**Dashboards will include**:
- Leadership status over time (which node is leader)
- Heartbeat freshness graphs
- Failover events timeline
- Sync operation success/failure rates
- Conflict resolution statistics
- Per-cluster and cross-cluster views

### Manual Monitoring (Current)

Until centralized monitoring is deployed, monitor clusters via:

**1. Health API Endpoints**:
```bash
# Check Node A
curl http://localhost:9443/health | jq

# Check Node B
curl http://localhost:9444/health | jq
```

**2. Database Views**:
```sql
-- Cluster health overview
SELECT * FROM sync_metadata.v_cluster_health;

-- Active sync jobs
SELECT * FROM sync_metadata.v_active_sync_jobs;

-- Recent conflicts
SELECT * FROM sync_metadata.v_recent_conflicts;
```

**3. Raw Metrics**:
```bash
# View all metrics from Node A
curl http://localhost:9443/metrics

# Filter specific metrics
curl http://localhost:9443/metrics | grep sync_is_leader
```

### Setting Up Monitoring (Future)

When the centralized monitoring stack is ready:

```bash
# Deploy monitoring infrastructure
cd mt/monitoring
docker compose up -d

# Access Grafana
open http://localhost:3000
# Default login: admin/admin

# Add new cluster to monitoring
# Edit prometheus/prometheus.yml
# Add scrape target for new cluster endpoints
docker compose restart prometheus
```

### Adding Clusters to Monitoring

To monitor a new sync cluster:

1. **Deploy sync cluster** on new host
2. **Get metrics endpoints** (`http://HOST:9443/metrics`, `http://HOST:9444/metrics`)
3. **Update Prometheus config** to scrape new endpoints
4. **Verify** in Grafana dashboards

### Troubleshooting Monitoring

**Metrics not appearing?**
- Verify containers are running: `docker ps | grep sync-node`
- Check metrics endpoint: `curl http://localhost:9443/metrics`
- Review container logs: `docker logs openwebui-sync-node-a`

**Stale heartbeat warnings?**
- Fixed in latest version with stable `host_id` across restarts
- View real-time status: `SELECT * FROM sync_metadata.v_cluster_health;`

### Archon Tasks for Monitoring Implementation

The following tasks are tracked in Archon for implementing centralized monitoring:

1. **Design monitoring architecture** - Decide on federation vs single instance
2. **Create Prometheus configuration** - Scrape configs and alert rules
3. **Create Grafana dashboards** - Multi-cluster views and drill-downs
4. **Create docker-compose** - Monitoring stack deployment

See Archon project `038661b1-7e1c-40d0-b4f9-950db24c2a3f` for task details.

## Quick Start

### Start Pre-configured Clients
```bash
# Start ACME Corp instance (port 8081)
./start-acme-corp.sh

# Start Beta Client instance (port 8082)
./start-beta-client.sh
```

### Start Custom Client
```bash
# Usage: ./start-template.sh CLIENT_NAME PORT DOMAIN
./start-template.sh xyz-corp 8083 xyz.yourdomain.com
```

### Manage All Clients
```bash
# Show help and available commands
./client-manager.sh

# List all client containers
./client-manager.sh list

# Stop all client containers
./client-manager.sh stop

# Start all stopped client containers
./client-manager.sh start

# View logs for specific client
./client-manager.sh logs acme-corp
```

### Migrate Database to PostgreSQL
```bash
# Access interactive client manager
./client-manager.sh

# Select "3) Manage Existing Deployment"
# Choose your client
# Select "8) Migrate to Supabase/PostgreSQL"

# The wizard will guide you through:
# - Entering Supabase credentials
# - Testing connectivity
# - Creating backups
# - Migrating data
# - Switching to PostgreSQL

# See "Database Migration" section below for full details
```

## File Structure

```
mt/
├── README.md                    # This file
├── start-template.sh            # Template for creating client instances
├── start-acme-corp.sh           # Pre-configured ACME Corp launcher
├── start-beta-client.sh         # Pre-configured Beta Client launcher
├── client-manager.sh            # Multi-client management tool
├── DB_MIGRATION/                # Database migration system (SQLite → PostgreSQL)
│   ├── README.md                # Complete migration documentation
│   ├── db-migration-helper.sh   # Migration utility functions
│   └── migrate-db.py            # Python data migration script
├── SYNC/                        # ⭐ NEW: SQLite + Supabase Sync System (Phase 1)
│   ├── README.md                # Complete sync system documentation
│   ├── python/                  # FastAPI application and sync modules
│   ├── scripts/                 # Deployment and sync automation
│   ├── docker/                  # Container infrastructure
│   └── config/                  # Configuration templates
├── tests/                       # ⭐ Testing & Certification Suite
│   ├── README.md                # Testing methodology and documentation
│   ├── sync-security-validation.py  # SYNC security tests (✅ all passing)
│   └── run-certification.sh     # Batch test runner (future)
├── nginx-template.conf          # Production nginx config template
├── nginx-template-local.conf    # Local testing nginx config
├── docker-compose.nginx.yml     # Local nginx setup
└── nginx/                       # Local nginx configurations
    ├── sites-available/
    └── sites-enabled/
```

## Container Naming Convention

| Client | Container Name | Port | Domain |
|--------|---------------|------|---------|
| ACME Corp | `openwebui-acme-corp` | 8081 | acme.yourdomain.com |
| Beta Client | `openwebui-beta-client` | 8082 | beta.yourdomain.com |
| Custom | `openwebui-CLIENT_NAME` | Custom | Custom |

## Volume Naming Convention

Each client gets an isolated Docker volume:
- `openwebui-acme-corp-data`
- `openwebui-beta-client-data`
- `openwebui-CLIENT_NAME-data`

## Adding New Clients

### Method 1: Use Template Script
```bash
./start-template.sh new-client 8084 newclient.yourdomain.com
```

### Method 2: Create Dedicated Script
1. Copy an existing client script:
   ```bash
   cp start-acme-corp.sh start-new-client.sh
   ```

2. Edit the new script to change the client name, port, and domain:
   ```bash
   ${SCRIPT_DIR}/start-template.sh new-client 8084 newclient.yourdomain.com
   ```

3. Make it executable:
   ```bash
   chmod +x start-new-client.sh
   ```

## Individual Container Management

```bash
# Stop specific client
docker stop openwebui-CLIENT_NAME

# Start specific client
docker start openwebui-CLIENT_NAME

# Restart specific client
docker restart openwebui-CLIENT_NAME

# View logs for specific client
docker logs -f openwebui-CLIENT_NAME

# Remove client (CAUTION: This deletes the container but preserves data volume)
docker stop openwebui-CLIENT_NAME && docker rm openwebui-CLIENT_NAME
```

## Port Management

**Used Ports:**
- 8081: ACME Corp
- 8082: Beta Client

**Available Ports:**
- 8083-8099: Available for new clients

**Port Conflict Check:**
```bash
# Check what ports are in use
docker ps --format "table {{.Names}}\t{{.Ports}}"

# Check specific port
sudo lsof -i :8083
```

## nginx Configuration

For each client, add an nginx server block:

```nginx
server {
    listen 443 ssl http2;
    server_name acme.yourdomain.com;

    # SSL configuration here...

    location / {
        proxy_pass http://localhost:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## OAuth Configuration

### QuantaBase Google Cloud Project

**Google Cloud Console:** https://console.cloud.google.com/apis/credentials?hl=en&project=quantabase
**OAuth 2.0 Client ID:** `Open WebUI`
**Client ID:** `1063776054060-2fa0vn14b7ahi1tmfk49cuio44goosc1.apps.googleusercontent.com`

### Shared OAuth Configuration

All QuantaBase client instances share the same Google OAuth configuration:

- **Domain Restriction:** `martins.net` (only @martins.net email addresses can sign in)
- **Authorized JavaScript Origins:** Must include each client's domain
- **Authorized Redirect URIs:** Must include each client's callback URL

### Adding New Client Domains

When creating a new client deployment, add these URLs to the OAuth configuration:

**For Development (localhost):**
```
Authorized JavaScript Origins:
- http://127.0.0.1:PORT
- http://localhost:PORT

Authorized Redirect URIs:
- http://127.0.0.1:PORT/oauth/google/callback
- http://localhost:PORT/oauth/google/callback
```

**For Production:**
```
Authorized JavaScript Origins:
- https://CLIENT_NAME.yourdomain.com

Authorized Redirect URIs:
- https://CLIENT_NAME.yourdomain.com/oauth/google/callback
```

### Current Configured Clients

| Client | Development | Production |
|--------|------------|------------|
| Main Instance | http://127.0.0.1:8080 | https://yourdomain.com |
| imagicrafter | http://127.0.0.1:8081 | https://imagicrafter.yourdomain.com |

### OAuth Configuration Steps

1. **Access Google Cloud Console:** https://console.cloud.google.com/apis/credentials?hl=en&project=quantabase
2. **Select "Open WebUI" OAuth 2.0 Client ID**
3. **Add new Authorized JavaScript Origins** for the client domain
4. **Add new Authorized Redirect URIs** for the OAuth callback
5. **Save changes**
6. **Test authentication** at the client URL

## Source Code Update Process

This system uses a custom fork of Open WebUI with QuantaBase branding. Follow this process to update to the latest Open WebUI version while preserving custom modifications.

### Repository Setup

**Custom Fork:** `https://github.com/imagicrafter/open-webui`
**Container Image:** `ghcr.io/imagicrafter/open-webui:main`
**Upstream:** `https://github.com/open-webui/open-webui`

### Your Customizations (What to Preserve)

The following files/directories contain your QuantaBase customizations:

**✅ Committed Custom Files:**
- `assets/logos/` - Custom QuantaBase branding assets
- `backend/open_webui/static/favicon.png` - Replaced favicon
- `backend/open_webui/static/logo.png` - Replaced logo
- `backend/open_webui/static/swagger-ui/favicon.png` - API docs favicon
- `static/favicon.png` and `static/static/` - Additional static file replacements
- `favicon_backup/` - Backup of original files
- `.claude/` - Claude Code session files
- `docker-start.md` - Custom documentation

**⚠️ Local-Only Files (Need to commit):**
- `mt/` - Multi-tenant client management system
- `start.sh` - Enhanced QuantaBase startup script

### Update Workflow (Branching Strategy)

This strategy ensures your customizations are never lost during updates:

#### 1. Prepare for Update

```bash
# Navigate to your local fork
cd /path/to/your/open-webui

# Ensure upstream remote exists
git remote add upstream https://github.com/open-webui/open-webui.git || true

# Commit any local changes first
git add mt/ start.sh
git commit -m "Add multi-tenant system and enhanced start script"
git push origin main
```

#### 2. Create Branching Structure

```bash
# Ensure you're on main and up to date
git checkout main
git pull origin main

# Create quantabase-branded branch (preserves all your customizations)
git checkout -b quantabase-branded
git push origin quantabase-branded

# Create update branch from quantabase-branded
git checkout -b quantabase-update
```

#### 3. Pull Upstream Changes

```bash
# Fetch latest from upstream
git fetch upstream

# Merge upstream changes into update branch
git merge upstream/main

# Handle merge conflicts:
# - Choose YOUR version for all files in "Your Customizations" list above
# - Accept UPSTREAM version for core Open WebUI functionality
# - Manually merge any files that need both changes
```

#### 4. Preserve Your Customizations

If conflicts occur with your custom files, resolve them like this:

```bash
# For custom branding files, keep your version:
git checkout --ours assets/logos/
git checkout --ours backend/open_webui/static/favicon.png
git checkout --ours backend/open_webui/static/logo.png
# ... repeat for all custom files

# For core functionality, accept upstream:
git checkout --theirs src/lib/components/
git checkout --theirs backend/open_webui/routers/
# ... etc for core files

# Commit the resolution
git add .
git commit -m "Merge upstream $(date +%Y-%m-%d) - preserved QuantaBase customizations"
```

#### 5. Merge Back to Branded Branch

```bash
# Merge update branch into quantabase-branded
git checkout quantabase-branded
git merge quantabase-update

# Push updated branded branch
git push origin quantabase-branded
```

#### 6. Build and Test Locally

```bash
# Still on quantabase-update branch
# Build your updated image locally
docker build -t ghcr.io/imagicrafter/open-webui:test .

# Test with a temporary container
docker run -d --name test-openwebui -p 8090:8080 \
  -e GOOGLE_CLIENT_ID=your_client_id \
  -e GOOGLE_CLIENT_SECRET=your_secret \
  -e GOOGLE_REDIRECT_URI=http://127.0.0.1:8090/oauth/google/callback \
  -e ENABLE_OAUTH_SIGNUP=true \
  -e OAUTH_ALLOWED_DOMAINS=martins.net \
  -e WEBUI_NAME="QuantaBase Test" \
  ghcr.io/imagicrafter/open-webui:test

# Test checklist:
# ✅ OAuth login works
# ✅ QuantaBase branding appears correctly
# ✅ Core Open WebUI features function
# ✅ Multi-tenant scripts work (if testing locally)

# Clean up test container
docker stop test-openwebui && docker rm test-openwebui
```

#### 7. Merge to Main Branch

```bash
# If tests pass, merge quantabase-update into main
git checkout main
git merge quantabase-update
git push origin main

# Tag the release
git tag -a v$(date +%Y.%m.%d) -m "Update to latest Open WebUI $(date +%Y-%m-%d)"
git push origin --tags

# Clean up update branch
git branch -d quantabase-update
git push origin --delete quantabase-update
```

#### 8. Wait for GitHub Actions Build

After pushing to main, **GitHub Actions automatically builds your custom image**:

- 🔄 **Monitor build**: https://github.com/imagicrafter/open-webui/actions
- ⏱️ **Build time**: ~15-20 minutes
- 📦 **Result**: `ghcr.io/imagicrafter/open-webui:main` with QuantaBase branding

**⚠️ Important**: Wait for build completion before proceeding to production deployment.

#### 9. Deploy to Production (Manual Process)

**GitHub Actions does NOT auto-deploy to your server.** You manually control when production updates:

```bash
# SSH to production server
ssh user@your-production-server

# Navigate to deployment directory
cd /path/to/open-webui

# Pull latest code (for scripts and configurations)
git pull origin main

# Pull the new custom image that GitHub Actions just built
docker pull ghcr.io/imagicrafter/open-webui:main
```

#### 10. Restart Client Containers

```bash
# Update all client deployments with new image
./mt/client-manager.sh stop
docker ps -a --filter "name=openwebui-" --format "{{.Names}}" | xargs docker rm
./mt/client-manager.sh start

# Verify all clients are running with updated image
./mt/client-manager.sh list
docker images ghcr.io/imagicrafter/open-webui
```

### Deployment Flow Summary

**🔄 What's Automated:**
- ✅ **Image Building**: GitHub Actions builds custom image on push to main
- ✅ **Image Publishing**: Pushes to `ghcr.io/imagicrafter/open-webui:main`
- ✅ **Multi-platform**: Supports both amd64 and arm64 architectures

**👤 What You Control:**
- ✅ **When to Deploy**: You decide when to update production
- ✅ **Which Clients**: Choose which clients to update
- ✅ **Rollback**: Keep previous images for quick rollback if needed

**🚫 What's NOT Automated:**
- ❌ **Production Deployment**: No automatic server access (security)
- ❌ **Client Updates**: No automatic container restarts
- ❌ **Configuration Changes**: Manual git pull required

This gives you **maximum control** over production deployments while automating the heavy lifting of image builds.

#### 4. GitHub Actions (Automatic Image Build)

Your GitHub repository should have Actions configured to automatically build and push to GitHub Container Registry when you push to main. If not set up, the workflow file should be:

```yaml
# .github/workflows/docker.yml
name: Build and Push Docker Image
on:
  push:
    branches: [ main ]
    tags: [ 'v*' ]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Log in to GitHub Container Registry
      uses: docker/login-action@v3
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: ghcr.io/imagicrafter/open-webui:main
```

#### 5. Update Production Deployments

```bash
# SSH to production server
ssh user@your-production-server

# Navigate to deployment directory
cd /path/to/open-webui

# Pull latest code (optional - for reference)
git pull origin main

# Pull updated image
docker pull ghcr.io/imagicrafter/open-webui:main

# Update all client deployments
./mt/client-manager.sh stop
docker ps -a --filter "name=openwebui-" --format "{{.Names}}" | xargs docker rm
./mt/client-manager.sh start

# Verify all clients are running
./mt/client-manager.sh list
```

### Rollback Process

If an update causes issues:

```bash
# Check recent image tags
docker images ghcr.io/imagicrafter/open-webui

# Use a previous tag
docker tag ghcr.io/imagicrafter/open-webui:v2024.01.15 ghcr.io/imagicrafter/open-webui:main

# Restart clients with previous version
./mt/client-manager.sh stop
docker ps -a --filter "name=openwebui-" --format "{{.Names}}" | xargs docker rm
./mt/client-manager.sh start
```

### Custom Branding Checklist

When updating, ensure these custom elements are preserved:

- [ ] QuantaBase logos in `assets/logos/`
- [ ] Custom favicon files
- [ ] Environment variable configurations
- [ ] OAuth settings and domain restrictions
- [ ] Any custom styling or themes

## Updates and Maintenance

### Image Updates (New Open WebUI Version)

To update a client to the latest Open WebUI version while preserving all data:

```bash
# Stop and remove container (keeps volume and data)
docker stop openwebui-CLIENT_NAME && docker rm openwebui-CLIENT_NAME

# Pull latest image
docker pull ghcr.io/imagicrafter/open-webui:main

# Recreate with new image (data automatically preserved)
./start-template.sh CLIENT_NAME PORT [DOMAIN]
```

**Example - Update imagicrafter client:**
```bash
docker stop openwebui-imagicrafter && docker rm openwebui-imagicrafter
docker pull ghcr.io/imagicrafter/open-webui:main
./start-template.sh imagicrafter 8081
```

### Configuration Updates

To update environment variables or settings:

```bash
# Stop and remove container
docker stop openwebui-CLIENT_NAME && docker rm openwebui-CLIENT_NAME

# Recreate with new configuration (data preserved)
./start-template.sh CLIENT_NAME PORT [DOMAIN]
```

### Fresh Start (Delete All Data)

⚠️ **WARNING: This permanently deletes all client data**

```bash
# Stop and remove container AND volume
docker stop openwebui-CLIENT_NAME && docker rm openwebui-CLIENT_NAME
docker volume rm openwebui-CLIENT_NAME-data

# Recreate from scratch
./start-template.sh CLIENT_NAME PORT [DOMAIN]
```

### Bulk Updates

Update all clients to latest image:

```bash
# Stop all clients
./client-manager.sh stop

# Pull latest image
docker pull ghcr.io/imagicrafter/open-webui:main

# Remove all containers (keeps volumes)
docker ps -a --filter "name=openwebui-" --format "{{.Names}}" | xargs docker rm

# Restart all clients (they'll use the new image)
./client-manager.sh start
```

### Volume Management

```bash
# List all client volumes
docker volume ls | grep openwebui

# Check volume disk usage
docker system df -v | grep openwebui

# Remove unused volumes (DANGER - only if you're sure)
docker volume prune
```

## Data Backup

Each client's data is stored in a named Docker volume:

```bash
# List all client volumes
docker volume ls | grep openwebui

# Backup client data
docker run --rm -v openwebui-CLIENT_NAME-data:/data -v $(pwd):/backup alpine tar czf /backup/CLIENT_NAME-backup.tar.gz -C /data .

# Restore client data
docker run --rm -v openwebui-CLIENT_NAME-data:/data -v $(pwd):/backup alpine tar xzf /backup/CLIENT_NAME-backup.tar.gz -C /data

# Backup all client data
for volume in $(docker volume ls --filter name=openwebui- --format "{{.Name}}"); do
  client=$(echo $volume | sed 's/openwebui-//' | sed 's/-data//')
  docker run --rm -v $volume:/data -v $(pwd):/backup alpine tar czf /backup/${client}-backup-$(date +%Y%m%d).tar.gz -C /data .
done
```

## Database Migration

### Overview

Open WebUI supports two database backends:
- **SQLite** (default): Local database stored in the container volume
- **PostgreSQL/Supabase**: Cloud-hosted PostgreSQL for scalability and multi-instance deployments

The client manager includes built-in migration capabilities to seamlessly migrate from SQLite to Supabase PostgreSQL.

### When to Migrate to PostgreSQL

Consider migrating to PostgreSQL/Supabase when you need:
- **Remote access** to your database for backups and analysis
- **Scalability** beyond local storage limits
- **Multi-instance deployments** sharing the same database
- **Better performance** for large datasets
- **Cloud-based backups** and disaster recovery

### Prerequisites

Before migrating, ensure you have:

1. **Supabase Account and Project**
   - Sign up at https://supabase.com
   - Create a new project (note the project reference and password)
   - Wait for project to be fully provisioned (~2 minutes)

2. **Enable pgvector Extension** (recommended for RAG features)
   ```sql
   -- Run this in Supabase SQL Editor
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

3. **Get Connection Details**
   - Go to Project Settings → Database → Connection String
   - Note your:
     - Project Reference (e.g., `abc123xyz`)
     - Database Password
     - Region (e.g., `aws-0-us-east-1`)

4. **Stable Internet Connection**
   - Migration can take 15-30 minutes for large databases
   - Ensure reliable connectivity throughout the process

### Migration Process

#### Step 1: Access Database Migration Menu

```bash
./client-manager.sh
# Select "3) Manage Existing Deployment"
# Choose your client
# Select "8) Migrate to Supabase/PostgreSQL"
```

#### Step 2: Review Migration Plan

The script will display:
- What will happen during migration
- Estimated time
- Requirements checklist

Confirm to proceed.

#### Step 3: Enter Supabase Configuration

When prompted, provide:
- **Project Reference**: Found in Supabase dashboard URL
- **Database Password**: The password you set when creating the project
- **Region**: Geographic region of your Supabase instance

The script will:
- Automatically use Transaction Mode (port 6543) for optimal performance
- URL-encode special characters in passwords
- Test the connection before proceeding

#### Step 4: Automated Migration

The script automatically:
1. ✅ Tests Supabase connectivity
2. ✅ Checks pgvector extension
3. ✅ Creates SQLite backup (in container and on host)
4. ✅ Initializes PostgreSQL schema
5. ✅ Runs migration tool (interactive)
6. ✅ Fixes null byte compatibility issues
7. ✅ Recreates container with PostgreSQL configuration
8. ✅ Verifies container is running

#### Step 5: Verify Migration

After successful migration:
```bash
# Check container is running
docker ps | grep openwebui-CLIENT_NAME

# Test web access
# Visit http://localhost:PORT

# Verify data
# - Log in with your account
# - Check chat history
# - Verify user settings
```

### Post-Migration

#### View Database Configuration

After migration, option 8 changes to "View database configuration":

```bash
./client-manager.sh
# Select "3) Manage Existing Deployment"
# Choose your migrated client
# Select "8) View database configuration"
```

This displays:
- Database type (PostgreSQL)
- Host and port
- Database name
- Connection status
- Masked connection string

#### Backup Location

SQLite backups are saved in two locations:
- **Container**: `/app/backend/data/webui-backup-TIMESTAMP.db`
- **Host**: `/tmp/webui-backup-TIMESTAMP.db`

**Keep backups for 2-4 weeks** before deleting.

### Rollback to SQLite

If you encounter issues after migration, you can rollback:

#### Automatic Rollback

If migration fails, the script automatically:
- Restores SQLite backup
- Recreates container with SQLite configuration
- Verifies container is running

#### Manual Rollback

If you need to rollback after successful migration:

```bash
# 1. Stop the PostgreSQL container
docker stop openwebui-CLIENT_NAME
docker rm openwebui-CLIENT_NAME

# 2. Restore backup (if you have it)
BACKUP_PATH="/tmp/webui-backup-TIMESTAMP.db"
docker run -d --name temp-restore \
  -v openwebui-CLIENT_NAME-data:/app/backend/data \
  ghcr.io/imagicrafter/open-webui:main sleep 3600

docker cp "$BACKUP_PATH" temp-restore:/app/backend/data/webui.db
docker stop temp-restore
docker rm temp-restore

# 3. Recreate container without DATABASE_URL
./start-template.sh CLIENT_NAME PORT [DOMAIN]
```

### Troubleshooting Migration

#### Connection Test Fails

**Problem**: Cannot connect to Supabase

**Solutions**:
- Verify project is fully provisioned (check Supabase dashboard)
- Check password is correct (no extra spaces)
- Ensure your IP isn't blocked by Supabase firewall
- Try resetting database password in Supabase settings

#### pgvector Extension Missing

**Problem**: Migration warns about missing pgvector

**Solutions**:
- Go to Supabase → Database → Extensions
- Enable "vector" extension
- Or run: `CREATE EXTENSION IF NOT EXISTS vector;`
- Continue without pgvector if you don't use RAG features

#### Migration Tool Fails

**Problem**: Data migration fails partway through

**Solutions**:
- Check internet connection stability
- Verify Supabase storage limits (500MB on free tier)
- Check Supabase dashboard for database errors
- Contact support if database is corrupted

#### Container Won't Start After Migration

**Problem**: Container exits immediately after migration

**Solutions**:
- Check logs: `docker logs openwebui-CLIENT_NAME`
- Verify DATABASE_URL format is correct
- Test connection to Supabase manually
- Try automatic rollback to SQLite

#### Special Characters in Password

**Problem**: Connection fails with special characters in password

**Solutions**:
- Script automatically URL-encodes passwords
- If still failing, try changing password to alphanumeric only
- Avoid: `@`, `#`, `!`, `%`, `&`, `:`, `/`

### Migration Best Practices

#### Before Migration

- [ ] Backup client data manually (see Data Backup section)
- [ ] Test Supabase connection from your server
- [ ] Check database size vs Supabase tier limits
- [ ] Schedule migration during low-traffic period
- [ ] Notify users of planned downtime

#### During Migration

- [ ] Don't interrupt the migration process
- [ ] Monitor progress in terminal
- [ ] Keep terminal session active
- [ ] Have Supabase dashboard open for monitoring

#### After Migration

- [ ] Test all critical functionality
- [ ] Monitor container logs for errors
- [ ] Keep SQLite backup for 2-4 weeks
- [ ] Document migration date and backup location
- [ ] Update your infrastructure documentation

### Connection String Reference

#### Format

```
postgresql://postgres.[PROJECT-REF]:[PASSWORD]@[REGION].pooler.supabase.com:6543/postgres
```

#### Components

- **Protocol**: `postgresql://` (required)
- **User**: `postgres.[PROJECT-REF]` (Supabase format)
- **Password**: URL-encoded password
- **Host**: `[REGION].pooler.supabase.com`
- **Port**: `6543` (Transaction Mode - recommended for web apps)
- **Database**: `postgres` (default Supabase database)

#### Example

```
postgresql://postgres.abc123xyz:myP%40ssword@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

**Note**: Password `myP@ssword` becomes `myP%40ssword` (URL-encoded)

### Security Considerations

#### Current Security Posture (Development/Testing)

After migrating to Supabase, you may notice tables show an **"Unrestricted"** tag in the Supabase dashboard. This indicates **Row Level Security (RLS)** is not enabled.

**For development and testing environments, this is acceptable** because:

- **Application-level security**: Open WebUI handles all authentication and authorization at the application layer
- **Backend-only access**: Users interact only through the web UI, not directly with the database
- **Database-per-client isolation**: Each client uses a separate Supabase project/database (not shared tables)
- **No public API exposure**: You're not using Supabase's auto-generated REST APIs or client libraries

#### When to Enable Row Level Security (RLS)

Consider enabling RLS when moving to **production** or when:

- **Exposing Supabase APIs**: Using Supabase's PostgREST API or client libraries directly
- **Multiple applications**: Different services accessing the same database with varying permissions
- **Shared database architecture**: Multiple clients sharing the same Supabase project (not recommended)
- **Compliance requirements**: Industry regulations requiring database-level access controls
- **Defense-in-depth**: Adding an extra security layer beyond application logic

#### How to Enable Row Level Security

If you decide to enable RLS for production:

1. **Enable RLS on Tables** (Supabase Dashboard → Table Editor → Settings):
   ```sql
   -- Enable RLS for all Open WebUI tables
   ALTER TABLE public.user ENABLE ROW LEVEL SECURITY;
   ALTER TABLE public.chat ENABLE ROW LEVEL SECURITY;
   ALTER TABLE public.document ENABLE ROW LEVEL SECURITY;
   -- Repeat for all tables
   ```

2. **Create RLS Policies** (match Open WebUI's application logic):
   ```sql
   -- Example: Users can only access their own chats
   CREATE POLICY "Users can view own chats"
     ON public.chat
     FOR SELECT
     USING (auth.uid() = user_id);

   -- Example: Users can modify their own chats
   CREATE POLICY "Users can update own chats"
     ON public.chat
     FOR UPDATE
     USING (auth.uid() = user_id);
   ```

3. **Test Thoroughly**: Ensure RLS policies don't break existing functionality

**Note**: Open WebUI connects as the `postgres` superuser, which bypasses RLS by default. You'll need to create a dedicated application user with restricted permissions for RLS to be effective.

#### Production Security Best Practices

When deploying to production, implement these additional security measures:

**Database Security:**
- [ ] Review and restrict Supabase API key permissions
- [ ] Enable connection pooling with `pgBouncer` (Transaction Mode)
- [ ] Use SSL/TLS for all database connections (enabled by default)
- [ ] Monitor database access logs in Supabase dashboard
- [ ] Set up database activity alerts
- [ ] Implement IP allowlisting if your infrastructure supports it

**Application Security:**
- [ ] Use environment variables for sensitive credentials (never hardcode)
- [ ] Rotate database passwords regularly
- [ ] Enable audit logging for authentication events
- [ ] Configure OAuth consent screen with privacy policy
- [ ] Restrict OAuth to specific Google Workspace domains
- [ ] Implement rate limiting at nginx/reverse proxy level

**Infrastructure Security:**
- [ ] Use separate Supabase projects per client for isolation
- [ ] Enable container health checks and automatic restarts
- [ ] Implement firewall rules to restrict database access
- [ ] Set up monitoring and alerting for anomalies
- [ ] Regular backup verification and disaster recovery testing
- [ ] Keep Docker images updated for security patches

**Compliance:**
- [ ] Document data retention policies
- [ ] Implement GDPR/privacy regulation requirements
- [ ] Set up encrypted backups with access controls
- [ ] Establish incident response procedures
- [ ] Regular security audits of database permissions

#### Recommended Security Architecture

For production deployments:

```
┌─────────────────────────────────────────────┐
│  Client 1 (client1.example.com)            │
│  ┌─────────────────────────────────────┐   │
│  │ Open WebUI Container                │   │
│  │ - OAuth (domain-restricted)         │───┼──> Supabase Project 1
│  │ - Application-level auth            │   │   (dedicated database)
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│  Client 2 (client2.example.com)            │
│  ┌─────────────────────────────────────┐   │
│  │ Open WebUI Container                │   │
│  │ - OAuth (domain-restricted)         │───┼──> Supabase Project 2
│  │ - Application-level auth            │   │   (dedicated database)
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

**Key Principle**: Database-per-client isolation provides strong security without requiring RLS.

### Multi-Instance Deployments (Future)

Once migrated to PostgreSQL, you can run multiple Open WebUI instances sharing the same database:

```bash
# Instance 1
./start-template.sh client1 8081 client1.example.com

# Instance 2 (sharing same database)
./start-template.sh client2 8082 client2.example.com
```

**Note**: Requires setting the same `DATABASE_URL` in both containers. This feature is not yet automated in the client manager.

## Troubleshooting

### Container Won't Start
```bash
# Check if container name already exists
docker ps -a | grep openwebui-CLIENT_NAME

# Check port conflicts
sudo lsof -i :PORT_NUMBER

# Check logs
docker logs openwebui-CLIENT_NAME
```

### Permission Issues
```bash
# Ensure scripts are executable
chmod +x *.sh
```

### OAuth Issues
1. Verify redirect URI in Google Cloud Console
2. Check domain DNS configuration
3. Ensure nginx proxy is working

## Security Notes

- All clients share the same OAuth configuration but have isolated data
- Each client gets their own session storage and user database
- Data volumes are isolated between clients
- Consider firewall rules for production deployment

## Production Deployment

1. Update domain names in client scripts
2. Configure nginx for each client domain
3. Update Google OAuth redirect URIs
4. Set up SSL certificates for each domain
5. Configure firewall rules
6. Set up monitoring and backups