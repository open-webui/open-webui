# Tauri Desktop App Implementation Plan

## Problem Statement

Convert Open WebUI from a web-based application to a standalone desktop application using Tauri. The desktop app needs a pre-launch screen that:
1. Checks if Python dependencies are installed (from `backend/requirements.txt`)
2. Checks if Ollama is installed
3. Installs Ollama if missing (with progress bar)
4. Checks if Ollama is running
5. Starts Ollama if not running
6. Launches the main UI once all checks pass

## Current State

### Application Architecture

Open WebUI is a full-stack application with:

**Frontend:**
- SvelteKit-based UI (`src/` directory)
- Static adapter configuration in `svelte.config.js`
- Built output goes to `build/` directory
- Entry point: `src/app.html`
- Key files: `package.json`, `vite.config.ts`

**Backend:**
- FastAPI Python server (`backend/open_webui/main.py`)
- Entry point: `uvicorn open_webui.main:app`
- Dependencies: `backend/requirements.txt` (150+ packages)
- Python requirement: `>= 3.11, < 3.13.0a1` (from `pyproject.toml`)
- Default host: `0.0.0.0`, port: `8080`
- Startup script: `backend/start.sh`

**Key Backend Dependencies:**
```
fastapi==0.118.0
uvicorn[standard]==0.37.0
chromadb==1.0.20
sentence-transformers==5.1.1
langchain==0.3.27
opencv-python-headless==4.11.0.86
faster-whisper==1.1.1
playwright==1.49.1
```

**Integration with Ollama:**
- Ollama is expected at `http://127.0.0.1:11434` or `host.docker.internal:11434`
- Config option: `OLLAMA_BASE_URLS` in `backend/open_webui/config.py`
- Can optionally start Ollama from startup script (`USE_OLLAMA_DOCKER=true`)

**Current Directory Structure:**
```
/Users/johnfields/Documents/code/open-webui/
├── src/                    # Svelte frontend
├── backend/                # Python backend
│   ├── open_webui/        # Main Python module
│   ├── requirements.txt   # Python dependencies
│   └── start.sh          # Backend startup script
├── src-tauri/             # Empty Tauri directory (exists but not configured)
├── package.json           # Frontend dependencies
├── svelte.config.js       # Svelte configuration
└── vite.config.ts         # Build configuration
```

**System Environment:**
- Platform: macOS
- Python: 3.13.3 (currently installed)
- Ollama: `/usr/local/bin/ollama` (already installed)

## Proposed Implementation

### Phase 1: Tauri Project Setup ✓

**Objective:** Initialize Tauri project structure and configure for SvelteKit frontend

**Tasks:**
1. Install Tauri CLI: `npm install --save-dev @tauri-apps/cli`
2. Initialize Tauri (will create/update `src-tauri/` directory):
   - `tauri.conf.json` - Main configuration
   - `src-tauri/Cargo.toml` - Rust dependencies
   - `src-tauri/src/main.rs` - Rust backend entry point
3. Configure `tauri.conf.json`:
   - Set `distDir: "../build"` to use SvelteKit build output
   - Set `devPath: "http://localhost:5173"` for dev server
   - Configure window title: "Open WebUI"
   - Set window dimensions (default: 1200x800)
   - Enable file system API for checking installations
4. Add Tauri dependencies to `src-tauri/Cargo.toml`:
   - `tauri-plugin-shell` - For running system commands
   - `tauri-plugin-dialog` - For progress dialogs
   - `tauri-plugin-fs` - For file system operations
   - `serde` and `serde_json` - For data serialization
5. Update `package.json` scripts:
   - `tauri:dev`: Development mode
   - `tauri:build`: Production build

### Phase 2: Pre-Launch Check Screen (Frontend)

**Objective:** Create a splash/setup screen that shows system checks and installation progress

**Tasks:**
1. Create new route: `src/routes/setup/+page.svelte`
2. Design UI components:
   - Progress indicator showing current step
   - Status checks with checkmarks/spinners
   - Progress bar for installations
   - Error messages with retry buttons
3. Create setup state management:
   - Track check status (pending, running, success, error)
   - Store installation progress percentage
   - Handle navigation to main app after completion
4. Create setup flow components:
   - `CheckItem.svelte` - Individual check display
   - `InstallProgress.svelte` - Installation progress bar
   - `SetupError.svelte` - Error display with actions

### Phase 3: System Checks (Rust Backend)

**Objective:** Implement Rust commands to check and install dependencies

**Implementation in `src-tauri/src/main.rs`:**

**3.1 Python Dependency Check:**
```rust
#[tauri::command]
async fn check_python_dependencies() -> Result<bool, String> {
    // Check if Python 3.11+ is installed
    // Run: python3 --version
    // Check if pip is available
    // Optionally: verify key packages are installed
}

#[tauri::command]
async fn install_python_dependencies(progress_callback: impl Fn(f64)) -> Result<(), String> {
    // Run: pip install -r backend/requirements.txt
    // Parse output to update progress
    // Call progress_callback with percentage
}
```

**3.2 Ollama Check and Installation:**
```rust
#[tauri::command]
async fn check_ollama_installed() -> Result<bool, String> {
    // Check if ollama binary exists in PATH
    // On macOS: check /usr/local/bin/ollama
    // On Linux: check /usr/bin/ollama or /usr/local/bin/ollama
    // On Windows: check %PROGRAMFILES%\Ollama\ollama.exe
}

#[tauri::command]
async fn install_ollama(progress_callback: impl Fn(f64)) -> Result<(), String> {
    // macOS: Download and run installer from ollama.ai
    // Linux: Run: curl -fsSL https://ollama.ai/install.sh | sh
    // Windows: Download and run .exe installer
    // Track download/install progress
}

#[tauri::command]
async fn check_ollama_running() -> Result<bool, String> {
    // Check if Ollama is responding
    // HTTP GET to http://127.0.0.1:11434/api/tags
    // Return true if responds with 200
}

#[tauri::command]
async fn start_ollama() -> Result<(), String> {
    // Start Ollama service
    // macOS/Linux: spawn process `ollama serve`
    // Windows: start Ollama service
    // Wait for health check to succeed
}
```

**3.3 Backend Server Management:**
```rust
#[tauri::command]
async fn start_backend_server() -> Result<(), String> {
    // Start Python FastAPI server
    // Change to backend directory
    // Run: python3 -m uvicorn open_webui.main:app --host 127.0.0.1 --port 8080
    // Keep process running in background
    // Store PID for cleanup on app exit
}

#[tauri::command]
async fn check_backend_health() -> Result<bool, String> {
    // HTTP GET to http://127.0.0.1:8080/health
    // Return true if responds with 200
}
```

### Phase 4: Frontend-Backend Integration

**Objective:** Connect setup UI to Rust commands

**Tasks:**
1. Create API wrapper in `src/lib/tauri-api.ts`:
   - Wrap all Tauri commands with TypeScript types
   - Add error handling
   - Add retry logic
2. Implement setup flow in `src/routes/setup/+page.svelte`:
   ```typescript
   1. Check Python dependencies → Install if needed
   2. Check Ollama installed → Install if needed (with progress)
   3. Check Ollama running → Start if needed
   4. Start backend server
   5. Wait for backend health check
   6. Navigate to main app (/)
   ```
3. Add loading states and progress indicators
4. Implement error handling with user-friendly messages

### Phase 5: App Lifecycle Management

**Objective:** Properly manage background processes

**Tasks:**
1. Store process handles in Tauri state:
   - Ollama serve process PID
   - Backend server process PID
2. Implement cleanup on app exit:
   - Stop backend server gracefully
   - Optionally stop Ollama (or leave running)
3. Add system tray icon (optional):
   - Show/hide window
   - View server status
   - Restart services
4. Add preferences for:
   - Auto-start Ollama
   - Keep Ollama running on exit
   - Backend port configuration

### Phase 6: Development and Build Configuration

**Objective:** Configure dev and production builds

**Tasks:**
1. Update `vite.config.ts`:
   - Configure base URL for Tauri
   - Add Tauri-specific build optimizations
2. Configure `tauri.conf.json` for production:
   - Set up code signing (macOS)
   - Configure Windows installer
   - Set up Linux AppImage/deb/rpm
3. Add resource files:
   - App icon (multiple sizes)
   - Bundle backend files with app
   - Bundle requirements.txt
4. Test builds on all platforms:
   - macOS: `.app` and `.dmg`
   - Windows: `.exe` installer
   - Linux: `.AppImage`, `.deb`

### Phase 7: Testing and Refinement

**Objective:** Ensure reliability across platforms

**Tasks:**
1. Test installation flows:
   - Fresh install (no Python, no Ollama)
   - Partial install (has Python, no Ollama)
   - Existing install (all dependencies present)
2. Test error scenarios:
   - Network failures during download
   - Permission issues
   - Port conflicts
3. Performance testing:
   - Startup time
   - Memory usage
   - Background process management
4. User experience:
   - Clear progress indicators
   - Helpful error messages
   - Recovery options

## Technical Considerations

**Python Environment:**
- Need to bundle Python or require system Python?
- Use virtual environment for isolation?
- Check for compatible Python version (3.11-3.12)

**Ollama Installation:**
- Platform-specific installers
- Require admin/sudo privileges
- Handle existing installations

**Backend Server:**
- Run as subprocess from Tauri
- Handle server crashes/restarts
- Proper cleanup on app exit

**Security:**
- Server runs on localhost only
- No external network access required
- Secure API communication

**Distribution:**
- App bundle size (Python deps are large)
- Auto-updates support
- Platform-specific packaging

## Success Criteria

1. ✅ User can launch desktop app
2. ✅ App checks for all dependencies automatically
3. ✅ Missing dependencies are installed with progress feedback
4. ✅ Backend server starts automatically
5. ✅ Main UI loads after all checks pass
6. ✅ App works on macOS, Windows, and Linux
7. ✅ Background processes shut down cleanly on app exit
8. ✅ Error handling provides clear guidance to users

## Next Steps

1. Get approval for implementation plan
2. Create feature branch: `feature/tauri-desktop-app`
3. Begin Phase 1: Tauri Project Setup
4. Iterate through phases with testing at each step
