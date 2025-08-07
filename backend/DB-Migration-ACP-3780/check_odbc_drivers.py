#!/usr/bin/env python3
"""
Script to check available ODBC drivers on the system
"""

import pyodbc
import platform

print("System Information:")
print(f"Platform: {platform.system()}")
print(f"Version: {platform.version()}")
print(f"Architecture: {platform.machine()}")
print()

print("Available ODBC Drivers:")
drivers = pyodbc.drivers()

if not drivers:
    print("No ODBC drivers found!")
    print("\nTo install SQL Server ODBC Driver:")
    print("1. Download from: https://go.microsoft.com/fwlink/?linkid=2249006")
    print("2. Run the installer and follow the prompts")
else:
    for driver in drivers:
        print(f"- {driver}")
        
    print("\nSQL Server drivers found:")
    sql_drivers = [d for d in drivers if 'SQL Server' in d]
    if sql_drivers:
        for driver in sql_drivers:
            print(f"- {driver}")
    else:
        print("None found. Please install ODBC Driver 18 for SQL Server.")
        print("Download from: https://go.microsoft.com/fwlink/?linkid=2249006")