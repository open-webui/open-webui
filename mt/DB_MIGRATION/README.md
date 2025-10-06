# Open WebUI Database Migration: SQLite to PostgreSQL (Supabase)

## Overview

This directory contains the tools and scripts for migrating Open WebUI deployments from SQLite to PostgreSQL (Supabase). The migration is fully integrated into the `client-manager.sh` multi-tenant management system and provides automated backup, schema initialization, data migration, and rollback capabilities.

## Table of Contents

- [Architecture](#architecture)
- [Migration Process](#migration-process)
- [Usage via Client Manager](#usage-via-client-manager)
- [Migration Scripts](#migration-scripts)
- [Security Posture](#security-posture)
- [Rollback Procedure](#rollback-procedure)
- [Troubleshooting](#troubleshooting)

---

## Architecture

### Components

1. **client-manager.sh**: Main entry point - provides menu-driven migration interface
2. **db-migration-helper.sh**: Core migration functions (backup, schema init, migration execution)
3. **migrate-db.py**: Python script for table-by-table data migration with type conversion

### Data Flow

```
┌─────────────────┐
│  SQLite WebUI   │
│   (Container)   │
└────────┬────────┘
         │ 1. Backup
         ▼
┌─────────────────┐
│ /tmp/backup.db  │
└────────┬────────┘
         │ 2. Schema Init
         ▼
┌─────────────────┐      ┌──────────────────┐
│   Temp Init     │─────▶│   PostgreSQL     │
│   Container     │      │   (Supabase)     │
└─────────────────┘      └────────┬─────────┘
                                  │ 3. Data Migration
                                  ▼
                         ┌──────────────────┐
                         │   Temp Migrate   │
                         │    Container     │
                         └────────┬─────────┘
                                  │ 4. Log Export
                                  ▼
                         ┌──────────────────┐
                         │  /tmp/migration  │
                         │   -FQDN-*.log    │
                         └──────────────────┘
```

---

## Migration Process

### Step-by-Step Flow

#### 1. **Pre-Migration Setup**
- User selects migration option from client-manager (Option 8)
- Gathers Supabase credentials:
  - Project Reference ID
  - Database Password
  - Region
  - Connection Mode (Session/Transaction)

#### 2. **Connection Validation**
- Tests connection to Supabase using temporary Docker container
- Verifies pgvector extension (recommended for vector operations)
- No changes made to production container

#### 3. **SQLite Backup**
- Creates timestamped backup: `/tmp/webui-backup-{FQDN}-{timestamp}.db`
- Backup includes client FQDN to distinguish multi-tenant deployments
- Example: `webui-backup-chat.example.com-20251006-143022.db`

#### 4. **PostgreSQL Schema Initialization**
- Spins up temporary container with DATABASE_URL configured
- Uses temporary port (original + 10000) to avoid conflicts
- Open WebUI auto-creates all tables via SQLAlchemy migrations
- Waits for startup indicators: "Application startup complete"
- Container automatically deleted after schema creation

#### 5. **Data Migration**
- Runs `migrate-db.py` in temporary Docker container
- Tables migrated in dependency order (respects foreign keys):
  ```
  user → auth → tag → config → chat → oauth_session → function → ...
  ```
- Type conversions applied:
  - SQLite integers (0/1) → PostgreSQL booleans (true/false)
  - Null bytes (`\u0000`) removed from strings
- Metadata tables skipped: `alembic_version`, `migratehistory`
- Each row uses individual transaction to prevent cascade failures
- Migration log saved: `/tmp/migration-{FQDN}-{timestamp}.log`

#### 6. **Container Recreation**
- Stops existing SQLite container
- Removes container (data volume preserved)
- Creates new container with PostgreSQL configuration
- Preserves all environment variables (OAuth, branding, etc.)

#### 7. **Post-Migration**
- Container starts with Supabase backend
- Data accessible via Open WebUI
- SQLite backup retained for rollback

---

## Usage via Client Manager

### Starting a Migration

1. **Launch client-manager**:
   ```bash
   cd /Users/justinmartin/github/open-webui/mt
   ./client-manager.sh
   ```

2. **Navigate to deployment**:
   - Select `3) Manage Existing Deployment`
   - Choose your deployment (e.g., `imagicrafter`)

3. **Initiate migration**:
   - Select `8) Migrate to Supabase/PostgreSQL`
   - Review warnings and confirm

4. **Provide Supabase credentials**:
   ```
   Project Ref: dgjvrkoxxmbndvtxvqjv
   Password: [your-password]
   Region: us-east-2
   Connection Mode: 1 (Session Mode) or 2 (Transaction Mode)
   ```

5. **Monitor progress**:
   - Schema initialization: ~2-3 minutes
   - Data migration: Varies by database size
   - Log file location displayed at completion

### Post-Migration Options

Once migrated, Option 8 becomes:
- `8) View database configuration (includes rollback)`

From this menu you can:
1. **Test connection** - Verify PostgreSQL connectivity
2. **Rollback to SQLite** - Restore from backup

---

## Migration Scripts

### db-migration-helper.sh

**Purpose**: Core migration functions sourced by client-manager

**Key Functions**:

| Function | Description |
|----------|-------------|
| `get_supabase_config()` | Interactive credential collection |
| `test_supabase_connection()` | Docker-based connection test |
| `check_pgvector_extension()` | Verify pgvector availability |
| `backup_sqlite_database()` | Create FQDN-stamped backup |
| `initialize_postgresql_schema()` | Auto-create tables via Open WebUI |
| `run_migration_tool()` | Execute Python migration script |
| `rollback_to_sqlite()` | Restore from backup |
| `display_postgres_config()` | Show config + rollback menu |

**Docker-Based Operations**:
All PostgreSQL operations use temporary Docker containers with `--rm` flag to:
- Eliminate host dependencies (no psql/psycopg2 installation needed)
- Ensure clean environment
- Automatic cleanup

### migrate-db.py

**Purpose**: Non-interactive data migration with automatic type conversion

**Features**:
- Command-line driven: `python3 migrate-db.py <sqlite_path> <postgres_url> [client_id]`
- Introspects PostgreSQL schema for column types
- Converts SQLite integers to PostgreSQL booleans
- Removes null bytes from strings
- Per-row transactions prevent cascade failures
- Comprehensive logging to `/tmp/migration-{client_id}-{timestamp}.log`

**Table Dependencies**:
```python
dependency_order = [
    'user',              # Parent table
    'auth',              # References user
    'tag',
    'config',
    'chat',              # References user
    'oauth_session',     # References user
    'function',
    'message',           # References chat
    ...
]
```

---

## Security Posture

### Why Open WebUI Tables Use Public Schema Without RLS

#### **Decision: Keep Open WebUI Tables in `public` Schema**

Open WebUI's database tables remain in the default PostgreSQL `public` schema without Row-Level Security (RLS) policies for the following architectural reasons:

#### 1. **Application-Level Security Model**

Open WebUI implements a **mature application-level security architecture**:

- **Authentication**: Built-in OAuth2 support (Google, Microsoft, GitHub, OIDC)
- **Authorization**: Role-based access control (admin, user, pending)
- **Session Management**: Secure session handling via `oauth_session` table
- **Multi-Tenancy**: User isolation enforced by application logic

The Python backend (FastAPI + SQLAlchemy) mediates all database access with proper authorization checks. Users never directly query the database.

#### 2. **Service Role Connection**

Open WebUI connects to PostgreSQL using a **service role** (not individual user credentials):

```env
DATABASE_URL=postgresql://postgres.[PROJECT]:PASSWORD@host:5432/postgres
```

This architecture pattern:
- ✅ Standard for application-tier security
- ✅ Enables connection pooling
- ✅ Simplifies deployment
- ✅ Matches SQLite security model (file-level access)

Adding RLS would provide **no additional security** since the service role already has full access.

#### 3. **ORM Compatibility**

Open WebUI's SQLAlchemy models expect tables in the `public` schema with standard naming:

```python
class User(Base):
    __tablename__ = "user"
    # ...

class Chat(Base):
    __tablename__ = "chat"
    # ...
```

**Any of these changes would break the application**:
- Moving tables to custom schema (requires `search_path` modification)
- Prefixing table names (`openwebui_user`, `openwebui_chat`)
- Implementing RLS (blocks service role queries)

#### 4. **Maintainability**

Open WebUI is actively developed with frequent updates:
- Forking and modifying schema would create maintenance burden
- Breaking changes on each upstream update
- Loss of official support
- Migration complexity multiplied

#### 5. **Recommended Architecture for Extensions**

If you build **custom features on top of Open WebUI data**, use a **separate schema**:

```sql
-- Open WebUI (unchanged)
public.user
public.chat
public.function

-- Your custom features
extensions.analytics
extensions.reports
custom.workflows
```

**Benefits**:
- ✅ Clear separation of concerns
- ✅ Open WebUI remains untouched
- ✅ You control RLS on YOUR schema
- ✅ Maintainable across Open WebUI updates

#### 6. **Supabase "Unrestricted" Warning**

The Supabase dashboard shows an "Unrestricted" tag on Open WebUI tables. This is:

- ✅ **Expected** - Application uses service role
- ✅ **Correct** - Security handled at application tier
- ✅ **Secure** - Users don't have direct database access

**Do NOT enable RLS on Open WebUI tables** - it will break authentication and authorization.

### Security Best Practices

**For Open WebUI Production Deployments**:

1. **Network Security**:
   - Use SSL/TLS for Supabase connection
   - Restrict database access to application IP ranges
   - Enable Supabase connection pooling with `PgBouncer`

2. **Credential Management**:
   - Store `DATABASE_URL` as environment variable
   - Use strong database passwords (20+ characters)
   - Rotate credentials periodically

3. **Application Security**:
   - Configure `OAUTH_ALLOWED_DOMAINS` to restrict signups
   - Use `DEFAULT_USER_ROLE=user` (not admin)
   - Enable Google OAuth with domain restrictions

4. **Monitoring**:
   - Monitor Supabase logs for suspicious queries
   - Set up alerts for failed authentication attempts
   - Regular security audits via Open WebUI admin panel

5. **Backups**:
   - Supabase provides automatic daily backups
   - Maintain SQLite backups during migration window
   - Test restore procedures regularly

### When to Use Custom Schema with RLS

**Only for YOUR custom features** that:
- Require direct database access (not via Open WebUI API)
- Need row-level user isolation at DB tier
- Store data independent of Open WebUI models

Example use case:
```sql
-- Custom analytics schema with RLS
CREATE SCHEMA extensions;

CREATE TABLE extensions.usage_analytics (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES public.user(id),
    event_type TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Enable RLS on YOUR table
ALTER TABLE extensions.usage_analytics ENABLE ROW LEVEL SECURITY;

-- Users only see their own analytics
CREATE POLICY "Users see own analytics"
ON extensions.usage_analytics
FOR SELECT
USING (auth.uid() = user_id);
```

---

## Rollback Procedure

### Automatic Rollback via Menu

1. **Access rollback menu**:
   - Client Manager → Manage Deployment → `8) View database configuration`
   - Select `2) Rollback to SQLite database`

2. **Review backup list**:
   - Shows 5 most recent backups for this FQDN
   - Example: `webui-backup-chat.example.com-20251006-143022.db`

3. **Confirm rollback**:
   - Type `yes` to proceed
   - System will:
     - Stop PostgreSQL container
     - Restore backup to volume
     - Recreate container with SQLite
     - Preserve OAuth and branding settings

4. **Verify data**:
   - Login to Open WebUI
   - Confirm chats, users, functions restored

### Manual Rollback (if needed)

```bash
# 1. Stop container
docker stop openwebui-CLIENTNAME

# 2. Copy backup to volume
docker run --rm \
  -v openwebui-CLIENTNAME-data:/data \
  -v /tmp:/backup \
  alpine sh -c "cp /backup/webui-backup-FQDN-TIMESTAMP.db /data/webui.db"

# 3. Start container without DATABASE_URL
docker start openwebui-CLIENTNAME
# OR recreate without -e DATABASE_URL
```

### Rollback Considerations

- **Data Loss**: Any changes made in PostgreSQL after migration will be lost
- **OAuth Sessions**: Users may need to re-authenticate
- **Backup Age**: Use most recent backup unless specific reason to use older version
- **PostgreSQL Data**: Remains in Supabase (not deleted) - can be manually cleared if needed

---

## Troubleshooting

### Migration Failures

#### Issue: Boolean Type Errors
```
column "active" is of type boolean but expression is of type integer
```

**Cause**: SQLite stores booleans as integers (0/1), PostgreSQL expects TRUE/FALSE

**Solution**: Fixed in `migrate-db.py` - automatically converts integer to boolean for boolean columns

#### Issue: Foreign Key Violations
```
violates foreign key constraint "oauth_session_user_id_fkey"
```

**Cause**: Child table inserted before parent table

**Solution**: Fixed in `migrate-db.py` - tables migrated in dependency order (user → auth → chat → oauth_session)

#### Issue: Duplicate Key Errors
```
duplicate key value violates unique constraint "alembic_version_pkc"
```

**Cause**: Metadata tables already populated by schema initialization

**Solution**: Fixed in `migrate-db.py` - skips `alembic_version` and `migratehistory` tables

#### Issue: Transaction Aborted Cascade
```
current transaction is aborted, commands ignored until end of transaction block
```

**Cause**: PostgreSQL aborts entire transaction after first error

**Solution**: Fixed in `migrate-db.py` - each row uses individual transaction with rollback on error

### Connection Issues

#### Issue: Password Authentication Failed
```
password authentication failed for user 'postgres'
```

**Solutions**:
- Verify password in Supabase dashboard (Settings → Database → Connection String)
- Check for special characters - may need URL encoding
- Ensure using correct connection mode (Session vs Transaction)

#### Issue: Connection Timeout
```
could not connect to server: Connection timed out
```

**Solutions**:
- Verify Supabase project is not paused (free tier auto-pauses)
- Check firewall/network restrictions
- Confirm region matches Supabase project region

### Log File Missing

#### Issue: Migration log not saved to /tmp
```
⚠ Warning: No migration log file found in container
```

**Cause**: Container deleted before log copy completed

**Solution**: Migration script includes pause before cleanup - press Enter when prompted to save log

**Debug**: Check for log in running container:
```bash
docker exec migration-temp-XXXXX ls -la /tmp/migration-*.log
docker cp migration-temp-XXXXX:/tmp/migration-FQDN-TIMESTAMP.log /tmp/
```

### Rollback Failures

#### Issue: No Backup Found
```
❌ No backup found for chat.example.com
```

**Causes**:
- Backup created with old naming scheme (no FQDN)
- Backup manually deleted
- Migration failed before backup completed

**Solutions**:
- Check `/tmp` for any `webui-backup-*.db` files
- Fallback: Script searches for ANY backup if client-specific not found
- Last resort: Use Open WebUI's built-in admin data export

### Performance Issues

#### Issue: Migration Very Slow
**Solutions**:
- Use Transaction Mode instead of Session Mode (6x faster)
- Ensure stable internet connection
- Check Supabase status page for incidents
- Consider migrating during off-peak hours

#### Issue: Large Database Timeout
**Solutions**:
- Increase timeout in `db-migration-helper.sh`:
  ```bash
  local timeout=600  # Increase from 180 seconds
  ```
- Split migration: Migrate critical tables first, then remaining tables

---

## File Locations

### Scripts
```
mt/DB_MIGRATION/
├── README.md                      (this file)
├── db-migration-helper.sh         (core migration functions)
└── migrate-db.py                  (Python data migration script)
```

### Logs and Backups
```
/tmp/
├── webui-backup-{FQDN}-{timestamp}.db       (SQLite backups)
└── migration-{FQDN}-{timestamp}.log         (Migration logs)
```

### Container Volumes
```
openwebui-{CLIENTNAME}-data/
└── webui.db                       (SQLite database in volume)
```

---

## Migration Checklist

### Pre-Migration

- [ ] Supabase project created with pgvector extension
- [ ] Database credentials documented securely
- [ ] Current Open WebUI deployment working (test login/chat)
- [ ] Backup of SQLite database exists outside container
- [ ] Maintenance window scheduled (expect 15-30 minutes downtime)
- [ ] Users notified of migration window

### During Migration

- [ ] Connection test passed
- [ ] pgvector extension verified
- [ ] SQLite backup created successfully
- [ ] Schema initialization completed
- [ ] Data migration completed (check log for failures)
- [ ] Migration log saved to `/tmp`
- [ ] Container recreated with PostgreSQL

### Post-Migration

- [ ] Open WebUI loads successfully
- [ ] Admin login works
- [ ] User accounts present
- [ ] Chats visible and accessible
- [ ] Functions/tools working
- [ ] OAuth authentication functional
- [ ] Test creating new chat
- [ ] Verify data persistence across container restart
- [ ] SQLite backup retained for rollback window (7-30 days)
- [ ] Document DATABASE_URL in secure location

### Rollback Testing

- [ ] Rollback menu accessible
- [ ] Backup list shows correct files
- [ ] Test rollback on non-critical deployment first
- [ ] Verify data restored after rollback

---

## Support and Resources

### Documentation
- Open WebUI: https://docs.openwebui.com
- Supabase: https://supabase.com/docs/guides/database/overview
- PostgreSQL: https://www.postgresql.org/docs/current/

### Common Commands

**View migration logs**:
```bash
ls -lht /tmp/migration-*.log
cat /tmp/migration-{FQDN}-{timestamp}.log
```

**View backups**:
```bash
ls -lht /tmp/webui-backup-*.db
```

**Check container database type**:
```bash
docker exec openwebui-CLIENTNAME env | grep DATABASE_URL
# Empty = SQLite, postgres://... = PostgreSQL
```

**Manually export SQLite backup**:
```bash
docker cp openwebui-CLIENTNAME:/app/backend/data/webui.db /tmp/manual-backup.db
```

**Manually clear PostgreSQL tables** (if needed):
```sql
-- Connect to Supabase via psql or dashboard SQL editor
TRUNCATE TABLE auth, chat, oauth_session, function, message CASCADE;
-- Or drop all data:
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01-06 | Initial implementation with automated backup, migration, and rollback |

---

## License

This migration tooling is part of the Open WebUI multi-tenant management system and follows the same license as the parent project.
