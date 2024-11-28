# Local Development Setup

This document provides detailed instructions for setting up the Whatever development environment locally. Whatever is a fork of Open WebUI that will become its own project with unique features and capabilities.

## Prerequisites

Before starting, ensure you have the following installed:
- Git
- Node.js (version 22 or higher)
- Python 3.11 or higher
- Docker and Docker Compose
- A code editor (VS Code recommended)

## Docker Development Strategy

Due to local compatibility issues, development will be conducted entirely within Docker containers. This approach ensures consistency across environments and simplifies dependency management.

### Docker Setup
- Ensure Docker and Docker Compose are installed and configured.
- Use Docker Compose to manage service orchestration.

### Starting the Development Environment

#### Start All Services
```bash
# Start all services using Docker Compose
# CPU only
docker-compose up -d

# For GPU support, add the gpu config:
docker-compose -f docker-compose.yaml -f docker-compose.gpu.yaml up -d
```

The application will be available at `http://localhost:3000` by default (configurable via OPEN_WEBUI_PORT).

## Development Workflow

### Branch Management
- Main development happens in the `develop` branch
- Feature branches should be created from `develop`:
  - Features: `feature/<team>/<feature-name>`
  - Fixes: `hotfix/<issue-name>`
  - Sub-tasks: `sub/<team>/<task-name>`

### Code Formatting and Linting
```bash
# Format frontend code
npm run format

# Format backend code (requires Python 3.11+)
npm run format:backend

# Run linting
npm run lint
```

### Running Tests
```bash
# Frontend tests
npm run test:frontend

# Run Cypress tests
npm run cy:open
```

## Available Docker Images

The project provides several Docker images to suit different needs:
- Main image: Multi-platform support (amd64/arm64)
- CUDA image: For systems with NVIDIA GPU support
- Ollama image: Optimized for Ollama integration

To use a specific image variant, modify your docker-compose.yaml accordingly.

## Troubleshooting

### Common Issues

1. **Ollama Connection Issues**
   - Ensure Ollama is running and accessible
   - Check the OLLAMA_BASE_URL in your .env.development file
   - Verify no firewall is blocking port 11434

2. **Node.js Dependencies**
   - If you encounter module not found errors, try:
     ```bash
     rm -rf node_modules
     npm install
     ```

3. **Python Dependencies**
   - If you encounter import errors, ensure your virtual environment is activated
   - Try reinstalling dependencies:
     ```bash
     pip install -e ".[dev]" --force-reinstall
     ```

## Additional Resources

- Original Open WebUI Documentation: [Link to docs]
- Project Strategy Document: `docs/STRATEGY.md`
- Contribution Guidelines: `CONTRIBUTING.md`

## Support

For additional help:
1. Check the `TROUBLESHOOTING.md` file
2. Create an issue in the GitHub repository
3. Reach out to the development team

Remember to keep your local environment up to date by regularly pulling changes from the repository and updating dependencies as needed.
