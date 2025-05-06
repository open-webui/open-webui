#!/usr/bin/env python3
import json
import sys
import os
from dotenv import load_dotenv
import asyncio
import logging
import pyodbc
from mcp.server import Server
from mcp.types import Resource, Tool, TextContent
from pydantic import AnyUrl
import re

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mssql_mcp_server")

app = Server("mssql_mcp_server")

class DBConfig:
    def __init__(self):
        self.config = {
            "server": os.getenv("MSSQL_SERVER"),
            "database": os.getenv("MSSQL_DATABASE"), 
            "user": os.getenv("MSSQL_USER"),
            "password": os.getenv("MSSQL_PASSWORD"),
            "driver": os.getenv("MSSQL_DRIVER")
        }
        self.connection = None

    def get_connection(self):
        try:
            if not self.connection:
                conn_str = (
                    f"DRIVER={self.config['driver']};"
                    f"SERVER={self.config['server']};"
                    f"DATABASE={self.config['database']};"
                    f"UID={self.config['user']};"
                    f"PWD={self.config['password']};"
                    "TrustServerCertificate=yes"
                )
                self.connection = pyodbc.connect(conn_str, readonly=True)  # เพิ่ม readonly=True
            return self.connection
        except:
            self.connection = None
            raise

class SQLValidator:
    @staticmethod
    def is_read_only_query(query: str) -> bool:
        # ทำความสะอาด query
        clean_query = query.strip().upper()
        
        # รายการคำสั่งที่อนุญาต
        allowed_statements = [
            'SELECT', 'WITH', 'DECLARE'
        ]
        
        # รายการคำสั่งที่ไม่อนุญาต
        forbidden_statements = [
            'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 
            'ALTER', 'TRUNCATE', 'MERGE', 'UPSERT', 'REPLACE',
            'GRANT', 'REVOKE', 'EXEC', 'EXECUTE', 'SP_'
        ]
        
        # ตรวจสอบว่าเริ่มต้นด้วยคำสั่งที่อนุญาตหรือไม่
        starts_with_allowed = any(clean_query.startswith(stmt) for stmt in allowed_statements)
        if not starts_with_allowed:
            return False
            
        # ตรวจสอบว่ามีคำสั่งต้องห้ามหรือไม่
        contains_forbidden = any(stmt in clean_query for stmt in forbidden_statements)
        if contains_forbidden:
            return False
            
        # ตรวจสอบเพิ่มเติมสำหรับ SQL Injection
        has_dangerous_chars = re.search(r';\s*\w+', clean_query)  # ตรวจหา semicolon ที่ตามด้วยคำสั่ง
        if has_dangerous_chars:
            return False
            
        return True

db = DBConfig()
sql_validator = SQLValidator()

@app.list_resources()
async def list_resources() -> list[Resource]:
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        tables = cursor.execute(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'"
        ).fetchall()
        
        return [
            Resource(
                uri=f"mssql://{table[0]}/data",
                name=f"Table: {table[0]}",
                mimeType="application/json",
                description=f"Data in table {table[0]}"
            )
            for table in tables
        ]
    except Exception as e:
        logger.error(f"Failed to list resources: {str(e)}")
        return []

@app.read_resource()
async def read_resource(uri: AnyUrl) -> str:
    uri_str = str(uri)
    if not uri_str.startswith("mssql://"):
        raise ValueError(f"Invalid URI scheme: {uri_str}")
        
    table = uri_str[8:].split('/')[0]
    query = f"SELECT TOP 100 * FROM {table}"
    
    if not sql_validator.is_read_only_query(query):
        raise ValueError("Only SELECT queries are allowed")
        
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        result = [",".join(map(str, row)) for row in rows]
        return "\n".join([",".join(columns)] + result)
    except Exception as e:
        logger.error(f"Error reading table {table}: {str(e)}")
        raise RuntimeError(f"Database error: {str(e)}")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="execute_sql",
            description="Execute a READ-ONLY SQL query (SELECT only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "SQL SELECT query to execute"}
                },
                "required": ["query"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name != "execute_sql":
        raise ValueError(f"Unknown tool: {name}")

    query = arguments.get("query")
    if not query:
        raise ValueError("Query is required")

    # ตรวจสอบว่าเป็น read-only query
    if not sql_validator.is_read_only_query(query):
        return [TextContent(type="text", text="Error: Only SELECT queries are allowed")]

    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        result = [",".join(map(str, row)) for row in rows]
        return [TextContent(type="text", text="\n".join([",".join(columns)] + result))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def main():
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
