# MS SQL Server Database Migration Guide

This guide explains how to configure Open WebUI to use Microsoft SQL Server as the backend database instead of the default SQLite.

## Prerequisites

- Microsoft SQL Server (2016 or later with JSON support)
- ODBC Driver 17 for SQL Server (already included in the Docker image)
- `pyodbc` Python package (already included in requirements.txt)

## Environment Variables

To use MS SQL Server as the backend database, configure the following environment variables:

### Backend Database Configuration

```bash
# MS SQL Server connection details
BACKEND_MSSQL_SERVER=your-server-address      # e.g., "server.example.com" or "192.168.1.100,1433"
BACKEND_MSSQL_DATABASE=your-database-name     # e.g., "openwebui"
BACKEND_MSSQL_USERNAME=your-username          # SQL Server username
BACKEND_MSSQL_PASSWORD=your-password          # SQL Server password

# Optional settings (with defaults)
BACKEND_MSSQL_DRIVER="ODBC Driver 17 for SQL Server"  # ODBC driver name
BACKEND_MSSQL_ENCRYPT="yes"                           # Use encryption (yes/no)
BACKEND_MSSQL_TRUST_CERT="no"                         # Trust server certificate (yes/no)

# Disable migrations when using pre-migrated database
DISABLE_MIGRATIONS="true"                              # Automatically set to true for MS SQL
```

### Group Sync Service Configuration (if using)

If you're also using the group sync service with a different MS SQL database:

```bash
# Group sync database (can be different from backend database)
GROUP_SYNC_MSSQL_SERVER=sync-server-address
GROUP_SYNC_MSSQL_DATABASE=sync-database-name
GROUP_SYNC_MSSQL_USERNAME=sync-username
GROUP_SYNC_MSSQL_PASSWORD=sync-password

# Optional settings for group sync
GROUP_SYNC_MSSQL_DRIVER="ODBC Driver 17 for SQL Server"
GROUP_SYNC_MSSQL_ENCRYPT="yes"
GROUP_SYNC_MSSQL_TRUST_CERT="no"
GROUP_SYNC_MSSQL_TIMEOUT="5"
```

## Migration Process

### Method 1: Using Existing SQLite Database

1. **Export from SQLite**:
   - Use the Open WebUI admin interface to export your database
   - Navigate to Settings → Admin → Database → Export Database

2. **Convert to MS SQL Server**:
   - Use Microsoft's SQL Server Migration Assistant (SSMA) for SQLite
   - Or use a custom migration script to transfer the data

3. **Import to MS SQL Server**:
   - Create a new database in MS SQL Server
   - Import the converted schema and data
   - Ensure JSON columns are properly configured

4. **Configure Open WebUI**:
   - Set the environment variables as shown above
   - Restart the application

### Method 2: Fresh Installation

1. **Create Database**:
   ```sql
   CREATE DATABASE openwebui;
   ```

2. **Configure Environment**:
   - Set the MS SQL Server environment variables
   - Set `DISABLE_MIGRATIONS=false` for initial setup
   - Start Open WebUI to create the schema

3. **Re-enable Migration Bypass**:
   - After initial setup, set `DISABLE_MIGRATIONS=true`
   - This prevents migration errors on subsequent starts

## JSON Support

Open WebUI uses JSON fields extensively. MS SQL Server 2016+ provides native JSON support through:
- `OPENJSON()` - Parse JSON arrays and objects
- `JSON_VALUE()` - Extract scalar values from JSON
- `JSON_QUERY()` - Extract objects or arrays from JSON

The implementation automatically uses MS SQL Server's JSON functions when the `mssql` dialect is detected.

## Troubleshooting

### Connection Issues

1. **Check ODBC Driver**:
   ```bash
   odbcinst -q -d
   ```

2. **Test Connection**:
   ```python
   import pyodbc
   conn_str = (
       f"DRIVER={{ODBC Driver 17 for SQL Server}};"
       f"SERVER={server};DATABASE={database};"
       f"UID={username};PWD={password}"
   )
   conn = pyodbc.connect(conn_str)
   ```

3. **Firewall/Network**:
   - Ensure port 1433 is accessible
   - Check SQL Server is configured for remote connections

### Migration Errors

If you encounter migration errors:
1. Ensure `DISABLE_MIGRATIONS=true` is set
2. Check that the database schema is properly imported
3. Verify JSON columns are correctly configured

### Performance Considerations

1. **Indexes**: Create indexes on frequently queried JSON paths:
   ```sql
   CREATE INDEX idx_chat_title ON chats(title);
   CREATE INDEX idx_chat_user ON chats(user_id);
   ```

2. **Connection Pooling**: Configure pool settings:
   ```bash
   DATABASE_POOL_SIZE=20
   DATABASE_POOL_MAX_OVERFLOW=10
   DATABASE_POOL_TIMEOUT=30
   DATABASE_POOL_RECYCLE=3600
   ```

## Security Notes

1. Use SQL Authentication with strong passwords
2. Enable encryption (`BACKEND_MSSQL_ENCRYPT=yes`)
3. Consider using Windows Authentication if available
4. Restrict database user permissions to minimum required

## Limitations

- Migrations must be handled externally when `DISABLE_MIGRATIONS=true`
- Some SQLite-specific features may need adjustment
- JSON query performance depends on proper indexing