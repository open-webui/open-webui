# Migrations Directory

This directory contains Alembic database migration scripts for Open WebUI's SQLAlchemy-based schema management. Migrations enable version-controlled, incremental database schema changes that can be applied forward (upgrade) or reverted backward (downgrade), supporting safe deployments and database evolution across development, staging, and production environments.

## Purpose

The migrations system provides:
- **Schema Version Control**: Track database schema changes over time
- **Incremental Updates**: Apply changes step-by-step without manual SQL
- **Rollback Support**: Revert schema changes if needed
- **Multi-Environment**: Same migrations work across SQLite, PostgreSQL, MySQL
- **Team Collaboration**: Share schema changes via version control

## Files in This Directory

### env.py
**Purpose:** Alembic environment configuration for running migrations online (with live database connection) or offline (generating SQL scripts).

**Key Components:**
- `target_metadata` - SQLAlchemy metadata from `Auth.metadata` (all models registered here)
- `DB_URL` - Database URL from environment (`DATABASE_URL`)
- `run_migrations_offline()` - Generate SQL scripts without database connection
- `run_migrations_online()` - Execute migrations directly against database
- `run_migrations()` - Entry point called by Alembic CLI

**Configuration:**
```python
target_metadata = Auth.metadata  # All models' tables
DB_URL = DATABASE_URL  # From env.py
```

**Used by:**
- `alembic` CLI commands
- `internal/db.py` - Database initialization

**Uses:**
- `models/auths.py` - Auth.metadata includes all model tables
- `env.py` - DATABASE_URL environment variable

### alembic.ini (Not in repo, generated)
**Purpose:** Alembic configuration file (typically at repository root).

**Key Settings:**
- `script_location` - Path to migrations directory
- `sqlalchemy.url` - Database connection string (overridden by env.py)
- `file_template` - Migration file naming template

**Note:** This file is usually at the repository root, not in this directory.

### README
**Purpose:** Brief documentation pointing to Alembic documentation.

**Contents:** Generic Alembic README template

### script.py.mako
**Purpose:** Mako template for generating new migration files.

**Template Variables:**
- `${message}` - Migration description
- `${up_revision}` - Previous revision ID
- `${down_revision}` - Revision to downgrade to
- `${branch_labels}` - Branch labels (for branching migrations)
- `${depends_on}` - Dependencies on other migrations

**Generated File Structure:**
```python
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa

revision = '${up_revision}'
down_revision = '${down_revision}'
branch_labels = ${branch_labels}
depends_on = ${depends_on}

def upgrade():
    ${upgrades if upgrades else "pass"}

def downgrade():
    ${downgrades if downgrades else "pass"}
```

**Used by:**
- `alembic revision` command

### util.py
**Purpose:** Utility functions for migrations (currently minimal).

**Functions:**
- Helper functions for common migration operations (if any)

**Note:** Often empty or contains project-specific migration helpers.

## Subdirectories

### versions/
**Purpose:** Contains all individual migration files, each representing a schema change.

**File Naming:** `{revision_id}_{description}.py`
- `revision_id`: Unique identifier (e.g., `10vr9xyets5m`)
- `description`: Human-readable description (e.g., `add_token_usage_tables`)

**Contents:** 20+ migration files representing the evolution of Open WebUI's schema

**See:** `versions/CLAUDE.md` for detailed documentation of individual migrations

## Architecture & Patterns

### Linear Migration Chain
Migrations form a linked list:
```
7e5b5dc7342b (init.py)
    ↓
242a2047eae0 (update_chat_table)
    ↓
3781e22d8b01 (update_message_table)
    ↓
... (more migrations)
    ↓
10vr9xyets5m (add_token_usage_tables)
```

Each migration references its predecessor via `down_revision`.

### Upgrade/Downgrade Pattern
Every migration implements two functions:
```python
def upgrade():
    # Apply schema changes
    op.create_table('token_usage', ...)

def downgrade():
    # Revert schema changes
    op.drop_table('token_usage')
```

This enables bidirectional schema evolution.

### Metadata-Driven Migrations
Alembic uses SQLAlchemy metadata to generate migrations:
```python
# In env.py
target_metadata = Auth.metadata

# Auth.metadata includes all model tables via registry
```

This allows `alembic revision --autogenerate` to detect schema changes automatically.

### Environment-Agnostic Migrations
Same migration files work across databases:
- SQLite (development)
- PostgreSQL (production)
- MySQL (alternative)

Alembic handles dialect-specific SQL generation.

## Integration Points

### internal/db.py → migrations/
Database initialization runs pending migrations:
```python
# In internal/db.py
def init_db():
    # Run Alembic migrations programmatically
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
```

### models/* → migrations/env.py
All models registered in Auth.metadata:
```python
# In models/auths.py
Base = declarative_base()

class Auth(Base):
    __tablename__ = "auth"
    # ...

# In env.py
target_metadata = Auth.metadata  # Includes all models
```

### alembic CLI → migrations/
Developers use Alembic CLI to manage migrations:
```bash
# Create new migration
alembic revision --autogenerate -m "Add new feature"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

### Deployment Scripts → migrations/
CI/CD pipelines run migrations during deployment:
```bash
# In deployment script
alembic upgrade head
```

## Key Workflows

### Creating New Migration (Manual)
```
1. Modify ORM model in models/
2. Run: alembic revision --autogenerate -m "Description"
3. Alembic compares models to database
4. Generates migration file in versions/
5. Review generated migration
6. Edit if necessary (autogenerate isn't perfect)
7. Commit migration file to git
```

### Creating New Migration (Manual)
```
1. Run: alembic revision -m "Description"
2. Alembic creates empty migration file
3. Manually write upgrade() and downgrade()
4. Test migration (upgrade and downgrade)
5. Commit to git
```

### Applying Migrations (Development)
```
1. Pull latest code (includes new migrations)
2. Run: alembic upgrade head
3. Alembic checks current database version
4. Applies pending migrations in order
5. Database schema updated
6. Application uses new schema
```

### Applying Migrations (Production)
```
1. Backup database
2. Deploy new application version
3. Run: alembic upgrade head (via deployment script)
4. Verify migrations succeeded
5. Start application
6. Verify application health
```

### Rolling Back Migration
```
1. Identify problematic migration revision ID
2. Run: alembic downgrade <revision_id>
3. Alembic reverts migrations in reverse order
4. Database schema reverted
5. Deploy previous application version
6. Verify application works
```

### Viewing Migration History
```
1. Run: alembic history --verbose
2. Output shows migration chain:
   Rev: 10vr9xyets5m (head)
   Parent: d31026856c01
   Path: versions/10vr9xyets5m_add_token_usage_tables.py

   Rev: d31026856c01
   Parent: 9f0c9cd09105
   ...
```

### Checking Current Version
```
1. Run: alembic current
2. Output shows current database revision:
   10vr9xyets5m (head)
```

## Important Notes

### Critical Dependencies
- `alembic` Python package
- `sqlalchemy` ORM
- Database driver (`psycopg2` for PostgreSQL, built-in for SQLite)
- Access to database with schema modification permissions

### Configuration
- `DATABASE_URL` environment variable specifies target database
- `alembic.ini` at repository root configures Alembic
- `env.py` overrides database URL from environment

### Migration File Ordering
Migrations applied in order determined by `down_revision` chain, not filename alphabetically. Always check `down_revision` field.

### Autogenerate Limitations
`alembic revision --autogenerate` doesn't detect:
- Table or column renames (generates drop + create)
- Changes to column server defaults
- Changes to constraints in some databases
- Custom types or database-specific features

Always review and test autogenerated migrations.

### Concurrent Migrations
Multiple developers creating migrations simultaneously can cause conflicts:
- Two migrations with same `down_revision`
- Solution: Merge migrations or use `alembic merge` command

### Data Migrations
Schema migrations can include data migrations:
```python
def upgrade():
    # Schema change
    op.add_column('user', sa.Column('status', sa.String(20)))

    # Data migration
    connection = op.get_bind()
    connection.execute("UPDATE user SET status = 'active'")
```

Use with caution in production (can be slow for large tables).

### Testing Migrations
Always test both upgrade and downgrade:
```bash
# Apply migration
alembic upgrade head

# Verify schema
python -c "from models import User; print(User.__table__.columns)"

# Rollback
alembic downgrade -1

# Verify rollback succeeded
python -c "from models import User; print(User.__table__.columns)"
```

### Production Deployment
Best practices:
1. **Backup** database before migration
2. **Test** migrations in staging environment
3. **Downtime** may be required for large migrations
4. **Monitoring** watch for migration errors
5. **Rollback plan** prepared if migration fails

### Database-Specific Considerations
Some operations not supported on all databases:
- **SQLite**: Limited ALTER TABLE support (use batch mode)
- **PostgreSQL**: Full DDL support
- **MySQL**: Limited transaction support for DDL

Alembic handles many differences automatically, but test on target database.

### Avoiding Migration Issues
- **Never edit applied migrations** (create new migration instead)
- **Never change revision IDs** (breaks migration chain)
- **Test migrations** before committing
- **Keep migrations atomic** (one logical change per migration)
- **Document complex migrations** with comments

### Migration Conflicts
If two developers create migrations simultaneously:
```
# Before merge
Branch A: rev_a → rev_a_new
Branch B: rev_a → rev_b_new

# After merge (conflict)
rev_a has two children: rev_a_new and rev_b_new
```

**Resolution:**
```bash
# Merge migrations into single chain
alembic merge rev_a_new rev_b_new -m "Merge migrations"

# Creates merge migration:
# rev_merge depends on both rev_a_new and rev_b_new
```

### Debugging Migration Failures
Migration fails during `alembic upgrade`:
1. Check error message for SQL details
2. Inspect generated SQL: `alembic upgrade head --sql`
3. Check database state: What tables/columns exist?
4. Check migration logic: Is upgrade() correct?
5. Test in development database first
6. Roll back if necessary: `alembic downgrade -1`
