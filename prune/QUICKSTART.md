# Prune Script Quick Start Guide

## 🚀 For Git Installation (Manual Install)

**Step 1: Install Backend Dependencies** (One-time setup)
```bash
cd ~/Downloads/open-webui  # Or wherever you cloned the repo
source venv/bin/activate    # Activate your Python virtual environment
pip install -r backend/requirements.txt
```

**Step 2: Run Interactive Mode**
```bash
cd ~/Downloads/open-webui  # Make sure you're in the repo root, NOT prune/
source venv/bin/activate    # Activate your Python virtual environment
python prune/prune.py       # Launch interactive mode - NO ARGUMENTS!
```

That's it! The beautiful interactive UI will launch.

---

## 🐳 For Docker Installation

**Option 1: Run Inside Container**
```bash
# Find your Open WebUI container
docker ps | grep open-webui

# Enter the container
docker exec -it <container-name> bash

# Run the prune script
python /app/backend/prune/prune.py
```

**Option 2: Use docker exec Directly**
```bash
docker exec <container-name> python /app/backend/prune/prune.py --days 90 --execute
```

---

## 📦 For Pip Installation

```bash
# Activate your environment where open-webui is installed
source venv/bin/activate

# Find where open-webui is installed
pip show open-webui | grep Location

# Run from that location
cd <location>
python -m open_webui.prune  # Or wherever the prune module is
```

---

## 🔍 Troubleshooting

### Error: "No module named 'typer'" or similar

**Problem**: Backend dependencies not installed

**Solution**:
```bash
cd ~/Downloads/open-webui
source venv/bin/activate
pip install -r backend/requirements.txt
```

### Error: "Failed to import Open WebUI modules"

**Problem**: Running from wrong directory

**Solution**: Must run from repo root, NOT from prune/ directory
```bash
cd ~/Downloads/open-webui  # Go UP to repo root
python prune/prune.py      # Run from here
```

### Error: "No module named 'rich'"

**Problem**: Rich library not installed (needed for interactive mode)

**Solution**:
```bash
pip install rich
```

---

## 📝 Command Line Mode Examples

If you prefer command-line mode over interactive:

```bash
# Preview what would be deleted (safe, no changes)
python prune/prune.py --days 90 --dry-run

# Delete chats older than 90 days (for real)
python prune/prune.py --days 90 --execute

# Delete inactive users (180+ days) and their data
python prune/prune.py --delete-inactive-users-days 180 --execute

# Full cleanup with database optimization
python prune/prune.py --days 90 --delete-inactive-users-days 180 --run-vacuum --execute

# Clean orphaned data only (no age-based deletion)
python prune/prune.py --delete-orphaned-chats --delete-orphaned-files --execute
```

---

## ✅ What the Script Does

1. **Detects your installation type** (pip/docker/git) automatically
2. **Finds your database** from environment variables
3. **Auto-detects vector database** (ChromaDB, PGVector, Milvus, Milvus Multitenancy)
4. **Shows preview** of what will be deleted before doing anything
5. **Uses file locking** to prevent concurrent runs
6. **Logs everything** for audit trail

---

## 🎯 Interactive Mode Features

- Beautiful terminal UI with menus
- Preview counts before deleting
- Confirmation prompts for safety
- Progress bars and spinners
- Detailed results display
- Safe and easy to use!

**Just run:** `python prune/prune.py` (no arguments)
