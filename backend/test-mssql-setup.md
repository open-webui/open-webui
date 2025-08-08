# Testing MS SQL Server Integration

## Option 1: Using Docker (Recommended for Testing)

### 1. Start MS SQL Server Container

```bash
# Run SQL Server 2022 in Docker
docker run -e "ACCEPT_EULA=Y" -e "MSSQL_SA_PASSWORD=YourStrong@Passw0rd" \
   -p 1433:1433 --name sql-server-test \
   -d mcr.microsoft.com/mssql/server:2022-latest
```

### 2. Create Test Database

```bash
# Connect to SQL Server and create database
docker exec -it sql-server-test /opt/mssql-tools/bin/sqlcmd \
   -S localhost -U sa -P "YourStrong@Passw0rd" \
   -Q "CREATE DATABASE openwebui_test"
```

### 3. Set Environment Variables

Create a `.env.test` file:

```bash
# MS SQL Server Backend Configuration
BACKEND_MSSQL_SERVER=localhost
BACKEND_MSSQL_DATABASE=openwebui_test
BACKEND_MSSQL_USERNAME=sa
BACKEND_MSSQL_PASSWORD=YourStrong@Passw0rd
BACKEND_MSSQL_ENCRYPT=no
BACKEND_MSSQL_TRUST_CERT=yes

# Disable migrations for testing
DISABLE_MIGRATIONS=false  # Set to false for initial setup

# Optional: Configure logging
LOG_LEVEL=DEBUG
```

### 4. Test Connection Script

Create `test_mssql_connection.py`:

```python
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
load_dotenv('.env.test')

# Test imports and connection
from open_webui.env import DATABASE_URL, BACKEND_MSSQL_SERVER
from open_webui.internal.db import engine

print(f"MS SQL Server: {BACKEND_MSSQL_SERVER}")
print(f"Database URL: {DATABASE_URL}")

try:
    # Test connection
    with engine.connect() as conn:
        result = conn.execute("SELECT @@VERSION")
        print("Connection successful!")
        print(f"SQL Server Version: {result.scalar()}")
        
    # Test JSON support
    with engine.connect() as conn:
        # Create a test table with JSON
        conn.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='json_test' AND xtype='U')
            CREATE TABLE json_test (
                id INT PRIMARY KEY,
                data NVARCHAR(MAX)
            )
        """)
        
        # Insert JSON data
        conn.execute("""
            INSERT INTO json_test (id, data) 
            VALUES (1, '{"name": "test", "tags": ["tag1", "tag2"]}')
        """)
        
        # Test OPENJSON
        result = conn.execute("""
            SELECT * FROM OPENJSON(
                (SELECT data FROM json_test WHERE id = 1),
                '$.tags'
            )
        """)
        
        print("\nJSON query test successful!")
        for row in result:
            print(f"Tag: {row}")
            
        # Cleanup
        conn.execute("DROP TABLE json_test")
        
except Exception as e:
    print(f"Error: {e}")
```

### 5. Run the Test

```bash
cd backend
python test_mssql_connection.py
```

## Option 2: Using Existing SQL Server

If you have an existing SQL Server:

### 1. Create Database and User

```sql
-- Create database
CREATE DATABASE openwebui;
GO

-- Create login and user
CREATE LOGIN openwebui_user WITH PASSWORD = 'YourStrong@Passw0rd';
GO

USE openwebui;
GO

CREATE USER openwebui_user FOR LOGIN openwebui_user;
GO

-- Grant permissions
ALTER ROLE db_owner ADD MEMBER openwebui_user;
GO
```

### 2. Configure Environment

```bash
export BACKEND_MSSQL_SERVER="your-server.database.windows.net"
export BACKEND_MSSQL_DATABASE="openwebui"
export BACKEND_MSSQL_USERNAME="openwebui_user"
export BACKEND_MSSQL_PASSWORD="YourStrong@Passw0rd"
export BACKEND_MSSQL_ENCRYPT="yes"
export BACKEND_MSSQL_TRUST_CERT="no"
```

## Testing the Full Application

### 1. Initial Setup (Fresh Database)

```bash
# Enable migrations for initial setup
export DISABLE_MIGRATIONS=false

# Start the application
cd backend
python main.py
```

### 2. Import Existing Data

If migrating from SQLite:

1. Export from SQLite using the admin interface
2. Use SQL Server Import/Export Wizard or SSMA
3. Set `DISABLE_MIGRATIONS=true` after import
4. Start the application

### 3. Verify Functionality

Test these key features:

1. **User Registration/Login**
   - Create a new user
   - Log in/out

2. **Chat Operations**
   - Create new chat
   - Send messages
   - Search chats (tests JSON queries)

3. **Tag Operations**
   - Add tags to chats
   - Filter by tags (tests JSON queries)

4. **Group Sync (if applicable)**
   - Verify GROUP_SYNC_MSSQL_* variables work
   - Test group synchronization

## Monitoring and Debugging

### Check Logs

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Watch for SQL queries
grep -i "sql" logs/openwebui.log
```

### SQL Server Profiler

Use SQL Server Profiler to monitor:
- Connection attempts
- Query execution
- JSON operations

### Common Issues

1. **Connection Timeout**
   ```bash
   # Increase timeout
   export DATABASE_POOL_TIMEOUT=60
   ```

2. **JSON Errors**
   - Ensure SQL Server 2016+ for JSON support
   - Check JSON syntax in queries

3. **Migration Errors**
   - Verify DISABLE_MIGRATIONS=true
   - Check database schema matches expected structure

## Automated Tests

Create `test_mssql_integration.py`:

```python
import pytest
from sqlalchemy import create_engine, text
from open_webui.models.chats import Chats

def test_mssql_json_query():
    """Test MS SQL Server JSON query functionality"""
    chats = Chats()
    
    # Test search with tags
    results = chats.get_chats_by_user_id_and_search_text(
        user_id="test_user",
        search_text="test",
        tag_ids=["tag1", "tag2"]
    )
    
    assert isinstance(results, list)

def test_mssql_tag_filter():
    """Test MS SQL Server tag filtering"""
    chats = Chats()
    
    # Test tag filtering
    results = chats.get_chat_list_by_user_id_and_tag_name(
        user_id="test_user",
        tag_name="important"
    )
    
    assert isinstance(results, list)
```

Run tests:
```bash
pytest test_mssql_integration.py -v
```