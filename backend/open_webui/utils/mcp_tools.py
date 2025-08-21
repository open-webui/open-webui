import logging
from typing import Any

from open_webui.models.tools import Tools as ToolsTable, ToolForm
from open_webui.models.users import UserModel
from open_webui.models.mcp_servers import MCPServers
from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.mcp_conversion import convert_mcp_tool_to_openai_spec

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


async def sync_mcp_server_tools_to_database(user: UserModel, server_id: str) -> None:
    server = MCPServers.get_mcp_server_by_id(server_id)
    if not server or not server.is_active:
        return

    from open_webui.utils.mcp.manager import MCPClientManager

    client = MCPClientManager().get_client(server.id)
    if not client:
        return

    tools_list = await client.get_available_tools()
    # Convert to the expected format
    tools = []
    for tool in tools_list:
        tool_dict = {
            "name": tool.name,
            "description": getattr(tool, "description", ""),
        }
        # Add input schema if available
        if hasattr(tool, "inputSchema"):
            tool_dict["inputSchema"] = tool.inputSchema
        # Add output schema if available
        if hasattr(tool, "outputSchema"):
            tool_dict["outputSchema"] = tool.outputSchema
        tools.append(tool_dict)
    
    # If the server returns no tools, remove all existing tools for this server
    if len(tools) == 0:
        try:
            log.info(f"Server {server.id} returned no tools; deleting all associated MCP tools")
            await delete_mcp_server_tools_from_database(server.id)
        except Exception as e:
            log.error(f"Failed to delete tools for server {server.id} when no tools returned: {e}")
        return

    # Remove stale tools that are no longer returned by the server
    try:
        from open_webui.internal.db import get_db
        from open_webui.models.tools import Tool

        current_tool_ids = set(
            f"mcp:{server.id}:{t.get('name')}" for t in tools if t.get("name")
        )

        with get_db() as db:
            existing_tools = db.query(Tool).filter(Tool.id.like(f"mcp:{server.id}:%")).all()
            existing_tool_ids = set(t.id for t in existing_tools)
            stale_tool_ids = existing_tool_ids - current_tool_ids

            if stale_tool_ids:
                log.info(
                    f"Deleting {len(stale_tool_ids)} stale MCP tools for server {server.id}"
                )
                db.query(Tool).filter(Tool.id.in_(list(stale_tool_ids))).delete(
                    synchronize_session=False
                )
                db.commit()
    except Exception as e:
        log.error(f"Failed to remove stale MCP tools for server {server.id}: {e}")

    for tool in tools:
        name = tool.get("name")
        if not name:
            continue

        tool_id = f"mcp:{server.id}:{name}"
        openai_spec = convert_mcp_tool_to_openai_spec(tool, server.name)
        openai_function_name = openai_spec["name"]

        wrapper_content = f'''"""
{tool.get("description", f"MCP tool {name} from {server.name}")}

This is an auto-generated MCP tool wrapper.
"""

import logging
from typing import Any, Dict
from open_webui.utils.mcp.manager import MCPClientManager

log = logging.getLogger(__name__)

class Tools:
    def __init__(self):
        pass

    async def {openai_function_name}(self, **kwargs) -> str:
        """
        {tool.get("description", f"Execute MCP tool {name}")}
        """
        try:
            client = MCPClientManager().get_client("{server.id}")
            if not client:
                return "Error: MCP server not available"
            result = await client.call_tool("{name}", kwargs)
            if isinstance(result, dict):
                # Try MCP content envelope
                if "content" in result:
                    content = result["content"]
                    try:
                        if isinstance(content, list) and content:
                            first = content[0]
                            if isinstance(first, dict) and "text" in first:
                                return str(first.get("text"))
                        return str(content)
                    except Exception:
                        return str(content)
                return str(result)
            return str(result)
        except Exception as e:
            from open_webui.utils.mcp.exceptions import MCPAuthenticationError
            if isinstance(e, MCPAuthenticationError):
                log.warning(f"Authentication required for MCP tool {name}: {{str(e)}}")
                
                # Return authentication instructions directly instead of relying on broken WebSocket events
                if e.challenge_type == "oauth":
                    if e.auth_url:
                        return f"""🔐 **Authentication Required for {{e.server_name}}**

The tool `{name}` requires OAuth authentication to continue.

[🔗 Click here to authenticate with {{e.server_name}}]({{e.auth_url}})

After completing authentication in the popup window, please ask me to retry the tool or click the regenerate button."""
                    else:
                        return f"""🔐 **OAuth Authentication Required for {{e.server_name}}**

The tool `{name}` requires OAuth authentication. Please:

1. Go to your MCP server settings 
2. Re-authenticate with {{e.server_name}}
3. Try running the tool again

Error: {{e.message}}"""
                else:
                    return f"""🔐 **Authentication Required for {{e.server_name}}**

The tool `{name}` requires manual authentication setup.

{{e.instructions or 'Please check your server configuration and credentials.'}}

Error: {{e.message}}"""
            else:
                log.error(f"Error calling MCP tool {name}: {{str(e)}}")
                return f"Error: {{str(e)}}"
'''
        form = ToolForm(
            id=tool_id,
            name=f"[MCP] {server.name} - {name}",
            content=wrapper_content,
            meta={
                "description": tool.get("description", ""),
                "manifest": {
                    "type": "mcp",
                    "mcp_server_id": server.id,
                    "mcp_server_name": server.name,
                    "mcp_tool_name": name,
                    "mcp_original_name": name,
                    "has_structured_output": bool(tool.get("outputSchema")),
                    "supports_json_response": False,
                    "output_schema": tool.get("outputSchema"),
                },
            },
            access_control=None,
        )

        existing = ToolsTable.get_tool_by_id(tool_id)
        if existing:
            ToolsTable.update_tool_by_id(
                tool_id,
                {
                    "name": form.name,
                    "content": form.content,
                    "specs": [openai_spec],
                    "meta": form.meta,
                },
            )
        else:
            # Use server's owner for public servers, otherwise use requesting user's id
            tool_user_id = server.user_id if (server.access_control is None) else user.id
            ToolsTable.insert_new_tool(tool_user_id, form, specs=[openai_spec])


async def sync_mcp_tools_to_database(user: UserModel) -> None:
    """Sync all MCP tools from all active servers to database"""
    servers = MCPServers.get_mcp_servers_by_user_id(user.id, "read")
    for server in servers:
        if server.is_active:
            await sync_mcp_server_tools_to_database(user, server.id)


async def delete_mcp_server_tools_from_database(server_id: str) -> None:
    """Delete all tools associated with an MCP server from the database"""
    log.info(f"Deleting all MCP tools for server: {server_id}")
    
    try:
        # Use direct database query for efficiency
        from open_webui.internal.db import get_db
        from open_webui.models.tools import Tool
        
        with get_db() as db:
            # Find all tools that belong to this server
            mcp_tools = db.query(Tool).filter(Tool.id.like(f"mcp:{server_id}:%")).all()
            deleted_count = len(mcp_tools)
            
            if deleted_count > 0:
                log.info(f"Deleting {deleted_count} MCP tools for server {server_id}")

                # Bulk delete all matching tools
                db.query(Tool).filter(Tool.id.like(f"mcp:{server_id}:%")).delete(synchronize_session=False)
                db.commit()
                
                log.info(f"Successfully deleted {deleted_count} MCP tools for server {server_id}")
            else:
                log.info(f"No MCP tools found for server {server_id}")
                
    except Exception as e:
        log.error(f"Failed to delete MCP tools for server {server_id}: {e}")
        # Fallback to the old method
        log.info("Falling back to individual tool deletion")
        tools = ToolsTable.get_tools()
        deleted_count = 0
        
        for tool in tools:
            if tool.id.startswith(f"mcp:{server_id}:"):
                log.info(f"Deleting MCP tool: {tool.id}")
                try:
                    ToolsTable.delete_tool_by_id(tool.id)
                    deleted_count += 1
                except Exception as delete_error:
                    log.error(f"Failed to delete tool {tool.id}: {delete_error}")
        
        log.info(f"Fallback method deleted {deleted_count} MCP tools for server {server_id}")


async def cleanup_orphaned_mcp_tools() -> None:
    """Clean up orphaned MCP tools where the associated server no longer exists"""
    log.info("Starting cleanup of orphaned MCP tools")
    
    try:
        from open_webui.internal.db import get_db
        from open_webui.models.tools import Tool
        
        with get_db() as db:
            # Get all MCP tools
            mcp_tools = db.query(Tool).filter(Tool.id.like("mcp:%")).all()
            log.info(f"Found {len(mcp_tools)} total MCP tools to check")
            
            orphaned_tools = []
            
            for tool in mcp_tools:
                # Extract server ID from tool ID (format: mcp:{server_id}:{tool_name})
                parts = tool.id.split(":")
                if len(parts) >= 3:
                    server_id = parts[1]
                    
                    # Check if the server still exists
                    server = MCPServers.get_mcp_server_by_id(server_id)
                    if not server:
                        orphaned_tools.append(tool)
                        log.info(f"Found orphaned MCP tool: {tool.id} (server {server_id} not found)")
            
            if orphaned_tools:
                log.info(f"Found {len(orphaned_tools)} orphaned MCP tools to delete")
                
                # Delete orphaned tools
                orphaned_tool_ids = [tool.id for tool in orphaned_tools]
                db.query(Tool).filter(Tool.id.in_(orphaned_tool_ids)).delete(synchronize_session=False)
                db.commit()
                
                log.info(f"Successfully deleted {len(orphaned_tools)} orphaned MCP tools")
                for tool in orphaned_tools:
                    log.info(f"Deleted orphaned tool: {tool.id}")
            else:
                log.info("No orphaned MCP tools found")
                
    except Exception as e:
        log.error(f"Failed to cleanup orphaned MCP tools: {e}")


async def sync_single_mcp_tool_to_database(user: UserModel, server_id: str, tool_name: str) -> None:
    """Sync a single MCP tool to the database"""
    server = MCPServers.get_mcp_server_by_id(server_id)
    if not server or not server.is_active:
        return

    from open_webui.utils.mcp.manager import MCPClientManager

    client = MCPClientManager().get_client(server.id)
    if not client:
        return

    tools_list = await client.get_available_tools()
    
    # Find the specific tool
    target_tool = None
    for tool in tools_list:
        if tool.name == tool_name:
            target_tool = {
                "name": tool.name,
                "description": getattr(tool, "description", ""),
            }
            # Add input schema if available
            if hasattr(tool, "inputSchema"):
                target_tool["inputSchema"] = tool.inputSchema
            # Add output schema if available
            if hasattr(tool, "outputSchema"):
                target_tool["outputSchema"] = tool.outputSchema
            break
    
    if not target_tool:
        return
    
    # Process the single tool (same logic as sync_mcp_server_tools_to_database)
    tool = target_tool
    name = tool.get("name")
    if not name:
        return

    tool_id = f"mcp:{server.id}:{name}"
    openai_spec = convert_mcp_tool_to_openai_spec(tool, server.name)
    openai_function_name = openai_spec["name"]

    wrapper_content = f'''"""
{tool.get("description", f"MCP tool {name} from {server.name}")}

This is an auto-generated MCP tool wrapper.
"""

import logging
from typing import Any, Dict
from open_webui.utils.mcp.manager import MCPClientManager

log = logging.getLogger(__name__)

class Tools:
    def __init__(self):
        pass

    async def {openai_function_name}(self, **kwargs) -> str:
        """
        {tool.get("description", f"Execute MCP tool {name}")}
        """
        try:
            client = MCPClientManager().get_client("{server.id}")
            if not client:
                return "Error: MCP server not available"
            result = await client.call_tool("{name}", kwargs)
            if isinstance(result, dict):
                # Try MCP content envelope
                if "content" in result:
                    content = result["content"]
                    try:
                        if isinstance(content, list) and content:
                            first = content[0]
                            if isinstance(first, dict) and "text" in first:
                                return str(first.get("text"))
                        return str(content)
                    except Exception:
                        return str(content)
                return str(result)
            return str(result)
        except Exception as e:
            from open_webui.utils.mcp.exceptions import MCPAuthenticationError
            if isinstance(e, MCPAuthenticationError):
                log.warning(f"Authentication required for MCP tool {name}: {{str(e)}}")
                
                # Return authentication instructions directly instead of relying on broken WebSocket events
                if e.challenge_type == "oauth":
                    if e.auth_url:
                        return f"""🔐 **Authentication Required for {{e.server_name}}**

The tool `{name}` requires OAuth authentication to continue.

[🔗 Click here to authenticate with {{e.server_name}}]({{e.auth_url}})

After completing authentication in the popup window, please ask me to retry the tool or click the regenerate button."""
                    else:
                        return f"""🔐 **OAuth Authentication Required for {{e.server_name}}**

The tool `{name}` requires OAuth authentication. Please:

1. Go to your MCP server settings 
2. Re-authenticate with {{e.server_name}}
3. Try running the tool again

Error: {{e.message}}"""
                else:
                    return f"""🔐 **Authentication Required for {{e.server_name}}**

The tool `{name}` requires manual authentication setup.

{{e.instructions or 'Please check your server configuration and credentials.'}}

Error: {{e.message}}"""
            else:
                log.error(f"Error calling MCP tool {name}: {{str(e)}}")
                return f"Error: {{str(e)}}"
'''
    form = ToolForm(
        id=tool_id,
        name=f"[MCP] {server.name} - {name}",
        content=wrapper_content,
        meta={
            "description": tool.get("description", ""),
            "manifest": {
                "type": "mcp",
                "mcp_server_id": server.id,
                "mcp_server_name": server.name,
                "mcp_tool_name": name,
                "mcp_original_name": name,
                "has_structured_output": bool(tool.get("outputSchema")),
                "supports_json_response": False,
                "output_schema": tool.get("outputSchema"),
            },
        },
        access_control=None,
    )

    existing = ToolsTable.get_tool_by_id(tool_id)
    if existing:
        ToolsTable.update_tool_by_id(
            tool_id,
            {
                "name": form.name,
                "content": form.content,
                "specs": [openai_spec],
                "meta": form.meta,
            },
        )
    else:
        # Use server's owner for public servers, otherwise use requesting user's id
        tool_user_id = server.user_id if (server.access_control is None) else user.id
        ToolsTable.insert_new_tool(tool_user_id, form, specs=[openai_spec])