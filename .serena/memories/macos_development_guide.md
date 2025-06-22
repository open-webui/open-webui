# macOS Development Environment Setup

## System Requirements

- **Operating System**: macOS
- **Python**: 3.11+ (required for backend)
- **Node.js**: 18.13.0+ (required for frontend)
- **Package Managers**: npm 6.0.0+, optionally uv for Python

## macOS Specific Commands

### System Information

```bash
# Check macOS version
sw_vers

# Check available memory
vm_stat | head -5

# Check disk space
df -h

# Check CPU information
sysctl -n machdep.cpu.brand_string

# Check running processes
ps aux | grep open-webui
```

### Package Management

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python with Homebrew
brew install python@3.11

# Install Node.js with Homebrew
brew install node

# Install Docker Desktop for Mac
brew install --cask docker

# Install uv (modern Python package manager)
brew install uv
```

### File System Operations

```bash
# Navigate to project directory
cd /path/to/open-webui-next

# Find files
find . -name "*.py" -type f    # Find Python files
find . -name "*.svelte" -type f # Find Svelte files

# Search in files
grep -r "search_term" backend/  # Search in backend
grep -r "search_term" src/      # Search in frontend

# File permissions
chmod +x backend/start.sh       # Make script executable
```

### Network and Ports

```bash
# Check if port is in use
lsof -i :8080                  # Check port 8080
lsof -i :3000                  # Check port 3000 (frontend dev)

# Kill process on port
kill -9 $(lsof -ti:8080)      # Kill process on port 8080
```

### Environment Management

```bash
# Python virtual environment
python3 -m venv venv
source venv/bin/activate
deactivate

# Environment variables
export OPENAI_API_KEY="your-key"
echo $OPENAI_API_KEY
printenv | grep WEBUI
```

### Troubleshooting Commands

```bash
# Check Python installation
which python3
python3 --version

# Check Node.js installation
which node
node --version
npm --version

# Check Docker
docker --version
docker ps
docker images

# Clear npm cache
npm cache clean --force

# Clear Python cache
find . -type d -name "__pycache__" -delete
find . -name "*.pyc" -delete
```

## Development Workflow on macOS

1. Use Terminal or iTerm2 for command line operations
2. Consider using VS Code or PyCharm for development
3. Use Docker Desktop for containerized development
4. Monitor system resources with Activity Monitor
5. Use Homebrew for package management
