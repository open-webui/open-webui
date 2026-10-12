# TracexGPT Complete Local Development Setup Guide

This guide covers setting up the entire development environment from scratch including Conda, NVM, API keys, and all services.

---

## Table of Contents

1. [Prerequisites Installation](#1-prerequisites-installation)
2. [Environment Setup](#2-environment-setup)
3. [API Keys Configuration](#3-api-keys-configuration)
4. [Running the Stack](#4-running-the-stack)
5. [Development Workflows](#5-development-workflows)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Prerequisites Installation

### 1.1 Install Conda (Python Environment Manager)

**macOS (using Homebrew):**
```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install miniconda
brew install miniconda

# Initialize conda for your shell
conda init zsh  # or 'conda init bash' if using bash
```

**Manual install (any OS):**
```bash
# Download Miniconda
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh -O ~/miniconda.sh
# For Intel Macs use: Miniconda3-latest-MacOSX-x86_64.sh
# For Linux use: Miniconda3-latest-Linux-x86_64.sh

# Install
bash ~/miniconda.sh -b -p $HOME/miniconda

# Add to PATH
export PATH="$HOME/miniconda/bin:$PATH"

# Initialize
conda init zsh
```

**Verify installation:**
```bash
conda --version  # Should show 23.x or higher
```

### 1.2 Install NVM (Node Version Manager)

```bash
# Install NVM
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash

# Reload shell configuration
source ~/.zshrc  # or ~/.bashrc

# Verify
nvm --version
```

### 1.3 Install Node.js (via NVM)

```bash
# Install Node 20 (LTS recommended for this project)
nvm install 20

# Set as default
nvm use 20
nvm alias default 20

# Verify
node --version  # v20.x.x
npm --version   # 10.x.x
```

### 1.4 Install Docker Desktop

**macOS:**
```bash
# Via Homebrew
brew install --cask docker

# Or download from: https://www.docker.com/products/docker-desktop
```

**Start Docker:**
```bash
# Open Docker Desktop app (first time only)
open -a Docker

# Wait for Docker to be ready
docker --version  # Should show version without errors
```

---

## 2. Environment Setup

### 2.1 Clone and Navigate to Repository

```bash
# Navigate to your workspace
cd /Users/apple/Documents/foodsign

# If you haven't cloned yet:
# git clone <repo-url> trace-open-webui

cd trace-open-webui
```

### 2.2 Create Python Conda Environment

```bash
# Create new environment with Python 3.11
conda create -n tracexgpt python=3.11 -y

# Activate environment
conda activate tracexgpt

# Verify Python version
python --version  # Python 3.11.x
```

### 2.3 Install Backend Dependencies

```bash
# Make sure you're in the conda environment
conda activate tracexgpt

# Install UV (fast Python package installer)
pip install uv

# Install backend dependencies
uv pip install -e ".[dev]"

# Verify installation
python -c "from open_webui.main import app; print('Backend OK')"
```

### 2.4 Install Frontend Dependencies

```bash
# Use correct Node version
nvm use 20

# Install npm dependencies
npm install

# Verify
npm list vite  # Should show vite@5.x.x
```

---

## 3. API Keys Configuration

### 3.1 Required API Keys

You need these API keys for full functionality:

| Service | Key Name | How to Get | Cost |
|---------|----------|------------|------|
| OpenAI | `OPENAI_API_KEY` | https://platform.openai.com/api-keys | Pay per use |
| HuggingFace | `HF_TOKEN` | https://huggingface.co/settings/tokens | Free tier available |

### 3.2 Create Environment File

```bash
# Copy template
cp .env.example .env

# Edit the file
nano .env  # or use your preferred editor (code .env, vim .env, etc.)
```

### 3.3 Minimum Required .env Configuration

```bash
# =============================================================================
# REQUIRED: OpenAI API Key
# =============================================================================
# Get from: https://platform.openai.com/api-keys
# Required for: LLM chat, embeddings, PPT generation, knowledge base
OPENAI_API_KEY=sk-your-openai-key-here

# =============================================================================
# REQUIRED: HuggingFace Token (for embeddings model downloads)
# =============================================================================
# Get from: https://huggingface.co/settings/tokens
# Create account, generate token with 'read' permission
HF_TOKEN=hf_your_huggingface_token_here

# =============================================================================
# Optional: Presenton (AI Presentation Generator)
# =============================================================================
# These defaults work for local Docker setup - no changes needed
PRESENTON_URL=http://presenton:80
PRESENTON_PUBLIC_URL=http://localhost:5000
PRESENTON_USER=admin
PRESENTON_PASS=changeme

# =============================================================================
# Optional: File TTL (auto-delete generated files)
# =============================================================================
FILE_TTL_DAYS=120

# =============================================================================
# Optional: Default budget for new users
# =============================================================================
DEFAULT_MONTHLY_LIMIT_USD=5.0

# =============================================================================
# Required: Security (change in production!)
# =============================================================================
WEBUI_SECRET_KEY=dev-secret-key-change-in-production

# =============================================================================
# Optional: Disable public signup
# =============================================================================
ENABLE_SIGNUP=false
```

### 3.4 Verify API Keys Work

```bash
# Test OpenAI API
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json"

# Should return a list of models
```

---

## 4. Running the Stack

### Option A: Full Docker Stack (Easiest - Everything in Containers)

Best for: Quick testing, verifying features work

```bash
# 1. Ensure Docker is running
open -a Docker

# 2. Export API keys to shell (so Docker can read them)
export OPENAI_API_KEY=sk-your-key
export HF_TOKEN=hf-your-token

# 3. Start all services
docker-compose -f docker-compose.dev.yml up

# Or run in background
docker-compose -f docker-compose.dev.yml up -d

# 4. Access the app
# Main app: http://localhost:3000
# Presenton Studio: http://localhost:5000

# 5. View logs
docker-compose -f docker-compose.dev.yml logs -f tracexgpt
docker-compose -f docker-compose.dev.yml logs -f presenton

# 6. Stop everything
docker-compose -f docker-compose.dev.yml down

# To reset database (WARNING: deletes all data)
docker-compose -f docker-compose.dev.yml down -v
```

### Option B: Hybrid Mode (Backend + Presenton in Docker, Frontend Local)

Best for: Frontend development with hot reload

**Terminal 1 - Backend + Presenton:**
```bash
# Export keys
export OPENAI_API_KEY=sk-your-key
export HF_TOKEN=hf-your-token

# Start backend and Presenton only
docker-compose -f docker-compose.dev.yml up tracexgpt presenton
```

**Terminal 2 - Frontend (with hot reload):**
```bash
# Navigate to project
cd /Users/apple/Documents/foodsign/trace-open-webui

# Use correct Node version
nvm use 20

# Install dependencies (first time only)
npm install

# Start dev server
npm run dev

# Frontend available at: http://localhost:5173
# Hot reload: Changes reflect immediately
```

### Option C: Full Local Development (Most Control)

Best for: Backend debugging, running with IDE breakpoints

**Terminal 1 - Presenton (Docker):**
```bash
# Presenton must run in Docker (it's a separate microservice)
# Make sure keys are exported
export OPENAI_API_KEY=sk-your-key

# Run Presenton
docker run -d \
  --name presenton \
  -p 5000:80 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e LLM=openai \
  -e CAN_CHANGE_KEYS=false \
  --restart unless-stopped \
  ghcr.io/presenton/presenton:latest

# Check Presenton is running
docker ps | grep presenton

# View Presenton logs
docker logs -f presenton

# Stop Presenton later
docker stop presenton && docker rm presenton
```

**Terminal 2 - Backend (Local Python):**
```bash
# Navigate to project
cd /Users/apple/Documents/foodsign/trace-open-webui

# Activate conda environment
conda activate tracexgpt

# Export all required environment variables
export OPENAI_API_KEY=sk-your-key
export HF_TOKEN=hf-your-token
export PRESENTON_URL=http://localhost:5000
export PRESENTON_PUBLIC_URL=http://localhost:5000
export PRESENTON_USER=admin
export PRESENTON_PASS=changeme
export FILE_TTL_DAYS=120
export WEBUI_SECRET_KEY=dev-local-secret
export ENABLE_SIGNUP=false
export DEFAULT_MONTHLY_LIMIT_USD=5.0

# Optional: Enable verbose logging
export LOG_LEVEL=DEBUG

# Start backend with auto-reload
uvicorn open_webui.main:app \
  --host 0.0.0.0 \
  --port 8080 \
  --reload \
  --reload-dir backend/open_webui

# Backend available at: http://localhost:8080
# API docs: http://localhost:8080/docs
```

**Terminal 3 - Frontend (Local with hot reload):**
```bash
cd /Users/apple/Documents/foodsign/trace-open-webui
nvm use 20
npm run dev

# Frontend: http://localhost:5173
# Proxies API calls to localhost:8080
```

### Option D: Production Build Test

Test the production build locally:

```bash
# 1. Build frontend
nvm use 20
npm run build

# 2. Set environment
export OPENAI_API_KEY=sk-your-key
export HF_TOKEN=hf-your-token
export WEBUI_SECRET_KEY=prod-test-secret
export ENV=prod

# 3. Run with production config
docker-compose -f docker-compose.prod.yml up --build

# 4. Access
# App: http://localhost:3000
```

---

## 5. Development Workflows

### 5.1 Making Backend Changes

```bash
# If running local backend (Option C):
# Just save your .py files - uvicorn --reload will auto-restart

# If running Docker backend (Option A or B):
# 1. Edit code
# 2. Restart container
docker-compose -f docker-compose.dev.yml restart tracexgpt

# Or for faster iteration, switch to Option C (local backend)
```

### 5.2 Making Frontend Changes

```bash
# Dev server (npm run dev) has hot reload
# Just save .svelte files and changes appear instantly

# For TypeScript/Svelte checking:
npm run check

# For linting:
npm run lint
```

### 5.3 Database Management

```bash
# Docker setup - reset everything
# WARNING: Deletes all chats, users, files
docker-compose -f docker-compose.dev.yml down -v

# Local setup - reset SQLite
rm backend/data/webui.db
rm -rf backend/data/uploads

# Backup before reset
cp backend/data/webui.db backup-$(date +%Y%m%d).db
```

### 5.4 Testing Presenton Integration

**Test Presenton is running:**
```bash
# Check container
docker ps | grep presenton

# Test API
curl -u admin:changeme http://localhost:5000/health

# Should return: {"status":"healthy"}
```

**Test PPT generation via chat:**
1. Open chat
2. Type: "Create a presentation about AI in healthcare"
3. Tool should auto-trigger and generate PPT
4. File appears in chat with download link

**Test Presenton Studio (full editor):**
1. Set `PRESENTON_PUBLIC_URL=http://localhost:5000` in .env
2. Go to Workspace → PPT Generator
3. Should show embedded Presenton Studio UI
4. Or visit http://localhost:5000 directly

---

## 6. Troubleshooting

### 6.1 "conda command not found"

```bash
# Initialize conda for your shell
~/miniconda/bin/conda init zsh

# Or add to PATH manually
export PATH="$HOME/miniconda/bin:$PATH"

# Reload shell
source ~/.zshrc
```

### 6.2 "nvm command not found"

```bash
# Source NVM
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Or reload shell
source ~/.zshrc
```

### 6.3 "module not found" errors (Python)

```bash
# Ensure you're in conda environment
conda activate tracexgpt

# Reinstall dependencies
uv pip install -e ".[dev]"
```

### 6.4 "cannot find module" errors (Node)

```bash
# Reinstall node_modules
rm -rf node_modules package-lock.json
npm install
```

### 6.5 Docker issues

```bash
# Docker not running
open -a Docker

# Permission denied
sudo chown -R $(whoami) ~/.docker

# Port already in use
lsof -i :3000  # Find process
kill -9 <PID>  # Kill it

# Or use different port
docker-compose -f docker-compose.dev.yml -p dev2 up
```

### 6.6 OpenAI API errors

```bash
# Test your key
curl https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"hi"}]}'

# Check billing at: https://platform.openai.com/settings/organization/billing/overview
```

### 6.7 Presenton not generating PPTs

```bash
# Check logs
docker logs presenton

# Common issues:
# 1. OPENAI_API_KEY not set correctly
# 2. Presenton container not running
# 3. Network connectivity issues

# Restart Presenton
docker stop presenton && docker rm presenton
docker run -d \
  --name presenton \
  -p 5000:80 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e LLM=openai \
  ghcr.io/presenton/presenton:latest
```

---

## Quick Reference Commands

```bash
# === START EVERYTHING (Docker) ===
export OPENAI_API_KEY=sk-xxx
export HF_TOKEN=hf_xxx
docker-compose -f docker-compose.dev.yml up

# === START HYBRID (Recommended for dev) ===
# Terminal 1
docker-compose -f docker-compose.dev.yml up tracexgpt presenton
# Terminal 2
conda activate tracexgpt
nvm use 20
npm run dev

# === START FULL LOCAL (Debugging) ===
# Terminal 1
docker run -d --name presenton -p 5000:80 -e OPENAI_API_KEY=$SK ghcr.io/presenton/presenton:latest
# Terminal 2
conda activate tracexgpt
uvicorn open_webui.main:app --reload --port 8080
# Terminal 3
nvm use 20 && npm run dev

# === STOP EVERYTHING ===
docker-compose -f docker-compose.dev.yml down
docker stop presenton && docker rm presenton
pkill -f uvicorn
pkill -f "vite"

# === RESET DATABASE ===
docker-compose -f docker-compose.dev.yml down -v
rm backend/data/webui.db
```

---

## Next Steps

1. **Create first admin user**: Sign up at http://localhost:3000 (first user = admin)
2. **Create a client user**: Admin → Clients → New Client
3. **Upload knowledge**: Workspace → Knowledge → Add
4. **Test PPT generation**: Chat → "Create presentation about [topic]"
