# Local Development Setup

This document provides detailed instructions for setting up the Whatever development environment locally. Whatever is a fork of Open WebUI that will become its own project with unique features and capabilities.

## Prerequisites

Before starting, ensure you have the following installed:
- Git
- Node.js (version 22 or higher)
- Python 3.11 or higher
- Docker and Docker Compose
- A code editor (VS Code recommended)

## Step-by-Step Setup

### 1. Repository Setup
```bash
# Clone the repository
git clone <repository-url>
cd whatever

# Create a Python virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
.\venv\Scripts\activate
# On Unix or MacOS:
source venv/bin/activate
```

### 2. Environment Configuration
```bash
# Copy the example environment file
cp .env.example .env.development

# Open .env.development and configure the following required variables:
# - OLLAMA_BASE_URL (default: http://localhost:11434)
# - WEBUI_SECRET_KEY (generate a secure random key)

# Optional environment variables:
# - OPENAI_API_BASE_URL: For OpenAI API integration
# - OPENAI_API_KEY: Your OpenAI API key
# - AUTOMATIC1111_BASE_URL: For Stable Diffusion integration (default: http://localhost:7860)
# - OLLAMA_GPU_DRIVER: GPU driver for Docker (default: nvidia)
# - OLLAMA_GPU_COUNT: Number of GPUs to use (default: 1)

# Analytics settings (all disabled by default):
# - SCARF_NO_ANALYTICS=true
# - DO_NOT_TRACK=true
# - ANONYMIZED_TELEMETRY=false
```

### 3. Install Dependencies

#### Python Dependencies
```bash
# Install Python packages with development dependencies
pip install -e ".[dev]"
```

#### Node.js Dependencies
```bash
# Install Node.js packages
npm install
```

### 4. Database Setup

The application uses SQLAlchemy with support for multiple databases:
- PostgreSQL (recommended for production)
- SQLite (default for development)

The database will be automatically initialized on first run.

### 5. Starting the Development Environment

#### Start Ollama Service
```bash
# Using Docker Compose
docker-compose up ollama

# Or if you have Ollama installed locally
ollama serve
```

#### Start the Development Server
```bash
# Start the frontend development server
npm run dev
```

The application will be available at `http://localhost:3000` by default.

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

## Docker Development Environment

If you prefer to run the entire stack in Docker:

```bash
# Start all services (CPU only)
docker-compose up -d

# For GPU support, add the gpu config:
docker-compose -f docker-compose.yaml -f docker-compose.gpu.yaml up -d

# View logs
docker-compose logs -f
```

The application will be available at `http://localhost:3000` by default (configurable via OPEN_WEBUI_PORT).

### Available Docker Images

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
