# 🪟 Windows Development Setup Guide - Open WebUI

Complete first-time setup guide for developing Open WebUI on Windows using modern tools (UV + Bun).

---

## 📋 Prerequisites

### Required Software

1. **Git for Windows**

   ```powershell
   winget install Git.Git
   ```

2. **UV (Python Package Manager)**

   ```powershell
   winget install astral-sh.uv
   ```

3. **Bun (JavaScript Runtime & Package Manager)**

   ```powershell
   # Visit: https://bun.sh/
   # Or use PowerShell:
   powershell -c "irm bun.sh/install.ps1 | iex"
   ```

4. **Visual Studio Code**

   ```powershell
   winget install Microsoft.VisualStudioCode
   ```

5. **PowerShell 7+ (Recommended)**
   ```powershell
   winget install Microsoft.PowerShell
   ```

### Verify Installations

```powershell
# Check all tools are installed
git --version
uv --version
bun --version
code --version
pwsh --version
```

---

## 🚀 First-Time Setup

### Step 1: Clone the Repository

```powershell
# Clone to your preferred location
cd D:\Coding  # Or your preferred directory
git clone https://github.com/open-webui/open-webui.git
cd open-webui
```

### Step 2: Open in VS Code

```powershell
# Open the project in VS Code
code .
```

### Step 3: Install Frontend Dependencies

```powershell
# From the project root, install frontend packages
bun install
```

This will:

- Install all Node.js dependencies
- Create `node_modules/` directory
- Generate `bun.lock` lockfile
- Takes ~30-60 seconds

### Step 4: Setup Backend Environment

```powershell
# Navigate to backend directory
cd backend

# Create virtual environment and install all Python dependencies
uv sync --all-extras --all-groups
```

This will:

- Create `backend/.venv/` directory
- Install all Python packages (FastAPI, SQLAlchemy, AI libraries, etc.)
- Generate `uv.lock` lockfile
- Takes ~2-5 minutes depending on your internet speed

**What gets installed:**

- Core dependencies (FastAPI, Uvicorn, Pydantic)
- AI/LLM libraries (OpenAI, Anthropic, LangChain)
- Database tools (SQLAlchemy, Alembic, Peewee)
- Document processing (PDF, DOCX, Excel)
- Vector databases (ChromaDB, OpenSearch)
- Development tools (Ruff, MyPy, Pytest)

---

## 🎮 Running the Development Servers

### Option 1: One-Key Startup (Recommended)

Press **Ctrl+Shift+B** in VS Code

This automatically:

- ✅ Starts the frontend server (Bun)
- ✅ Activates Python virtual environment
- ✅ Starts the backend server (Uvicorn)
- ✅ Shows both in split terminal view

### Option 2: Manual Startup

**Terminal 1 - Frontend:**

```powershell
# From project root
bun run dev
```

**Terminal 2 - Backend:**

```powershell
# From project root
pwsh backend/dev.ps1
```

---

## 🌐 Access the Application

Once both servers are running:

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8080
- **API Documentation**: http://localhost:8080/docs (Swagger UI)

---

## 📁 Project Structure

```
open-webui/
├── .vscode/
│   └── tasks.json              # Ctrl+Shift+B configuration
│
├── backend/
│   ├── .venv/                  # Python virtual environment (created by UV)
│   ├── pyproject.toml          # Python dependencies & configuration
│   ├── dev.ps1                 # Windows development startup script
│   ├── dev.sh                  # Linux development startup script
│   ├── requirements.txt        # Legacy pip requirements (still supported)
│   └── open_webui/             # Python source code
│       ├── main.py             # FastAPI application entry point
│       ├── models/             # Database models
│       ├── routers/            # API route handlers
│       └── ...
│
├── src/                        # Frontend Svelte source code
│   ├── lib/
│   │   ├── components/         # Svelte components
│   │   ├── apis/               # API client functions
│   │   └── ...
│   └── routes/                 # SvelteKit routes
│
├── static/                     # Static assets
├── pyproject.toml              # Root project configuration
├── package.json                # Frontend dependencies
├── bun.lock                    # Frontend dependency lockfile
├── uv.lock                     # Backend dependency lockfile
└── vite.config.ts              # Vite build configuration
```

---

## 🛠️ Common Development Tasks

### Adding Python Dependencies

```powershell
cd backend

# Add a new package
uv add package-name

# Add a development dependency
uv add --dev pytest-cov

# Add with version constraint
uv add "fastapi>=0.100.0"

# After adding, sync environment
uv sync
```

### Adding Frontend Dependencies

```powershell
# From project root
bun add package-name

# Add as dev dependency
bun add -d package-name
```

### Updating Dependencies

```powershell
# Update Python packages
cd backend
uv sync --upgrade

# Update Frontend packages
cd ..
bun update
```

### Running Tests

```powershell
# Backend tests
cd backend
uv run pytest

# Frontend tests (if configured)
cd ..
bun test
```

### Code Formatting & Linting

```powershell
# Backend - Format with Ruff
cd backend
uv run ruff format .
uv run ruff check .

# Frontend - Format with Prettier (if configured)
cd ..
bun run format
```

---

## 🔧 Environment Variables

Create a `.env` file in the `backend/` directory for local configuration:

```env
# backend/.env
PORT=8080
CORS_ALLOW_ORIGIN=http://localhost:5173;http://localhost:8080

# Database
DATABASE_URL=sqlite:///./webui.db

# OpenAI API (optional)
OPENAI_API_KEY=your_key_here

# Other API keys as needed
ANTHROPIC_API_KEY=your_key_here
```

The `dev.ps1` script automatically loads these variables.

---

## 📝 Development Workflow

### Daily Development

1. Open VS Code: `code D:\Coding\open-webui`
2. Press **Ctrl+Shift+B**
3. Wait for both servers to start (~5-10 seconds)
4. Open browser to http://localhost:5173
5. Make changes - both servers auto-reload!

### Making Changes

- **Frontend**: Edit files in `src/` - Vite hot-reloads instantly
- **Backend**: Edit files in `backend/open_webui/` - Uvicorn auto-reloads

### Git Workflow

```powershell
# Create a feature branch
git checkout -b feature/my-awesome-feature

# Make changes...

# Stage and commit
git add .
git commit -m "Add awesome feature"

# Push to your fork
git push origin feature/my-awesome-feature
```

---

## 🐛 Troubleshooting

### Virtual Environment Not Found

**Error**: `WARNING: Virtual environment not found`

**Solution**:

```powershell
cd backend
uv sync --all-extras --all-groups
```

### Port Already in Use

**Error**: `Address already in use: 8080`

**Solution**:

```powershell
# Change the backend port
$env:PORT = "8081"
pwsh backend/dev.ps1
```

Or kill the process using the port:

```powershell
# Find process using port 8080
netstat -ano | findstr :8080

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

### Frontend Won't Start

**Error**: `Cannot find module...`

**Solution**:

```powershell
# Reinstall frontend dependencies
Remove-Item node_modules -Recurse -Force
bun install
```

### Python Package Conflicts

**Solution**:

```powershell
cd backend
Remove-Item .venv -Recurse -Force
uv sync --all-extras --all-groups
```

### UV Command Not Found

**Solution**:

```powershell
# Reinstall UV
winget install astral-sh.uv

# Restart your terminal
# Or add to PATH manually: C:\Users\<YourName>\.cargo\bin
```

### Bun Command Not Found

**Solution**:

```powershell
# Reinstall Bun
powershell -c "irm bun.sh/install.ps1 | iex"

# Restart your terminal
```

### Ctrl+Shift+B Not Working

**Solution**:

1. Open `.vscode/tasks.json` to verify it exists
2. Reload VS Code: `Ctrl+Shift+P` → "Reload Window"
3. Try again

---

## 🎯 What Each Tool Does

### UV (Python Package Manager)

- **Replaces**: pip, pip-tools, virtualenv, conda
- **10-100x faster** than pip
- **Modern**: Built with Rust for speed
- **Simple**: One tool for everything Python

### Bun (JavaScript Runtime)

- **Replaces**: Node.js, npm, yarn, webpack
- **Fast**: Native JavaScript runtime in Zig
- **All-in-one**: Runtime, package manager, bundler, test runner
- **Compatible**: Works with Node.js packages

### Why Not Conda?

- UV is faster and simpler
- Better lock files for reproducibility
- Native Windows support without conda's complexity
- Smaller, cleaner environments

---

## 📚 Additional Resources

- **Open WebUI Docs**: https://docs.openwebui.com/
- **UV Documentation**: https://docs.astral.sh/uv/
- **Bun Documentation**: https://bun.sh/docs
- **Contributing Guide**: See `docs/CONTRIBUTING.md`
- **UV Build Guide**: See `UV_BUILD_GUIDE.md`
- **UV Quickstart**: See `UV_QUICKSTART.md`

---

## 🎉 You're Ready!

You now have a modern, fast development environment for Open WebUI on Windows!

**Next Steps:**

1. Press **Ctrl+Shift+B** to start developing
2. Open http://localhost:5173 in your browser
3. Make some changes and see them live reload
4. Check out the API docs at http://localhost:8080/docs
5. Read `docs/CONTRIBUTING.md` for contribution guidelines

**Happy Coding! 🚀**

---

## 💡 Pro Tips

1. **Use PowerShell 7**: It's faster and has better features than Windows PowerShell 5.1
2. **Enable Hot Reload**: Both frontend and backend auto-reload on file changes
3. **Use VS Code Extensions**:
   - Python extension for IntelliSense
   - Svelte for VS Code
   - Ruff for linting
   - GitLens for Git integration
4. **Keep Dependencies Updated**: Run `uv sync --upgrade` weekly
5. **Learn UV Commands**: `uv --help` shows all available commands
6. **Check API Docs**: http://localhost:8080/docs shows all API endpoints with examples

---

## 🆘 Need Help?

- **GitHub Issues**: https://github.com/open-webui/open-webui/issues
- **Discord**: https://discord.gg/5rJgQTnV4s
- **Documentation**: https://docs.openwebui.com/

---

Made with ❤️ by the Open WebUI community
