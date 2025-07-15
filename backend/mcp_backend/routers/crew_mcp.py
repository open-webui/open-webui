"""
CrewAI MCP Router for Open WebUI
API endpoints for CrewAI integration with MCP servers
"""

import logging
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.routers.tasks import generate_chat_tags, generate_title
from open_webui.models.chats import Chats
from open_webui.socket.main import get_event_emitter

# Add the backend directory to the path to import crew_mcp_integration
backend_dir = Path(__file__).parent.parent.parent
sys.path.append(str(backend_dir))

try:
    from mcp_backend.integration.crew_mcp_integration import CrewMCPManager
except ImportError as e:
    logging.error(f"Failed to import CrewMCPManager: {e}")
    CrewMCPManager = None

log = logging.getLogger(__name__)
router = APIRouter()


# Request/Response models
class CrewMCPQuery(BaseModel):
    query: str
    llm_config: Optional[Dict[str, Any]] = None
    selected_tools: Optional[list] = None  # List of selected tool IDs from frontend
    chat_id: Optional[str] = None  # Chat ID for title and tag generation
    model: Optional[str] = None  # Model used for the query
    session_id: Optional[str] = None  # Session ID for WebSocket events


class CrewMCPResponse(BaseModel):
    result: str
    tools_used: list
    success: bool
    error: Optional[str] = None


class MCPToolsResponse(BaseModel):
    tools: list
    count: int


async def _setup_event_emitter(request: CrewMCPQuery, user):
    """Setup event emitter for WebSocket notifications"""
    try:
        return get_event_emitter(
            {
                "chat_id": request.chat_id,
                "user_id": user.id,
                "message_id": f"crew_msg_{request.chat_id}",
                "session_id": request.session_id,
            }
        )
    except Exception as e:
        log.warning(f"Could not set up event emitter for chat {request.chat_id}: {e}")
        return None


async def _generate_title(
    request_data, request: CrewMCPQuery, result: str, user, task_model_id
):
    """Generate and update chat title"""
    from open_webui.utils.chat import generate_chat_completion

    title_prompt = f"""Create a concise, 3-5 word title with an emoji for this conversation:

User: {request.query}
Assistant: {result[:500]}...

Respond with just the title, no quotes or formatting."""

    title_payload = {
        "model": task_model_id,
        "messages": [{"role": "user", "content": title_prompt}],
        "stream": False,
        "max_tokens": 50,
        "metadata": {"task": "title_generation", "chat_id": request.chat_id},
    }

    title_res = await generate_chat_completion(
        request_data, form_data=title_payload, user=user
    )

    if title_res and len(title_res.get("choices", [])) == 1:
        title = title_res["choices"][0]["message"]["content"].strip()
        if title:
            Chats.update_chat_title_by_id(request.chat_id, title)
            return title

    return None


async def _generate_tags(
    request_data, request: CrewMCPQuery, result: str, user, task_model_id
):
    """Generate and update chat tags"""
    from open_webui.utils.chat import generate_chat_completion
    import json
    import re

    tags_prompt = f"""Generate 3-6 tags for this conversation. Return ONLY a JSON object:
{{"tags": ["tag1", "tag2", "tag3"]}}

Conversation:
User: {request.query}
Assistant: {result[:1000]}..."""

    tags_payload = {
        "model": task_model_id,
        "messages": [{"role": "user", "content": tags_prompt}],
        "stream": False,
        "metadata": {"task": "tags_generation", "chat_id": request.chat_id},
    }

    tags_res = await generate_chat_completion(
        request_data, form_data=tags_payload, user=user
    )

    if tags_res and len(tags_res.get("choices", [])) == 1:
        content = tags_res["choices"][0]["message"]["content"]

        # Extract and parse JSON
        json_match = re.search(r"\{[^}]*\}", content)
        if json_match:
            try:
                tags_json = json.loads(json_match.group())
                tags = tags_json.get("tags", [])
                if isinstance(tags, list) and tags:
                    Chats.update_chat_tags_by_id(request.chat_id, tags, user)
                    return tags
            except json.JSONDecodeError:
                pass

    return None


async def _emit_event(event_emitter, event_type: str, data, chat_id: str):
    """Safely emit WebSocket event"""
    if not event_emitter:
        return

    try:
        await event_emitter({"type": event_type, "data": data})
        log.info(f"Emitted {event_type} event for chat {chat_id}")
    except Exception as e:
        log.error(f"Failed to emit {event_type} event for chat {chat_id}: {e}")


async def generate_title_and_tags_background(
    request_data, request: CrewMCPQuery, result: str, user
):
    """
    Background task to generate title and tags for MCP requests.
    Uses standard Open WebUI model selection.
    """
    try:
        # Setup
        event_emitter = await _setup_event_emitter(request, user)

        from open_webui.utils.task import get_task_model_id

        models = request_data.app.state.MODELS

        # Safety check to prevent crashes
        if not models or not isinstance(models, dict):
            return

        # For deployment environments, try to use any available model
        # Prefer Ollama models but fall back to others if needed
        ollama_models = [k for k, v in models.items() if v.get("owned_by") == "ollama"]

        task_model_id = None
        if ollama_models:
            # Use the smallest/most reliable Ollama model
            task_model_id = (
                "llama3.2:3b" if "llama3.2:3b" in ollama_models else ollama_models[0]
            )
        elif models:
            # In deployment, use the first available model if no Ollama models
            task_model_id = next(iter(models.keys()))
        else:
            # No models available at all
            return

        # Only proceed if we have a valid model
        if not task_model_id:
            return

        # Generate title and tags
        try:
            title = await _generate_title(
                request_data, request, result, user, task_model_id
            )
            if title:
                await _emit_event(event_emitter, "chat:title", title, request.chat_id)
        except Exception as e:
            pass

        try:
            tags = await _generate_tags(
                request_data, request, result, user, task_model_id
            )
            if tags:
                await _emit_event(event_emitter, "chat:tags", tags, request.chat_id)
        except Exception as e:
            pass

    except Exception as e:
        pass


# Global manager instance
crew_mcp_manager = None
if CrewMCPManager:
    try:
        crew_mcp_manager = CrewMCPManager()
    except Exception as e:
        logging.error(f"Failed to initialize CrewMCPManager: {e}")


@router.get("/tools")
async def get_mcp_tools(user=Depends(get_verified_user)) -> MCPToolsResponse:
    """Get available MCP tools"""
    if not crew_mcp_manager:
        raise HTTPException(
            status_code=503,
            detail="CrewAI MCP integration not available. Check dependencies.",
        )

    try:
        tools = crew_mcp_manager.get_available_tools()
        return MCPToolsResponse(tools=tools, count=len(tools))
    except Exception as e:
        log.exception(f"Error getting MCP tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def run_crew_query(
    request_data: Request, request: CrewMCPQuery, user=Depends(get_verified_user)
) -> CrewMCPResponse:
    """Run a CrewAI query with MCP tools"""
    if not crew_mcp_manager:
        return CrewMCPResponse(
            result="",
            tools_used=[],
            success=False,
            error="CrewAI MCP integration not available",
        )

    try:
        log.info(f"Running CrewAI query for user {user.id}: {request.query}")
        log.info(f"Selected tools: {request.selected_tools}")

        # Get available tools first
        tools = crew_mcp_manager.get_available_tools()
        if not tools:
            raise HTTPException(
                status_code=503,
                detail="No MCP tools available. Check MCP server configuration.",
            )

        # Use intelligent crew approach with manager agent
        selected_tools = request.selected_tools or []

        log.info(f"Selected tools: {selected_tools}")
        log.info(f"Using intelligent crew with manager agent for routing")

        # Always use the intelligent crew - it will handle routing internally
        # Run in executor to prevent blocking the main thread and causing health check failures
        import asyncio
        import concurrent.futures

        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(
                executor,
                crew_mcp_manager.run_intelligent_crew,
                request.query,
                selected_tools,
            )

        used_tools = [tool["name"] for tool in tools]  # All tools potentially available

        # Generate proper title and tags if chat_id is provided (like standard chat flow)
        if request.chat_id:
            try:
                # Run the title and tag generation in the background
                import asyncio

                # Create background task for title/tag generation
                async def safe_background_task():
                    try:
                        await generate_title_and_tags_background(
                            request_data, request, result, user
                        )
                    except Exception as e:
                        # Completely isolate any background task exceptions
                        pass

                task = asyncio.create_task(safe_background_task())

                # Add error handling for the background task
                def handle_background_task_completion(task):
                    try:
                        if task.cancelled():
                            pass
                        elif task.exception():
                            # Don't re-raise the exception, just log it if needed
                            exc = task.exception()
                            # Silently handle the exception without logging to avoid spam
                            pass
                        else:
                            # Task completed successfully
                            pass
                    except Exception as e:
                        # Don't let callback exceptions propagate
                        pass

                task.add_done_callback(handle_background_task_completion)

            except Exception as e:
                # Completely isolate any background task creation exceptions
                pass

        return CrewMCPResponse(result=result, tools_used=used_tools, success=True)

    except Exception as e:
        log.exception(f"Error running CrewAI query: {e}")
        return CrewMCPResponse(result="", tools_used=[], success=False, error=str(e))


@router.post("/multi")
async def run_multi_server_crew_query(
    request: CrewMCPQuery, user=Depends(get_verified_user)
) -> CrewMCPResponse:
    """Run a CrewAI query using ALL available MCP servers and tools simultaneously"""
    if not crew_mcp_manager:
        return CrewMCPResponse(
            result="",
            tools_used=[],
            success=False,
            error="CrewAI MCP integration not available",
        )

    try:
        log.info(
            f"Running CrewAI multi-server query for user {user.id}: {request.query}"
        )

        # Get available tools first
        tools = crew_mcp_manager.get_available_tools()
        if not tools:
            raise HTTPException(
                status_code=503,
                detail="No MCP tools available. Check MCP server configuration.",
            )

        # Run the intelligent crew (same as regular query, since manager handles everything)
        selected_tools = request.selected_tools or []
        result = crew_mcp_manager.run_intelligent_crew(request.query, selected_tools)

        return CrewMCPResponse(
            result=result, tools_used=[tool["name"] for tool in tools], success=True
        )

    except Exception as e:
        log.exception(f"Error running CrewAI multi-server query: {e}")
        return CrewMCPResponse(result="", tools_used=[], success=False, error=str(e))


@router.get("/status")
async def get_crew_mcp_status(user=Depends(get_verified_user)) -> dict:
    """Get CrewAI MCP integration status"""
    if not crew_mcp_manager:
        return {
            "status": "unavailable",
            "error": "CrewAI MCP integration not available",
            "tools_count": 0,
            "servers": {},
            "azure_config_present": False,
        }

    try:
        tools = crew_mcp_manager.get_available_tools()
        available_servers = crew_mcp_manager.get_available_servers()

        # Get server details
        server_details = {}
        for server_name, server_path in available_servers.items():
            server_tools = [tool for tool in tools if tool.get("server") == server_name]
            server_details[server_name] = {
                "available": True,
                "path": str(server_path),
                "tool_count": len(server_tools),
                "tools": [tool["name"] for tool in server_tools],
            }

        return {
            "status": "active" if tools else "inactive",
            "tools_count": len(tools),
            "servers": server_details,
            "azure_config_present": bool(crew_mcp_manager.azure_config.api_key),
            "multi_server_support": True,
        }
    except Exception as e:
        log.exception(f"Error getting CrewAI MCP status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "tools_count": 0,
            "servers": {},
            "azure_config_present": False,
        }
