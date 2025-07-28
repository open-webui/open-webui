# mAI Development Environment Setup

This guide explains how to set up the development environment for mAI using the two-container architecture with hot reload capabilities.

## Overview

The development environment uses a two-container architecture that provides:

- **Frontend Container** (`mai-frontend-dev`): Vite dev server with Hot Module Replacement (HMR) on port 5173
- **Backend Container** (`mai-backend-dev`): FastAPI with uvicorn --reload on port 8080  
- **Independent Hot Reload**: Frontend and backend reload separately without interference
- **Cross-Container Communication**: Docker networking with API proxy
- **Instant Updates**: Sub-second frontend changes via HMR, automatic backend restart

## Prerequisites

1. **OpenRouter Provisioning API Key**
   - Log in to [OpenRouter](https://openrouter.ai)
   - Go to [Provisioning API Keys](https://openrouter.ai/settings/provisioning-keys)
   - Click "Create New Key" and copy it

2. **Docker and Docker Compose**
   ```bash
   docker --version
   docker-compose --version
   ```

3. **Python Environment**
   ```bash
   pip install requests
   ```

## Development Setup

### Step 1: Generate Development Environment Configuration

Run the development environment generator script:

```bash
python generate_client_env_dev.py
```

The script will prompt you for:
- **Provisioning Key**: Your OpenRouter provisioning API key
- **Organization Name**: Client company name (e.g., "ABC Company Sp. z o.o.")
- **Spending Limit**: Either "unlimited" or a dollar amount (e.g., "1000.0")

### Step 2: Generated Files

The script creates:

```bash
.env.dev                # Development environment configuration
```

**Example .env.dev content:**
```bash
# mAI Development Environment Configuration
# Generated on: 2025-01-28T15:30:45.123456
# Organization: ABC Company Sp. z o.o. (DEV)
# Spending Limit: 1000.0

# OpenRouter Configuration (Development Environment)
OPENROUTER_API_KEY=sk-or-v1-YOUR_DEVELOPMENT_API_KEY_HERE
OPENROUTER_HOST=https://openrouter.ai/api/v1
OPENROUTER_EXTERNAL_USER=dev_mai_client_a1b2c3d4

# Organization Configuration  
ORGANIZATION_NAME=ABC Company Sp. z o.o. (DEV)
SPENDING_LIMIT=1000.0
```

### Step 3: Start Development Environment

Use the hot reload management script:

```bash
# Start development environment
./dev-hot-reload.sh up

# Check status
./dev-hot-reload.sh status

# View logs
./dev-hot-reload.sh logs-fe    # Frontend logs
./dev-hot-reload.sh logs-be    # Backend logs
```

### Step 4: Access Development Instance

- **Primary Development URL**: http://localhost:5173
- **Backend API Endpoint**: http://localhost:8080
- **Health Check**: http://localhost:8080/health

## Development Workflow

### Daily Development Commands

```bash
# 1. Start Development Environment
./dev-hot-reload.sh up      # Start both containers with hot reload

# 2. Develop with Instant Updates
# - Edit .svelte, .ts, .css files → Frontend updates instantly via HMR
# - Edit .py files in backend/ → Backend restarts automatically  
# - Access: http://localhost:5173 (main development URL)

# 3. Stop When Done
./dev-hot-reload.sh down    # Stop all containers
```

### Container Management

```bash
# Container Management
./dev-hot-reload.sh status    # Check container status
./dev-hot-reload.sh restart   # Restart both containers
./dev-hot-reload.sh clean     # Clean up containers

# Debugging & Logs  
./dev-hot-reload.sh logs-fe   # Frontend logs
./dev-hot-reload.sh logs-be   # Backend logs
./dev-hot-reload.sh shell-fe  # Access frontend container
./dev-hot-reload.sh shell-be  # Access backend container
./dev-hot-reload.sh help      # Show all available commands
```

## Architecture Benefits

### 🔥 **Hot Reload Development**
- **Frontend**: Instant updates via Vite HMR preserving component state
- **Backend**: Automatic restart on Python file changes
- **No Cache Busting**: Eliminated need for `docker build --no-cache`
- **~10x Faster**: Iteration cycle for UI changes

### 🏗️ **Container Architecture**
- **Independent Reload**: Frontend and backend reload separately
- **Specialized Containers**: Each optimized for its purpose
- **Docker Networking**: Proper container communication
- **Volume Mounts**: Hot reload via bind mounts

### 🔒 **Development Isolation**
- **Separate API Key**: Development API key prefixed with `dev_`
- **Isolated Database**: `mai_backend_dev_data` volume separate from production
- **Environment Variables**: `.env.dev` keeps development config separate
- **Safe Testing**: No impact on production data

## Database Architecture

### Development Database Setup

```bash
# Development uses bind mounts for hot reload
volumes:
  - ./backend:/app/backend                    # Code hot reload
  - mai_backend_dev_data:/app/backend/data   # Database persistence
  - /app/backend/.venv                       # Preserve venv
```

### Verification Commands

```bash
# Check development database
docker exec mai-backend-dev sqlite3 /app/backend/data/webui.db "SELECT COUNT(*) FROM client_user_daily_usage;"

# Verify database initialization
docker exec mai-backend-dev python3 -c "
import sys; sys.path.append('/app/backend')
from open_webui.config import DATA_DIR
print('Development DB path:', DATA_DIR + '/webui.db')
"
```

## Troubleshooting

### Common Development Issues

**1. Containers Not Starting**
```bash
./dev-hot-reload.sh status
./dev-hot-reload.sh logs-be
./dev-hot-reload.sh logs-fe
```

**2. Hot Reload Not Working**
- Check volume mounts are correct
- Verify HMR WebSocket connection in browser console
- Restart containers: `./dev-hot-reload.sh restart`

**3. API Calls Failing**
- Check Docker network connectivity
- Verify Vite proxy configuration in `vite.config.ts`
- Check backend container logs: `./dev-hot-reload.sh logs-be`

**4. Port Conflicts**
- Port 5173 (frontend) or 8080 (backend) already in use
- Stop conflicting services or change ports in docker-compose.dev.yml

### Environment Health Check

```bash
# Full development environment verification
./dev-hot-reload.sh status              # Both containers running
curl http://localhost:5173              # Frontend responds
curl http://localhost:8080/health       # Backend health endpoint

# Test hot reload functionality
# 1. Edit a .svelte file → Check browser updates instantly
# 2. Edit a .py file in backend/ → Check backend restarts in logs
```

### Validation Checklist

- ✅ `.env.dev` file exists with correct content
- ✅ Both containers start successfully
- ✅ Frontend accessible at http://localhost:5173
- ✅ Backend API accessible at http://localhost:8080
- ✅ Hot reload working for both frontend and backend
- ✅ Database initialized and accessible
- ✅ Usage tracking configured and working

## Comparison: Development vs Production

| Aspect | Development | Production |
|--------|-------------|------------|
| **Architecture** | Two containers | Single container |
| **Ports** | 5173 (FE) + 8080 (BE) | 3001 |
| **Hot Reload** | ✅ Vite HMR + uvicorn | ❌ Requires rebuild |
| **Database** | `mai_backend_dev_data` | Client-specific volume |
| **API Key** | `dev_` prefixed | Production key |
| **Environment** | `.env.dev` | `.env` |
| **Startup** | `./dev-hot-reload.sh up` | `docker-compose up` |

## Next Steps

After successful development setup:

1. **Development Ready**: Start coding with instant feedback
2. **Usage Tracking**: Test usage tracking features safely
3. **Production Deploy**: Use `generate_client_env.py` for production `.env`
4. **Multi-Client Testing**: Create multiple `.env.dev` files for different clients

---

**✅ Development Environment**: Optimized for rapid iteration with full production feature parity.