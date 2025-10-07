# FEATURE: Migrate OpenWebUI SQLite Database to Supabase PostgreSQL

## OVERVIEW:

Update mt/client_manager.sh to support automating the migration of an existing OpenWebUI instance from SQLite (default) to Supabase-hosted PostgreSQL database. This enables better scalability, remote database management, automated backups, and preparation for multi-instance deployments.

!Important! All code for this capability must stay within the open-webui/mt directory.

## CURRENT ENVIRONMENT:

### Open WebUI Server
- **Server**: Digital Ocean Droplet (Ubuntu 22.04 LTS, 1vCPU, 1GB RAM, NYC3)
- **IP Address**: 64.225.13.69 
- **Container**: `openwebui-chat` (ghcr.io/imagicrafter/open-webui:main)
- **Port Mapping**: 8081:8080 (internal Docker port to external)
- **Reverse Proxy**: Nginx routing port 80/443 → localhost:8081
- **Current Database**: SQLite at `/app/backend/data/webui.db` (inside container)
- **Other Running Containers**: 
  - loonies-lawn-landing-page-loonies-stable-1 (port 3020)
  - quantareport-quantareport-stable-1 (port 3010)
  - quantareport-quantareport-stage-1 (port 3012)
- Always validate the Server, IP and port configurations of the Open WebUI host as it may be different that the configuration using for this development work.

### Management script
Thoroughly review the current mt/client-manager.sh script.  This update will add an option to the Managing Menu which appears after a specific Open WebUI instance is selected.   The existing database configuration and status will be shown as the top with the existing status and ports information.  IF the existing database configuration of the Open Webui instance's database is using SQLlite, then a menu option will appear for migrating the database to Supabase/Posgresql.  Else if the database is already using a Supabase/Postgresql database then the menu option will be changed to enabled to view key information related to the existing Supabase/postgresl database configuration.  

## EXAMPLES:

### Open Source Migration Tool for reference
Within the ../open-webui-postgres-migration/ directory is installed an open source migration tool.  
Use this as a model for the capability being integrated with the client-manager.sh script.

### Example 1: Database Connection String Format

**SQLite (Current):**
```bash
# No DATABASE_URL needed - uses default file-based database
# Location: /app/backend/data/webui.db
```

**Supabase PostgreSQL (Target):**
```bash
DATABASE_URL="postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
```

### Example 2: Docker Container Configuration

**Current (SQLite):**
```bash
docker run -d \
  --name openwebui-chat \
  --restart always \
  -p 8081:8080 \
  -v open-webui:/app/backend/data \
  ghcr.io/imagicrafter/open-webui:main
```

**After Migration (PostgreSQL):**
```bash
docker run -d \
  --name openwebui-chat \
  --restart always \
  -p 8081:8080 \
  -e DATABASE_URL="postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres" \
  -e VECTOR_DB="pgvector" \
  -v open-webui:/app/backend/data \
  ghcr.io/imagicrafter/open-webui:main
```

### Example 3: Docker Compose Configuration (Recommended)

**Create `~/openwebui/docker-compose.yml`:**
```yaml
version: '3.8'

services:
  openwebui:
    image: ghcr.io/imagicrafter/open-webui:main
    container_name: openwebui-chat
    restart: always
    ports:
      - "8081:8080"
    environment:
      - DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
      - VECTOR_DB=pgvector
      # Add other env vars as needed
    volumes:
      - open-webui:/app/backend/data

volumes:
  open-webui:
```

### Example 4: Backup and Export Database

```bash
# Backup from running container
docker cp openwebui-chat:/app/backend/data/webui.db ~/backups/webui-backup-$(date +%Y%m%d-%H%M%S).db

# Download to local machine (run from Mac)
scp imagin8ncrafter@64.225.13.69:~/backups/webui-backup-*.db ~/Desktop/
```

### Example 5: Migration Script Usage

```bash
# Using the community migration tool
pip install open-webui-postgres-migration

# Or with uvx (no installation)
uvx open-webui-postgres-migration

# Follow interactive prompts:
# - SQLite path: ~/backups/webui-backup-20251005.db
# - PostgreSQL URL: [Supabase connection string]
```

### Example 6: Testing PostgreSQL Connection

```bash
# Install PostgreSQL client
sudo apt install postgresql-client -y

# Test connection to Supabase
psql "postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres"

# If successful, you'll see:
# psql (14.x, server 15.x)
# SSL connection (protocol: TLSv1.3...)
# Type "help" for help.
# postgres=>
```

## DOCUMENTATION:

### Official Documentation

1. **Open WebUI Database Documentation**
   - https://docs.openwebui.com/tutorials/database/
   - Export/Import process for SQLite
   - Environment variable configuration

2. **Open WebUI Environment Variables**
   - https://docs.openwebui.com/getting-started/env-configuration/
   - DATABASE_URL configuration
   - VECTOR_DB settings
   - All available environment variables

3. **Open WebUI Features**
   - https://docs.openwebui.com/features/
   - Database integration capabilities
   - Supported databases (SQLite, PostgreSQL, Milvus, Qdrant, etc.)

4. **Supabase Documentation**
   - https://supabase.com/docs/guides/database
   - PostgreSQL setup and configuration
   - Connection string formats
   - pgvector extension

5. **Supabase Database Settings**
   - https://supabase.com/docs/guides/database/connecting-to-postgres
   - Connection pooling (port 6543 vs 5432)
   - SSL requirements
   - IP allowlisting

### Community Resources

6. **Migration Guide - Medium Article**
   - https://ciodave.medium.com/migrating-open-webui-sqlite-database-to-postgresql-8efe7b2e4156
   - Step-by-step migration process
   - JavaScript migration script
   - Common issues and solutions

7. **GitHub Migration Tool**
   - https://github.com/taylorwilsdon/open-webui-postgres-migration
   - Interactive migration tool
   - Database integrity checking
   - Batch processing support

8. **PyPI Migration Package**
   - https://pypi.org/project/open-webui-postgres-migration/
   - Installation instructions
   - Usage examples

9. **GitHub Discussions**
   - https://github.com/open-webui/open-webui/discussions/8116
   - Python conversion script
   - Null byte issue fix
   - Community troubleshooting

10. **GitHub Discussions - Production Setup**
    - https://github.com/open-webui/open-webui/discussions/10451
    - Interactive migration script
    - Production deployment examples
    - AWS Aurora Postgres examples

11. **PostgreSQL with OpenWebUI Guide**
    - https://installvirtual.com/how-to-use-postgresql-with-openwebui/
    - Kubernetes/Helm setup
    - pgvector extension setup
    - Troubleshooting tips

12. **Qdrant, Postgres, and Open WebUI Discussion**
    - https://github.com/open-webui/open-webui/discussions/11597
    - Vector database considerations
    - Migration experiences
    - Performance comparisons

13. **Complete Setup Guide**
    - https://www.heyitworks.tech/blog/openwebui-with-postgres-and-qdrant-a-setup-guide/
    - PostgreSQL + Qdrant setup
    - Production considerations
    - Performance insights

### PostgreSQL/Database References

14. **pgvector Extension**
    - https://github.com/pgvector/pgvector
    - Vector similarity search
    - Installation and usage
    - Required for RAG features

15. **PostgreSQL Documentation**
    - https://www.postgresql.org/docs/
    - SQL commands
    - Data types
    - Connection management

## OTHER CONSIDERATIONS:

### Critical Gotchas and Common Mistakes

1. **Null Byte Issue (CRITICAL)**
   - SQLite supports `\u0000` (null byte) content, PostgreSQL does NOT
   - This WILL cause search function failures after migration
   - **Fix AFTER migration:**
     ```sql
     UPDATE chat SET chat = REPLACE(chat::TEXT, '\u0000', '')::JSONB;
     ```
   - Run this in Supabase SQL Editor immediately after migration

2. **Connection String Format**
   - Supabase provides multiple connection strings
   - Use **Transaction Mode** (port 6543) for most cases, NOT Session Mode (port 5432)
   - Session mode can cause connection pool exhaustion
   - **Wrong:** `postgresql://...@...supabase.com:5432/postgres`
   - **Right:** `postgresql://...@...pooler.supabase.com:6543/postgres`

3. **Schema Initialization Order**
   - MUST initialize PostgreSQL schema BEFORE running migration script
   - Start Open WebUI once with DATABASE_URL to create tables
   - Then stop it before migrating data
   - Otherwise migration will fail with "table does not exist" errors

4. **pgvector Extension Required**
   - Open WebUI uses vector embeddings for RAG (Retrieval Augmented Generation)
   - MUST enable pgvector extension in Supabase:
     ```sql
     CREATE EXTENSION IF NOT EXISTS vector;
     ```
   - Do this BEFORE starting Open WebUI with PostgreSQL

5. **Environment Variable Persistence**
   - Environment variables in `docker run` are NOT persistent after container recreates
   - Use Docker Compose or store in a `.env` file
   - Alternative: Use systemd service file to manage container

6. **Volume Mount Confusion**
   - After migration, SQLite file in volume is NOT used (but remains there)
   - Volume still needed for file uploads, documents, etc.
   - Don't remove the volume - it contains more than just the database

7. **Nginx Reverse Proxy**
   - Container restart won't affect Nginx routing
   - No Nginx configuration changes needed
   - External access remains unchanged

8. **Container Naming with Docker Compose**
   - If switching to docker-compose, container name might change
   - This can break Nginx proxy_pass if using container name instead of localhost:8081
   - **Safe:** `proxy_pass http://localhost:8081;`
   - **Risky:** `proxy_pass http://openwebui-chat:8080;`

9. **Migration Tool Selection**
   - Multiple migration tools available (JavaScript, Python, interactive)
   - **Recommended:** `open-webui-postgres-migration` (PyPI package)
   - Has integrity checking, batch processing, progress tracking
   - Handles edge cases better than manual scripts

10. **Backup Strategy**
    - Create Digital Ocean snapshot BEFORE migration (done ✅)
    - Export SQLite database to droplet AND local machine
    - Keep SQLite backup for at least 2-4 weeks after successful migration
    - Test restoration process before deleting backups

11. **Downtime Considerations**
    - Migration requires stopping Open WebUI container
    - Estimated downtime: 15-30 minutes
    - Users will lose access during this time
    - Plan migration during low-traffic period

12. **Data Validation Post-Migration**
    - Verify user count matches
    - Check chat history is preserved
    - Test login functionality
    - Verify API integrations still work
    - Check file uploads/downloads work

13. **Supabase Project Region**
    - Choose region closest to your droplet (NYC → US East)
    - Cross-region latency can impact performance
    - Can't change region after project creation

14. **Password Management**
    - Supabase database password is set during project creation
    - Store securely (password manager, encrypted file)
    - Changing password requires updating connection string everywhere
    - Consider using environment variable files, not hardcoding

15. **Firewall Considerations**
    - Supabase uses outbound HTTPS (port 443)
    - UFW already allows outbound traffic (default)
    - No firewall changes needed on droplet
    - Supabase allows connections from any IP by default (can restrict in settings)

16. **Image-Specific Considerations**
    - Using custom image: `ghcr.io/imagicrafter/open-webui:main`
    - Not the official `ghcr.io/open-webui/open-webui:main`
    - Verify this image supports PostgreSQL (it should, but test)
    - Check for image-specific environment variables or quirks

17. **Multiple Container Environment**
    - Multiple web apps running on same droplet
    - RAM is limited (1GB total, 60% already in use)
    - PostgreSQL connection pooling is important
    - Monitor memory usage after migration

18. **RAG/Vector Database**
    - Current setup likely uses ChromaDB (default, bundled with container)
    - Setting VECTOR_DB=pgvector moves vector storage to PostgreSQL
    - Alternative: Keep ChromaDB or switch to external Qdrant
    - Decision impacts migration complexity

19. **SSL/TLS Certificates**
    - Supabase requires SSL connection (enforced)
    - psycopg2 handles this automatically
    - Connection string should include SSL parameters
    - Test with `psql` client before running migration

20. **Rollback Plan**
    - If migration fails, restore from Digital Ocean snapshot
    - Snapshot restoration requires droplet power-off
    - Estimated rollback time: 10-15 minutes
    - Alternative: Keep old container stopped but not removed for quick rollback

### Performance Considerations

21. **Database Connection Pooling**
    - Supabase Transaction Mode (port 6543) uses PgBouncer
    - Limited to transaction-level pooling
    - Good for web applications with many short connections
    - Monitor connection count in Supabase dashboard

22. **Latency Expectations**
    - SQLite: <1ms (local file)
    - Supabase PostgreSQL: 10-50ms (network call to NYC region)
    - Most users won't notice difference
    - Batch operations might be slightly slower

23. **Concurrent Users**
    - SQLite: Limited concurrent write performance
    - PostgreSQL: Better concurrent access handling
    - Good for future scaling (2 users → more users)

### Security Considerations

24. **Connection String in Environment Variables**
    - Contains password in plain text
    - Docker inspect can reveal environment variables
    - Use secrets management for production
    - Alternative: Use `.env` file with restricted permissions (chmod 600)

25. **Supabase Security**
    - Database password different from Supabase dashboard password
    - Enable Row Level Security (RLS) for additional protection
    - Review Supabase security best practices
    - Enable 2FA on Supabase account

### Cost Considerations

26. **Supabase Free Tier Limits**
    - 500MB database storage
    - 2GB bandwidth per month
    - Unlimited API requests
    - Check current database size before migrating
    - Monitor usage in Supabase dashboard

27. **Digital Ocean Costs**
    - No change in droplet costs
    - SQLite vs PostgreSQL: same server resources
    - Consider upgrading RAM if needed (currently 60% usage)

### Testing Strategy

28. **Pre-Migration Testing**
    - Test Supabase connection from droplet
    - Verify pgvector extension works
    - Test migration script with copy of database
    - Document current functionality for comparison

29. **Post-Migration Testing Checklist**
    - [ ] Login with existing credentials
    - [ ] Chat history visible
    - [ ] Create new chat
    - [ ] Upload file to knowledge base
    - [ ] Test RAG/search functionality
    - [ ] Verify user settings preserved
    - [ ] Check API integrations
    - [ ] Test from multiple browsers/devices

### Monitoring and Maintenance

30. **What to Monitor Post-Migration**
    - Supabase database size (dashboard)
    - Connection count (Supabase metrics)
    - Query performance (slow query log)
    - Error logs (docker logs openwebui-chat)
    - Nginx access/error logs
    - Droplet resource usage (htop, free -h)

31. **Backup Strategy with Supabase**
    - Supabase automatic daily backups (free tier: 7 days retention)
    - Can trigger manual backup in Supabase dashboard
    - Export database with pg_dump for local backups
    - Keep SQLite backup as final fallback (for a few weeks)

## MIGRATION PHASES SUMMARY:

### Phase 1: Supabase Setup (10 minutes)
- Create Supabase project
- Enable pgvector extension
- Get connection string
- Test connection from droplet

### Phase 2: Backup (5 minutes)
- Export SQLite database from container
- Copy to droplet filesystem
- Download to local machine
- Verify backup integrity

### Phase 3: Schema Initialization (5 minutes)
- Stop Open WebUI container
- Start container temporarily with DATABASE_URL
- Let it create PostgreSQL schema
- Stop container

### Phase 4: Data Migration (20-30 minutes)
- Run migration tool
- Monitor progress
- Verify data integrity
- Fix null byte issues if any

### Phase 5: Container Reconfiguration (10 minutes)
- Remove old container
- Create docker-compose.yml (recommended)
- Start new container with PostgreSQL
- Verify container health

### Phase 6: Testing and Verification (15 minutes)
- Test web access
- Verify data in Supabase
- Check all functionality
- Monitor logs for errors

### Phase 7: Cleanup (After 2-4 weeks)
- Remove SQLite backup from droplet
- Keep local backup permanently
- Optional: Remove old Docker volume

## TOTAL ESTIMATED TIME: 60-90 minutes

## Key migration requirements for the script

This script will always be ran from the host where the Open WebUI docker container is running.  The first steps of the migration must validate connectivity after gathering the Supabase/Postgresql connection details. Checks should occur to validate connectivity.  The script will handle the intial loading of the database objects, but must not take down the existing instance during that process.  

Under no circumstances will the existing Open WebUI instance become unavailable.  This script should handle a smooth migration where the database used for the specific Open WebUI can be reverted back to the original local SQL Lite database.