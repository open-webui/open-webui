# Local Setup Implementation Checklist

## Pre-setup Requirements
- [x] Install Git
  - Git version 2.37.3 installed
- [x] Install Node.js v22 or higher
  - [x] Verify installation: `node --version` (v22.11.0)
- [x] Install Python 3.11 or higher
  - [x] Verify installation: `python --version` (Python 3.11.0)
- [x] Install Docker and Docker Compose
  - [x] Verify Docker installation: `docker --version` (27.2.0)
  - [x] Verify Docker Compose installation: `docker compose version`
- [x] Install VS Code (recommended) or preferred code editor

## Environment Management Strategy

To ensure scalability and clear segregation of responsibilities, all environments will be managed using Docker and Docker Compose. This includes development, testing, and production environments.

### Docker Compose Profiles
- Utilize Docker Compose profiles to manage different configurations for each environment.
- Activate profiles using the `--profile` flag to switch between environments.

### Separate Compose Files
- Create separate Docker Compose files for each environment:
  - `docker-compose.dev.yaml`
  - `docker-compose.test.yaml`
  - `docker-compose.prod.yaml`
- Use the `-f` flag to specify which compose file to use.

### Environment-Specific Variables
- Define environment-specific variables in `.env` files:
  - `.env.development`
  - `.env.testing`
  - `.env.production`
- Reference these files in Docker Compose using the `env_file` directive.

### Modular Dockerfiles
- Use a base Dockerfile for common configurations and extend it for environment-specific needs.
- Example: `FROM base AS development` or `FROM base AS production`.

### CI/CD Integration
- Integrate Docker and Docker Compose with CI/CD pipelines for automated environment setup and deployment.

### Network and Volume Management
- Use Docker networks to isolate services in different environments.
- Define volumes for persistent data storage and scope them appropriately.

## Repository Setup
- [x] Fork the Open WebUI repository to your GitHub account
- [x] Clone your forked repository:
  ```bash
  git clone <your-fork-url>
  cd whatever
  ```
- [x] Rename project references from "open-webui" to "whatever"
  - [x] Update package.json name
  - [x] Update pyproject.toml name
  - [x] Update Docker image names in docker-compose files
  - [ ] Update any other project-specific naming

## Environment Configuration
- [x] Create development environment file:
  ```bash
  cp .env.example .env.development
  ```
- [x] Configure required environment variables in `.env.development`:
  - [x] Set `OLLAMA_BASE_URL` (verify default: http://localhost:11434)
  - [x] Generate and set `WEBUI_SECRET_KEY`
- [x] Configure optional environment variables (if needed):
  - [ ] Set `OPENAI_API_BASE_URL` for OpenAI integration
  - [ ] Set `OPENAI_API_KEY` for OpenAI integration
  - [ ] Set `AUTOMATIC1111_BASE_URL` for Stable Diffusion
  - [ ] Set `OLLAMA_GPU_DRIVER` for GPU support
  - [ ] Set `OLLAMA_GPU_COUNT` for GPU support
  - [ ] Set `OPEN_WEBUI_PORT` if default 3000 is not desired
- [x] Verify analytics settings are disabled (if desired):
  - [ ] `SCARF_NO_ANALYTICS=true`
  - [ ] `DO_NOT_TRACK=true`
  - [ ] `ANONYMIZED_TELEMETRY=false`

## Python Development Environment
- [x] Create and activate Python virtual environment:
  ```bash
  python -m venv venv
  # On Windows:
  .\venv\Scripts\activate
  # On Unix/MacOS:
  source venv/bin/activate
  ```
- [ ] Install Python dependencies:
  ```bash
  pip install -e "[dev]"
  ```
- [ ] Verify Python environment:
  - [ ] Check installed packages: `pip list`
  - [ ] Verify key dependencies (FastAPI, uvicorn, etc.)

## Node.js Development Environment
- [ ] Install Node.js dependencies:
  ```bash
  npm install
  ```
- [ ] Verify Node.js setup:
  - [ ] Check installed packages: `npm list --depth=0`
  - [ ] Verify build tools are available: `npm run check`

## Database Setup
- [ ] Choose database type:
  - [ ] SQLite (default for development)
  - [ ] PostgreSQL (if needed for production-like environment)
- [ ] Verify database initialization on first run

## Ollama Setup
- [ ] Choose Ollama deployment method:
  Option 1 - Docker:
  - [ ] Start Ollama service:
    ```bash
    docker-compose up ollama -d
    ```
  Option 2 - Local installation:
  - [ ] Install Ollama locally
  - [ ] Start Ollama service:
    ```bash
    ollama serve
    ```
- [ ] Verify Ollama is running:
  - [ ] Check endpoint is accessible: `curl http://localhost:11434`

## Application Startup
- [ ] Start the development server:
  ```bash
  npm run dev
  ```
- [ ] Verify application is running:
  - [ ] Check http://localhost:3000 (or configured port)
  - [ ] Verify no console errors
  - [ ] Check Ollama connection

## Docker Environment (Alternative Setup)
If using full Docker setup:
- [ ] Choose Docker configuration:
  Option 1 - CPU only:
  - [ ] Start services:
    ```bash
    docker-compose up -d
    ```
  Option 2 - With GPU support:
  - [ ] Verify NVIDIA drivers and Docker GPU support
  - [ ] Start services with GPU config:
    ```bash
    docker-compose -f docker-compose.yaml -f docker-compose.gpu.yaml up -d
    ```
- [ ] Verify Docker setup:
  - [ ] Check container status: `docker-compose ps`
  - [ ] View logs: `docker-compose logs -f`
  - [ ] Verify application access at configured port

## Development Workflow Setup
- [x] Configure Git branches:
  - [x] Create develop branch: `git checkout -b develop`
  - [x] Set up feature branch template: `feature/<team>/<feature-name>`
  - [x] Set up hotfix branch template: `hotfix/<issue-name>`
  - [x] Set up sub-task branch template: `sub/<team>/<task-name>`
- [x] Set up code formatting:
  - [x] Test frontend formatting: `npm run format`
  - [x] Test backend formatting: `npm run format:backend`
  - [x] Test linting: `npm run lint`
- [x] Set up testing environment:
  - [x] Run frontend tests: `npm run test:frontend`
  - [ ] Set up Cypress: `npm run cy:open`

## Troubleshooting Preparation
- [ ] Review common issues and solutions:
  1. Ollama Connection Issues:
     - [ ] Check Ollama service status
     - [ ] Verify OLLAMA_BASE_URL configuration
     - [ ] Check firewall settings for port 11434
  2. Node.js Issues:
     - [ ] Know how to clean and reinstall dependencies:
       ```bash
       rm -rf node_modules
       npm install
       ```
  3. Python Issues:
     - [ ] Know how to reinstall dependencies:
       ```bash
       pip install -e "[dev]" --force-reinstall
       ```
- [ ] Locate support resources:
  - [ ] Bookmark `TROUBLESHOOTING.md`
  - [ ] Locate GitHub Issues page
  - [ ] Save development team contact information

## Maintenance Plan
- [ ] Set up regular maintenance schedule:
  - [ ] Pull latest changes from repository
  - [ ] Update dependencies
  - [ ] Review and update documentation
  - [ ] Backup configuration files

## Reset and Fresh Start Procedure
- [ ] Backup current changes:
  ```bash
  # Create a new branch for current changes
  git checkout -b backup-changes
  git add .
  git commit -m "backup: current state before reset"
  ```
- [ ] Return to main branch and reset:
  ```bash
  # Switch to main branch
  git checkout main
  # Remove all untracked files and directories
  git clean -fd
  # Reset to match remote main
  git fetch origin
  git reset --hard origin/main
  ```
- [ ] Reapply essential changes one by one:
  - [ ] Rename project references:
    1. Update package.json name
    2. Update pyproject.toml name
    3. Update Docker image names
  - [ ] Environment configuration:
    1. Copy .env.example to .env.development
    2. Update essential environment variables
  - [ ] Create fresh virtual environment:
    ```bash
    # Remove existing venv if present
    rm -rf venv
    # Create new virtual environment with Python 3.11
    py -3.11 -m venv venv
    ```

## Previous Implementation Status (Archived)
## Final Verification
- [ ] Verify all services are running
- [ ] Test basic functionality
- [ ] Check logs for any errors
- [ ] Document any environment-specific configurations made
