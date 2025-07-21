# mAI Deployment System

## Overview
This directory contains everything needed to deploy mAI for production use and manage client-specific customizations.

## Quick Start

### 1. Deploy Version Zero
```bash
# Tag and deploy your current stable version
git tag v0.0.0
docker build -t mai:v0.0.0 .
docker push ghcr.io/pilpat/mai:v0.0.0
```

### 2. Update from Open WebUI
```bash
# Automated update process
./scripts/update-from-upstream.sh
```

### 3. Deploy for a Client
```bash
# Copy template
cp -r deployments/clients/template deployments/clients/client-name

# Configure
nano deployments/clients/client-name/config/client.yaml

# Deploy
cd deployments/clients/client-name
docker compose up -d
```

## Directory Structure
```
deployments/
├── README.md           # This file
├── clients/           # Client-specific configurations
│   ├── template/      # Template for new clients
│   └── example-client/# Example configuration
├── scripts/           # Deployment automation
└── docs/             # Documentation
    └── HETZNER-DEPLOYMENT-GUIDE.md
```

## Key Features

### Version Management
- **v0.0.0**: Your stable production baseline
- **v0-stable branch**: Frozen version for production
- **Automated updates**: Script to merge Open WebUI updates

### Client Customization
- Configuration-based customization (future)
- Per-client branding and features
- Isolated deployments

### Production Ready
- Docker-based deployment
- SSL/TLS support
- Automated backups
- Health monitoring

## Workflow

### For New Clients
1. Copy the template directory
2. Customize `client.yaml`
3. Add client assets (logos, etc.)
4. Deploy using Docker Compose
5. Configure DNS and SSL

### For Updates
1. Run update script to get latest Open WebUI
2. Test in development environment
3. Deploy to staging
4. Roll out to production clients

### For Maintenance
- Use monitoring scripts
- Automated backup runs daily
- Check logs regularly
- Update SSL certificates

## Configuration Options

### Branding
- Application name
- Taglines (multi-language)
- Logos and favicons
- Color schemes

### Features
- Background patterns
- Custom themes
- Font controls
- Language options
- Authentication methods

### Infrastructure
- Server specifications
- Database type
- Backup schedule
- Monitoring setup

## Security

### Best Practices
- Use environment variables for secrets
- Enable firewall rules
- Configure rate limiting
- Regular security updates
- Automated backups

### Client Isolation
- Separate databases
- Individual configurations
- Isolated Docker networks
- Per-client SSL certificates

## Support

### Documentation
- [Hetzner Deployment Guide](../docs/deployment/hetzner-guide.md)
- [Customization Plan](../docs/customization/extraction-plan.md)
- [Upgrade Guide](../docs/development/upgrade-guide.md)

### Troubleshooting
1. Check Docker logs: `docker compose logs`
2. Verify configurations: `docker compose config`
3. Test health endpoint: `curl http://localhost:8080/health`
4. Review system resources: `docker stats`

## Future Roadmap

### Phase 1 (Current)
- ✅ Version zero established
- ✅ Basic deployment structure
- ✅ Update automation

### Phase 2 (Next)
- [ ] Configuration-based customization
- [ ] CI/CD pipeline
- [ ] Automated testing

### Phase 3 (Future)
- [ ] Multi-region deployment
- [ ] Advanced monitoring
- [ ] A/B testing support

## License
mAI follows the Open WebUI license requirements. Ensure compliance for deployments over 50 users.