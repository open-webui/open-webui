# SQLite to MSSQL Data Migration Script

This script imports SQLite data exported from SqliteStudio (JSON format) into a Microsoft SQL Server database.

## Prerequisites

1. Python 3.7 or higher
2. SQL Server ODBC Driver (the script will auto-detect available drivers)
   - Recommended: ODBC Driver 18 for SQL Server
   - Download from: https://go.microsoft.com/fwlink/?linkid=2249006
   - Alternative drivers supported: ODBC Driver 17, 13, 11, SQL Server Native Client
3. Network access to the MSSQL server
4. Appropriate database permissions

## Installation

1. Install the required Python package:
```bash
pip install -r requirements.txt
```

## Configuration

Before running the script, you must configure the authentication method in the `DB_CONFIG` dictionary in `import_data_to_mssql.py`:

### Option 1: SQL Authentication
```python
DB_CONFIG = {
    'server': 'dvse-cepm-sqlmi.dceaba912a56.database.windows.net',
    'database': 'openwebui',
    'driver': '{ODBC Driver 18 for SQL Server}',
    'username': 'your_username',
    'password': 'your_password'
}
```

### Option 2: Windows Authentication
```python
DB_CONFIG = {
    'server': 'dvse-cepm-sqlmi.dceaba912a56.database.windows.net',
    'database': 'openwebui',
    'driver': '{ODBC Driver 18 for SQL Server}',
    'trusted_connection': 'yes'
}
```

### Option 3: Azure AD Authentication (Default)
The script is configured to use Azure AD authentication by default if no other authentication method is specified.

## Usage

1. Ensure the MSSQL database schema has been created using `dev-openwebui-schema.sqlserver.sql`

2. Place the exported data file (`dev-openwebui-data.json`) in the same directory as the script

3. Configure authentication as described above

4. Run the script:
```bash
python import_data_to_mssql.py
```

## Features

- **Transactional Safety**: The entire import process is wrapped in a single transaction. If any error occurs, all changes are rolled back automatically
- Handles foreign key constraints by temporarily disabling them during import
- Imports tables in the correct order to respect dependencies
- Provides detailed logging of the import process
- Includes error handling with automatic rollback on any failure
- Clears existing data before importing to ensure clean state
- All-or-nothing approach: either all data is imported successfully or no changes are made to the database

## Troubleshooting

### Check Available ODBC Drivers
Run the included diagnostic script to see what drivers are installed:
```bash
python check_odbc_drivers.py
```

### Common Issues

1. **"Data source name not found" Error**: 
   - No SQL Server ODBC driver is installed
   - Run `check_odbc_drivers.py` to see available drivers
   - Install ODBC Driver 18 from the link above

2. **Connection Issues**: 
   - Ensure the server address is correct
   - Check firewall settings
   - Verify network connectivity to the SQL Server

3. **Authentication Failures**: 
   - Verify your credentials
   - Ensure your account has the necessary permissions
   - Try different authentication methods (SQL, Windows, Azure AD)

4. **Encoding Errors**: 
   - The script automatically tries multiple encodings
   - Check the logs to see which encoding was successful

5. **Data Type Errors**: 
   - The script attempts to handle data type conversions automatically
   - Check the logs for specific error messages

6. **Foreign Key Violations**: 
   - The script disables constraints during import
   - If enabling them fails afterward, check for data integrity issues

## Logging

The script provides detailed logging output to help track the import progress and troubleshoot any issues. Look for:
- INFO messages for normal progress
- WARNING messages for non-critical issues
- ERROR messages for failures that need attention