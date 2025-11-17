# Open WebUI Prune Tool - Comprehensive Usage Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Interactive Mode](#interactive-mode)
5. [Non-Interactive Mode](#non-interactive-mode)
6. [Configuration Options](#configuration-options)
7. [Safety Warnings](#safety-warnings)
8. [Use Cases](#use-cases)
9. [Automation](#automation)
10. [Troubleshooting](#troubleshooting)

## Introduction

The Open WebUI Prune Tool provides a comprehensive solution for cleaning up your Open WebUI database and reclaiming disk space. It offers two modes of operation:

- **Interactive Mode**: Beautiful terminal UI for manual operations
- **Non-Interactive Mode**: Command-line interface for automation

## Installation

### Prerequisites

1. Open WebUI installation
2. Python 3.8+ environment
3. Open WebUI dependencies installed

### Install Additional Dependencies

```bash
cd /path/to/open-webui
pip install -r prune/requirements.txt
```

This installs:
- `rich` - For interactive terminal UI
- `pytest` - For running tests (optional)

## Quick Start

### Interactive Mode (Recommended for First-Time Users)

```bash
# Launch interactive UI
python prune/prune.py

# Or explicitly
python prune/prune_cli_interactive.py
```

### Non-Interactive Mode

```bash
# Preview what will be deleted (safe)
python prune/standalone_prune.py --dry-run

# Delete chats older than 60 days
python prune/standalone_prune.py --days 60 --execute

# Use the unified entry point
python prune/prune.py --days 60 --execute
```

### Using the Wrapper Script

```bash
# Make executable
chmod +x prune/run_prune.sh

# Run with automatic environment setup
./prune/run_prune.sh --dry-run
```

## Interactive Mode

### Features

✨ **Beautiful Terminal UI**
- Color-coded output for readability
- Tables and trees for organized information
- Progress bars for long operations
- Syntax highlighting for code

✨ **Step-by-Step Wizard**
- Guided configuration process
- Category-based settings
- Inline help and warnings
- Setting preview before execution

✨ **Safety Features**
- Multiple confirmation prompts
- Clear warning messages
- Preview mode before execution
- Impossible to accidentally delete

### Navigation

**Main Menu:**
1. Configure Settings - Set up what to delete
2. Preview Changes - See what will be deleted (safe)
3. Execute Pruning - Actually delete data (requires confirmation)
4. Help & Information - Learn about operations
5. Exit

**Configuration Categories:**
1. User Account Deletion - Delete inactive users
2. Chat Deletion Settings - Age-based and orphaned chats
3. Orphaned Data Cleanup - Tools, functions, prompts, etc.
4. Audio Cache Cleanup - TTS/STT files
5. System Optimization (VACUUM) - Database optimization

### Example Session

```
┌─────────────────────────────────────────────────────┐
│ Open WebUI Interactive Prune Tool                  │
│                                                     │
│ A safe and powerful way to clean up your Open      │
│ WebUI database and reclaim disk space.             │
└─────────────────────────────────────────────────────┘

Checking environment...
✓ Database connection successful (42 users found)
✓ Vector database: chromadb

══════════════════════════════════════════════════════
Main Menu
══════════════════════════════════════════════════════

[1] Configure Settings - Set up what to delete
[2] Preview Changes - See what will be deleted (safe)
[3] Execute Pruning - Actually delete data (DESTRUCTIVE)
[4] Help & Information - Learn about prune operations
[5] Exit

Choose an option [1]:
```

## Non-Interactive Mode

### Basic Syntax

```bash
python standalone_prune.py [OPTIONS]
```

### Execution Modes

**Dry-Run Mode (Default):**
```bash
# Preview only, no changes
python standalone_prune.py --dry-run

# Dry-run is default if --execute not specified
python standalone_prune.py --days 60
```

**Execution Mode:**
```bash
# Actually delete data
python standalone_prune.py --days 60 --execute
```

### Common Patterns

**Preview Everything:**
```bash
python standalone_prune.py \
  --days 90 \
  --delete-inactive-users-days 180 \
  --audio-cache-max-age-days 30 \
  --dry-run
```

**Conservative Cleanup:**
```bash
python standalone_prune.py \
  --days 180 \
  --exempt-archived-chats \
  --exempt-chats-in-folders \
  --audio-cache-max-age-days 60 \
  --execute
```

**Aggressive Cleanup:**
```bash
python standalone_prune.py \
  --days 30 \
  --delete-inactive-users-days 90 \
  --audio-cache-max-age-days 14 \
  --run-vacuum \
  --execute
```

**Orphaned Data Only:**
```bash
python standalone_prune.py \
  --delete-orphaned-chats \
  --delete-orphaned-knowledge-bases \
  --delete-orphaned-tools \
  --delete-orphaned-functions \
  --execute
```

## Configuration Options

### Age-Based Chat Deletion

**`--days N`**
- Delete chats older than N days
- Based on `updated_at` timestamp (last modification)
- Set to `None` to disable

**`--exempt-archived-chats`**
- Keep archived chats even if old
- Default: `False`
- Recommended: `True` for important chats

**`--exempt-chats-in-folders`**
- Keep chats organized in folders or pinned
- Default: `False`
- Useful for preserving organized work

**Example:**
```bash
# Delete chats older than 90 days, but keep archived ones
python standalone_prune.py --days 90 --exempt-archived-chats --execute
```

### Inactive User Deletion

⚠️ **WARNING: VERY DESTRUCTIVE** - Deletes all user data

**`--delete-inactive-users-days N`**
- Delete users inactive for N+ days
- Based on `last_active_at` timestamp
- Cascades to ALL user data
- Set to `None` to disable

**`--exempt-admin-users`**
- Never delete admin users
- Default: `True`
- **STRONGLY RECOMMENDED**: Always keep enabled

**`--exempt-pending-users`**
- Never delete pending/unapproved users
- Default: `True`
- Recommended for approval workflows

**Example:**
```bash
# Delete users inactive for 180+ days, keeping admins and pending
python standalone_prune.py \
  --delete-inactive-users-days 180 \
  --exempt-admin-users \
  --exempt-pending-users \
  --execute
```

### Orphaned Data Cleanup

Data from deleted users that no longer has an owner:

**`--delete-orphaned-chats`** (default: `True`)
- Chats from deleted users

**`--delete-orphaned-tools`** (default: `False`)
- Custom tools from deleted users

**`--delete-orphaned-functions`** (default: `False`)
- Actions, Pipes, Filters from deleted users

**`--delete-orphaned-prompts`** (default: `True`)
- Custom prompts from deleted users

**`--delete-orphaned-knowledge-bases`** (default: `True`)
- Knowledge bases from deleted users
- Also deletes vector collections

**`--delete-orphaned-models`** (default: `True`)
- Custom model configs from deleted users

**`--delete-orphaned-notes`** (default: `True`)
- Notes from deleted users

**`--delete-orphaned-folders`** (default: `True`)
- Folders from deleted users

**Example:**
```bash
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

**`--audio-cache-max-age-days N`**
- Delete audio files older than N days
- Includes TTS (text-to-speech) generated audio
- Includes STT (speech-to-text) transcription files
- Set to `None` to disable

**Example:**
```bash
# Clean audio cache older than 30 days
python standalone_prune.py --audio-cache-max-age-days 30 --execute
```

### System Optimization

⚠️ **WARNING: LOCKS DATABASE DURING EXECUTION**

**`--run-vacuum`**
- Run VACUUM to reclaim disk space
- Rebuilds database file
- **Locks entire database** during operation
- Can take 5-30+ minutes
- Users will experience errors during VACUUM
- **Only use during maintenance windows**

**Example:**
```bash
# Full cleanup with optimization (maintenance window only!)
python standalone_prune.py \
  --days 90 \
  --audio-cache-max-age-days 30 \
  --run-vacuum \
  --execute
```

### Logging Options

**`--verbose, -v`**
- Enable debug logging
- Shows detailed operation info
- Useful for troubleshooting

**`--quiet, -q`**
- Suppress all output except errors
- Useful for cron jobs
- Still logs to file if configured

**Example:**
```bash
# Verbose output for troubleshooting
python standalone_prune.py --dry-run --verbose

# Quiet mode for cron
python standalone_prune.py --execute --quiet
```

## Safety Warnings

### ⚠️ Critical Warnings

**ALWAYS CREATE A BACKUP BEFORE EXECUTING**

1. **Database Backup:**
   ```bash
   # For SQLite
   cp data/webui.db data/webui.db.backup

   # For PostgreSQL
   pg_dump openwebui > backup.sql
   ```

2. **File System Backup:**
   ```bash
   # Backup uploads and vector DB
   tar -czf backup.tar.gz data/uploads data/vector_db
   ```

### ⚠️ Destructive Operations

**User Deletion** (delete-inactive-users-days)
- Deletes ALL user data (chats, files, everything)
- Cannot be undone
- Test on staging first

**VACUUM** (run-vacuum)
- Locks database completely
- All users experience errors
- Can take very long time
- Only for maintenance windows

**Chat Deletion** (days)
- Permanently deletes conversations
- Includes all messages and history
- Consider archiving first

### ⚠️ Testing Recommendations

1. **Always preview first:**
   ```bash
   python standalone_prune.py --days 60 --dry-run
   ```

2. **Test on staging:**
   - Copy production database to staging
   - Run prune on staging first
   - Verify results before production

3. **Start conservative:**
   - Begin with longer retention periods
   - Gradually decrease as comfortable

4. **Monitor logs:**
   - Check logs after execution
   - Verify expected deletions
   - Watch for errors

## Use Cases

### 1. Regular Maintenance (Weekly)

**Goal:** Keep database clean without losing important data

```bash
# Cron: Every Sunday at 2 AM
0 2 * * 0 /path/to/prune/run_prune.sh \
  --days 90 \
  --exempt-archived-chats \
  --audio-cache-max-age-days 30 \
  --execute >> /var/log/prune-weekly.log 2>&1
```

### 2. Disk Space Emergency

**Goal:** Quickly reclaim space when running out

```bash
# Aggressive cleanup + VACUUM
python standalone_prune.py \
  --days 30 \
  --audio-cache-max-age-days 14 \
  --run-vacuum \
  --execute
```

### 3. User Cleanup (Monthly)

**Goal:** Remove inactive accounts and their data

```bash
# Cron: First Sunday of month at 3 AM
0 3 1-7 * 0 /path/to/prune/run_prune.sh \
  --delete-inactive-users-days 180 \
  --exempt-admin-users \
  --exempt-pending-users \
  --execute >> /var/log/prune-users.log 2>&1
```

### 4. Monitoring (Daily)

**Goal:** Track what would be deleted for trending

```bash
# Cron: Every day at 1 AM (dry-run only)
0 1 * * * /path/to/prune/run_prune.sh \
  --days 60 \
  --dry-run >> /var/log/prune-preview.log 2>&1
```

### 5. Manual Interactive Cleanup

**Goal:** One-off cleanup with visual feedback

```bash
# Launch interactive mode
python prune/prune.py

# Follow wizard:
# 1. Configure settings
# 2. Preview changes
# 3. Create backup
# 4. Execute with confirmation
```

## Automation

### Cron Job Setup

1. **Create wrapper script** (`/usr/local/bin/prune-openwebui.sh`):
   ```bash
   #!/bin/bash
   cd /path/to/open-webui
   source .venv/bin/activate
   export $(cat .env | grep -v '^#' | xargs)
   python prune/standalone_prune.py "$@"
   ```

2. **Make executable:**
   ```bash
   chmod +x /usr/local/bin/prune-openwebui.sh
   ```

3. **Add to crontab:**
   ```bash
   crontab -e

   # Add lines:
   0 2 * * 0 /usr/local/bin/prune-openwebui.sh --days 90 --execute
   ```

### Systemd Timer (Alternative to Cron)

1. **Create service** (`/etc/systemd/system/openwebui-prune.service`):
   ```ini
   [Unit]
   Description=Open WebUI Database Pruning
   After=network.target

   [Service]
   Type=oneshot
   User=openwebui
   WorkingDirectory=/path/to/open-webui
   EnvironmentFile=/path/to/open-webui/.env
   ExecStart=/path/to/open-webui/.venv/bin/python prune/standalone_prune.py --days 90 --execute
   ```

2. **Create timer** (`/etc/systemd/system/openwebui-prune.timer`):
   ```ini
   [Unit]
   Description=Weekly Open WebUI Prune

   [Timer]
   OnCalendar=Sun *-*-* 02:00:00
   Persistent=true

   [Install]
   WantedBy=timers.target
   ```

3. **Enable and start:**
   ```bash
   systemctl enable openwebui-prune.timer
   systemctl start openwebui-prune.timer
   ```

### Log Rotation

**Create logrotate config** (`/etc/logrotate.d/openwebui-prune`):
```
/var/log/openwebui-prune*.log {
    weekly
    rotate 12
    compress
    delaycompress
    missingok
    notifempty
    create 0640 openwebui openwebui
}
```

## Troubleshooting

### Common Issues

**Issue: "Failed to import Open WebUI modules"**

Solution:
```bash
# Ensure running from Open WebUI directory
cd /path/to/open-webui

# Activate virtual environment
source .venv/bin/activate

# Verify imports work
python -c "from backend.open_webui.models.users import Users"
```

**Issue: "Failed to connect to database"**

Solution:
```bash
# Check DATABASE_URL is set
echo $DATABASE_URL

# For SQLite, verify file exists
ls -la data/webui.db

# For PostgreSQL, test connection
psql $DATABASE_URL -c "SELECT 1"
```

**Issue: "Operation already in progress"**

Solution:
```bash
# Check for stale lock file
ls -la cache/.prune.lock

# If stale (>2 hours old), remove it
rm cache/.prune.lock
```

**Issue: "VACUUM failed"**

Solution:
```bash
# VACUUM needs exclusive access
# 1. Stop Open WebUI server
# 2. Run prune with VACUUM
# 3. Restart server

# Or skip VACUUM for now
python standalone_prune.py --days 60 --execute
# (without --run-vacuum)
```

**Issue: "Permission denied" errors**

Solution:
```bash
# Run as same user as Open WebUI
sudo -u openwebui python prune/standalone_prune.py --dry-run

# Or fix permissions
chown -R openwebui:openwebui data/
```

### Getting Debug Information

```bash
# Run with verbose logging
python standalone_prune.py --dry-run --verbose

# Check logs
tail -f /var/log/openwebui-prune.log

# Test database connection
python -c "
from backend.open_webui.models.users import Users
users = Users.get_users()
print(f'Found {len(users[\"users\"])} users')
"
```

### Performance Issues

**If preview/execution is very slow:**

1. **Check database size:**
   ```bash
   # SQLite
   du -h data/webui.db

   # PostgreSQL
   psql -c "SELECT pg_size_pretty(pg_database_size('openwebui'))"
   ```

2. **Monitor during execution:**
   ```bash
   # In one terminal, run prune
   python standalone_prune.py --execute

   # In another, monitor resources
   htop
   iotop
   ```

3. **Consider running during low-usage times**

## Best Practices

### 1. Testing Workflow

1. ✓ Always preview first (`--dry-run`)
2. ✓ Test on staging environment
3. ✓ Backup before execution
4. ✓ Start with conservative settings
5. ✓ Monitor logs after execution
6. ✓ Verify deletions were expected

### 2. Production Workflow

1. ✓ Schedule during low-usage hours
2. ✓ Create automated backups before prune
3. ✓ Use log rotation
4. ✓ Set up monitoring/alerts
5. ✓ Document your settings
6. ✓ Review logs regularly

### 3. Safety Checklist

Before executing:
- [ ] Created database backup
- [ ] Created file system backup
- [ ] Ran preview and reviewed counts
- [ ] Verified settings are correct
- [ ] Scheduled during maintenance window (if using VACUUM)
- [ ] Notified users (if using VACUUM)
- [ ] Have rollback plan ready

### 4. Automation Checklist

For cron jobs:
- [ ] Tested command manually first
- [ ] Logging is configured
- [ ] Log rotation is set up
- [ ] Error notifications are configured
- [ ] Monitoring is in place
- [ ] Documentation is updated

## Additional Resources

- **README.md** - Quick start guide
- **ANALYSIS.md** - Technical details and feasibility
- **FEATURES.md** - Complete feature catalog
- **example_cron.txt** - Cron job examples
- **test_prune.py** - Test suite for verification

## Support

For issues or questions:
- Check the troubleshooting section above
- Review the Open WebUI documentation
- Open an issue on GitHub
- Check community forums

## License

This tool is part of Open WebUI and follows the same license.
