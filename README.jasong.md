# Open WebUI Setup and Run Guide

This guide explains how to use the provided script to set up and run Open WebUI.

## Prerequisites

Before running the setup script, ensure you have the following installed:

- Python 3.10+ (Python 3.11 recommended)
- Node.js 18+
- npm 6+
- tmux (optional, but recommended for running both frontend and backend simultaneously)

## Setup and Run

1. Make sure you're on the `jasong` branch:
   ```bash
   git checkout jasong
   ```

2. Run the setup script:
   ```bash
   ./setup_and_run.sh
   ```

3. The script will:
   - Check for required dependencies
   - Create an environment file (.env) if it doesn't exist
   - Set up a Python virtual environment and install backend dependencies
   - Install frontend dependencies
   - Offer to run both frontend and backend in development mode

## Running Options

When you run the script, you'll be presented with two options:

1. **Development Mode**: 
   - Uses tmux to run both the backend and frontend concurrently
   - Backend will be available at http://localhost:8080
   - Frontend will be available at http://localhost:5173
   - If tmux is not installed, it will only run the backend

2. **Exit After Setup**:
   - Completes the setup but doesn't run any services
   - Provides instructions on how to run the services manually

## Using the Development Environment

### With tmux

If you're using tmux (option 1), you'll see two panes:
- Left pane: Backend server
- Right pane: Frontend development server

**Tmux Commands:**
- Detach from the session (without stopping services): `Ctrl+B` then `D`
- Attach to an existing session: `tmux attach -t openwebui`
- Kill the session (stop all services): `tmux kill-session -t openwebui`

### Without tmux

If you're not using tmux:
1. Run the backend: `cd backend && ./dev.sh`
2. In another terminal, run the frontend: `npm run dev`

## Configuration

- The default configuration is provided in the `.env` file (copied from `.env.example`)
- Edit this file to customize your setup
- Key configurations:
  - `OLLAMA_BASE_URL`: URL for Ollama API (default: http://localhost:11434)
  - `OPENAI_API_BASE_URL` and `OPENAI_API_KEY`: For OpenAI API integration (optional)

## Troubleshooting

If you encounter any issues:

1. **Backend errors**: Check the console output in the backend pane
2. **Frontend errors**: Check the console output in the frontend pane
3. **Dependency issues**: Make sure all prerequisites are installed
4. **Port conflicts**: Ensure ports 8080 and 5173 are not in use by other applications

---

For more information about Open WebUI, refer to the main [README.md](README.md).
