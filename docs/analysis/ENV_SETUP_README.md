# mAI Client Environment Setup

This guide explains how to set up environment-based OpenRouter configuration for mAI client Docker instances.

## Environment Types

- **Production Environment**: Single-container deployment for client instances
- **Development Environment**: Two-container architecture with hot reload capabilities

> 💡 **For Development**: See [ENV_SETUP_DEV_README.md](ENV_SETUP_DEV_README.md) for the two-container development setup with hot reload.

## Overview

The new `.env`-based approach replaces the complex database-driven API key management with simple environment variables. Each client Docker instance gets its own `.env` file with:

- **Dedicated OpenRouter API key** (generated from your provisioning key)
- **Organization configuration** (name, spending limits)
- **External user mapping** (automatic OpenRouter user identification)
- **Complete isolation** between client instances

## Prerequisites

1. **OpenRouter Provisioning API Key**
   - Log in to [OpenRouter](https://openrouter.ai)
   - Go to [Provisioning API Keys](https://openrouter.ai/settings/provisioning-keys)
   - Click "Create New Key" and copy it

2. **Python Environment**
   ```bash
   pip install requests
   ```

## Usage

### Production Environment Setup

#### Step 1: Generate Client Environment

For **production deployment**, run the environment generator script:

```bash
python generate_client_env.py
```

> 📝 **Note**: For development, use `python generate_client_env_dev.py` instead to create `.env.dev` with development-specific configuration.

**Note**: The script now uses Clean Architecture with proper separation of concerns:
- **Domain Layer**: Business entities and validation logic
- **Infrastructure Layer**: OpenRouter API client, database operations, file generation
- **Presentation Layer**: CLI interface and user interactions

The script will prompt you for:
- **Provisioning Key**: Your OpenRouter provisioning API key
- **Organization Name**: Client company name (e.g., "ABC Company Sp. z o.o.")
- **Spending Limit**: Either "unlimited" or a dollar amount (e.g., "1000.0")

#### Step 2: Generated Files

The production script creates:

```bash
.env                    # Production environment configuration for Docker
```

**Development Alternative**: The development script creates `.env.dev` instead to avoid conflicts.

**Example .env content:**
```bash
# mAI Client Environment Configuration
# Generated on: 2025-01-20T15:30:45.123456
# Organization: ABC Company Sp. z o.o.
# Spending Limit: 1000.0

# OpenRouter Configuration
OPENROUTER_API_KEY=sk-or-v1-YOUR_OPENROUTER_API_KEY_HERE
OPENROUTER_HOST=https://openrouter.ai/api/v1
OPENROUTER_EXTERNAL_USER=mai_client_a1b2c3d4

# Organization Configuration  
ORGANIZATION_NAME=ABC Company Sp. z o.o.
SPENDING_LIMIT=1000.0
```

#### Step 3: Production Docker Deployment

1. **Copy .env to deployment directory:**
   ```bash
   cp .env /path/to/client-deployment/
   ```

2. **Update docker-compose.yml:**
   ```yaml
   services:
     mai-app:
       env_file: .env
       # ... rest of configuration
   ```

3. **Deploy:**
   ```bash
   docker-compose up -d
   ```

### Development Environment Setup

For development with hot reload capabilities:

1. **Generate development configuration:**
   ```bash
   python generate_client_env_dev.py
   ```

2. **Start development environment:**
   ```bash
   ./dev-hot-reload.sh up
   ```

3. **Access development instance:**
   - Primary URL: http://localhost:5173
   - Backend API: http://localhost:8080

> 📖 **Full Development Guide**: See [ENV_SETUP_DEV_README.md](ENV_SETUP_DEV_README.md) for complete development setup instructions.

## Production Architecture Benefits

### 🔒 **Security & Isolation**
- Each client gets dedicated API key
- No shared API keys between clients
- Environment variables not tracked in git
- Container-level isolation

### 🚀 **Deployment Simplicity**
- Single .env file per client
- No database seeding required
- Standard Docker configuration pattern
- Easy backup and migration

### 📊 **Usage Tracking Preserved**
- All existing usage tracking functionality maintained
- Automatic external_user mapping
- Real-time cost calculation
- Admin usage dashboards continue working

### 🎯 **Perfect for Multi-Tenant Model**
- 20 client instances = 20 .env files
- Complete data isolation
- Independent scaling per client
- Simplified client onboarding

### 🚀 **Development vs Production**
- **Production**: Single-container, optimized for deployment
- **Development**: Two-container with hot reload for rapid iteration
- **Consistency**: Same environment variables, different container architecture

## User Identification

The system automatically handles unique user identification:

1. **Internal User ID**: Each user has unique `user_id` in Open WebUI
2. **External User Mapping**: OpenRouter returns `external_user` in API responses  
3. **Auto-Learning**: System automatically maps internal users to OpenRouter external users
4. **Persistent Tracking**: Usage tracking works across all user interactions

## Troubleshooting

### Common Issues

**1. Invalid Provisioning Key**
```
❌ Invalid provisioning key. Please check your key and try again.
```
- Verify key starts with `sk-or-`
- Check key is from Provisioning API Keys section (not regular API keys)
- Ensure key has not expired

**2. API Key Creation Failed**
```
❌ Failed to create API key: 402 - Insufficient credits
```
- Add credits to your OpenRouter account
- Check spending limits on provisioning key

**3. Test Request Failed**
```
❌ Test request failed: 401 - Unauthorized
```
- Usually resolves automatically with fallback external_user
- API key is still valid for production use

### Validation

To verify your setup:

1. **Check .env file exists and has correct content**
2. **Verify API key format starts with `sk-or-v1-`**
3. **Test Docker deployment loads environment variables**
4. **Monitor first API requests show usage tracking**

## Environment Comparison

| Aspect | Production | Development |
|--------|-------------|-------------|
| **Script** | `generate_client_env.py` | `generate_client_env_dev.py` |
| **Config File** | `.env` | `.env.dev` |
| **Architecture** | Single container | Two containers |
| **Ports** | 3001 | 5173 (FE) + 8080 (BE) |
| **Hot Reload** | No | Yes (HMR + uvicorn) |
| **External User** | `mai_client_*` | `dev_mai_client_*` |
| **Database** | Client-specific volume | `mai_backend_dev_data` |
| **Startup** | `docker-compose up -d` | `./dev-hot-reload.sh up` |

## Migration from Current System

If migrating from the existing database-driven system:

1. **Run cleanup script first:**
   ```bash
   bash cleanup_current_solution.sh
   ```

2. **Generate new environment configuration:**
   - Production: `python generate_client_env.py`
   - Development: `python generate_client_env_dev.py`
3. **Update application code to read from environment variables**
4. **Deploy with new configuration**

## Support

For issues or questions:
- Check Docker logs: `docker-compose logs mai-app`
- Verify .env file permissions (should be 600)
- Ensure all environment variables are properly set
- Monitor OpenRouter usage in their dashboard

## Quick Reference

### Production Deployment
```bash
python generate_client_env.py          # Generate .env
docker-compose up -d                   # Deploy
```

### Development Environment
```bash
python generate_client_env_dev.py      # Generate .env.dev
./dev-hot-reload.sh up                 # Start dev environment
# Access: http://localhost:5173
```

---

**✅ Ready for Production**: This approach is production-ready and scales perfectly for your 20-client deployment model with full development environment support.