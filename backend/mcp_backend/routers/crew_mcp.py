"""
CrewAI MCP Router for Open WebUI
API endpoints for CrewAI integration with MCP servers
"""

import logging
import sys
import json
import aiohttp
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from open_webui.utils.auth import get_verified_user
from open_webui.models.chats import Chats
from open_webui.socket.main import get_event_emitter

# Add the backend directory to the path to import crew_mcp_integration
backend_dir = Path(__file__).parent.parent.parent
sys.path.append(str(backend_dir))

# Initialize HTTPBearer for token extraction
bearer_security = HTTPBearer(auto_error=False)

# OAuth token extraction configuration
OAUTH_HEADERS_TO_CHECK = [
    "X-Forwarded-Access-Token",
    "X-Auth-Request-Access-Token",
    "X-Oauth-Token",
    "X-Access-Token",
    "Authorization",
]

OAUTH_COOKIES_TO_CHECK = [
    "oauth_access_token",
    "oauth_id_token",
    "oauth_token",
    "_oauth2_proxy",  # Default oauth2-proxy session cookie
    "CANChat",  # Our configured cookie name
]

MS_GRAPH_HEADERS = [
    "X-MS-Token-AAD-Access-Token",
    "X-MS-Token-AAD-Id-Token",
    "X-Forwarded-AAD-Access-Token",
]


def extract_user_token(
    request: Request,
    auth_token: Optional[HTTPAuthorizationCredentials] = Depends(bearer_security),
) -> Optional[str]:
    """
    Extract the user's OAuth token from the request for OBO flow.
    Supports multiple OAuth2 proxy configurations and token sources.
    """
    import os

    # Check if we're in localhost development environment
    # Be precise to avoid matching k8s "canchat-development" environment
    environment = os.getenv("ENVIRONMENT", "").lower()
    is_localhost = (
        environment in ["local", "localhost", "development"]  # Exact match only
        and not environment.startswith(
            "canchat-"
        )  # Exclude k8s environments like "canchat-development"
        or "localhost" in os.getenv("WEBUI_BASE_URL", "")
        or "127.0.0.1" in os.getenv("WEBUI_BASE_URL", "")
        or os.getenv("WEBUI_BASE_URL", "").startswith("http://localhost")
    )

    # Cache debug info to avoid repeated computation
    available_headers = list(request.headers.keys())
    available_cookies = list(request.cookies.keys())

    logging.info("=== OAuth Token Extraction Debug ===")
    logging.info(f"Available headers: {available_headers}")
    logging.info(f"Available cookies: {available_cookies}")

    # Method 1: OAuth2 proxy forwarded headers
    # Check common OAuth2 proxy header patterns
    for header_name in OAUTH_HEADERS_TO_CHECK:
        token = request.headers.get(header_name, "")
        if token:
            # Handle Authorization header specifically
            if header_name == "Authorization" and token.startswith("Bearer "):
                token = token.split("Bearer ", 1)[1]

            if token and token != "user_token_placeholder":
                logging.info(
                    f"Found OAuth token in header {header_name} (length: {len(token)})"
                )
                return token

    # Method 2: OAuth2 proxy cookies (standard oauth2-proxy cookie names)
    for cookie_name in OAUTH_COOKIES_TO_CHECK:
        token = request.cookies.get(cookie_name, "")
        if token and token != "user_token_placeholder":
            logging.info(
                f"Found OAuth token in cookie {cookie_name} (length: {len(token)})"
            )

            # Skip oauth2-proxy session cookies as they're not meant for direct token extraction
            # OAuth2-proxy should be configured to forward access tokens via headers instead
            if cookie_name in ["_oauth2_proxy", "CANChat"]:
                logging.debug(
                    f"Skipping oauth2-proxy session cookie {cookie_name} - use header forwarding instead"
                )
                continue

            return token

    # Method 3: Try to use FastAPI HTTPBearer token
    if auth_token and auth_token.credentials:
        token = auth_token.credentials
        if token and token != "user_token_placeholder":
            logging.info(f"Found OAuth token via HTTPBearer (length: {len(token)})")
            return token

    # Method 4: Check for Microsoft Graph specific headers/cookies
    for header_name in MS_GRAPH_HEADERS:
        token = request.headers.get(header_name, "")
        if token and token != "user_token_placeholder":
            logging.info(f"Found Microsoft Graph token in header {header_name}")
            return token

    # No OAuth tokens found
    if is_localhost:
        logging.info(
            "No OAuth tokens found in localhost - will use application-only authentication"
        )
        return None
    else:
        logging.warning("No OAuth tokens found in k8s environment")
        logging.warning("Available headers: " + ", ".join(available_headers))
        logging.warning("Available cookies: " + ", ".join(available_cookies))
        logging.warning(
            "This may indicate OAuth2 proxy is not configured to forward tokens"
        )
        return None


def determine_department_from_tools(selected_tools: Optional[list] = None) -> str:
    """
    Determine department prefix from selected tools.

    Args:
        selected_tools: List of selected tool IDs from the frontend

    Returns:
        Department prefix (defaults to "MPO" if unable to determine)
    """
    if not selected_tools:
        return "MPO"  # Default to MPO for backwards compatibility

    # Look for department-specific tool patterns
    for tool in selected_tools:
        if isinstance(tool, str):
            tool_str = tool.lower()
            if "mpo" in tool_str or "major_projects" in tool_str:
                return "MPO"
            elif "fin" in tool_str or "finance" in tool_str:
                return "FIN"
            # Add more department mappings as needed

    # Default to MPO if no specific department detected
    return "MPO"


async def get_microsoft_graph_token_for_user(
    request: Request, department: str = "MPO"
) -> Optional[str]:
    """
    Obtain a Microsoft Graph access token for the current user.
    This uses the application's credentials to get an on-behalf-of token.

    Args:
        request: The HTTP request object
        department: Department prefix for environment variables (e.g., "MPO", "FIN")
    """
    import os
    import aiohttp
    import logging

    try:
        # Get user email from OAuth2 proxy headers
        user_email = request.headers.get("X-Forwarded-Email") or request.headers.get(
            "X-Forwarded-User"
        )
        if not user_email:
            logging.error("No user email found in OAuth2 proxy headers")
            return None

        # Get SharePoint app credentials using department prefix
        client_id = os.getenv(f"{department}_SHP_ID_APP")
        client_secret = os.getenv(f"{department}_SHP_ID_APP_SECRET")
        tenant_id = os.getenv(f"{department}_SHP_TENANT_ID")

        if not all([client_id, client_secret, tenant_id]):
            logging.error(
                f"Missing SharePoint app credentials for {department} department. "
                f"Required: {department}_SHP_ID_APP, {department}_SHP_ID_APP_SECRET, {department}_SHP_TENANT_ID"
            )
            return None

        # Use client credentials flow to get an app-only token, then use it for user delegation
        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

        # First, try to get a token using the application's identity
        async with aiohttp.ClientSession() as session:
            # Method 1: Try to use any existing user token for on-behalf-of flow
            existing_token = await extract_any_available_token(request)
            if existing_token:
                logging.info("Attempting on-behalf-of flow with existing token")

                data = {
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "assertion": existing_token,
                    "scope": "https://graph.microsoft.com/Sites.Read.All https://graph.microsoft.com/Files.Read.All",
                    "requested_token_use": "on_behalf_of",
                }

                async with session.post(token_url, data=data) as response:
                    if response.status == 200:
                        token_data = await response.json()
                        access_token = token_data.get("access_token")
                        if access_token:
                            logging.info(
                                "Successfully obtained on-behalf-of token for SharePoint"
                            )
                            return access_token
                    else:
                        error_text = await response.text()
                        logging.warning(
                            f"On-behalf-of flow failed: {response.status} - {error_text}"
                        )

            # Method 2: Fallback to application-only token (current working method)
            logging.info("Falling back to application-only token for SharePoint access")

            data = {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "https://graph.microsoft.com/.default",
            }

            async with session.post(token_url, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    access_token = token_data.get("access_token")
                    if access_token:
                        logging.info(
                            "Successfully obtained application-only token for SharePoint"
                        )
                        return access_token
                else:
                    error_text = await response.text()
                    logging.error(
                        f"Failed to obtain application token: {response.status} - {error_text}"
                    )

    except Exception as e:
        logging.error(f"Error obtaining Microsoft Graph token: {e}")

    return None


async def extract_any_available_token(request: Request) -> Optional[str]:
    """
    Extract any available token that might be suitable for on-behalf-of flow.
    This includes ID tokens which can sometimes be used for OBO.
    """
    # Check for ID token in headers (OAuth2 proxy might provide this)
    id_token_headers = [
        "X-Forwarded-Id-Token",
        "X-Auth-Request-Id-Token",
        "X-Oauth-Id-Token",
    ]

    for header_name in id_token_headers:
        token = request.headers.get(header_name, "")
        if token and len(token) > 50:  # Basic validation
            logging.info(f"Found potential ID token in header {header_name}")
            return token

    # Check cookies for any JWT-like tokens
    for cookie_name, cookie_value in request.cookies.items():
        if len(cookie_value) > 100 and "." in cookie_value:  # JWT-like structure
            # Skip obvious session cookies
            if cookie_name.lower() in ["session", "sessionid", "csrftoken"]:
                continue
            logging.info(f"Found potential JWT token in cookie {cookie_name}")
            return cookie_value

    return None


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
    from open_webui.utils.misc import remove_details_with_reasoning

    # Filter reasoning content from the result for title generation
    filtered_result = remove_details_with_reasoning(result)

    title_prompt = f"""Create a concise, 3-5 word title with an emoji for this conversation:

User: {request.query}
Assistant: {filtered_result[:500]}...

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
        except Exception:
            pass

        try:
            tags = await _generate_tags(
                request_data, request, result, user, task_model_id
            )
            if tags:
                await _emit_event(event_emitter, "chat:tags", tags, request.chat_id)
        except Exception:
            pass

    except Exception:
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
    request_data: Request,
    request: CrewMCPQuery,
    user=Depends(get_verified_user),
    auth_token: Optional[HTTPAuthorizationCredentials] = Depends(bearer_security),
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
        # Determine department from selected tools
        department = determine_department_from_tools(request.selected_tools)

        # Try to get a proper Microsoft Graph token for SharePoint OBO flow
        user_jwt_token = await get_microsoft_graph_token_for_user(
            request_data, department
        )

        # Fallback to extracting any available token from OAuth2 proxy
        if not user_jwt_token:
            user_jwt_token = extract_user_token(request_data, auth_token)

        log.info(f"Running CrewAI query for user {user.id}: {request.query}")
        log.info(f"Selected tools: {request.selected_tools}")
        log.info(f"User token available for OBO flow: {bool(user_jwt_token)}")

        # Set user token in CrewAI manager for SharePoint OBO authentication
        # This works in both local (gracefully degraded) and K8s (full OAuth) environments
        if user_jwt_token and user_jwt_token != "user_token_placeholder":
            crew_mcp_manager.set_user_token(user_jwt_token)
            log.info("Successfully set user token for SharePoint OBO flow")
        else:
            log.warning(
                "No OAuth token available - falling back to application-only authentication"
            )

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
        log.info("Using intelligent crew with manager agent for routing")

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
                    except Exception:
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
                    except Exception:
                        # Don't let callback exceptions propagate
                        pass

                task.add_done_callback(handle_background_task_completion)

            except Exception:
                # Completely isolate any background task creation exceptions
                pass

        return CrewMCPResponse(result=result, tools_used=used_tools, success=True)

    except Exception as e:
        log.exception(f"Error running CrewAI query: {e}")
        return CrewMCPResponse(result="", tools_used=[], success=False, error=str(e))


@router.post("/multi")
async def run_multi_server_crew_query(
    request_data: Request,
    request: CrewMCPQuery,
    user=Depends(get_verified_user),
    auth_token: Optional[HTTPAuthorizationCredentials] = Depends(bearer_security),
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
        # Determine department from selected tools (default to MPO for multi-server queries)
        department = determine_department_from_tools(request.selected_tools)

        # Try to get a proper Microsoft Graph token for SharePoint OBO flow
        user_jwt_token = await get_microsoft_graph_token_for_user(
            request_data, department
        )

        # Fallback to extracting any available token from OAuth2 proxy
        if not user_jwt_token:
            user_jwt_token = extract_user_token(request_data, auth_token)

        log.info(
            f"Running CrewAI multi-server query for user {user.id}: {request.query}"
        )
        log.info(f"User token available for OBO flow: {bool(user_jwt_token)}")

        # Set user token in CrewAI manager for SharePoint OBO authentication
        if user_jwt_token and user_jwt_token != "user_token_placeholder":
            crew_mcp_manager.set_user_token(user_jwt_token)
            log.info("Successfully set user token for SharePoint OBO flow")
        else:
            log.warning(
                "No OAuth token available - falling back to application-only authentication"
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
