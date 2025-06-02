#!/usr/bin/env python3
"""
FastMCP Time Server
A modern MCP server implementation using FastMCP for time-related tools
"""

from datetime import datetime
import pytz
from fastmcp import FastMCP

# Create FastMCP server
mcp = FastMCP("time-server")

@mcp.tool()
def get_current_time(timezone: str = "UTC", format: str = "human") -> str:
    """Get the current date and time
    
    Args:
        timezone: Timezone (default: UTC) - e.g., 'UTC', 'US/Eastern', 'Europe/London'
        format: Format type - 'human', 'iso', or 'timestamp'
    
    Returns:
        Current time in the specified timezone and format
    """
    try:
        if timezone.upper() == "UTC":
            tz = pytz.UTC
        else:
            tz = pytz.timezone(timezone)
            
        now = datetime.now(tz)
        
        if format == "iso":
            return now.isoformat()
        elif format == "timestamp":
            return str(int(now.timestamp()))
        else:  # human format
            return now.strftime("%Y-%m-%d %H:%M:%S %Z")
            
    except Exception as e:
        return f"Error getting time: {str(e)}"

if __name__ == "__main__":
    import sys
    
    # Check if we should run with HTTP transport
    if len(sys.argv) > 1 and sys.argv[1] == "--http":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8083
        print(f"Starting FastMCP server on SSE port {port}")
        mcp.run(transport="sse", port=port)
    else:
        # Run with stdio transport (standard MCP)
        print("Starting FastMCP server with stdio transport")
        mcp.run()
