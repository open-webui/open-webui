import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mssql.server import MCPServer

def test_connection():
    server = MCPServer()
    try:
        conn = server.get_connection()
        print("✓ Database connection successful")
        conn.close()
    except Exception as e:
        print(f"✗ Database connection failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    test_connection()