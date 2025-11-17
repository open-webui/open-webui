# ⚠️ COMPREHENSIVE WARNINGS - Open WebUI Prune Tool

This document contains ALL warnings and safety information from the web UI prune dialog,
ensuring you have complete understanding of what this tool does and its implications.

## 🔴 CRITICAL: Destructive Operation Warning

### THIS ACTION WILL PERMANENTLY DELETE DATA

**This operation cannot be undone. Create a complete backup before proceeding.**

This action will permanently delete data from your database. Only orphaned or old data,
based on your configuration settings, will be deleted. All active, referenced data
remains completely safe.

This operation is performed entirely at your own risk - having a backup ensures you
can restore any data if something unexpected occurs.

## ⚠️ PERFORMANCE WARNING

**This operation may take a very long time to complete.**

Especially if you have never cleaned your database before or if your instance stores
large amounts of data. The process could take anywhere from:
- **Seconds** - Small databases with little data
- **Minutes** - Medium databases with moderate data
- **Half an hour and beyond** - Large databases with extensive data

The duration depends on:
- Total database size
- Number of chats and messages
- Number of files and uploads
- Vector database size
- Whether VACUUM is enabled

## 📊 What Will Be Deleted

### Note
This list provides an overview of what will be deleted during the pruning process
and may not be complete or fully up-to-date. Always run preview mode first!

### 👤 Users

#### Inactive User Account Deletion
- Removes user accounts that have been inactive for a specified period based on
  their `last_active_at` timestamp
- **CASCADES TO ALL USER DATA** - Everything the user created will be deleted

#### Safety Exemptions
- **Admin users**: Can be exempted from deletion (STRONGLY RECOMMENDED)
- **Pending users**: Can be exempted from deletion (awaiting approval)

### 💬 Chats

#### Age-Based Chat Deletion
- Removes conversations older than specified days based on when they were last
  modified or updated (NOT when they were created)
- Uses `updated_at` timestamp

#### Supports exemptions for:
- **Archived chats** - Conversations you've archived for safe-keeping
- **Chats organized in folders** - Organized work you want to preserve
- **Pinned chats** - Important conversations you've marked

#### Orphaned Content Cleanup
- **Delete orphaned chats from deleted users** - Conversations with no owner
- **Delete orphaned folders from deleted users** - Organization structure with no owner

### 🔧 Workspace

#### Orphaned Workspace Items from Deleted Users

**What gets deleted:**
- **Orphaned knowledge bases** - RAG databases from deleted users
- **Orphaned custom tools** - Tool integrations created by deleted users
- **Orphaned custom functions** - Actions, Pipes, and Filters from deleted users
- **Orphaned custom prompts and templates** - Prompt library items from deleted users
- **Orphaned custom models and configurations** - Model settings from deleted users
- **Orphaned notes** - Personal notes from deleted users

**Why delete:**
These items no longer have an owner and cannot be accessed or managed.

### 💾 Files & Vector Storage

#### What gets cleaned:
- **Orphaned files and attachments** - Files from deleted content
- **Vector embeddings and collections** - AI embeddings for removed data
- **Uploaded files that lost their database references** - Physical files without DB records
- **Vector storage directories without corresponding data** - Empty vector DB directories

#### Technical Details:
- Scans knowledge bases for file references
- Scans chats and messages for file usage
- Scans folders for file organization
- Cross-references with physical file system
- Validates vector database collections
- Removes orphaned vector embeddings

### 🖼️ Images & Audio Content Cleanup

#### Generated Images
- **Already integrated with file system** - Orphaned images are automatically cleaned
  up when chats are deleted
- Part of the comprehensive file cleanup process

#### Uploaded Images
- **Already integrated with file system** - Orphaned images are automatically cleaned
  up based on active references
- Validated against active file IDs

#### Audio Cache Cleanup
- **Remove old text-to-speech (TTS) generated audio files**
- **Remove speech-to-text (STT) transcription files**
- Based on file modification time (mtime)
- Configurable age threshold (default: 30 days)

#### Audio Directories:
- `cache/audio/speech/` - TTS generated audio
- `cache/audio/transcriptions/` - STT recordings and metadata

### 💽 Database & System Cleanup

#### What gets cleaned:
- **Removal of broken database references and stale entries**
- **Disk space reclamation** by database cleanup and optimization
- **Synchronization** of database records with actual file storage
- **Fix inconsistencies** between storage systems

#### VACUUM Operation:
- **Database performance optimization**
- **Rebuilds database file** to reclaim space
- **LOCKS DATABASE** during execution
- **Users will experience errors** while VACUUM runs
- Can take **5-30+ minutes** depending on database size

## ⚠️ SPECIFIC WARNINGS BY CATEGORY

### 1. Inactive User Deletion ⚠️⚠️⚠️

**MOST DESTRUCTIVE OPERATION**

When you delete a user, you delete EVERYTHING they created:
- ✗ All their chats and conversations
- ✗ All their messages and history
- ✗ All their uploaded files
- ✗ All their custom tools
- ✗ All their custom functions (Actions, Pipes, Filters)
- ✗ All their custom prompts
- ✗ All their knowledge bases and vector data
- ✗ All their custom model configurations
- ✗ All their notes
- ✗ All their folders and organization
- ✗ Everything else associated with their account

**Recommendations:**
- ✓ Use long periods (180+ days minimum)
- ✓ ALWAYS exempt admin users
- ✓ Consider exempting pending users
- ✓ Test on staging first
- ✓ Create backups before execution

**Warning for short periods (<30 days):**
Very short periods may accidentally delete active users who are just on vacation
or temporarily inactive. Consider using 30+ days for safety.

### 2. Age-Based Chat Deletion ⚠️⚠️

**PERMANENT LOSS OF CONVERSATIONS**

Chats are deleted based on `updated_at` timestamp (when last modified):
- Includes all messages in the conversation
- Includes all chat metadata
- Cannot be recovered after deletion

**Exemptions help preserve important data:**
- **Archived chats** - Conversations you've marked for keeping
- **Chats in folders** - Organized work projects
- **Pinned chats** - Important ongoing conversations

**Recommendations:**
- ✓ Start with longer periods (90+ days)
- ✓ Enable archived chat exemption
- ✓ Consider folder exemption for organized work
- ✓ Archive important chats before running
- ✓ Run preview first to see what will be deleted

### 3. VACUUM Database Optimization ⚠️⚠️⚠️

**LOCKS DATABASE - CAUSES DOWNTIME**

When VACUUM runs:
- ✗ **Entire database is locked**
- ✗ **ALL users will experience errors**
- ✗ **No operations can proceed**
- ✗ **Can take 5-30+ minutes** (or longer)

**Operation Details:**
1. Database is locked exclusively
2. All data is rewritten to new file
3. Old file is replaced with new file
4. Free space is reclaimed
5. Database is unlocked

**When to use:**
- ✓ During scheduled maintenance windows
- ✓ When users have been notified
- ✓ When significant space needs reclaiming
- ✓ When you can afford downtime

**When NOT to use:**
- ✗ During normal operations
- ✗ When users are active
- ✗ For routine cleanups
- ✗ When you can't afford downtime

**Recommendations:**
- ✓ Schedule during off-hours (2-4 AM)
- ✓ Notify users in advance
- ✓ Plan for 30-60 minute window
- ✓ Monitor disk space during operation
- ✓ Have rollback plan ready
- ✓ Consider doing separately from prune

### 4. Orphaned Data Cleanup ⚠️

**Generally Safe, But Permanent**

Orphaned data is content from deleted users that no longer has an owner:
- Cannot be accessed through UI
- Cannot be managed or edited
- Takes up database and disk space

**What happens:**
- Database records are deleted
- Physical files are removed
- Vector embeddings are cleaned up
- References are removed

**Safety:**
- ✓ Less risky than user deletion
- ✓ Unlikely to affect active users
- ✓ Reclaims significant space
- ✓ Improves database performance

**But still:**
- ✗ Cannot be undone
- ✗ Some orphaned data might be valuable
- ✗ May have shared knowledge bases

### 5. Audio Cache Cleanup ⚠️

**Low Risk, Good for Space**

Audio cache includes:
- TTS files - Generated when AI speaks to users
- STT files - Uploaded audio for transcription
- Metadata files - Transcription data

**What happens:**
- Old audio files are deleted based on mtime
- Only affects cached files
- Does not affect transcribed text (already saved)
- Can regenerate TTS if needed

**Safety:**
- ✓ Low risk operation
- ✓ Files can be regenerated if needed
- ✓ Good space savings
- ✓ Fast operation

**Recommendations:**
- ✓ Use 30-60 day threshold
- ✓ Safe to run regularly
- ✓ Significant space savings for heavy TTS/STT usage

### 6. Vector Database Cleanup ⚠️

**Technical but Important**

Vector databases store embeddings for:
- File content (for RAG)
- Knowledge bases
- Search indices

**What gets cleaned:**
- Orphaned collections from deleted files
- Orphaned collections from deleted knowledge bases
- Unused vector directories
- Stale embeddings

**Supported Databases:**
- **ChromaDB** - Full cleanup including:
  - Physical directories
  - SQLite metadata
  - Orphaned embeddings
  - Full-text search indices
  - Segment metadata
- **PGVector** - Uses existing client delete methods
- **Others** - No-op (safe, does nothing)

**Safety:**
- ✓ Only deletes truly orphaned data
- ✓ Validates against active references
- ✓ Multiple safety checks
- ✓ Graceful error handling

## 🎯 SAFETY CHECKLIST

Before running prune operations, ensure:

### Pre-Execution
- [ ] Created database backup
- [ ] Created file system backup (uploads, vector_db)
- [ ] Ran preview mode and reviewed counts
- [ ] Understand what will be deleted
- [ ] Verified configuration settings
- [ ] Tested on staging environment
- [ ] Scheduled during appropriate time
- [ ] Notified users (if using VACUUM)

### Configuration Review
- [ ] User deletion period is appropriate (if enabled)
- [ ] Chat deletion period is appropriate (if enabled)
- [ ] Admin users are exempted (CRITICAL)
- [ ] Pending users are exempted (if needed)
- [ ] Archived chats are exempted (if desired)
- [ ] Folder/pinned chats are exempted (if desired)
- [ ] VACUUM is only enabled for maintenance windows

### Post-Execution
- [ ] Check logs for errors
- [ ] Verify deletion counts match preview
- [ ] Verify database size reduced (if expected)
- [ ] Test system functionality
- [ ] Verify no unintended deletions
- [ ] Document what was cleaned
- [ ] Update backup rotation

## 📚 UNDERSTANDING TIMESTAMPS

### last_active_at (Users)
- Updated when user logs in
- Updated when user makes API calls
- Used for inactive user deletion
- Timestamp format: Unix epoch (seconds since 1970)

### updated_at (Chats)
- Updated when chat is modified
- Updated when messages are added
- NOT when chat is created
- Used for age-based chat deletion
- Timestamp format: Unix epoch (seconds since 1970)

### File mtime (Audio Cache)
- File system modification time
- Updated when file is created or modified
- Used for audio cache cleanup
- Timestamp format: Unix epoch (seconds since 1970)

## 🔍 WHAT IS PRESERVED

### Always Preserved (Never Deleted)
- Active user accounts (with activity)
- Referenced files (used in chats, KBs)
- Files in active knowledge bases
- Files referenced in messages
- Valid vector collections
- Database structure and schema

### Optionally Preserved (Based on Settings)
- Admin users (if exempted)
- Pending users (if exempted)
- Archived chats (if exempted)
- Chats in folders (if exempted)
- Pinned chats (if folders exempted)
- Recent data (within retention period)

### What Determines "Active"
A file is considered active if it's referenced by:
- Any knowledge base
- Any chat message
- Any folder
- Any other active data structure

## 🚨 EMERGENCY RECOVERY

### If Something Goes Wrong

**1. Stop immediately:**
```bash
# If running, Ctrl+C to cancel
# Remove lock file if stuck
rm cache/.prune.lock
```

**2. Restore from backup:**
```bash
# For SQLite
cp data/webui.db.backup data/webui.db

# For PostgreSQL
psql openwebui < backup.sql

# Restore files
tar -xzf backup.tar.gz
```

**3. Verify restoration:**
```bash
# Check user count
# Check chat count
# Check file count
# Test login and basic operations
```

**4. Investigate what happened:**
```bash
# Check logs
tail -100 /var/log/openwebui-prune.log

# Review configuration that was used
# Determine what went wrong
```

## 📖 ADDITIONAL WARNINGS

### Database Locks
- Operations may lock database briefly
- Large operations take longer
- VACUUM locks exclusively
- Users may experience slowness

### Disk Space
- VACUUM temporarily needs 2x space
- Ensure sufficient free disk space
- Monitor disk usage during operation
- May temporarily increase before decreasing

### Performance Impact
- Large deletions may slow database
- Many file deletions may stress I/O
- Vector DB cleanup can be CPU intensive
- Consider running during low-usage times

### Irreversibility
- **THIS CANNOT BE STRESSED ENOUGH**
- Once data is deleted, it's **GONE FOREVER**
- Backups are your **ONLY recovery option**
- No "undo" or "restore" feature
- No trash bin or recovery mode

## 📞 GETTING HELP

If you're unsure:
- Review the USAGE_GUIDE.md
- Check the FEATURES.md for complete details
- Run preview mode first
- Test on staging environment
- Start with conservative settings
- Ask in community forums
- Open GitHub issue for bugs

## ✅ FINAL SAFETY REMINDER

**GOLDEN RULES:**
1. **ALWAYS** create backups before executing
2. **ALWAYS** run preview first
3. **NEVER** delete admins (keep exempted)
4. **NEVER** use short deletion periods
5. **NEVER** run VACUUM during active hours
6. **START** conservative, adjust gradually
7. **TEST** on staging before production
8. **MONITOR** logs after execution
9. **VERIFY** results match expectations
10. **DOCUMENT** your configuration and results

When in doubt, **DON'T DELETE**. Better to have a larger database than to lose important data!

---

**Remember:** This tool is powerful and efficient, but with great power comes great responsibility. Use it wisely!
