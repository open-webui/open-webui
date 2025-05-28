# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RAUX is AMD's fork of Open-WebUI, an extensible AI platform designed to operate entirely offline. It provides a user-friendly web interface for interacting with various LLM backends including GAIA (AMD's AI solution), Ollama, OpenAI-compatible APIs, and Lemonade.

**Architecture**: Svelte frontend + Python FastAPI backend with Socket.IO for real-time communication.

## RAUX-GAIA-Lemonade Integration

RAUX is designed to be installed as part of the GAIA ecosystem, though it maintains standalone installation capability. The integration works as follows:

### Installation Flow
1. **GAIA Installer** downloads `raux-wheel-context.zip` from GitHub releases
2. **RAUX Setup** (via `rauxSetup.ts`) extracts and installs the Python wheel
3. **Environment Detection** determines if Lemonade is available and configures accordingly:
   - **Hybrid Mode** (`raux-hybrid.env`): Integrates with Lemonade server at `http://localhost:8000/api/v0`
   - **Generic Mode** (`raux-generic.env`): Standalone mode with Ollama integration

### Key Components
- **Python Wheel**: Built from `/backend` directory via `pyproject.toml`
- **Electron Wrapper**: Provides desktop application experience
- **Environment Files**: 
  - `raux-hybrid.env`: Lemonade integration configuration
  - `raux-generic.env`: Standalone mode configuration
- **Build Context**: Packaged as `raux-wheel-context.zip` containing wheel + env files

### Release Artifacts
- `raux-setup.exe`: Standalone Electron installer
- `raux-wheel-context.zip`: For GAIA installer consumption
- SHA256 checksums for verification

### Installation Process Details
**From GAIA Perspective:**
1. Downloads wheel context from: `https://github.com/aigdat/raux/releases/<VERSION>/download/raux-wheel-context.zip`
2. Invokes RAUX Electron app installation process
3. RAUX setup handles Python environment, wheel installation, and configuration

**Installer Architecture:**
- **GAIA**: Uses NSIS installer (traditional Windows installer system)
- **RAUX**: Uses Squirrel installer from Electron Forge (auto-updater/installer for Electron apps)
- **Integration**: GAIA NSIS installer downloads and invokes RAUX Squirrel installer (`raux-setup.exe`)
- **Auto-launch Coordination**: Squirrel installer auto-launches RAUX by default; coordination mechanism needed to prevent this when installed via GAIA

**Key Installation Files:**
- `raux-electron/src/rauxSetup.ts`: Main installation orchestration
- `raux-electron/src/pythonExec.ts`: Python environment management
- Environment detection logic automatically selects hybrid vs generic mode

### Environment Mode Selection
**Hybrid Mode Triggers:**
- Lemonade server detected in PATH or USERPROFILE
- `GAIA_MODE=HYBRID` environment variable
- Results in Lemonade integration at `http://localhost:8000/api/v0`

**Generic Mode:**
- Default fallback when Lemonade not detected
- Uses Ollama backend at `http://localhost:11434`

### Build Process for GAIA Integration
**GitHub Actions Workflow** (`.github/workflows/build-and-package.yml`):
1. **build-wheel**: Creates Python wheel from backend + frontend
2. **build-context**: Packages wheel with `raux-hybrid.env` and `raux-generic.env`
3. **package-electron**: Creates Windows installer with embedded context

**Wheel Context Structure:**
```
raux-wheel-context.zip
├── open_webui-*.whl     # Python wheel with backend + built frontend
├── raux-hybrid.env      # Lemonade integration config
└── raux-generic.env     # Standalone mode config
```

## Development Commands

### Frontend Development
```bash
npm run dev                    # Start dev server (localhost:5173)
npm run dev:5050              # Start dev server on port 5050
npm run build                 # Build for production
npm run check                 # Type checking
npm run lint                  # Lint frontend + backend
npm run format                # Format code
npm run test:frontend         # Run frontend tests
```

### Backend Development
```bash
cd backend
./dev.sh                      # Start backend dev server (port 8080)
./start.sh                    # Start production backend
```

### Testing
```bash
npm run cy:open              # Open Cypress GUI for E2E tests
```

### Docker (Production Only)
```bash
make install                  # Docker compose up
make start                    # Start containers
make stop                     # Stop containers
make update                   # Update and rebuild
```

**Important**: This project does NOT run in Docker for development. Any Docker configurations are for production deployment only.

## Architecture Overview

### Frontend (src/)
- **Svelte** with SvelteKit using static adapter
- **TypeScript** with comprehensive type checking
- **Tailwind CSS** for styling
- **Routes structure**: `src/routes/` contains SvelteKit routes
- **Components**: `src/lib/components/` for shared UI components
- **Stores**: `src/lib/stores/` for state management

### Backend (backend/open_webui/)
- **FastAPI** application with **main.py** as entry point
- **Routers**: API endpoints organized in `routers/` directory
- **Models**: Database models using SQLAlchemy + Peewee in `models/`
- **Utils**: Shared utilities in `utils/` directory
- **Socket.IO**: Real-time communication via `socket/main.py`

### Electron App (raux-electron/)
- Wrapper for desktop application distribution
- Contains IPC communication, window management, and setup logic

## Key Development Practices

### Code Organization
- **Files**: snake_case.py
- **Classes**: PascalCase
- **Functions**: snake_case
- **Constants**: UPPER_SNAKE_CASE

### GAIA Integration
- Maintain clear separation between RAUX and GAIA components
- Use defined interfaces for RAUX-GAIA interaction
- Support standalone installation

### Environment Requirements
- **Python**: 3.11-3.12
- **Node.js**: >=18.13.0 <=22.x.x
- **Pyodide**: Used for in-browser Python execution

### Development Workflow
1. **Analysis First**: Always start with understanding the current state before making changes
2. **One Step at a Time**: Focus on single tasks, avoid multiple simultaneous changes
3. **Plan Confirmation**: Develop clear plans and confirm before modifying code
4. **VSCode Debugging**: 
   - Access application through backend URL (port 8080) for full functionality
   - Use Chrome debugging for Svelte frontend
   - Configure both frontend and backend debugging in launch.json

### Environment Variables
Extensive configuration via environment variables (see `backend/open_webui/config.py`):
- **OPENAI_API_BASE_URLS**: For OpenAI compatible endpoints
- **OLLAMA_BASE_URL**: For Ollama connection
- **HF_HUB_OFFLINE=1**: For offline mode

### Code Quality Requirements
- Copyright notice and MIT license header in new files
- Function/class docstrings for documentation
- Unit tests for new functionality (tests/ directory)
- Graceful error handling with descriptive messages

### Special Features
- **Offline-first design** with OFFLINE_MODE support
- **Multi-modal support**: Text, images, audio, video
- **RAG capabilities** with ChromaDB vector storage
- **Real-time collaboration** via WebSocket
- **Multi-language support** (i18n)
- **Pyodide integration** for code execution

## File Structure Notes
- `src/routes/(app)/`: Main application routes
- `backend/open_webui/routers/`: API endpoint handlers
- `backend/open_webui/models/`: Database schema definitions
- `raux-electron/src/`: Electron wrapper implementation
- `cypress/`: E2E test suites
- `static/`: Static assets and themes

## Installation Context
RAUX can be installed:
1. As optional component during GAIA installation (default enabled)
2. Via standalone Installer-UX.exe
3. Via raux_installer.py script with debug capabilities
4. Through Python pip for development

**Versioning**: Dual scheme (0.6.5+raux.0.2.0) with original OpenWebUI version (0.6.5) and RAUX (raux.0.2.0); Electron follows RAUX version (0.2.0).

## Memories and Guidance

- Remember that "node_modules" folder is not our code; its ok to reference but don't check for errors or lint