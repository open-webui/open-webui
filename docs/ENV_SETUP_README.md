# mAI Client Environment Setup

This guide explains how to set up environment-based OpenRouter configuration for mAI client Docker instances.

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

### Step 1: Generate Client Environment

Run the environment generator script:

```bash
python generate_client_env.py
```

The script will prompt you for:
- **Provisioning Key**: Your OpenRouter provisioning API key
- **Organization Name**: Client company name (e.g., "ABC Company Sp. z o.o.")
- **Spending Limit**: Either "unlimited" or a dollar amount (e.g., "1000.0")

### Step 2: Generated Files

The script creates:

```bash
.env                    # Environment configuration for Docker
```

**Example .env content:**
```bash
# mAI Client Environment Configuration
# Generated on: 2025-01-20T15:30:45.123456
# Organization: ABC Company Sp. z o.o.
# Spending Limit: 1000.0

# OpenRouter Configuration
OPENROUTER_API_KEY=sk-or-v1-abc123def456...
OPENROUTER_HOST=https://openrouter.ai/api/v1
OPENROUTER_EXTERNAL_USER=mai_client_a1b2c3d4

# Organization Configuration  
ORGANIZATION_NAME=ABC Company Sp. z o.o.
SPENDING_LIMIT=1000.0
```

### Step 3: Docker Deployment

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

## Architecture Benefits

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

## Migration from Current System

If migrating from the existing database-driven system:

1. **Run cleanup script first:**
   ```bash
   bash cleanup_current_solution.sh
   ```

2. **Generate new .env configuration**
3. **Update application code to read from environment variables**
4. **Deploy with new configuration**

## Support

For issues or questions:
- Check Docker logs: `docker-compose logs mai-app`
- Verify .env file permissions (should be 600)
- Ensure all environment variables are properly set
- Monitor OpenRouter usage in their dashboard

---

**✅ Ready for Production**: This approach is production-ready and scales perfectly for your 20-client deployment model.