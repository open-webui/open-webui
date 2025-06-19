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
    from crew_mcp_integration import CrewMCPManager
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


async def generate_title_and_tags_background(request_data, request: CrewMCPQuery, result: str, user):
    """Background task to generate title and tags without blocking the main response"""
    try:
        log.info(f"Starting background title/tag generation for chat {request.chat_id}")
        
        # Set up event emitter for real-time updates (if possible)
        event_emitter = None
        try:
            event_emitter = get_event_emitter({
                "chat_id": request.chat_id,
                "user_id": user.id,
                "message_id": f"crew_msg_{request.chat_id}",  # Provide a synthetic message_id
                "session_id": request.session_id  # Use session_id from request
            })
        except Exception as ee_error:
            log.warning(f"Could not set up event emitter for chat {request.chat_id}: {ee_error}")
            event_emitter = None
        
        messages = [
            {"role": "user", "content": request.query, "id": f"msg_user_{request.chat_id}"},
            {"role": "assistant", "content": result, "id": f"msg_assistant_{request.chat_id}"}
        ]
        
        model_to_use = request.model or "mistral:7b"
        
        # Generate proper title using the same logic as standard chats
        try:
            # Create a simpler title generation call
            from open_webui.utils.chat import generate_chat_completion
            from open_webui.utils.task import get_task_model_id
            from open_webui.config import DEFAULT_TITLE_GENERATION_PROMPT_TEMPLATE
            
            # Get the task model
            models = request_data.app.state.MODELS
            task_model_id = get_task_model_id(
                model_to_use,
                request_data.app.state.config.TASK_MODEL,
                request_data.app.state.config.TASK_MODEL_EXTERNAL,
                models,
            )
            
            # Create a simple title prompt
            title_prompt = f"""Create a concise, 3-5 word title with an emoji for this conversation:

User: {request.query}
Assistant: {result[:500]}...

Respond with just the title, no quotes or formatting."""
            
            title_payload = {
                "model": task_model_id,
                "messages": [{"role": "user", "content": title_prompt}],
                "stream": False,
                "max_tokens": 50,
                "metadata": {
                    "task": "title_generation",
                    "chat_id": request.chat_id,
                },
            }
            
            title_res = await generate_chat_completion(request_data, form_data=title_payload, user=user)
            
            if title_res and isinstance(title_res, dict):
                if len(title_res.get("choices", [])) == 1:
                    title = (
                        title_res.get("choices", [])[0]
                        .get("message", {})
                        .get("content", "")
                        .strip()
                    )
                    
                    if title:
                        Chats.update_chat_title_by_id(request.chat_id, title)
                        log.info(f"Generated and updated title for chat {request.chat_id}: {title}")
                        
                        # Emit title update event for real-time frontend update
                        if event_emitter:
                            try:
                                await event_emitter({
                                    "type": "chat:title",
                                    "data": title,
                                })
                            except Exception as event_error:
                                log.warning(f"Failed to emit title event for chat {request.chat_id}: {event_error}")
                    else:
                        log.warning(f"Empty title generated for chat {request.chat_id}")
                else:
                    log.warning(f"No choices in title response for chat {request.chat_id}")
            else:
                log.warning(f"Invalid title response format for chat {request.chat_id}")
        except Exception as title_error:
            log.error(f"Failed to generate title for chat {request.chat_id}: {title_error}")
            
        # Generate tags using direct approach to avoid message format issues
        try:
            # Create a simple tags generation call
            tags_prompt = f"""Generate 1-3 broad tags categorizing the main themes of this conversation, along with 1-3 more specific subtopic tags.

Guidelines:
- Start with high-level domains (e.g. Science, Technology, Philosophy, Arts, Politics, Business, Health, Sports, Entertainment, Education)
- Consider including relevant subfields/subdomains if they are strongly represented
- Use the conversation's primary language; default to English if multilingual
- Prioritize accuracy over specificity

Output format: Return ONLY a single JSON object with this exact structure:
{{"tags": ["broad_tag1", "broad_tag2", "specific_tag1", "specific_tag2"]}}

Do not include any other text, explanations, or multiple JSON objects.

Conversation:
User: {request.query}
Assistant: {result[:1000]}...
"""
            
            tags_payload = {
                "model": task_model_id,
                "messages": [{"role": "user", "content": tags_prompt}],
                "stream": False,
                "metadata": {
                    "task": "tags_generation",
                    "chat_id": request.chat_id,
                },
            }
            
            tags_res = await generate_chat_completion(request_data, form_data=tags_payload, user=user)
            
            if tags_res and isinstance(tags_res, dict):
                if len(tags_res.get("choices", [])) == 1:
                    tags_string = (
                        tags_res.get("choices", [])[0]
                        .get("message", {})
                        .get("content", "")
                    )
                    
                    # Extract JSON from the response (same logic as middleware)
                    tags_string = tags_string[
                        tags_string.find("{") : tags_string.rfind("}") + 1
                    ]
                    
                    if tags_string:
                        import json
                        import re
                        try:
                            # First try to extract the first complete JSON object
                            first_json_match = re.search(r'\{[^}]*\}', tags_string)
                            if first_json_match:
                                first_json_str = first_json_match.group()
                                tags_json = json.loads(first_json_str)
                                
                                if isinstance(tags_json, dict) and "tags" in tags_json:
                                    tags = tags_json["tags"]
                                else:
                                    # If first JSON doesn't have tags, try to find all JSON objects and combine
                                    all_json_matches = re.findall(r'\{[^}]*\}', tags_string)
                                    all_tags = []
                                    for json_str in all_json_matches:
                                        try:
                                            json_obj = json.loads(json_str)
                                            if isinstance(json_obj, dict):
                                                # Extract tags from any key that contains tag-like data
                                                for key, value in json_obj.items():
                                                    if isinstance(value, list) and len(value) > 0:
                                                        all_tags.extend(value)
                                        except:
                                            continue
                                    tags = all_tags
                                
                                if isinstance(tags, list) and len(tags) > 0:
                                    Chats.update_chat_tags_by_id(request.chat_id, tags, user)
                                    log.info(f"Generated and updated tags for chat {request.chat_id}: {tags}")
                                    
                                    # Emit tags update event for real-time frontend update
                                    if event_emitter:
                                        try:
                                            await event_emitter({
                                                "type": "chat:tags",
                                                "data": tags,
                                            })
                                        except Exception as event_error:
                                            log.warning(f"Failed to emit tags event for chat {request.chat_id}: {event_error}")
                                else:
                                    log.warning(f"Invalid tags format for chat {request.chat_id}: {tags}")
                            else:
                                log.warning(f"No JSON found in tags response for chat {request.chat_id}")
                        except json.JSONDecodeError as json_error:
                            log.error(f"Failed to parse tags JSON for chat {request.chat_id}: {json_error}")
                            log.error(f"Tags string was: {tags_string}")
                        except Exception as parse_error:
                            log.error(f"Unexpected error parsing tags for chat {request.chat_id}: {parse_error}")
                            log.error(f"Tags string was: {tags_string}")
                    else:
                        log.warning(f"Empty tags string for chat {request.chat_id}")
                else:
                    log.warning(f"No choices in tags response for chat {request.chat_id}")
            else:
                log.warning(f"Invalid tags response format for chat {request.chat_id}")
        except Exception as tags_error:
            log.error(f"Failed to generate tags for chat {request.chat_id}: {tags_error}")
            import traceback
            log.error(f"Tags generation traceback: {traceback.format_exc()}")
            
    except Exception as e:
        log.error(f"Error in background title/tag generation for chat {request.chat_id}: {e}")
        import traceback
        log.error(f"Full background traceback: {traceback.format_exc()}")


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
        result = crew_mcp_manager.run_intelligent_crew(request.query, selected_tools)
        used_tools = [tool["name"] for tool in tools]  # All tools potentially available

        # Generate proper title and tags if chat_id is provided (like standard chat flow)
        if request.chat_id:
            log.info(f"Processing title and tag generation for chat {request.chat_id}")
            try:
                # Run the title and tag generation in the background
                import asyncio
                log.info(f"About to create background task for chat {request.chat_id}")
                task = asyncio.create_task(generate_title_and_tags_background(request_data, request, result, user))
                log.info(f"Created background task: {task}")
                
            except Exception as e:
                log.error(f"Error in title/tag generation for chat {request.chat_id}: {e}")
                import traceback
                log.error(f"Full traceback: {traceback.format_exc()}")

        return CrewMCPResponse(
            result=result, tools_used=used_tools, success=True
        )

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
        log.info(f"Running CrewAI multi-server query for user {user.id}: {request.query}")

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
                "tools": [tool["name"] for tool in server_tools]
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
