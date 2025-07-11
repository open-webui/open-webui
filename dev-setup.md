# Open WebUI Development Setup

## Prerequisites

- Node.js 22.x (use `nvm use 22` if you have nvm)
- Python 3.11+
- uv (Python package manager)

## Quick Start

### 1. Install Dependencies

```bash
# Use correct Node.js version
nvm use 22

# Install frontend dependencies
npm install

# Install Python dependencies
uv sync
```

### 2. Start Development Servers

#### Option A: Fast Development (Recommended for UI work)

```bash
# Single command to start both servers (fast mode)
./dev-start.sh

# OR manually:
# Terminal 1 - Frontend (fast mode, no pyodide)
npm run dev:fast

# Terminal 2 - Backend
cd backend && uv run bash dev.sh
```

#### Option B: Full Development (includes Python notebook features)

```bash
# Terminal 1 - Frontend (with pyodide setup)
npm run dev

# Terminal 2 - Backend
cd backend && uv run bash dev.sh
```

#### Option C: Frontend only (for UI development)

```bash
npm run dev:fast
```

## Performance Tips

### 🚀 Fast Development Mode

- Use `npm run dev:fast` instead of `npm run dev` to skip pyodide setup
- Saves ~30-60 seconds on startup
- Use this unless you need Python notebook features

### ⚡ Optimization Features

- Vite dependency pre-bundling for faster HMR
- Svelte inspector enabled (Cmd+Shift to toggle)
- esbuild for faster transpilation
- Optimized large dependency handling

## Available Scripts

### Frontend (package.json)

- `npm run dev:fast` - Start development server (fast mode, no pyodide)
- `npm run dev` - Start development server (full mode, with pyodide)
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run linting
- `npm run format` - Format code

### Backend

- `cd backend && uv run bash dev.sh` - Start development server
- `uv run python -m open_webui.main` - Run backend directly

### Development Scripts

- `./dev-start.sh` - Start both frontend and backend in fast mode

## Development URLs

- Frontend: http://localhost:5173
- Backend API: http://localhost:8080
- Backend API Docs: http://localhost:8080/docs

## Project Structure

```
open-webui/
├── src/                 # Frontend SvelteKit source
├── backend/            # Python FastAPI backend
│   └── open_webui/     # Main backend package
├── package.json        # Frontend dependencies
├── pyproject.toml      # Python project config
├── uv.lock            # Python dependency lock file
├── svelte.config.js   # SvelteKit configuration
└── vite.config.ts     # Vite configuration
```

## Notes

- The project uses `uv` for Python dependency management
- Frontend requires Node.js 18.13.0 - 22.x.x (use Node 22 for best compatibility)
- Backend API is automatically configured with CORS for development
- First run will download required AI models (may take a few minutes)
- **Use fast mode (`dev:fast`) for most development work** - only use full mode when working with Python notebooks
