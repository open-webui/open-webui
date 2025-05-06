#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import pyodbc
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mssql_test")


def test_connection():
    # Load environment variables
    load_dotenv()

    # Get connection parameters
    server = os.getenv("MSSQL_SERVER")
    database = os.getenv("MSSQL_DATABASE")
    username = os.getenv("MSSQL_USER")
    password = os.getenv("MSSQL_PASSWORD")
    driver = os.getenv("MSSQL_DRIVER")

    # Log connection parameters (without password)
    logger.info(f"Testing connection to: {server}")
    logger.info(f"Database: {database}")
    logger.info(f"Username: {username}")
    logger.info(f"Driver: {driver}")

    try:
        # Create connection string
        conn_str = (
            f"DRIVER={driver};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            "TrustServerCertificate=yes"
        )

        # Attempt connection
        logger.info("Attempting to connect...")
        conn = pyodbc.connect(conn_str)

        # Test query
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION as version")
        version = cursor.fetchone()[0]

        logger.info("Connection successful!")
        logger.info(f"SQL Server Version: {version}")

        # Close connection
        conn.close()
        return True

    except pyodbc.Error as e:
        logger.error(f"Connection failed: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return False


if __name__ == "__main__":
    test_connection()
