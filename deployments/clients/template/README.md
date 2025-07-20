# Client Deployment Template

This directory contains the template for deploying mAI for a specific client.

## Structure
```
template/
├── config/
│   └── client.yaml      # Client configuration
├── assets/             # Client-specific assets (logos, etc.)
├── .env.example        # Environment variables template
├── docker-compose.yml  # Docker deployment config
└── README.md          # This file
```

## Setup Instructions

1. **Copy Template**
   ```bash
   cp -r deployments/clients/template deployments/clients/[client-name]
   ```

2. **Configure Client**
   - Edit `config/client.yaml` with client details
   - Add client logos to `assets/` directory
   - Copy `.env.example` to `.env` and fill in values

3. **Deploy**
   ```bash
   cd deployments/clients/[client-name]
   ./deploy.sh
   ```

## Configuration Guide

### Required Fields
- `client.id` - Unique identifier (used in URLs, Docker images)
- `client.domain` - Production domain
- `branding.appName` - Client's branded name

### Optional Customizations
- Theme selection
- Feature toggles
- Authentication providers
- Integration settings

## Security Checklist
- [ ] Generate secure secret keys
- [ ] Configure SSL certificates
- [ ] Set up firewall rules
- [ ] Enable rate limiting
- [ ] Configure backup schedule
- [ ] Set up monitoring alerts

## Support
For assistance, contact the mAI deployment team.