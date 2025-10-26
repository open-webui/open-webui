# Backend Internal Directory

This directory contains the database abstraction, initialization, and migration handling layer for Open WebUI. It manages database connections, schema migrations, and provides the ORM foundation for all models.

## Files

### db.py
- `JSONField` - Custom SQLAlchemy type for JSON serialization
- `handle_peewee_migration()` - Runs legacy Peewee migrations before SQLAlchemy setup
- `engine` - SQLAlchemy engine instance configured from DATABASE_URL
- `SessionLocal` - Session factory for database operations
- `Base` - Declarative base for all ORM models
- `get_db()` - Context manager providing database sessions

**Used by:**
- `models/*.py` (ALL models) - Imports Base, get_db, JSONField
- `main.py` - Database health checks and OpenTelemetry setup
- `config.py` - Configuration model initialization

**Uses:**
- `internal/wrappers.py` - Peewee connection registration for migrations
- `env.py` - DATABASE_URL, pool configuration

**Key Details:**
- Supports both SQLite and PostgreSQL
- Connection pooling: QueuePool (pool_size>0) or NullPool (pool_size=0)
- Pre-ping health checks prevent stale connections
- Schema namespace support via DATABASE_SCHEMA environment variable

### wrappers.py
- `PeeweeConnectionState` - Thread-safe connection tracking using contextvars
- `CustomReconnectMixin` - Auto-reconnection for PostgreSQL
- `ReconnectingPostgresqlDatabase` - Self-healing database connections
- `register_connection()` - Factory for creating database connections

**Used by:**
- `db.py` - Called during Peewee migration phase

**Uses:**
- `utils/redis.py` - Redis connection utilities

**Key Details:**
- Only used during migrations, not runtime
- Handles PostgreSQL connection failures gracefully
- URL scheme normalization: `postgresql://` → `postgres://` for Peewee compatibility

### migrations/ Directory
Contains Alembic migration files for schema versioning:
- `env.py` - Alembic environment configuration
- `util.py` - Helper functions (get_existing_tables, get_revision_id)
- `versions/` - 18 migration files tracking schema evolution

**Key Migrations:**
- `7e5b5dc7342b_init.py` - Initial 12-table schema
- `ca81bd47c050_add_config_table.py` - Configuration storage
- `6a39f3d8e55c_add_knowledge_table.py` - Knowledge bases/RAG
- `57c599a3cb57_add_channel_table.py` - Channels + messages + reactions
- `922e7a387820_add_group_table.py` - Groups and access_control columns
- `10vr9xyets5m_add_token_usage_tables.py` - Token tracking (fork feature)

**Used by:**
- `config.py` - Calls run_migrations() at module load time
- Executed before application startup

## Architecture & Patterns

### Dual ORM Strategy
The codebase is in **transition from Peewee to SQLAlchemy**:

1. **Peewee Phase** (handle_peewee_migration):
   - Runs first on module load
   - Applies legacy migrations from `migrations/` directory
   - Uses `register_connection()` from wrappers.py

2. **SQLAlchemy Phase**:
   - Engine created after Peewee migrations
   - ORM models inherit from Base
   - Active runtime database layer

3. **Alembic Phase**:
   - Modern migrations in `migrations/versions/`
   - Auto-executed by config.py

### Context Manager Pattern
All database operations use:
```python
with get_db() as db:
    # Operations here
    db.commit()
# Auto-closes session
```

### Connection Pooling Configuration
```python
# From environment:
DATABASE_POOL_SIZE=10          # 0 = NullPool (serverless)
DATABASE_POOL_MAX_OVERFLOW=5   # Extra connections
DATABASE_POOL_TIMEOUT=30       # Wait time
DATABASE_POOL_RECYCLE=3600     # Refresh interval
pool_pre_ping=True             # Health check
```

## Integration Points

### Models Layer
All 18+ model files import from this directory:
```python
from open_webui.internal.db import Base, get_db, JSONField
```

### Application Startup
```
Application start
  ↓
config.py loads → run_migrations()
  ↓
Peewee migrations execute (handle_peewee_migration)
  ↓
SQLAlchemy engine created (db.py)
  ↓
Alembic migrations execute
  ↓
Models initialized (all inherit from Base)
```

### Request Lifecycle
```
HTTP Request
  ↓
Router endpoint
  ↓
with get_db() as db:
  ↓
Model.method(db, ...)
  ↓
ORM operations
  ↓
db.commit()
  ↓
Session closes automatically
```

## Key Workflows

### Migration Execution Path
```
1. App imports config.py
2. config.py calls run_migrations()
3. Migrations check current database version
4. Apply pending migrations sequentially
5. Update alembic_version table
6. Application continues startup
```

### Database Schema Creation
```
First Run:
1. handle_peewee_migration() creates initial schema
2. Alembic migrations run (may be no-ops if Peewee created tables)
3. All models registered with Base.metadata
4. Application ready
```

## Important Notes

**Critical Gotchas:**

1. **Migration Order Matters**: Peewee runs before SQLAlchemy; changing order breaks schema
2. **Schema Modifications**: Must update both Peewee migration AND SQLAlchemy model class
3. **URL Scheme**: PostgreSQL URLs automatically converted for Peewee compatibility
4. **Connection Pooling**: NullPool (pool_size=0) for serverless; QueuePool for persistent deployments

**Database Support:**
- **SQLite**: Development/single-server (check_same_thread=False)
- **PostgreSQL**: Production/distributed (with connection pooling)
- Schema namespace support for multi-tenant PostgreSQL

**Performance:**
- Pool exhaustion risk with high concurrency; tune DATABASE_POOL_SIZE
- Stale connections prevented by pool_pre_ping and pool_recycle
- PgVector can share connection pool if PGVECTOR_DB_URL not set

**Security:**
- No built-in connection encryption configuration
- Database credentials in DATABASE_URL environment variable
- API keys stored in plaintext in User model (security concern)
