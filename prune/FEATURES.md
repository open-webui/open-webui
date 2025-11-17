# Complete Feature Catalog from prune.py

This document catalogs EVERY feature, class, function, and piece of logic from the original `backend/open_webui/routers/prune.py` to ensure complete coverage.

## File Statistics
- **Total Lines**: 1794
- **Classes**: 7
- **Functions**: 20
- **Models**: 2

## Classes

### 1. PruneLock (Lines 42-114)
**Purpose**: File-based locking mechanism to prevent concurrent prune operations

**Features**:
- `LOCK_FILE`: Path to lock file in CACHE_DIR
- `LOCK_TIMEOUT`: 2-hour safety timeout
- `acquire()`: Try to acquire lock, handle stale locks
- `release()`: Release lock by removing file
- Stores operation ID, timestamp, and PID in lock file
- Automatic stale lock cleanup

### 2. JSONFileIDExtractor (Lines 116-183)
**Purpose**: Utility for extracting and validating file IDs from JSON content

**Features**:
- `_FILE_ID_PATTERN`: Regex for UUID in "id" field
- `_URL_PATTERN`: Regex for UUID in API URLs
- `extract_file_ids()`: Extract without validation
- `extract_and_validate_file_ids()`: Extract and validate against DB
- Compiled patterns for performance

### 3. VectorDatabaseCleaner (Abstract, Lines 244-304)
**Purpose**: Abstract base class for vector database cleanup

**Methods**:
- `count_orphaned_collections()`: Preview count
- `cleanup_orphaned_collections()`: Actual deletion
- `delete_collection()`: Delete specific collection

### 4. ChromaDatabaseCleaner (Lines 306-679)
**Purpose**: ChromaDB-specific cleanup implementation

**Features**:
- SQLite metadata database handling
- Physical directory cleanup
- Collection name to UUID mapping
- Segment-based storage architecture
- Orphaned database record cleanup
- FTS (full-text search) cleanup
- FTS index rebuild
- Selective FTS preservation
- Atomic transaction handling
- VACUUM support

**Methods**:
- `__init__()`: Set up paths to vector_dir and chroma.sqlite3
- `count_orphaned_collections()`: Count using UUID mapping
- `cleanup_orphaned_collections()`: Delete directories and DB records
- `delete_collection()`: Delete via client and physical cleanup
- `_build_expected_collections()`: Build set of valid collection names
- `_get_collection_mappings()`: Map segment UUIDs to collection names
- `_cleanup_orphaned_database_records()`: Clean embeddings, metadata, FTS
- `_cleanup_fts_selectively()`: Preserve valid FTS entries

### 5. PGVectorDatabaseCleaner (Lines 681-859)
**Purpose**: PGVector database cleanup implementation

**Features**:
- PostgreSQL session management
- document_chunk table cleanup
- VACUUM ANALYZE support
- Simple delete() method usage

**Methods**:
- `__init__()`: Initialize with PGVector session
- `count_orphaned_collections()`: Count from document_chunk table
- `cleanup_orphaned_collections()`: Delete using VECTOR_DB_CLIENT.delete()
- `delete_collection()`: Simple delete via client
- `_get_orphaned_collections()`: Query distinct collection names
- `_build_expected_collections()`: Build expected set

### 6. MilvusDatabaseCleaner (Extended - Not in Original)
**Purpose**: Milvus database cleanup implementation (standard mode)

**Features**:
- Handles collection-based storage
- Each collection is independent
- Collection naming pattern: `{prefix}_{collection_name}`
- Converts dashes to underscores (Milvus naming convention)
- Lists all collections via client.list_collections()
- Deletes orphaned collections via client.drop_collection()

**Methods**:
- `__init__()`: Initialize with Milvus client
- `count_orphaned_collections()`: Count orphaned collections
- `cleanup_orphaned_collections()`: Delete orphaned collections
- `delete_collection()`: Delete specific collection
- `_build_expected_collections()`: Build set of expected collections

### 7. MilvusMultitenancyDatabaseCleaner (Extended - Not in Original)
**Purpose**: Milvus multitenancy database cleanup implementation

**Features**:
- Handles shared collections with resource_id partitioning
- Uses 5 shared collections: memories, knowledge, files, web_search, hash_based
- Multiple logical collections share physical collections
- Distinguished by resource_id field
- Queries each shared collection for distinct resource_ids
- Deletes orphaned data by resource_id filter expressions
- Safer for large deployments with many logical collections

**Methods**:
- `__init__()`: Initialize with Milvus client and shared_collections
- `count_orphaned_collections()`: Count orphaned resource_ids
- `cleanup_orphaned_collections()`: Delete orphaned data by resource_id
- `delete_collection()`: Delete data for specific resource_id
- `_build_expected_resource_ids()`: Build set of expected resource_ids

### 8. NoOpVectorDatabaseCleaner (Lines 861-884)
**Purpose**: No-operation implementation for unsupported databases

**Methods**:
- All methods return 0 or success without doing anything

### 9. get_vector_database_cleaner() (Lines 886-910)
**Purpose**: Factory function to get appropriate cleaner

**Logic**:
- Detect VECTOR_DB type from environment
- Return ChromaDatabaseCleaner for "chroma"
- Return PGVectorDatabaseCleaner for "pgvector"
- Return MilvusDatabaseCleaner for "milvus" (standard mode)
- Return MilvusMultitenancyDatabaseCleaner for "milvus" (multitenancy mode)
- Auto-detect multitenancy via hasattr(client, 'shared_collections')
- Return NoOpVectorDatabaseCleaner for others

## Models

### 1. PruneDataForm (Lines 912-930)
**Purpose**: Configuration for prune operation

**Fields**:
- `days`: Optional[int] - Age threshold for chats
- `exempt_archived_chats`: bool = False
- `exempt_chats_in_folders`: bool = False
- `delete_orphaned_chats`: bool = True
- `delete_orphaned_tools`: bool = False
- `delete_orphaned_functions`: bool = False
- `delete_orphaned_prompts`: bool = True
- `delete_orphaned_knowledge_bases`: bool = True
- `delete_orphaned_models`: bool = True
- `delete_orphaned_notes`: bool = True
- `delete_orphaned_folders`: bool = True
- `audio_cache_max_age_days`: Optional[int] = 30
- `delete_inactive_users_days`: Optional[int] = None
- `exempt_admin_users`: bool = True
- `exempt_pending_users`: bool = True
- `run_vacuum`: bool = False
- `dry_run`: bool = True

### 2. PrunePreviewResult (Lines 932-947)
**Purpose**: Preview counts for dry-run mode

**Fields**:
- `inactive_users`: int = 0
- `old_chats`: int = 0
- `orphaned_chats`: int = 0
- `orphaned_files`: int = 0
- `orphaned_tools`: int = 0
- `orphaned_functions`: int = 0
- `orphaned_prompts`: int = 0
- `orphaned_knowledge_bases`: int = 0
- `orphaned_models`: int = 0
- `orphaned_notes`: int = 0
- `orphaned_folders`: int = 0
- `orphaned_uploads`: int = 0
- `orphaned_vector_collections`: int = 0
- `audio_cache_files`: int = 0

## Helper Functions

### 1. collect_file_ids_from_dict() (Lines 191-242)
**Purpose**: Recursively traverse dict/list to collect file IDs

**Features**:
- Direct dict traversal (no json.dumps)
- 75% memory reduction on large databases
- O(1) validation against preloaded set
- Recursion depth limit (100)
- Detects patterns: id, file_id, fileId, file_ids, fileIds

### 2. count_inactive_users() (Lines 950-981)
**Purpose**: Count users for deletion by inactivity

**Features**:
- Cutoff time calculation
- Admin exemption
- Pending user exemption
- last_active_at timestamp check
- Optional pre-fetched user list

### 3. count_old_chats() (Lines 983-1008)
**Purpose**: Count chats for deletion by age

**Features**:
- Cutoff time calculation
- Archived chat exemption
- Folder/pinned chat exemption
- updated_at timestamp check

### 4. count_orphaned_records() (Lines 1010-1083)
**Purpose**: Count all types of orphaned records

**Features**:
- Counts for: chats, files, tools, functions, prompts, KBs, models, notes, folders
- Respects form_data toggle settings
- Checks against active_user_ids
- Checks against active_file_ids

### 5. count_orphaned_uploads() (Lines 1085-1121)
**Purpose**: Count orphaned files in uploads directory

**Features**:
- File path iteration
- UUID extraction from filenames
- Multiple filename pattern support
- Validation against active_file_ids

### 6. count_audio_cache_files() (Lines 1123-1148)
**Purpose**: Count audio cache files for deletion

**Features**:
- Two directories: speech and transcriptions
- mtime-based age check
- Cutoff time calculation

### 7. get_active_file_ids() (Lines 1150-1282)
**Purpose**: Get all actively referenced file IDs

**Features**:
- Preload all file IDs for O(1) validation
- Scan knowledge bases for file references
- Stream chats using Core SELECT (avoid ORM overhead)
- Direct dict traversal (Phase 1.5 optimization)
- Scan folders (items and data fields)
- Scan standalone messages
- Batch processing (1000 rows for chats, 100 for folders)
- Handles multiple data structures

### 8. safe_delete_file_by_id() (Lines 1284-1304)
**Purpose**: Safely delete file record and vector collection

**Features**:
- Check if file exists
- Use modular vector database cleaner
- Delete vector collection
- Delete file record
- Error handling

### 9. cleanup_orphaned_uploads() (Lines 1306-1351)
**Purpose**: Clean up orphaned physical upload files

**Features**:
- Directory iteration
- UUID extraction from filenames
- Multiple pattern matching
- Physical file deletion
- Deletion count tracking

### 10. delete_inactive_users() (Lines 1353-1400)
**Purpose**: Delete inactive users

**Features**:
- Cutoff time calculation
- Admin exemption
- Pending user exemption
- Cascade deletion (all user data)
- Per-user logging
- Error handling per user

### 11. cleanup_audio_cache() (Lines 1402-1447)
**Purpose**: Clean up old audio cache files

**Features**:
- Two directories: speech and transcriptions
- mtime-based deletion
- Size tracking
- MB calculation and logging

### 12. prune_data() (Lines 1449-1794)
**Purpose**: Main prune operation endpoint

**Features**:

#### Lock Management
- Acquire lock at start
- Release lock in finally block
- Prevent concurrent operations

#### Dry-Run Mode (Lines 1468-1516)
- Preview counts calculation
- Build active user/KB/file ID sets
- Call all count functions
- Return PrunePreviewResult

#### Execution Mode (Lines 1518-1779)

**Stage 0: Delete Inactive Users** (Lines 1530-1546)
- Check if enabled
- Call delete_inactive_users()
- Log results

**Stage 1: Delete Old Chats** (Lines 1548-1572)
- Calculate cutoff time
- Iterate all chats
- Apply exemptions (archived, folders, pinned)
- Batch delete

**Stage 2: Build Preservation Set** (Lines 1574-1590)
- Get active user IDs
- Get active KB IDs
- Get active file IDs

**Stage 3: Delete Orphaned Database Records** (Lines 1592-1710)
- Delete orphaned files with vector collections
- Delete orphaned knowledge bases
- Delete orphaned chats (if enabled)
- Delete orphaned tools (if enabled)
- Delete orphaned functions (if enabled)
- Delete orphaned notes (if enabled)
- Delete orphaned prompts (if enabled)
- Delete orphaned models (if enabled)
- Delete orphaned folders (if enabled)
- Track counts for each type

**Stage 4: Clean Up Orphaned Physical Files** (Lines 1712-1728)
- Rebuild active file/KB sets
- Cleanup orphaned uploads
- Cleanup orphaned vector collections
- Track warnings

**Stage 5: Audio Cache Cleanup** (Duplicate at 1729-1737)
- Clean if enabled
- Log results

**Stage 6: Database Optimization** (Lines 1738-1772)
- VACUUM main database (if enabled)
- VACUUM ChromaDB database (if ChromaDB)
- VACUUM ANALYZE PostgreSQL (if PGVector)
- Error handling per database

#### Final Cleanup (Lines 1774-1779)
- Log warnings if any
- Log success
- Return True

#### Error Handling (Lines 1781-1794)
- Catch all exceptions
- Log with stack trace
- Raise HTTPException
- Release lock in finally

## Constants and Patterns

### UUID_PATTERN (Line 186-188)
- Regex for validating UUIDs
- Used in collect_file_ids_from_dict

### Lock File Settings (Lines 50-51)
- Path: `CACHE_DIR/.prune.lock`
- Timeout: 2 hours

## Special Logic & Optimizations

### 1. Memory Optimization
- Direct dict traversal instead of json.dumps() + regex
- Reduces memory by 75% on large databases
- Preload file IDs for O(1) validation

### 2. Database Streaming
- Use Core SELECT with stream_results
- Batch fetching (1000 rows for chats, 100 for folders)
- Avoid ORM overhead

### 3. ChromaDB FTS Cleanup
- Selective preservation of valid entries
- Atomic operations with temp tables
- Validation before deletion
- Conservative fallback on errors
- Index rebuild after cleanup

### 4. Error Handling
- Per-item error handling (continue on failure)
- Graceful degradation
- Comprehensive logging
- Lock cleanup in finally blocks

### 5. Safety Features
- Dry-run by default
- File-based locking
- Stale lock detection
- Admin exemption by default
- Pending user exemption by default
- Archived chat exemption option
- Folder/pinned chat exemption option

## Integration Points

### Database
- SQLAlchemy ORM models
- Core SELECT for streaming
- Raw SQL for VACUUM
- get_db() context manager

### Vector Database
- VECTOR_DB_CLIENT global
- VECTOR_DB type detection
- ChromaDB: sqlite3 + shutil
- PGVector: session + text()

### File System
- CACHE_DIR for lock, audio
- uploads/ directory
- vector_db/ directory
- Path operations

### Configuration
- Environment variables
- Pydantic models
- SRC_LOG_LEVELS for logging

## API Endpoint

### Route: POST /
- Requires admin authentication
- Accepts PruneDataForm
- Returns Union[bool, PrunePreviewResult]
- Dry-run returns preview
- Execute returns True on success

## Logging

### Log Levels
- DEBUG: Detailed operation info
- INFO: Major operations, counts
- WARNING: Non-fatal issues, stale locks
- ERROR: Failures, exceptions

### Log Messages
- Operation start/complete
- Counts for each deletion type
- Warnings for partial failures
- Stack traces for exceptions

## Edge Cases Handled

1. **Stale Locks**: Automatic removal after timeout
2. **Corrupt Lock Files**: Remove and retry
3. **Missing Directories**: Skip gracefully
4. **Concurrent Operations**: Prevented by lock
5. **Partial Failures**: Continue with warnings
6. **Empty Results**: Handle gracefully
7. **Database Unavailable**: Error and exit
8. **Vector DB Not Found**: No-op cleaner
9. **FTS Corruption**: Skip FTS cleanup
10. **Permission Errors**: Log and continue

## Total Feature Count

**Original prune.py Features:**
- **7 Classes** (original)
- **20 Functions** (original)
- **2 Models** (original)
- **17 Configuration Options**
- **14 Deletion Types**
- **6 Execution Stages**
- **10+ Safety Features**
- **Multiple Optimizations**
- **Comprehensive Error Handling**

**Extended Features (Standalone Script Additions):**
- **+2 Vector DB Cleaner Classes** (MilvusDatabaseCleaner, MilvusMultitenancyDatabaseCleaner)
- **Total Classes in Standalone Implementation: 9**
- **Total Vector Database Implementations: 5** (Chroma, PGVector, Milvus, Milvus Multitenancy, NoOp)

This represents the COMPLETE functionality from the original prune.py PLUS extended Milvus support.
