# Development Strategy

## 1. Branch Management

### Main Branches
- `main` - Production code
- `release` - Testing and validation
- `develop` - Integration testing

### Working Branches
- Features: `feature/<team>/<feature-name>`
- Fixes: `hotfix/<issue-name>`
- Sub-tasks: `sub/<team>/<task-name>`

## 2. Environment Setup

### Development Environment Variables
Required:
- `OLLAMA_BASE_URL` - Ollama API endpoint
- `WEBUI_SECRET_KEY` - Security key for the application

Optional:
- `OPENAI_API_BASE_URL` - OpenAI API endpoint
- `OPENAI_API_KEY` - OpenAI API key
- `AUTOMATIC1111_BASE_URL` - Stable Diffusion endpoint
- `OLLAMA_GPU_DRIVER` - GPU driver for Docker
- `OLLAMA_GPU_COUNT` - Number of GPUs to use
- `OPEN_WEBUI_PORT` - Port for the web interface (default: 3000)

Analytics (disabled by default):
- `SCARF_NO_ANALYTICS=true`
- `DO_NOT_TRACK=true`
- `ANONYMIZED_TELEMETRY=false`

### Local Development
1. Setup Steps:
   ```bash
   # Clone repository
   git clone <repository-url>
   
   # Create environment file
   cp .env.example .env.development
   
   # Install dependencies
   npm install
   pip install -e ".[dev]"
   ```

2. Run Services:
   ```bash
   # Start Ollama
   docker-compose up ollama
   
   # Start WebUI in dev mode
   npm run dev
   ```

### Testing Environment
1. Deployment:
   - Triggered by merges to `release` branch
   - Uses `.github/workflows/integration-test.yml` for integration tests
   - Uses `.github/workflows/format-build-frontend.yaml` for frontend builds
   - Runs integration tests with Cypress
   - Includes database migration tests (SQLite, PostgreSQL)

2. Validation Steps:
   - Unit tests (Python & Node.js)
   - Performance tests
   - Security scanning (Snyk)

### Production Environment
1. Deployment:
   - Triggered by merges to `main` branch
   - Uses `.github/workflows/docker-build.yaml` for multi-platform Docker images (amd64/arm64)
   - Uses `.github/workflows/format-build-frontend.yaml` for frontend builds
   - Uses `.github/workflows/format-backend.yaml` for backend formatting
   - Uses `.github/workflows/release-pypi.yml` for PyPI releases
   - Uses `.github/workflows/build-release.yml` for GitHub releases
   - Uses `.github/workflows/deploy-to-hf-spaces.yml` for Hugging Face Spaces deployment
   - Builds and publishes Docker images and Python packages

2. Configuration:
   - Uses production environment variables
   - Requires `WEBUI_SECRET_KEY`
   - Optional: `HF_TOKEN` for Hugging Face Spaces deployment
   - Optional: Analytics and monitoring

3. Docker Images:
   - Main image: Multi-platform support (amd64/arm64)
   - CUDA image: For GPU support
   - Ollama image: For Ollama integration

## 3. Implementation Checklist

### Phase 1: Local Setup
- [x] Configure local development environment
- [x] Set up Docker containers
- [ ] Verify hot-reloading
- [ ] Test local builds
- [x] Configure PostgreSQL database

### Phase 2: Testing Pipeline
- [ ] Configure GitHub Actions
- [ ] Set up test environment
- [ ] Implement automated tests
- [ ] Configure security scanning

### Phase 3: Production Deployment
- [ ] Set up production environment
- [ ] Configure monitoring
- [ ] Implement backup strategy
- [ ] Document deployment process

## 4. Service Architecture

### Core Services
1. Ollama Service
   - Container: `ollama`
   - Port: 11434
   - Volume: `ollama:/root/.ollama`

2. PostgreSQL Service
   - Container: `whatever-db`
   - Port: 5432
   - Volume: `postgres_data:/var/lib/postgresql/data`
   - Environment:
     - POSTGRES_USER
     - POSTGRES_PASSWORD
     - POSTGRES_DB

3. WebUI Service
   - Container: `whatever`
   - Port: 3000 (configurable)
   - Volume: `whatever:/app/backend/data`
   - Dependencies: 
     - Ollama service
     - PostgreSQL service

### Integration Points
- Ollama API endpoint
- Optional: OpenAI API
- Optional: AUTOMATIC1111
