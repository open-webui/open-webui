# migrate_files_to_pgvector.py

`backend/scripts/migrate_files_to_pgvector.py` re-processes every file stored under `backend/data/uploads` and rebuilds its embeddings directly into Pgvector. It mirrors the normal upload pipeline (loader, splitter, metadata, embedding) and recreates both `knowledge.id` collections and the per-file `file-{file.id}` collections.

## Prerequisites
- `docker-compose.local.yaml` (or your environment) must set `VECTOR_DB=pgvector`, `DATABASE_URL`, `PGVECTOR_DB_URL`, embedding keys, etc.
- Pgvector extension enabled on the target Postgres database.
- Uploaded files must be accessible at the paths stored in the `file` table.
- Run inside the backend container: `docker compose exec open-webui bash`.
- `tqdm` package installed (for progress bars): `pip install tqdm`

## Usage

### Basic Usage
```bash
cd /app/backend/scripts
python migrate_files_to_pgvector.py [options]
```

### Running as Background Process

For long-running migrations, run the script in the background with output redirected to a log file:

```bash
# Run with timestamped log file
nohup python migrate_files_to_pgvector.py > migration_$(date +%Y%m%d_%H%M%S).log 2>&1 &

# Or with a simple log filename
nohup python migrate_files_to_pgvector.py > migration.log 2>&1 &

# Combine with flags (examples):
nohup python migrate_files_to_pgvector.py --knowledge-only > migration_$(date +%Y%m%d_%H%M%S).log 2>&1 &
nohup python migrate_files_to_pgvector.py --overwrite > migration_$(date +%Y%m%d_%H%M%S).log 2>&1 &
nohup python migrate_files_to_pgvector.py --knowledge-only --overwrite > migration_$(date +%Y%m%d_%H%M%S).log 2>&1 &
nohup python migrate_files_to_pgvector.py --knowledge-id <uuid> > migration_$(date +%Y%m%d_%H%M%S).log 2>&1 &
```


### If run as a background process, how to monitor the progress?
**Quick status check:**
```bash
for pid in /proc/[0-9]*; do [ -f "$pid/cmdline" ] && grep -q "migrate_files_to_pgvector" "$pid/cmdline" 2>/dev/null && echo "⏳ Running (PID: $(basename $pid))" && exit 0; done; echo "❌ Not running"; tail -n 5 migration*.log 2>/dev/null | tail -n 1

**Stop the process:**
```bash
for pid in /proc/[0-9]*; do [ -f "$pid/cmdline" ] && grep -q "migrate_files_to_pgvector" "$pid/cmdline" 2>/dev/null && kill $(basename $pid) 2>/dev/null && echo "Killed: $(basename $pid)"; done
```

**Monitor progress:**
```bash
# Watch the log file in real-time
tail -f migration_*.log

# Check for completion
tail -n 20 migration_*.log | grep "Processing complete"
```

**Check completion:**
- Look for `✅ Processing complete!` in the log file
- Look for `Migration script completed successfully.` message
- Process will no longer appear in `ps` output when done

## Command-Line Options

- `--dry-run` – Parse + embed but **don't** write to Pgvector. Useful for testing.
- `--overwrite` – Re-process all files even if already complete. Deletes existing chunks before inserting. **Default behavior is to skip complete files.**
- `--knowledge-id <uuid>` – Limit processing to files in a specific knowledge base.
- `--file-id <uuid>` – Process only a single file (useful for re-running failed files).
- `--knowledge-only` – Process only files that are part of knowledge bases (skip standalone files).

## Features

### Smart Skipping (Default Behavior)
- **Automatically skips files that are already complete** in all their collections
- Detects partial inserts (some chunks missing) and re-processes only incomplete collections
- Safe to re-run: won't duplicate work or lose progress

### Rate Limit Handling
- Automatically handles 429 (Too Many Requests) errors with exponential backoff
- Proactively splits large batches (max 500 chunks) to avoid rate limits
- Retries failed requests with automatic batch splitting

### Progress Tracking
- Progress bars show file processing and embedding generation
- Detailed logging of skipped, processed, and failed files
- Summary statistics at completion

### Error Handling
- Gracefully handles image files that can't be processed as text
- Continues processing other files if one fails
- Detailed error messages for troubleshooting

## What it does
1. Reads `knowledge` + `file` tables to map each file to the collections it belongs to.
2. Checks completeness: compares expected chunk count with existing chunks in database.
3. Skips files that are already complete (unless `--overwrite` is used).
4. Loads each file via the same loader used at upload time.
5. Splits text using the configured splitter + chunk settings.
6. Generates fresh embeddings (with retry/backoff on rate limits and network errors).
7. Writes chunks into all relevant collections, with unique IDs per collection.
8. Rebuilds pgvector index for optimal retrieval performance.

## Tips

### First Run
- Use `--dry-run` first to confirm counts and catch missing files.
- Check the log for any files that can't be processed (e.g., image files without OCR).

### Resuming After Interruption
- **Safe to restart**: The script automatically detects completed files and skips them.
- Partial work is preserved: only incomplete collections are re-processed.
- No need to use `--overwrite` unless you want to re-process everything.

### Re-processing Specific Files
- If migrations left stale chunks, run with `--overwrite` to re-process everything.
- To re-run only failed files, pass `--file-id <uuid>` from the logs.
- Use `--knowledge-id <uuid>` to re-process files in a specific knowledge base.

### Performance
- The script processes files sequentially to avoid overwhelming the embedding API.
- Large files are automatically split into smaller batches to prevent rate limits.
- Progress bars help track long-running migrations.

