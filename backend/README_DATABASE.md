# Database Configuration

## Current Setup (CONSOLIDATED)

The database has been consolidated to a single file:

- **Ground truth database**: `backend/data/webui.db` (used by Alembic by default)
- **Symlink**: `backend/open_webui/data/webui.db` → points to the ground truth database

This ensures Alembic migrations and the application both use the same database file. The ground truth is determined by Alembic's default `DATABASE_URL` path.

## How It Works

1. **Alembic** reads `DATABASE_URL` from `open_webui.env.py`
2. `DATABASE_URL` defaults to `sqlite:///{DATA_DIR}/webui.db`
3. `DATA_DIR` defaults to `backend/data`
4. **Ground truth database**: `backend/data/webui.db` (the actual file)
5. **Symlink**: `backend/open_webui/data/webui.db` → `../../data/webui.db`
6. **Result**: Both Alembic and the app use the same database file, with `backend/data/webui.db` as the source of truth

## Running Migrations

Now you can run migrations normally:

```bash
cd backend/open_webui
alembic upgrade head
```

This will modify `backend/data/webui.db` which is a symlink to `backend/open_webui/data/webui.db`.

## If You Need to Use a Different Database

### Option 1: Use DATABASE_URL Environment Variable

```bash
export DATABASE_URL="sqlite:////absolute/path/to/webui.db"
cd backend/open_webui
alembic upgrade head
```

### Option 2: Set DATA_DIR Environment Variable

```bash
export DATA_DIR="/absolute/path/to/data/directory"
# The database will be at: $DATA_DIR/webui.db
```

## Important Notes

- **`DB_ABS` is NOT used** by Alembic or the application - it's a custom variable
- Always use `DATABASE_URL` or `DATA_DIR` for database configuration
- The symlink ensures both default paths point to the same database
