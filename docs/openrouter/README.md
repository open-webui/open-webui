# OpenRouter Configuration for mAI

This directory contains all documentation and scripts related to configuring OpenRouter model restrictions in mAI (Open WebUI).

## 📁 Directory Structure

### Documentation
- `production-config.md` - Production deployment guide with best practices
- `manage-models.md` - Comprehensive guide for managing OpenRouter models
- `quick-reference.md` - Quick commands and one-liners
- `debug-findings.md` - Technical analysis from debugging the issue
- `initial-implementation.md` - Initial approach (for reference)

### Scripts (`/scripts/openrouter/`)
- `production_fix.py` - Production-ready initialization script (recommended)
- `manage_models.py` - Model management utility
- `fix_openrouter_docker.py` - Direct database fix for Docker deployments
- `verify_config.py` - Configuration verification tool

## 🚀 Quick Start

### For Production Deployment

**Note: OpenRouter scripts are now included in the Docker image (as of July 2025)**

1. Build the Docker image:
   ```bash
   docker build -t mai-production:latest .
   ```

2. Run the initialization script on first deployment:
   ```bash
   docker exec mai-prod python /app/scripts/openrouter/production_fix.py init
   ```

3. Verify configuration:
   ```bash
   docker exec mai-prod python /app/scripts/openrouter/verify_config.py
   ```

### For Managing Models

```bash
# List current models
docker exec mai-prod python /app/scripts/openrouter/manage_models.py list

# Add a model
docker exec mai-prod python /app/scripts/openrouter/manage_models.py add "anthropic/claude-3-opus"

# Remove a model
docker exec mai-prod python /app/scripts/openrouter/manage_models.py remove "openai/o3"
```

## 📝 Key Files to Keep

### Essential for Production:
1. `/scripts/openrouter/production_fix.py` - Main production script
2. `/scripts/openrouter/manage_models.py` - For ongoing management
3. `/docs/openrouter/production-config.md` - Production deployment guide
4. `/docs/openrouter/quick-reference.md` - Quick reference

### Can Be Deleted (Development/Debug Only):
- `check_db_schema.py` - One-time schema investigation
- `diagnose_openrouter.py` - Initial debugging
- `test_openrouter_config.py` - Testing script
- `setup_openrouter_models.py` - Early attempt
- `fix_openrouter_config.py` - Superseded by production_fix.py
- `openrouter_models_config.json` - Test configuration file

## 🔧 How It Works

The solution leverages Open WebUI's PersistentConfig system:

1. **Initial Setup**: Set `OPENROUTER_ALLOWED_MODELS` environment variable
2. **Persistence**: Configuration is stored in the database
3. **Management**: Update through Admin UI or management scripts
4. **No Restarts**: Changes take effect immediately

## 🎯 Best Practices

1. **Use Environment Variables** for initial deployment
2. **Use PersistentConfig** - it's designed for production
3. **Avoid Manual Database Edits** after initial setup
4. **Document Model Changes** for audit trail

## 📚 Additional Resources

- See `production-config.md` for detailed production setup
- See `manage-models.md` for comprehensive management guide
- See `quick-reference.md` for quick commands