"""MCP Routers

This module contains FastAPI routers for MCP functionality including:
- Main MCP router for tool discovery and execution
- CrewAI MCP router for AI agent integration
"""

from .mcp import router as mcp_router
from .crew_mcp import router as crew_mcp_router

__all__ = ["mcp_router", "crew_mcp_router"]