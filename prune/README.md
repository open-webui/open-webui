# Open WebUI Standalone Prune Script

This directory contains a standalone command-line script that replicates the full logic and configurability of the Open WebUI prune API router, but runs independently without requiring the web server to be running.

## Purpose

The `standalone_prune.py` script allows you to:

- Run data pruning operations via command line or cron jobs
- Clean up orphaned data, old chats, inactive users
- Preview what will be deleted before committing changes
- Run database optimization (VACUUM)
- Maintain your Open WebUI instance without using the web UI

## Features

✅ **Fully Configurable** - All options from the web UI prune dialog are available via command-line flags
✅ **Safe by Default** - Dry-run mode by default, requires explicit `--execute` flag for actual deletion
✅ **Complete Logic** - Uses the exact same code paths as the API router
✅ **Database Access** - Full access to SQLAlchemy models and database operations
✅ **Vector Database Support** - Supports ChromaDB and PGVector cleanup
✅ **File System Operations** - Cleans up orphaned uploads and audio cache
✅ **Locking Mechanism** - Prevents concurrent prune operations
✅ **Detailed Logging** - Comprehensive logging of all operations

## Requirements

### Environment Access

The script requires access to the same environment as Open WebUI:

1. **Python Environment**: Same Python version and dependencies as Open WebUI backend
2. **Database Access**: Must have `DATABASE_URL` environment variable set
3. **File System Access**: Must be able to read/write to Open WebUI data directories
4. **Module Imports**: Must be able to import from `backend.open_webui` modules

### How to Access Database and Configuration

The script imports directly from Open WebUI's backend modules, which means it automatically gets:

- **Database Connection**: Via `DATABASE_URL` environment variable (same as Open WebUI)
- **Vector Database Config**: Via `VECTOR_DB` and related environment variables
- **File Paths**: Via `CACHE_DIR` and other path configurations
- **All Models**: Direct access to Users, Chats, Files, etc. ORM models

## Installation & Setup

### Method 1: Run from Open WebUI Directory (Recommended)

```bash
cd /path/to/open-webui

# Make sure you have the same environment as Open WebUI
source .venv/bin/activate  # If using virtual environment

# Export same environment variables as Open WebUI uses
export DATABASE_URL="..."
export VECTOR_DB="chromadb"  # or pgvector
# ... other environment variables

# Run the script
python prune/standalone_prune.py --help
```

### Method 2: Set PYTHONPATH

```bash
export PYTHONPATH="/path/to/open-webui:$PYTHONPATH"
export DATABASE_URL="..."
# ... other environment variables

python /path/to/open-webui/prune/standalone_prune.py --help
```

### Method 3: Create a Wrapper Script

Create a file `run_prune.sh`:

```bash
#!/bin/bash
cd /path/to/open-webui
source .venv/bin/activate

# Load environment from Open WebUI
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Run the prune script with arguments
python prune/standalone_prune.py "$@"
```

Make it executable:
```bash
chmod +x run_prune.sh
```

Now you can run:
```bash
./run_prune.sh --dry-run
./run_prune.sh --days 60 --execute
```

## Usage Examples

### Basic Preview (Safe - No Changes)

```bash
# Preview what would be deleted with default settings
python standalone_prune.py --dry-run

# Equivalent (dry-run is default if --execute not specified)
python standalone_prune.py
```

### Delete Old Chats

```bash
# Preview deletion of chats older than 60 days
python standalone_prune.py --days 60 --dry-run

# Actually delete chats older than 60 days
python standalone_prune.py --days 60 --execute

# Delete chats older than 90 days, including archived chats
python standalone_prune.py --days 90 --no-exempt-archived-chats --execute
```

### Delete Inactive Users

```bash
# Preview deletion of users inactive for 180+ days
python standalone_prune.py --delete-inactive-users-days 180 --dry-run

# Actually delete inactive users (exempting admins and pending users)
python standalone_prune.py --delete-inactive-users-days 180 --execute

# Delete inactive users including admins (NOT RECOMMENDED)
python standalone_prune.py --delete-inactive-users-days 180 --no-exempt-admin-users --execute
```

### Clean Orphaned Data

```bash
# Clean only orphaned data (no age-based deletion)
python standalone_prune.py --delete-orphaned-chats --execute

# Clean all types of orphaned data
python standalone_prune.py \
  --delete-orphaned-chats \
  --delete-orphaned-tools \
  --delete-orphaned-functions \
  --delete-orphaned-prompts \
  --delete-orphaned-knowledge-bases \
  --delete-orphaned-models \
  --delete-orphaned-notes \
  --delete-orphaned-folders \
  --execute
```

### Audio Cache Cleanup

```bash
# Clean audio cache files older than 30 days
python standalone_prune.py --audio-cache-max-age-days 30 --execute
```

### Full Cleanup with VACUUM

```bash
# Complete cleanup with database optimization
python standalone_prune.py \
  --days 90 \
  --delete-inactive-users-days 180 \
  --audio-cache-max-age-days 30 \
  --run-vacuum \
  --execute
```

### Verbose Logging

```bash
# Enable debug logging for troubleshooting
python standalone_prune.py --dry-run --verbose

# Quiet mode (only errors)
python standalone_prune.py --execute --quiet
```

## Automation with Cron

Create a cron job to run pruning automatically:

```bash
# Edit crontab
crontab -e

# Add job to run every Sunday at 2 AM
0 2 * * 0 /path/to/run_prune.sh --days 60 --audio-cache-max-age-days 30 --execute >> /var/log/openwebui-prune.log 2>&1

# Add job to run preview daily (for monitoring)
0 1 * * * /path/to/run_prune.sh --dry-run >> /var/log/openwebui-prune-preview.log 2>&1
```

## Configuration Options

### Execution Mode
- `--dry-run`: Preview only, no changes (default)
- `--execute`: Actually perform deletions

### Age-Based Deletion
- `--days N`: Delete chats older than N days
- `--exempt-archived-chats`: Keep archived chats (default: true)
- `--no-exempt-archived-chats`: Include archived chats in deletion
- `--exempt-chats-in-folders`: Keep chats in folders/pinned

### Inactive User Deletion
- `--delete-inactive-users-days N`: Delete users inactive for N+ days
- `--exempt-admin-users`: Never delete admins (default: true, RECOMMENDED)
- `--no-exempt-admin-users`: Include admins (NOT RECOMMENDED)
- `--exempt-pending-users`: Never delete pending users (default: true)
- `--no-exempt-pending-users`: Include pending users

### Orphaned Data Deletion
- `--delete-orphaned-chats`: Delete orphaned chats (default: true)
- `--no-delete-orphaned-chats`: Skip orphaned chats
- `--delete-orphaned-tools`: Delete orphaned tools
- `--delete-orphaned-functions`: Delete orphaned functions
- `--delete-orphaned-prompts`: Delete orphaned prompts (default: true)
- `--delete-orphaned-knowledge-bases`: Delete orphaned KBs (default: true)
- `--delete-orphaned-models`: Delete orphaned models (default: true)
- `--delete-orphaned-notes`: Delete orphaned notes (default: true)
- `--delete-orphaned-folders`: Delete orphaned folders (default: true)

### Other Options
- `--audio-cache-max-age-days N`: Delete audio cache files older than N days
- `--run-vacuum`: Run VACUUM optimization (locks database!)
- `--verbose, -v`: Enable debug logging
- `--quiet, -q`: Suppress all output except errors

## How It Works

### Database Access

The script imports Open WebUI's backend modules directly:

```python
from backend.open_webui.models.users import Users
from backend.open_webui.models.chats import Chats
from backend.open_webui.internal.db import get_db
```

This means it uses the exact same:
- Database connection string (`DATABASE_URL`)
- ORM models and schemas
- Database session management
- Query logic

### Vector Database Access

The script uses Open WebUI's vector database factory:

```python
from backend.open_webui.routers.prune import get_vector_database_cleaner
```

This automatically detects and uses:
- ChromaDB: SQLite metadata + directory cleanup
- PGVector: PostgreSQL table cleanup
- Configures based on `VECTOR_DB` environment variable

### File System Operations

The script accesses the same file paths:

```python
from backend.open_webui.config import CACHE_DIR
```

This provides access to:
- Upload directory: `{DATA_DIR}/uploads/`
- Audio cache: `{CACHE_DIR}/audio/`
- Vector DB: `{DATA_DIR}/vector_db/`
- Lock file: `{CACHE_DIR}/.prune.lock`

## Is This Script Truly Standalone?

**Yes and No:**

✅ **Yes, it's standalone in that:**
- It's a command-line script (not part of the web server)
- It can be run independently without the API
- It can be scheduled via cron
- It doesn't require the FastAPI server to be running
- It has its own CLI interface

❌ **No, it's not completely isolated because:**
- It imports from Open WebUI backend modules
- It requires the same Python environment
- It needs access to the same database
- It reads the same environment variables
- It's essentially a CLI wrapper around the existing prune logic

**This is actually a GOOD thing** because:
- It reuses battle-tested code (no code duplication)
- It automatically gets bug fixes and improvements
- It maintains consistency with the web UI version
- It reduces maintenance burden

## Safety Features

1. **File-Based Locking**: Prevents concurrent prune operations
2. **Dry-Run by Default**: Requires explicit `--execute` flag
3. **Detailed Preview**: Shows exactly what will be deleted
4. **Comprehensive Logging**: All operations are logged
5. **Error Handling**: Graceful failure with proper cleanup
6. **Admin Protection**: Admins exempted from deletion by default

## Troubleshooting

### "Failed to import Open WebUI modules"

**Problem**: Script can't find Open WebUI backend modules

**Solutions**:
```bash
# Option 1: Run from Open WebUI directory
cd /path/to/open-webui
python prune/standalone_prune.py

# Option 2: Set PYTHONPATH
export PYTHONPATH="/path/to/open-webui:$PYTHONPATH"

# Option 3: Activate Open WebUI virtual environment
source /path/to/open-webui/.venv/bin/activate
```

### "Failed to connect to database"

**Problem**: Can't access database

**Solutions**:
```bash
# Make sure DATABASE_URL is set
export DATABASE_URL="sqlite:////path/to/webui.db"
# or for PostgreSQL
export DATABASE_URL="postgresql://user:pass@localhost/openwebui"

# Check if database file exists and is accessible
ls -la /path/to/webui.db
```

### "Vector database not available"

**Problem**: Vector database client initialization fails

**Solutions**:
```bash
# Set vector database type
export VECTOR_DB="chromadb"  # or "pgvector"

# For ChromaDB, ensure directory exists
ls -la /path/to/open-webui/data/vector_db/

# For PGVector, ensure PostgreSQL connection works
export VECTOR_DB_URL="postgresql://..."
```

### "Permission denied" errors

**Problem**: Can't read/write files

**Solutions**:
```bash
# Run as the same user as Open WebUI
sudo -u openwebui python prune/standalone_prune.py

# Or fix permissions
chown -R openwebui:openwebui /path/to/open-webui/data/
```

## Comparison: Standalone Script vs API

| Feature | Standalone Script | API Router |
|---------|------------------|------------|
| **Execution** | Command line | HTTP POST |
| **Authentication** | None (OS-level) | Admin JWT token |
| **Scheduling** | Cron jobs | External scheduler |
| **Server Required** | No | Yes |
| **Configuration** | CLI flags | JSON payload |
| **Output** | Console/logs | JSON response |
| **Code Reuse** | 100% (imports from prune.py) | Original implementation |

## Best Practices

1. **Always Preview First**: Run with `--dry-run` to see what will be deleted
2. **Test on Staging**: Test on a copy of your database first
3. **Backup Before Execution**: Create database backups before large cleanups
4. **Schedule During Low Usage**: Run during maintenance windows
5. **Monitor Logs**: Check logs after automated runs
6. **Start Conservative**: Begin with longer retention periods
7. **Avoid VACUUM on Production**: Unless during scheduled maintenance
8. **Keep Admins Exempt**: Always use `--exempt-admin-users`

## Support

For issues or questions:
- Check the Open WebUI documentation
- Review the prune.py source code for implementation details
- Open an issue on the Open WebUI GitHub repository

## License

This script is part of Open WebUI and follows the same license.
