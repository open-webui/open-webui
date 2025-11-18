# Open WebUI Deployment on AWS Lightsail

This guide explains how to deploy Open WebUI with Azure OpenAI on AWS Lightsail using Docker.

## Prerequisites

- AWS Lightsail instance (Ubuntu 22.04 LTS recommended)
- Docker and Docker Compose installed
- Azure OpenAI resource with API key
- Domain configured (optional but recommended for production)

## Quick Start

### 1. SSH into your Lightsail instance
```bash
ssh -i ~/.ssh/your-key.pem ubuntu@YOUR_LIGHTSAIL_IP
```

### 2. Clone the repository
```bash
git clone https://github.com/open-webui/open-webui.git
cd open-webui
```

### 3. Configure Azure OpenAI credentials
```bash
# Copy the environment template
cp azure.env.example azure.env

# Edit with your actual Azure OpenAI details
nano azure.env
```

Update the following values in `azure.env`:
```bash
AZURE_OPENAI_BASE_URL=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-azure-api-key-here
AZURE_OPENAI_API_VERSION=2024-02-01
WEBUI_SECRET_KEY=your-secret-key-here
ENABLE_SIGNUP=false
```

### 4. Start the container

#### Option A: Direct Azure OpenAI (recommended first try)
```bash
docker compose -f docker-compose.azure.yml --env-file azure.env up -d
```

#### Option B: Using LiteLLM Proxy (if direct connection doesn't work)
```bash
# Copy LiteLLM configuration files
cp litellm_config.yaml ~/
cp litellm.env ~/

# Start with LiteLLM proxy
docker compose -f docker-compose.litellm.yml --env-file litellm.env up -d
```

### 5. Access your application
- **Direct access**: `http://YOUR_LIGHTSAIL_IP:3000`
- **With domain**: `https://dev.owu.app.bio-rad.com` (if configured)

## Management Commands

### View running containers
```bash
docker ps
```

### View logs
```bash
docker compose -f docker-compose.azure.yml logs -f
```

### Stop the application
```bash
# Stop all services
docker compose -f docker-compose.azure.yml --env-file azure.env down

# Or stop specific service
docker compose -f docker-compose.azure.yml --env-file azure.env stop open-webui
```

### Start/Restart the application
```bash
# Start all services
docker compose -f docker-compose.azure.yml --env-file azure.env up -d

# Or start specific service (recommended)
docker compose -f docker-compose.azure.yml --env-file azure.env up -d open-webui
```

### Update configuration or restart
```bash
# Stop the specific service
docker compose -f docker-compose.azure.yml --env-file azure.env stop open-webui

# Start with updated configuration
docker compose -f docker-compose.azure.yml --env-file azure.env up -d open-webui
```

### Update to latest version
```bash
# Pull latest image
docker compose -f docker-compose.azure.yml pull

# Restart with new image
docker compose -f docker-compose.azure.yml --env-file azure.env up -d open-webui
```

### Backup data
```bash
# Create backup of persistent data
docker run --rm -v open-webui_open-webui-data:/data -v $(pwd):/backup ubuntu tar czf /backup/open-webui-backup-$(date +%Y%m%d).tar.gz /data
```

### Restore data
```bash
# Restore from backup
docker run --rm -v open-webui_open-webui-data:/data -v $(pwd):/backup ubuntu tar xzf /backup/open-webui-backup-YYYYMMDD.tar.gz -C /
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AZURE_OPENAI_BASE_URL` | Your Azure OpenAI endpoint | Required |
| `AZURE_OPENAI_API_KEY` | Your Azure OpenAI API key | Required |
| `AZURE_OPENAI_API_VERSION` | API version | `2024-02-01` |
| `WEBUI_SECRET_KEY` | Secret key for sessions | Auto-generated |
| `ENABLE_SIGNUP` | Allow user registration | `false` |
| `WEBUI_DOCKER_TAG` | Docker image tag | `main` |

### Port Configuration

The application runs on:
- **Container port**: 8080
- **Host port**: 3000
- **Mapping**: `0.0.0.0:3000:8080`

### Volume Mounts

- **Data persistence**: `open-webui-data:/app/backend/data`
- Contains user data, conversations, and uploaded files

## Troubleshooting

### Container won't start
```bash
# Check logs for errors
docker-compose -f docker-compose.azure.yml logs

# Check container status
docker ps -a
```

### Permission denied errors
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in
exit
ssh -i ~/.ssh/your-key.pem ubuntu@YOUR_LIGHTSAIL_IP
```

### Port already in use
```bash
# Check what's using port 3000
sudo netstat -tulpn | grep :3000

# Stop conflicting services
docker stop container-name
```

### Azure OpenAI connection issues
1. Verify your API key and endpoint URL
2. Check Azure OpenAI resource is active
3. Ensure API version is supported
4. Check firewall/network settings

### Domain not working
1. Verify DNS points to Lightsail IP
2. Check Nginx configuration
3. Ensure SSL certificates are valid
4. Check Lightsail firewall rules

## Security Considerations

### Production Deployment
- Set `ENABLE_SIGNUP=false` to disable public registration
- Use strong `WEBUI_SECRET_KEY`
- Configure proper SSL/TLS with valid certificates
- Restrict access with firewall rules
- Regular backups of data volume

### Lightsail Firewall
Ensure these ports are open:
- **Port 80**: HTTP (for SSL certificate generation)
- **Port 443**: HTTPS (for secure access)
- **Port 3000**: Direct container access (optional)

## File Structure

```
open-webui/
├── docker-compose.azure.yml    # Azure-specific compose file
├── azure.env                   # Environment variables
├── lightsail/
│   ├── README.md              # This file
│   ├── install-docker.sh      # Docker installation script
│   └── deploy-git.sh          # Git-based deployment script
└── ...
```

## Support

For issues and questions:
- **Open WebUI Documentation**: https://docs.openwebui.com/
- **GitHub Issues**: https://github.com/open-webui/open-webui/issues
- **Discord Community**: https://discord.gg/5rJgQTnV4s

## License

This project is licensed under the MIT License - see the LICENSE file for details.
