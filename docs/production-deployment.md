# mAI Production Deployment Guide

## Overview

This guide covers the production-ready deployment of mAI OpenRouter model filtering across multiple client instances. The system restricts OpenRouter access to exactly 12 approved models for cost control and consistent user experience.

## Architecture

### Multi-Tenant Setup
- **Target**: ~20 small companies (5-20 employees each)
- **Infrastructure**: Single Hetzner Cloud server
- **Isolation**: Separate Docker containers per client
- **Configuration**: Environment-based with centralized model filtering

### Model Filtering
- **Total Available Models**: 317+ from OpenRouter
- **Filtered Models**: Exactly 12 approved models
- **Implementation**: `OPENAI_API_CONFIGS` environment variable
- **Validation**: Automatic configuration validation and rollback

## Prerequisites

1. **Docker & Docker Compose** installed
2. **Python 3.11+** with required packages
3. **OpenRouter API keys** for each client
4. **Hetzner Cloud server** with sufficient resources

## Production Scripts

### Core Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/production/model_filtering_config.py` | Centralized model configuration | `python model_filtering_config.py --summary` |
| `scripts/production/deploy_model_filtering.py` | Single-instance deployment | `python deploy_model_filtering.py --deploy` |
| `scripts/production/multi_client_deploy.py` | Multi-client deployment | `python multi_client_deploy.py --deploy-all` |

### Configuration Files

| File | Purpose | 
|------|---------|
| `scripts/production/env_template.env` | Environment template for clients |
| `scripts/production/clients.yaml.example` | Client configuration example |

## Deployment Process

### 1. Initial Setup

```bash
# Clone and prepare repository
git clone <repository-url>
cd mAI
git checkout customization

# Install dependencies
pip install pyyaml

# Create client configuration
cp scripts/production/clients.yaml.example scripts/production/clients.yaml
# Edit clients.yaml with actual client data
```

### 2. Configure Clients

Edit `scripts/production/clients.yaml`:

```yaml
clients:
  - name: "company_a"
    organization_name: "Company A Sp. z o.o."
    openrouter_api_key: "sk-or-v1-YOUR_ACTUAL_KEY"
    external_user_id: "mai_client_company_a_001"
    port_offset: 0
    server_ip: "192.168.1.100"
```

### 3. Validate Configuration

```bash
# Validate all client configurations
python scripts/production/multi_client_deploy.py --validate

# Validate model filtering configuration
python scripts/production/model_filtering_config.py --summary
```

### 4. Deploy to All Clients

```bash
# Dry run first
python scripts/production/multi_client_deploy.py --deploy-all --dry-run

# Actual deployment
python scripts/production/multi_client_deploy.py --deploy-all
```

### 5. Deploy Single Client

```bash
# Deploy specific client
python scripts/production/multi_client_deploy.py --deploy-client company_a

# Deploy with production build and verification
python scripts/production/deploy_model_filtering.py --deploy
```

## The 12 Approved Models

| # | Provider | Model ID |
|---|----------|----------|
| 1 | Anthropic | `anthropic/claude-sonnet-4` |
| 2 | Google | `google/gemini-2.5-flash` |
| 3 | Google | `google/gemini-2.5-pro` |
| 4 | DeepSeek | `deepseek/deepseek-chat-v3-0324` |
| 5 | Anthropic | `anthropic/claude-3.7-sonnet` |
| 6 | Google | `google/gemini-2.5-flash-lite-preview-06-17` |
| 7 | OpenAI | `openai/gpt-4.1` |
| 8 | xAI | `x-ai/grok-4` |
| 9 | OpenAI | `openai/gpt-4o-mini` |
| 10 | OpenAI | `openai/o4-mini-high` |
| 11 | OpenAI | `openai/o3` |
| 12 | OpenAI | `openai/chatgpt-4o-latest` |

## Configuration Management

### Environment Variables

Key environment variables for each client:

```bash
# Client-specific
ORGANIZATION_NAME="Company A Sp. z o.o."
OPENROUTER_API_KEY="sk-or-v1-client-specific-key"
OPENROUTER_EXTERNAL_USER="mai_client_company_a_001"

# Model filtering (identical across all clients)
OPENAI_API_CONFIGS='{"0":{"enable":true,"connection_type":"external","model_ids":[...]}}'
```

### Port Allocation

Each client uses unique ports to avoid conflicts:

- **Client A**: Frontend 3000, Backend 8080 (offset 0)
- **Client B**: Frontend 3010, Backend 8090 (offset 10)
- **Client C**: Frontend 3020, Backend 8100 (offset 20)

## Monitoring and Validation

### Deployment Verification

```bash
# Verify specific deployment
python scripts/production/deploy_model_filtering.py --verify-only

# Check configuration loading
docker-compose logs | grep "Number of API configs: 1"
docker-compose logs | grep "model_ids"
```

### Health Checks

Monitor for these log entries:
- `✅ Number of API configs: 1` - Configuration loaded
- `✅ Using exact model IDs for idx 0` - Filtering active
- `✅ Models count before filtering: 12` - Correct model count

## Backup and Recovery

### Automatic Backups

The deployment script automatically creates backups:

```bash
# Backups stored in
backups/model-filtering/backup_YYYYMMDD_HHMMSS/
├── .env
├── docker-compose-customization.yaml
└── webui.db
```

### Manual Backup

```bash
# Create backup only
python scripts/production/deploy_model_filtering.py --backup-only
```

### Rollback Procedure

```bash
# Automatic rollback on deployment failure
# Manual rollback to specific backup
cp backups/model-filtering/backup_20250125_140000/.env .
docker-compose restart
```

## Troubleshooting

### Common Issues

1. **No models showing**
   - Check: `OPENAI_API_CONFIGS` environment variable
   - Verify: JSON syntax is valid
   - Logs: Look for "Number of API configs: 0"

2. **All models showing (317+)**
   - Check: Model filtering configuration not loaded
   - Verify: Container restart after configuration change
   - Logs: Look for "Config: {}" (empty config)

3. **Port conflicts**
   - Check: `clients.yaml` port_offset values
   - Verify: No duplicate port assignments
   - Fix: Update port_offset for conflicting clients

### Debug Commands

```bash
# Check current configuration
python scripts/production/model_filtering_config.py --summary

# Validate JSON configuration
python scripts/production/model_filtering_config.py --validate-json "$OPENAI_API_CONFIGS"

# Check container logs
docker-compose logs --tail=100 | grep -E "(model|config|openai)"

# Verify environment variables
docker exec CONTAINER_NAME env | grep OPENAI_API_CONFIGS
```

## Security Considerations

1. **API Key Management**
   - Each client has separate OpenRouter API key
   - Keys stored in environment variables (not code)
   - Regular key rotation recommended

2. **Access Control**
   - Container isolation between clients
   - No shared databases or volumes
   - Network isolation where possible

3. **Configuration Validation**
   - All configurations validated before deployment
   - Automatic rollback on validation failure
   - Audit trail of configuration changes

## Maintenance

### Updating Model List

To update the approved model list:

1. Edit `PRODUCTION_MODEL_CONFIG` in `model_filtering_config.py`
2. Validate new configuration
3. Deploy to test instance first
4. Deploy to all production clients

```bash
# Validate new configuration
python scripts/production/model_filtering_config.py --validate-json "NEW_CONFIG"

# Deploy to all clients
python scripts/production/multi_client_deploy.py --deploy-all
```

### Adding New Clients

1. Add client configuration to `clients.yaml`
2. Ensure unique port allocation
3. Deploy client-specific configuration

```bash
# Add to clients.yaml, then:
python scripts/production/multi_client_deploy.py --deploy-client new_client_name
```

## Support and Monitoring

### Log Monitoring

Key log patterns to monitor:
- Model filtering activation
- Configuration loading errors
- Container startup issues
- API connectivity problems

### Performance Monitoring

- Container resource usage
- API response times
- Model request patterns
- Error rates per client

---

## Quick Reference

```bash
# Complete production deployment
python scripts/production/multi_client_deploy.py --deploy-all

# Single client deployment
python scripts/production/deploy_model_filtering.py --deploy

# Configuration validation
python scripts/production/model_filtering_config.py --summary

# Emergency rollback
cp backups/model-filtering/backup_LATEST/.env . && docker-compose restart
```