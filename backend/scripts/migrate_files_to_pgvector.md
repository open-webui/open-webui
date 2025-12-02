# migrate_files_to_pgvector.py

`backend/scripts/migrate_files_to_pgvector.py` re-processes every file stored under `backend/data/uploads` and rebuilds its embeddings directly into Pgvector. It mirrors the normal upload pipeline (loader, splitter, metadata, embedding) and recreates both `knowledge.id` collections and the per-file `file-{file.id}` collections.

## Prerequisites
- `docker-compose.local.yaml` (or your environment) must set `VECTOR_DB=pgvector`, `DATABASE_URL`, `PGVECTOR_DB_URL`, embedding keys, etc.
- Pgvector extension enabled on the target Postgres database.
- Uploaded files must be accessible at the paths stored in the `file` table.
- Run inside the backend container: `docker compose exec open-webui bash`.

## Usage
```bash
cd /app/backend/scripts
python migrate_files_to_pgvector.py [options]
```

Common flags:
- `--dry-run` – parse + embed but **don’t** write to Pgvector.
- `--overwrite` – delete existing chunks for each file/collection before inserting.
- `--knowledge-id <uuid>` – limit to one knowledge base.
- `--file-id <uuid>` – limit to a single file.
- `--knowledge-only` – process only files referenced by any knowledge base.

## What it does
1. Reads `knowledge` + `file` tables to map each file to the collections it belongs to.
2. Loads each file via the same loader used at upload time.
3. Splits text using the configured splitter + chunk settings.
4. Generates fresh embeddings (with retry/backoff on transient network errors).
5. Writes chunks into all relevant collections, with unique IDs per collection.

## Tips
- Use `--dry-run` first to confirm counts and catch missing files.
- If migrations left stale chunks, run with `--overwrite`.
- To re-run only failed files, pass `--file-id <uuid>` from the logs.

