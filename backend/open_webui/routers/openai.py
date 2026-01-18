import asyncio
import copy
import hashlib
import json
import logging
import re
import time
from typing import Optional, List, Dict, Tuple

import aiohttp
from aiocache import cached
import requests

from azure.identity import DefaultAzureCredential, get_bearer_token_provider

from fastapi import Depends, HTTPException, Request, APIRouter
from fastapi.responses import (
    FileResponse,
    StreamingResponse,
    JSONResponse,
    PlainTextResponse,
)
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from open_webui.models.models import Models
from open_webui.config import (
    CACHE_DIR,
)
from open_webui.env import (
    MODELS_CACHE_TTL,
    AIOHTTP_CLIENT_SESSION_SSL,
    AIOHTTP_CLIENT_TIMEOUT,
    AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST,
    ENABLE_FORWARD_USER_INFO_HEADERS,
    BYPASS_MODEL_ACCESS_CONTROL,
)
from open_webui.models.users import UserModel

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS


from open_webui.utils.payload import (
    apply_model_params_to_body_openai,
    apply_system_prompt_to_body,
)
from open_webui.utils.misc import (
    convert_logit_bias_input_to_json,
    stream_chunks_handler,
)

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.rate_limiter import limiter, get_role_based_limit, get_write_operation_limit
from open_webui.utils.access_control import has_access
from open_webui.utils.headers import include_user_info_headers
from open_webui.utils.prompt_composer import compose_with_fallback
from open_webui.utils.tool_gating import (
    build_tool_catalog,
    build_tool_selection_system_prompt,
    parse_tool_selection_response,
    get_tool_prompts_by_commands,
    compose_stage2_system_prompt,
    ToolSelectionResponse,
)
from open_webui.utils.tool_inline_executor import build_tool_hints
from open_webui.utils.gemini_cache_manager import GeminiCacheManager


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["OPENAI"])


##########################################
#
# Pydantic Models
#
##########################################


class ChapterRecommendationResponse(BaseModel):
    """LLM response for chapter recommendation."""
    chapter_id: Optional[str] = Field(None, description="Recommended chapter ID (e.g., 'ch-5') or null")
    reasoning: Optional[str] = Field(None, description="Korean explanation (1-2 sentences)")


def _clean_schema_for_gemini(schema: dict) -> dict:
    """
    Remove unsupported fields from JSON schema for Gemini API.

    Gemini doesn't support: 'default', 'additionalProperties', 'title', 'anyOf'

    Args:
        schema: JSON schema dictionary

    Returns:
        Cleaned schema
    """
    if isinstance(schema, dict):
        # Handle anyOf pattern from Optional[T] → extract the non-null type
        if 'anyOf' in schema:
            any_of_list = schema['anyOf']
            if isinstance(any_of_list, list):
                # Find the non-null type schema
                non_null_schemas = [s for s in any_of_list if isinstance(s, dict) and s.get('type') != 'null']
                if non_null_schemas:
                    # Replace anyOf with the first non-null type
                    non_null_schema = non_null_schemas[0]
                    schema = {**schema, **non_null_schema}
                    del schema['anyOf']

        # Remove unsupported fields
        schema = {k: v for k, v in schema.items() if k not in ('default', 'additionalProperties', 'title')}

        # Recursively clean nested schemas
        for key, value in schema.items():
            if isinstance(value, dict):
                schema[key] = _clean_schema_for_gemini(value)
            elif isinstance(value, list):
                schema[key] = [_clean_schema_for_gemini(item) if isinstance(item, dict) else item for item in value]

    return schema


async def detect_chapter_from_conversation(chat_id: str, api_key: str) -> Optional[str]:
    """
    Use LLM to analyze chat history and recommend a chapter_id.

    Args:
        chat_id: Chat ID to analyze
        api_key: Gemini API key

    Returns:
        Recommended chapter_id or None
    """
    try:
        from open_webui.models.chats import Chats
        from open_webui.models.textbooks import TextbookChapters
        import google.generativeai as genai

        # Fetch chat
        chat = Chats.get_chat_by_id(chat_id)
        if not chat or chat.chapter_id:
            return None  # Skip if no chat or already has chapter

        # Extract conversation (user + assistant messages only)
        messages = chat.chat.get("history", {}).get("messages", {})
        if not messages:
            return None

        conversation = []
        for msg_id in sorted(messages.keys()):
            msg = messages[msg_id]
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ["user", "assistant"]:
                conversation.append(f"{role.upper()}: {content}")

        if not conversation:
            return None

        # Get all chapters (ID + Korean title)
        chapter_mappings = TextbookChapters.get_all_rag_store_mappings()
        chapter_list = "\n".join([
            f"- {ch_id}: {info['display_name']}"
            for ch_id, info in sorted(chapter_mappings.items())
        ])

        # Build prompt
        prompt = f"""다음 대화를 분석하고, 가장 관련이 깊은 공업수학 챕터를 추천하세요.

대화:
{chr(10).join(conversation[:10])}

챕터 목록:
{chapter_list}

중요:
- 명확한 챕터 관련 내용이 있을 때만 chapter_id 반환
- 일반 인사("안녕하세요"), 짧은 대화 → null 반환
- 수학 내용이지만 챕터 불명확 → null 반환
"""

        # Call Gemini with cleaned JSON schema
        genai.configure(api_key=api_key)

        # Convert Pydantic model to JSON schema and clean it
        json_schema = ChapterRecommendationResponse.model_json_schema()
        # Remove 'default', 'additionalProperties', 'title' fields (Gemini doesn't support them)
        json_schema = _clean_schema_for_gemini(json_schema)

        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": json_schema
            }
        )

        response = model.generate_content(prompt)
        result = ChapterRecommendationResponse.model_validate_json(response.text)

        # Log
        if result.chapter_id:
            log.info(f"[CHAPTER-AUTO] LLM: {result.chapter_id} for chat {chat_id}")
            log.info(f"[CHAPTER-AUTO] Why: {result.reasoning}")
        else:
            log.info(f"[CHAPTER-AUTO] LLM: No chapter for chat {chat_id}")

        # Validate
        if result.chapter_id and result.chapter_id in chapter_mappings:
            return result.chapter_id
        return None

    except Exception as e:
        log.error(f"[CHAPTER-AUTO] Error: {e}")
        return None


##########################################
#
# Utility functions
#
##########################################


async def send_get_request(url, key=None, user: UserModel = None):
    timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST)
    try:
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            headers = {
                **({"Authorization": f"Bearer {key}"} if key else {}),
            }

            if ENABLE_FORWARD_USER_INFO_HEADERS and user:
                headers = include_user_info_headers(headers, user)

            async with session.get(
                url,
                headers=headers,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as response:
                return await response.json()
    except Exception as e:
        # Handle connection error here
        log.error(f"Connection error: {e}")
        return None


async def cleanup_response(
    response: Optional[aiohttp.ClientResponse],
    session: Optional[aiohttp.ClientSession],
):
    if response:
        response.close()
    if session:
        await session.close()


def openai_reasoning_model_handler(payload):
    """
    Handle reasoning model specific parameters
    """
    if "max_tokens" in payload:
        # Convert "max_tokens" to "max_completion_tokens" for all reasoning models
        payload["max_completion_tokens"] = payload["max_tokens"]
        del payload["max_tokens"]

    # Handle system role conversion based on model type
    if payload["messages"][0]["role"] == "system":
        model_lower = payload["model"].lower()
        # Legacy models use "user" role instead of "system"
        if model_lower.startswith("o1-mini") or model_lower.startswith("o1-preview"):
            payload["messages"][0]["role"] = "user"
        else:
            payload["messages"][0]["role"] = "developer"

    return payload


async def get_headers_and_cookies(
    request: Request,
    url,
    key=None,
    config=None,
    metadata: Optional[dict] = None,
    user: UserModel = None,
):
    cookies = {}
    headers = {
        "Content-Type": "application/json",
        **(
            {
                "HTTP-Referer": "https://openwebui.com/",
                "X-Title": "Open WebUI",
            }
            if "openrouter.ai" in url
            else {}
        ),
    }

    if ENABLE_FORWARD_USER_INFO_HEADERS and user:
        headers = include_user_info_headers(headers, user)
        if metadata and metadata.get("chat_id"):
            headers["X-OpenWebUI-Chat-Id"] = metadata.get("chat_id")

    token = None
    auth_type = config.get("auth_type")

    if auth_type == "bearer" or auth_type is None:
        # Default to bearer if not specified
        token = f"{key}"
    elif auth_type == "none":
        token = None
    elif auth_type == "session":
        cookies = request.cookies
        token = request.state.token.credentials
    elif auth_type == "system_oauth":
        cookies = request.cookies

        oauth_token = None
        try:
            if request.cookies.get("oauth_session_id", None):
                oauth_token = await request.app.state.oauth_manager.get_oauth_token(
                    user.id,
                    request.cookies.get("oauth_session_id", None),
                )
        except Exception as e:
            log.error(f"Error getting OAuth token: {e}")

        if oauth_token:
            token = f"{oauth_token.get('access_token', '')}"

    elif auth_type in ("azure_ad", "microsoft_entra_id"):
        token = get_microsoft_entra_id_access_token()

    if token:
        headers["Authorization"] = f"Bearer {token}"

    if config.get("headers") and isinstance(config.get("headers"), dict):
        headers = {**headers, **config.get("headers")}

    return headers, cookies


def get_microsoft_entra_id_access_token():
    """
    Get Microsoft Entra ID access token using DefaultAzureCredential for Azure OpenAI.
    Returns the token string or None if authentication fails.
    """
    try:
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
        )
        return token_provider()
    except Exception as e:
        log.error(f"Error getting Microsoft Entra ID access token: {e}")
        return None


async def make_gemini_llm_call(
    request_url: str,
    headers: dict,
    cookies: dict,
    base_payload: dict,
    system_prompt: str,
    query: str,
) -> dict:
    """
    Make a non-streaming LLM call to Gemini backend for tool gating Stage 1.

    Args:
        request_url: The Gemini API endpoint URL
        headers: Request headers
        cookies: Request cookies
        base_payload: Base payload dict (will be modified with system prompt)
        system_prompt: System prompt to use
        query: User query (already in messages)

    Returns:
        dict with 'success' and 'text' (or 'error') keys
    """
    try:
        # Create a copy of the payload for Stage 1
        payload = copy.deepcopy(base_payload)

        # Ensure stream is False for Stage 1
        payload["stream"] = False

        # Update system prompt in messages
        if payload.get("messages") and len(payload["messages"]) > 0:
            if payload["messages"][0].get("role") == "system":
                payload["messages"][0]["content"] = system_prompt
            else:
                # Insert system message at the beginning
                payload["messages"].insert(0, {
                    "role": "system",
                    "content": system_prompt
                })

        payload_json = json.dumps(payload)

        log.info(f"[OPENAI-TOOL-GATING] Making LLM call to: {request_url}")
        log.info(f"[OPENAI-TOOL-GATING] System prompt length: {len(system_prompt)} chars")

        async with aiohttp.ClientSession(
            trust_env=True,
            timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
        ) as session:
            async with session.post(
                request_url,
                data=payload_json,
                headers=headers,
                cookies=cookies,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as r:
                if r.status >= 400:
                    error_text = await r.text()
                    log.error(f"[OPENAI-TOOL-GATING] LLM call failed: {r.status} - {error_text}")
                    return {"success": False, "error": f"HTTP {r.status}: {error_text}"}

                response = await r.json()

                # Extract text from OpenAI-compatible response format
                text = ""
                if response.get("choices") and len(response["choices"]) > 0:
                    choice = response["choices"][0]
                    if choice.get("message"):
                        text = choice["message"].get("content", "")
                    elif choice.get("text"):
                        text = choice["text"]

                log.info(f"[OPENAI-TOOL-GATING] LLM response received: {len(text)} chars")
                return {"success": True, "text": text}

    except Exception as e:
        log.error(f"[OPENAI-TOOL-GATING] LLM call exception: {e}")
        return {"success": False, "error": str(e)}


async def make_gemini_native_call_with_cache(
    api_key: str,
    model: str,
    system_prompt: str,
    query: str = None,
    contents: List[Dict] = None,
    cache_stage: Optional[str] = None,
    cache_manager: Optional[GeminiCacheManager] = None,
    temperature: float = 0.2,
    cache_strategy: str = "auto",
    response_schema: Optional[type] = None,
) -> dict:
    """
    Make a non-streaming LLM call using Gemini native API with caching support.

    Args:
        api_key: Gemini API key
        model: Model ID (e.g., "gemini-2.5-flash")
        system_prompt: System prompt to use
        query: User query (single turn). For backward compatibility.
        contents: Gemini-format conversation history.
                 If provided, this takes precedence over query.
                 Format: [{"role": "user", "parts": [{"text": "..."}]}, ...]
        cache_stage: Optional cache stage ("gating" or "execution")
        cache_manager: Optional GeminiCacheManager instance
        temperature: Sampling temperature
        cache_strategy: Cache strategy - "auto" | "force" | "off" (default: "auto")
        response_schema: Optional Pydantic model for structured JSON output.
                        If provided, response will be in JSON format matching the schema.

    Returns:
        dict with 'success' and 'text' (or 'error') keys
    """
    try:
        from google import genai
        from google.genai import types

        log.info(f"[GEMINI-NATIVE-CACHE] Making LLM call with native API")
        log.info(f"  Model: {model}")
        log.info(f"  System prompt length: {len(system_prompt)} chars")
        log.info(f"  Cache stage: {cache_stage}")
        log.info(f"  Cache manager: {'SET' if cache_manager else 'NONE'}")

        # Create Gemini client
        client = genai.Client(api_key=api_key)

        # Get or create cache if cache_stage provided
        cached_content_name = None
        if cache_stage and cache_manager and system_prompt:
            cached_content_name = cache_manager.get_or_create_cache(
                model_id=model,
                system_prompt=system_prompt,
                stage=cache_stage,
                cache_strategy=cache_strategy
            )
            if cached_content_name:
                log.info(f"[GEMINI-NATIVE-CACHE] Using global cache: {cached_content_name}")

        # Build config
        config = types.GenerateContentConfig(
            temperature=temperature,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=False,          # Enable automatic function calling
                maximum_remote_calls=5  # Limit to 5 calls (default is 10)
            )
        )

        # Add response_schema if provided (for structured JSON output)
        if response_schema:
            from pydantic import BaseModel
            from open_webui.utils.gemini_rag import remove_additional_properties

            config.response_mime_type = "application/json"
            # Convert Pydantic model to JSON schema and remove additionalProperties
            # (Gemini API doesn't support additionalProperties field)
            if isinstance(response_schema, type) and issubclass(response_schema, BaseModel):
                json_schema = response_schema.model_json_schema()
                json_schema = remove_additional_properties(json_schema)
                config.response_schema = json_schema
                log.info(f"[RESPONSE SCHEMA] ✅ Using schema: {response_schema.__name__} (cleaned)")
            else:
                config.response_schema = response_schema
                log.info(f"[RESPONSE SCHEMA] ✅ Using schema: {response_schema}")

        # Use cached content OR system_instruction
        if cached_content_name:
            config.cached_content = cached_content_name
        elif system_prompt:
            config.system_instruction = system_prompt

        # Determine contents to use: contents parameter OR convert query to single-turn
        if contents:
            api_contents = contents
            log.info(f"[GEMINI-NATIVE-CACHE] Using provided contents (multi-turn): {len(contents)} messages")
        elif query:
            api_contents = query
            log.info(f"[GEMINI-NATIVE-CACHE] Using query (single-turn)")
        else:
            raise ValueError("Either 'query' or 'contents' must be provided")

        # Call Gemini native API
        response = client.models.generate_content(
            model=model,
            contents=api_contents,
            config=config
        )

        # Extract text from native API response
        text = response.text if hasattr(response, 'text') else ""

        log.info(f"[GEMINI-NATIVE-CACHE] Response received: {len(text)} chars")
        return {"success": True, "text": text}

    except Exception as e:
        log.error(f"[GEMINI-NATIVE-CACHE] Call exception: {e}")
        log.exception(e)
        return {"success": False, "error": str(e)}


def get_or_create_gemini_cache_manager(request: Request, api_key: str) -> GeminiCacheManager:
    """
    Get or create a GeminiCacheManager for the given API key.
    Cache managers are stored in app.state per API key.

    Args:
        request: FastAPI request object
        api_key: Gemini API key

    Returns:
        GeminiCacheManager instance
    """
    from google import genai

    # Initialize cache managers dict if not exists
    if not hasattr(request.app.state, "gemini_cache_managers"):
        request.app.state.gemini_cache_managers = {}

    # Create cache manager if not exists for this API key
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
    if key_hash not in request.app.state.gemini_cache_managers:
        log.info(f"[CACHE] Creating new GeminiCacheManager for key: {key_hash}")
        client = genai.Client(api_key=api_key)
        request.app.state.gemini_cache_managers[key_hash] = GeminiCacheManager(client)

    return request.app.state.gemini_cache_managers[key_hash]


def filter_code_blocks(text: str) -> str:
    """
    Filter out code blocks from chat history to prevent Gemini from being confused by
    previous tool execution results.

    CRITICAL: Replaces tool outputs with SYSTEM LOG style (not JSON) to prevent format pollution.

    Strategy (Best Practice for System Prompt Caching):
    1. Extract key info from tool outputs (type, expression, field, etc.)
    2. Replace ENTIRE TAGS (not just content) with system log format
    3. Model sees it as "system record" not "my output pattern"

    Example:
        Before: <graph-spec>{"type": "function_2d", "expression": "sin(x)", ...12000 chars...}</graph-spec>
        After:
        [Tool Execution Log]
        - Type: function_2d
        - Expr: sin(x)
        (Data Omitted)

    Benefits:
    - Token savings: 12k → 100 chars (99% reduction)
    - Context preserved: Model remembers what was generated
    - Format pollution prevented: No JSON/tags in history = model can't copy wrong format
    - In-Context Learning preserved: Model sees "system used tool" but not output pattern

    Args:
        text: Original text with potential code blocks

    Returns:
        Text with tool outputs replaced by system log summaries
    """
    import re
    import json

    def summarize_tool_output(tag_name: str, json_content: str) -> str:
        """
        Extract minimal key info from tool JSON.

        CRITICAL: Keep format EXTREMELY simple to avoid model copying it.
        No "Log", no "Execution", no structured format that looks like output.
        Just a tiny note that graph was created.
        """
        try:
            data = json.loads(json_content.strip())

            # Extract only type (minimal info)
            graph_type = data.get("type", "graph")

            # Ultra-minimal format: just a brief parenthetical note
            return f"(그래프: {graph_type})"

        except (json.JSONDecodeError, Exception):
            # Parsing failed
            return "(그래프 생성됨)"

    # Replace tool markers (ENTIRE TAG) with system log summaries
    # <tool-name>...JSON...</tool-name> → [Tool Execution Log]\n...
    def replace_tool_marker(match):
        tag_name = match.group(1)
        content = match.group(2)
        return summarize_tool_output(tag_name, content)

    text = re.sub(r'<([a-z-]+)>([\s\S]*?)</\1>', replace_tool_marker, text)

    # Remove fenced code blocks (```...```)
    text = re.sub(r'```[\s\S]*?```', '', text)

    # Clean up multiple consecutive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text


def convert_openai_messages_to_gemini_contents(messages: list, filter_code: bool = True) -> list:
    """
    Convert OpenAI-format messages to Gemini contents format with multimodal support.

    OpenAI format:
        [
            {"role": "system", "content": "..."},  # Excluded (use system_instruction)
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": [
                {"type": "text", "text": "What's in this image?"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
            ]}
        ]

    Gemini format:
        [
            {"role": "user", "parts": [{"text": "Hello"}]},
            {"role": "model", "parts": [{"text": "Hi there"}]},
            {"role": "user", "parts": [
                {"text": "What's in this image?"},
                {"inline_data": {"mime_type": "image/png", "data": "..."}}
            ]}
        ]

    Args:
        messages: OpenAI-format messages list
        filter_code: Whether to filter code blocks from content (default: True)

    Returns:
        Gemini-format contents list
    """
    contents = []

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")

        # Skip system messages (handled by system_instruction)
        if role == "system":
            continue

        # Convert role: assistant → model
        gemini_role = "model" if role == "assistant" else role

        # Build parts array (multimodal)
        parts = []

        if isinstance(content, str):
            # Simple text content
            text = content
            if filter_code and gemini_role == "model":
                text = filter_code_blocks(text)
            if text:
                parts.append({"text": text})

        elif isinstance(content, list):
            # Multimodal content - handle text, images, and other types
            for part in content:
                if not isinstance(part, dict):
                    continue

                part_type = part.get("type")

                if part_type == "text":
                    # Text part
                    text = part.get("text", "")
                    if filter_code and gemini_role == "model":
                        text = filter_code_blocks(text)
                    if text:
                        parts.append({"text": text})

                elif part_type == "image_url":
                    # Image part - convert to Gemini format
                    image_url_data = part.get("image_url", {})
                    url = image_url_data.get("url", "")

                    if url.startswith("data:"):
                        # Data URL format: data:image/png;base64,iVBORw0KGgo...
                        try:
                            # Extract mime type and base64 data
                            match = re.match(r'data:([^;]+);base64,(.+)', url)
                            if match:
                                mime_type = match.group(1)
                                base64_data = match.group(2)

                                # Add inline_data part for Gemini
                                parts.append({
                                    "inline_data": {
                                        "mime_type": mime_type,
                                        "data": base64_data
                                    }
                                })
                                log.info(f"[GEMINI-MULTIMODAL] Converted image_url to inline_data: {mime_type}")
                            else:
                                log.warning(f"[GEMINI-MULTIMODAL] Malformed data URL, skipping image")
                        except Exception as e:
                            log.error(f"[GEMINI-MULTIMODAL] Failed to parse data URL: {e}")

                    elif url.startswith("http"):
                        # HTTP URL - not yet supported
                        log.warning(f"[GEMINI-MULTIMODAL] HTTP image URLs not yet supported: {url[:100]}...")

                    else:
                        log.warning(f"[GEMINI-MULTIMODAL] Unknown image URL format: {url[:50]}...")

        else:
            # Fallback to string conversion
            text = str(content)
            if text:
                parts.append({"text": text})

        # Add to contents if we have parts
        if parts:
            contents.append({
                "role": gemini_role,
                "parts": parts
            })

    return contents


def extract_chapter_from_citations(citations: List[Dict], chapter_mappings: Dict) -> Optional[Tuple[str, float]]:
    """
    Extract most likely chapter_id from citations.

    Args:
        citations: List of citation dicts with 'source' field
        chapter_mappings: Dict mapping chapter_id → {"store_name": ..., "display_name": ...}

    Returns:
        Tuple of (chapter_id, confidence) or None
        confidence = ratio of citations from the detected chapter (0.0-1.0)
    """
    import re

    if not citations or len(citations) == 0:
        return None

    # Reverse mapping: store_name → chapter_id
    store_to_chapter = {
        info["store_name"]: ch_id
        for ch_id, info in chapter_mappings.items()
    }

    # Count citations by chapter
    chapter_counts = {}
    for citation in citations:
        source = citation.get("source", "")

        # Strategy 1: Try to match source to store_name (for multi-store setups)
        matched = False
        for store_name, chapter_id in store_to_chapter.items():
            if store_name in source:
                chapter_counts[chapter_id] = chapter_counts.get(chapter_id, 0) + 1
                matched = True
                break

        # Strategy 2: If no store matched, try to extract chapter ID from filename (for unified store)
        # Look for patterns like "ch-5", "ch-10", "chapter-5", "chapter-10" in the source
        if not matched:
            # Try pattern: ch-N or ch-NN
            match = re.search(r'ch-(\d+)', source, re.IGNORECASE)
            if match:
                chapter_num = match.group(1)
                chapter_id = f"ch-{chapter_num}"

                # Validate chapter_id exists in chapter_mappings
                if chapter_id in chapter_mappings:
                    chapter_counts[chapter_id] = chapter_counts.get(chapter_id, 0) + 1
                    matched = True
                    log.debug(f"[CHAPTER-AUTO] Extracted chapter {chapter_id} from source: {source}")

            # Try alternative pattern: chapter-N or chapter-NN
            if not matched:
                match = re.search(r'chapter[-_]?(\d+)', source, re.IGNORECASE)
                if match:
                    chapter_num = match.group(1)
                    chapter_id = f"ch-{chapter_num}"

                    if chapter_id in chapter_mappings:
                        chapter_counts[chapter_id] = chapter_counts.get(chapter_id, 0) + 1
                        log.debug(f"[CHAPTER-AUTO] Extracted chapter {chapter_id} from source: {source}")

    if not chapter_counts:
        log.warning("[CHAPTER-AUTO] No chapter IDs could be extracted from citations")
        return None

    # Find chapter with most citations
    total_citations = len(citations)
    top_chapter = max(chapter_counts.items(), key=lambda x: x[1])
    chapter_id, count = top_chapter
    confidence = count / total_citations

    log.info(f"[CHAPTER-AUTO] Detected chapter: {chapter_id} ({count}/{total_citations} = {confidence:.2%})")

    return (chapter_id, confidence)


async def handle_gemini_native_request(
    request: Request,
    api_key: str,
    model_id: str,
    payload: dict,
    final_system: Optional[str],
    cache_stage: Optional[str] = None,
    metadata: Optional[dict] = None,
):
    """
    Handle chat completion request using unified Gemini service.

    This function routes all Gemini requests to GeminiRAGService for unified handling.
    Regular chat (no RAG) is handled by passing empty store_names.

    Args:
        request: FastAPI request object
        api_key: Gemini API key
        model_id: Model ID (e.g., "gemini-2.5-flash")
        payload: OpenAI-format payload with messages
        final_system: Final system prompt (may be cached)
        cache_stage: Optional cache stage ("execution", "gating", etc.)
        metadata: Optional metadata dict (for inline tool execution)

    Returns:
        OpenAI-compatible response dict or StreamingResponse
    """
    try:
        from open_webui.utils.gemini_rag import get_gemini_rag_service
        from open_webui.utils.misc import openai_chat_chunk_message_template

        log.info("=" * 80)
        log.info("[GEMINI-NATIVE] Routing to unified GeminiRAGService")
        log.info(f"  Model: {model_id}")
        log.info(f"  Cache stage: {cache_stage}")
        log.info(f"  System prompt length: {len(final_system) if final_system else 0} chars")
        log.info("=" * 80)

        # Convert OpenAI messages to Gemini contents (preserves conversation history)
        messages = payload.get("messages", [])
        gemini_contents = convert_openai_messages_to_gemini_contents(messages)

        if not gemini_contents:
            return {
                "error": {
                    "message": "No valid messages found in request",
                    "type": "invalid_request_error",
                    "code": "no_messages"
                }
            }

        log.info(f"[GEMINI-NATIVE] Converted {len(messages)} OpenAI messages to {len(gemini_contents)} Gemini contents")
        if gemini_contents:
            last_msg = gemini_contents[-1]
            if last_msg.get("parts"):
                preview = last_msg["parts"][0].get("text", "")[:100]
                log.info(f"[GEMINI-NATIVE] Last message preview: {preview}...")

        # Store metadata in request state for middleware access
        if metadata:
            if not hasattr(request.state, "_metadata"):
                request.state._metadata = {}
            request.state._metadata.update(metadata)
            log.info(f"[GEMINI-NATIVE] Metadata stored in request.state: {list(metadata.keys())}")

        # Get unified Gemini service
        service = get_gemini_rag_service(api_key)

        # Extract temperature and streaming flag from payload
        temperature = payload.get("temperature", 0.2)
        stream = payload.get("stream", False)

        # ============================================================
        # Phase 3: Determine RAG store_names based on chapter_id
        # ============================================================
        # Get chat_id and chapter_id from metadata (if available)
        chat_id = metadata.get("chat_id") if metadata else None
        chapter_id = metadata.get("chapter_id") if metadata else None
        task = metadata.get("task") if metadata else None

        # Determine RAG store_names based on chapter_id
        store_names = []
        used_default_chapter = False

        # Skip RAG for utility requests (title generation, tags, emoji, etc.)
        # These requests analyze existing conversation content and don't need document retrieval
        utility_tasks = ["title_generation", "tags", "emoji"]
        if task in utility_tasks:
            log.info(f"[CHAPTER-AUTO] Skipping RAG for utility task: {task}")
            # Continue with empty store_names (no RAG)
        elif chat_id and not chapter_id:
            # Chat exists but no chapter_id → check global default RAG store
            try:
                # Get global default RAG store from config
                try:
                    default_store_name = request.app.state.config.DEFAULT_RAG_STORE_NAME
                except AttributeError:
                    default_store_name = None

                if default_store_name:
                    # Use default RAG store (not tied to chapters)
                    store_names = [default_store_name]
                    used_default_chapter = True
                    log.info(f"[CHAPTER-AUTO] Using default RAG store {default_store_name} for chat {chat_id}")
                else:
                    log.info(f"[CHAPTER-AUTO] Chat {chat_id} has no chapter_id and no default RAG store configured")
            except Exception as e:
                log.error(f"[CHAPTER-AUTO] Error determining default RAG store: {e}")
                log.exception(e)

        elif chapter_id:
            # Chapter explicitly set → use its store
            try:
                from open_webui.models.textbooks import TextbookChapters
                store_name = TextbookChapters.get_rag_store(chapter_id)
                if store_name:
                    store_names = [store_name]
                    log.info(f"[CHAPTER-AUTO] Using explicit chapter {chapter_id} (store: {store_name})")
                else:
                    log.warning(f"[CHAPTER-AUTO] Chapter {chapter_id} has no RAG store")
            except Exception as e:
                log.error(f"[CHAPTER-AUTO] Error getting RAG store for chapter {chapter_id}: {e}")
                log.exception(e)

        # If no stores determined, use empty list (current behavior - no RAG)
        if not store_names:
            log.info("[CHAPTER-AUTO] No RAG stores configured, using regular chat mode")

        # IMPORTANT: Disable caching when using RAG stores
        # Gemini API does not allow cached_content with tools (FileSearch)
        if store_names:
            cache_stage = None
            log.info("[CHAPTER-AUTO] Disabling cache when using RAG stores")

            # Force FileSearch usage with explicit instruction
            # This helps AFC (Automatic Function Calling) understand it should search documents
            # even when conversation history might seem sufficient
            final_system += "\n\n⚠️ CRITICAL INSTRUCTION: You MUST search the provided document store to ground your responses in textbook content. Even when answering follow-up questions or meta-questions about previous responses, ALWAYS use the document store to verify and supplement your answers with accurate, authoritative textbook information. Do not rely solely on conversation history."
            log.info("[CHAPTER-AUTO] Added explicit FileSearch instruction to system prompt")

        # Handle streaming requests
        if stream:
            log.info("[GEMINI-NATIVE] Streaming mode enabled")

            async def stream_generator():
                """Generate OpenAI-compatible SSE chunks from Gemini stream"""
                try:
                    citations = []

                    # Call streaming service with conversation history
                    # NOTE: force_tool_use only works with function_declarations, not with FileSearch
                    # We rely on system_instruction to encourage FileSearch usage instead
                    async for chunk_text in service.query_stream(
                        contents=gemini_contents,  # Full conversation history
                        store_names=store_names,  # RAG stores based on chapter_id or default
                        model=model_id,
                        temperature=temperature,
                        system_instruction=final_system,
                        cache_stage=cache_stage
                    ):
                        # Check for citation marker
                        if chunk_text.startswith("\n__CITATIONS__:"):
                            # Extract citations from marker
                            try:
                                citation_json = chunk_text.replace("\n__CITATIONS__:", "")
                                citations = json.loads(citation_json)
                                log.info(f"[CHAPTER-AUTO] Received {len(citations)} citations from RAG stream")
                                # Don't send this marker to the client
                                continue
                            except Exception as e:
                                log.error(f"[CHAPTER-AUTO] Failed to parse citations: {e}")

                        # Format as OpenAI chunk
                        chunk_data = openai_chat_chunk_message_template(
                            model=model_id,
                            content=chunk_text
                        )
                        yield f"data: {json.dumps(chunk_data)}\n\n"

                    # ============================================================
                    # Auto-chapter assignment (streaming mode) - LLM-based
                    # ============================================================
                    if chat_id and not metadata.get("chapter_id"):
                        try:
                            from open_webui.models.chats import Chats

                            # Check if chat still has no chapter
                            chat = Chats.get_chat_by_id(chat_id)
                            if chat and not chat.chapter_id:
                                # Detect using LLM
                                detected = await detect_chapter_from_conversation(chat_id, api_key)

                                if detected:
                                    updated = Chats.update_chat_chapter_id_by_id(chat_id, detected)
                                    if updated:
                                        log.info(f"[CHAPTER-AUTO] ✅ Assigned {detected} to chat {chat_id}")

                                        # Emit socket event to notify frontend
                                        try:
                                            from open_webui.socket.main import sio
                                            await sio.emit(
                                                "chat:chapter:updated",
                                                {
                                                    "chat_id": chat_id,
                                                    "chapter_id": detected
                                                },
                                                room=f"user:{chat.user_id}"
                                            )
                                            log.info(f"[CHAPTER-AUTO] 🔔 Notified user {chat.user_id} via socket")
                                        except Exception as socket_error:
                                            log.error(f"[CHAPTER-AUTO] Socket emit failed: {socket_error}")
                        except Exception as e:
                            log.error(f"[CHAPTER-AUTO] Error: {e}")

                    # Send final chunk with finish_reason
                    final_chunk = openai_chat_chunk_message_template(
                        model=model_id,
                        content=None  # No content = finish
                    )
                    yield f"data: {json.dumps(final_chunk)}\n\n"

                    # Send [DONE] marker
                    yield "data: [DONE]\n\n"

                except Exception as e:
                    log.error(f"[GEMINI-NATIVE] Streaming error: {e}")
                    log.exception(e)
                    error_chunk = {
                        "error": {
                            "message": str(e),
                            "type": "api_error",
                            "code": "streaming_error"
                        }
                    }
                    yield f"data: {json.dumps(error_chunk)}\n\n"
                    yield "data: [DONE]\n\n"

            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )

        # Non-streaming mode
        else:
            # Call unified service with conversation history
            # CRITICAL: Run in thread pool to avoid blocking event loop (multi-user support)
            # NOTE: force_tool_use only works with function_declarations, not with FileSearch
            # We rely on system_instruction to encourage FileSearch usage instead
            import asyncio
            result = await asyncio.to_thread(
                service.query,
                contents=gemini_contents,  # Full conversation history
                store_names=store_names,  # RAG stores based on chapter_id or default
                model=model_id,
                temperature=temperature,
                system_instruction=final_system,
                cache_stage=cache_stage
            )

            if not result.get("success"):
                return {
                    "error": {
                        "message": result.get("error", "Unknown error"),
                        "type": "api_error",
                        "code": "gemini_service_error"
                    }
                }

            text = result.get("text", "")
            log.info(f"[GEMINI-NATIVE] Response received: {len(text)} chars")

            # ============================================================
            # Auto-chapter assignment (non-streaming mode) - LLM-based
            # ============================================================
            if chat_id and not metadata.get("chapter_id"):
                try:
                    from open_webui.models.chats import Chats

                    # Check if chat still has no chapter
                    chat = Chats.get_chat_by_id(chat_id)
                    if chat and not chat.chapter_id:
                        # Detect using LLM
                        detected = await detect_chapter_from_conversation(chat_id, api_key)

                        if detected:
                            updated = Chats.update_chat_chapter_id_by_id(chat_id, detected)
                            if updated:
                                log.info(f"[CHAPTER-AUTO] ✅ Assigned {detected} to chat {chat_id}")

                                # Emit socket event to notify frontend
                                try:
                                    from open_webui.socket.main import sio
                                    await sio.emit(
                                        "chat:chapter:updated",
                                        {
                                            "chat_id": chat_id,
                                            "chapter_id": detected
                                        },
                                        room=f"user:{chat.user_id}"
                                    )
                                    log.info(f"[CHAPTER-AUTO] 🔔 Notified user {chat.user_id} via socket")
                                except Exception as socket_error:
                                    log.error(f"[CHAPTER-AUTO] Socket emit failed: {socket_error}")
                except Exception as e:
                    log.error(f"[CHAPTER-AUTO] Error: {e}")

            # Convert to OpenAI format
            return {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model_id,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": text
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 0,  # Gemini doesn't provide this
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            }

    except Exception as e:
        log.error(f"[GEMINI-NATIVE] Request handling error: {e}")
        log.exception(e)
        return {
            "error": {
                "message": str(e),
                "type": "api_error",
                "code": "gemini_native_error"
            }
        }


##########################################
#
# API routes
#
##########################################

router = APIRouter()


@router.get("/config")
@get_role_based_limit
async def get_config(request: Request, user=Depends(get_admin_user)):
    return {
        "ENABLE_OPENAI_API": request.app.state.config.ENABLE_OPENAI_API,
        "OPENAI_API_BASE_URLS": request.app.state.config.OPENAI_API_BASE_URLS,
        "OPENAI_API_KEYS": request.app.state.config.OPENAI_API_KEYS,
        "OPENAI_API_CONFIGS": request.app.state.config.OPENAI_API_CONFIGS,
    }


class OpenAIConfigForm(BaseModel):
    ENABLE_OPENAI_API: Optional[bool] = None
    OPENAI_API_BASE_URLS: list[str]
    OPENAI_API_KEYS: list[str]
    OPENAI_API_CONFIGS: dict


@router.post("/config/update")
@get_write_operation_limit
async def update_config(
    request: Request, form_data: OpenAIConfigForm, user=Depends(get_admin_user)
):
    request.app.state.config.ENABLE_OPENAI_API = form_data.ENABLE_OPENAI_API
    request.app.state.config.OPENAI_API_BASE_URLS = form_data.OPENAI_API_BASE_URLS
    request.app.state.config.OPENAI_API_KEYS = form_data.OPENAI_API_KEYS

    # Check if API KEYS length is same than API URLS length
    if len(request.app.state.config.OPENAI_API_KEYS) != len(
        request.app.state.config.OPENAI_API_BASE_URLS
    ):
        if len(request.app.state.config.OPENAI_API_KEYS) > len(
            request.app.state.config.OPENAI_API_BASE_URLS
        ):
            request.app.state.config.OPENAI_API_KEYS = (
                request.app.state.config.OPENAI_API_KEYS[
                    : len(request.app.state.config.OPENAI_API_BASE_URLS)
                ]
            )
        else:
            request.app.state.config.OPENAI_API_KEYS += [""] * (
                len(request.app.state.config.OPENAI_API_BASE_URLS)
                - len(request.app.state.config.OPENAI_API_KEYS)
            )

    request.app.state.config.OPENAI_API_CONFIGS = form_data.OPENAI_API_CONFIGS

    # Remove the API configs that are not in the API URLS
    keys = list(map(str, range(len(request.app.state.config.OPENAI_API_BASE_URLS))))
    request.app.state.config.OPENAI_API_CONFIGS = {
        key: value
        for key, value in request.app.state.config.OPENAI_API_CONFIGS.items()
        if key in keys
    }

    return {
        "ENABLE_OPENAI_API": request.app.state.config.ENABLE_OPENAI_API,
        "OPENAI_API_BASE_URLS": request.app.state.config.OPENAI_API_BASE_URLS,
        "OPENAI_API_KEYS": request.app.state.config.OPENAI_API_KEYS,
        "OPENAI_API_CONFIGS": request.app.state.config.OPENAI_API_CONFIGS,
    }


@router.post("/audio/speech")
@get_write_operation_limit
async def speech(request: Request, user=Depends(get_verified_user)):
    idx = None
    try:
        idx = request.app.state.config.OPENAI_API_BASE_URLS.index(
            "https://api.openai.com/v1"
        )

        body = await request.body()
        name = hashlib.sha256(body).hexdigest()

        SPEECH_CACHE_DIR = CACHE_DIR / "audio" / "speech"
        SPEECH_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        file_path = SPEECH_CACHE_DIR.joinpath(f"{name}.mp3")
        file_body_path = SPEECH_CACHE_DIR.joinpath(f"{name}.json")

        # Check if the file already exists in the cache
        if file_path.is_file():
            return FileResponse(file_path)

        url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
        key = request.app.state.config.OPENAI_API_KEYS[idx]
        api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
            str(idx),
            request.app.state.config.OPENAI_API_CONFIGS.get(url, {}),  # Legacy support
        )

        headers, cookies = await get_headers_and_cookies(
            request, url, key, api_config, user=user
        )

        r = None
        try:
            r = requests.post(
                url=f"{url}/audio/speech",
                data=body,
                headers=headers,
                cookies=cookies,
                stream=True,
            )

            r.raise_for_status()

            # Save the streaming content to a file
            with open(file_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

            with open(file_body_path, "w") as f:
                json.dump(json.loads(body.decode("utf-8")), f)

            # Return the saved file
            return FileResponse(file_path)

        except Exception as e:
            log.exception(e)

            detail = None
            if r is not None:
                try:
                    res = r.json()
                    if "error" in res:
                        detail = f"External: {res['error']}"
                except Exception:
                    detail = f"External: {e}"

            raise HTTPException(
                status_code=r.status_code if r else 500,
                detail=detail if detail else "Open WebUI: Server Connection Error",
            )

    except ValueError:
        raise HTTPException(status_code=401, detail=ERROR_MESSAGES.OPENAI_NOT_FOUND)


async def get_all_models_responses(request: Request, user: UserModel) -> list:
    if not request.app.state.config.ENABLE_OPENAI_API:
        return []

    # Check if API KEYS length is same than API URLS length
    num_urls = len(request.app.state.config.OPENAI_API_BASE_URLS)
    num_keys = len(request.app.state.config.OPENAI_API_KEYS)

    if num_keys != num_urls:
        # if there are more keys than urls, remove the extra keys
        if num_keys > num_urls:
            new_keys = request.app.state.config.OPENAI_API_KEYS[:num_urls]
            request.app.state.config.OPENAI_API_KEYS = new_keys
        # if there are more urls than keys, add empty keys
        else:
            request.app.state.config.OPENAI_API_KEYS += [""] * (num_urls - num_keys)

    request_tasks = []
    for idx, url in enumerate(request.app.state.config.OPENAI_API_BASE_URLS):
        if (str(idx) not in request.app.state.config.OPENAI_API_CONFIGS) and (
            url not in request.app.state.config.OPENAI_API_CONFIGS  # Legacy support
        ):
            request_tasks.append(
                send_get_request(
                    f"{url}/models",
                    request.app.state.config.OPENAI_API_KEYS[idx],
                    user=user,
                )
            )
        else:
            api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
                str(idx),
                request.app.state.config.OPENAI_API_CONFIGS.get(
                    url, {}
                ),  # Legacy support
            )

            enable = api_config.get("enable", True)
            model_ids = api_config.get("model_ids", [])

            if enable:
                if len(model_ids) == 0:
                    request_tasks.append(
                        send_get_request(
                            f"{url}/models",
                            request.app.state.config.OPENAI_API_KEYS[idx],
                            user=user,
                        )
                    )
                else:
                    model_list = {
                        "object": "list",
                        "data": [
                            {
                                "id": model_id,
                                "name": model_id,
                                "owned_by": "openai",
                                "openai": {"id": model_id},
                                "urlIdx": idx,
                            }
                            for model_id in model_ids
                        ],
                    }

                    request_tasks.append(
                        asyncio.ensure_future(asyncio.sleep(0, model_list))
                    )
            else:
                request_tasks.append(asyncio.ensure_future(asyncio.sleep(0, None)))

    responses = await asyncio.gather(*request_tasks)

    for idx, response in enumerate(responses):
        if response:
            url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
            api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
                str(idx),
                request.app.state.config.OPENAI_API_CONFIGS.get(
                    url, {}
                ),  # Legacy support
            )

            connection_type = api_config.get("connection_type", "external")
            prefix_id = api_config.get("prefix_id", None)
            tags = api_config.get("tags", [])

            model_list = (
                response if isinstance(response, list) else response.get("data", [])
            )
            if not isinstance(model_list, list):
                # Catch non-list responses
                model_list = []

            for model in model_list:
                # Remove name key if its value is None #16689
                if "name" in model and model["name"] is None:
                    del model["name"]

                if prefix_id:
                    model["id"] = (
                        f"{prefix_id}.{model.get('id', model.get('name', ''))}"
                    )

                if tags:
                    model["tags"] = tags

                if connection_type:
                    model["connection_type"] = connection_type

    log.debug(f"get_all_models:responses() {responses}")
    return responses


async def get_filtered_models(models, user):
    # Filter models based on user access control
    filtered_models = []
    for model in models.get("data", []):
        model_info = Models.get_model_by_id(model["id"])
        if model_info:
            if user.id == model_info.user_id or has_access(
                user.id, type="read", access_control=model_info.access_control
            ):
                filtered_models.append(model)
    return filtered_models


@cached(
    ttl=MODELS_CACHE_TTL,
    key=lambda _, user: f"openai_all_models_{user.id}" if user else "openai_all_models",
)
async def get_all_models(request: Request, user: UserModel) -> dict[str, list]:
    log.info("get_all_models()")

    if not request.app.state.config.ENABLE_OPENAI_API:
        return {"data": []}

    responses = await get_all_models_responses(request, user=user)

    def extract_data(response):
        if response and "data" in response:
            return response["data"]
        if isinstance(response, list):
            return response
        return None

    def is_supported_openai_models(model_id):
        if any(
            name in model_id
            for name in [
                "babbage",
                "dall-e",
                "davinci",
                "embedding",
                "tts",
                "whisper",
            ]
        ):
            return False
        return True

    def get_merged_models(model_lists):
        log.debug(f"merge_models_lists {model_lists}")
        models = {}

        for idx, model_list in enumerate(model_lists):
            if model_list is not None and "error" not in model_list:
                for model in model_list:
                    model_id = model.get("id") or model.get("name")

                    if (
                        "api.openai.com"
                        in request.app.state.config.OPENAI_API_BASE_URLS[idx]
                        and not is_supported_openai_models(model_id)
                    ):
                        # Skip unwanted OpenAI models
                        continue

                    if model_id and model_id not in models:
                        models[model_id] = {
                            **model,
                            "name": model.get("name", model_id),
                            "owned_by": "openai",
                            "openai": model,
                            "connection_type": model.get("connection_type", "external"),
                            "urlIdx": idx,
                        }

        return models

    models = get_merged_models(map(extract_data, responses))
    log.debug(f"models: {models}")

    request.app.state.OPENAI_MODELS = models
    return {"data": list(models.values())}


@router.get("/models")
@router.get("/models/{url_idx}")
@get_role_based_limit
async def get_models(
    request: Request, url_idx: Optional[int] = None, user=Depends(get_verified_user)
):
    models = {
        "data": [],
    }

    if url_idx is None:
        models = await get_all_models(request, user=user)
    else:
        url = request.app.state.config.OPENAI_API_BASE_URLS[url_idx]
        key = request.app.state.config.OPENAI_API_KEYS[url_idx]

        api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
            str(url_idx),
            request.app.state.config.OPENAI_API_CONFIGS.get(url, {}),  # Legacy support
        )

        r = None
        async with aiohttp.ClientSession(
            trust_env=True,
            timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST),
        ) as session:
            try:
                headers, cookies = await get_headers_and_cookies(
                    request, url, key, api_config, user=user
                )

                if api_config.get("azure", False):
                    models = {
                        "data": api_config.get("model_ids", []) or [],
                        "object": "list",
                    }
                else:
                    async with session.get(
                        f"{url}/models",
                        headers=headers,
                        cookies=cookies,
                        ssl=AIOHTTP_CLIENT_SESSION_SSL,
                    ) as r:
                        if r.status != 200:
                            # Extract response error details if available
                            error_detail = f"HTTP Error: {r.status}"
                            res = await r.json()
                            if "error" in res:
                                error_detail = f"External Error: {res['error']}"
                            raise Exception(error_detail)

                        response_data = await r.json()

                        # Check if we're calling OpenAI API based on the URL
                        if "api.openai.com" in url:
                            # Filter models according to the specified conditions
                            response_data["data"] = [
                                model
                                for model in response_data.get("data", [])
                                if not any(
                                    name in model["id"]
                                    for name in [
                                        "babbage",
                                        "dall-e",
                                        "davinci",
                                        "embedding",
                                        "tts",
                                        "whisper",
                                    ]
                                )
                            ]

                        models = response_data
            except aiohttp.ClientError as e:
                # ClientError covers all aiohttp requests issues
                log.exception(f"Client error: {str(e)}")
                raise HTTPException(
                    status_code=500, detail="Open WebUI: Server Connection Error"
                )
            except Exception as e:
                log.exception(f"Unexpected error: {e}")
                error_detail = f"Unexpected error: {str(e)}"
                raise HTTPException(status_code=500, detail=error_detail)

    if user.role in {"user", "professor"} and not BYPASS_MODEL_ACCESS_CONTROL:
        models["data"] = await get_filtered_models(models, user)

    return models


class ConnectionVerificationForm(BaseModel):
    url: str
    key: str

    config: Optional[dict] = None


@router.post("/verify")
@get_write_operation_limit
async def verify_connection(
    request: Request,
    form_data: ConnectionVerificationForm,
    user=Depends(get_admin_user),
):
    url = form_data.url
    key = form_data.key

    api_config = form_data.config or {}

    async with aiohttp.ClientSession(
        trust_env=True,
        timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST),
    ) as session:
        try:
            headers, cookies = await get_headers_and_cookies(
                request, url, key, api_config, user=user
            )

            if api_config.get("azure", False):
                # Only set api-key header if not using Azure Entra ID authentication
                auth_type = api_config.get("auth_type", "bearer")
                if auth_type not in ("azure_ad", "microsoft_entra_id"):
                    headers["api-key"] = key

                api_version = api_config.get("api_version", "") or "2023-03-15-preview"
                async with session.get(
                    url=f"{url}/openai/models?api-version={api_version}",
                    headers=headers,
                    cookies=cookies,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as r:
                    try:
                        response_data = await r.json()
                    except Exception:
                        response_data = await r.text()

                    if r.status != 200:
                        if isinstance(response_data, (dict, list)):
                            return JSONResponse(
                                status_code=r.status, content=response_data
                            )
                        else:
                            return PlainTextResponse(
                                status_code=r.status, content=response_data
                            )

                    return response_data
            else:
                async with session.get(
                    f"{url}/models",
                    headers=headers,
                    cookies=cookies,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as r:
                    try:
                        response_data = await r.json()
                    except Exception:
                        response_data = await r.text()

                    if r.status != 200:
                        if isinstance(response_data, (dict, list)):
                            return JSONResponse(
                                status_code=r.status, content=response_data
                            )
                        else:
                            return PlainTextResponse(
                                status_code=r.status, content=response_data
                            )

                    return response_data

        except aiohttp.ClientError as e:
            # ClientError covers all aiohttp requests issues
            log.exception(f"Client error: {str(e)}")
            raise HTTPException(
                status_code=500, detail="Open WebUI: Server Connection Error"
            )
        except Exception as e:
            log.exception(f"Unexpected error: {e}")
            raise HTTPException(
                status_code=500, detail="Open WebUI: Server Connection Error"
            )


def get_azure_allowed_params(api_version: str) -> set[str]:
    allowed_params = {
        "messages",
        "temperature",
        "role",
        "content",
        "contentPart",
        "contentPartImage",
        "enhancements",
        "dataSources",
        "n",
        "stream",
        "stop",
        "max_tokens",
        "presence_penalty",
        "frequency_penalty",
        "logit_bias",
        "user",
        "function_call",
        "functions",
        "tools",
        "tool_choice",
        "top_p",
        "log_probs",
        "top_logprobs",
        "response_format",
        "seed",
        "max_completion_tokens",
        "reasoning_effort",
    }

    try:
        if api_version >= "2024-09-01-preview":
            allowed_params.add("stream_options")
    except ValueError:
        log.debug(
            f"Invalid API version {api_version} for Azure OpenAI. Defaulting to allowed parameters."
        )

    return allowed_params


def is_openai_reasoning_model(model: str) -> bool:
    return model.lower().startswith(("o1", "o3", "o4", "gpt-5"))


def convert_to_azure_payload(url, payload: dict, api_version: str):
    model = payload.get("model", "")

    # Filter allowed parameters based on Azure OpenAI API
    allowed_params = get_azure_allowed_params(api_version)

    # Special handling for o-series models
    if is_openai_reasoning_model(model):
        # Convert max_tokens to max_completion_tokens for o-series models
        if "max_tokens" in payload:
            payload["max_completion_tokens"] = payload["max_tokens"]
            del payload["max_tokens"]

        # Remove temperature if not 1 for o-series models
        if "temperature" in payload and payload["temperature"] != 1:
            log.debug(
                f"Removing temperature parameter for o-series model {model} as only default value (1) is supported"
            )
            del payload["temperature"]

    # Filter out unsupported parameters
    payload = {k: v for k, v in payload.items() if k in allowed_params}

    url = f"{url}/openai/deployments/{model}"
    return url, payload


@router.post("/chat/completions")
@get_role_based_limit
async def generate_chat_completion(
    request: Request,
    form_data: dict,
    user=Depends(get_verified_user),
    bypass_filter: Optional[bool] = False,
):
    if BYPASS_MODEL_ACCESS_CONTROL:
        bypass_filter = True

    idx = 0

    payload = {**form_data}
    metadata = payload.pop("metadata", None)

    model_id = form_data.get("model")
    model_info = Models.get_model_by_id(model_id)

    # Initialize variables for tool handling (may be updated in model_info block)
    base_system = None
    tool_prompts = []

    # Check model info and override the payload
    # Model-level settings for tool handling
    model_tool_mode = None  # "gating" | "concat" | "none" | None
    tool_gating_model = None  # Optional: Model for Stage 1 tool gating
    cache_strategy = "auto"  # Default: "auto" | "force" | "off"

    if model_info:
        if model_info.base_model_id:
            payload["model"] = model_info.base_model_id
            model_id = model_info.base_model_id

        params = model_info.params.model_dump()
        meta = model_info.meta.model_dump() if model_info.meta else {}

        # Extract tool_mode and prompt_group_id from meta (model settings)
        model_tool_mode = meta.get("tool_mode")  # "gating" | "concat" | "none" | None
        tool_gating_model = meta.get("tool_gating_model")  # Optional: Flash model for Stage 1 tool gating
        cache_strategy = meta.get("cache_strategy") or "auto"  # Cache strategy for Gemini caching
        prompt_group_id_from_meta = meta.get("prompt_group_id")

        # Extract system and prompt_group_id from params (legacy support)
        system = None
        prompt_group_id_from_params = None
        if params:
            system = params.pop("system", None)
            prompt_group_id_from_params = params.pop("prompt_group_id", None)

        # Priority: meta.prompt_group_id > params.prompt_group_id
        prompt_group_id = prompt_group_id_from_meta or prompt_group_id_from_params

        log.info(f"[OPENAI] Model settings - tool_mode: {model_tool_mode}, tool_gating_model: {tool_gating_model}, prompt_group_id: {prompt_group_id}")

        # Always try to compose prompts (even if params is None)
        # Get persona values from metadata (stored in chat)
        proficiency_level = metadata.get("proficiency_level") if metadata else None
        response_style = metadata.get("response_style") if metadata else None

        # Compose prompts with fallback logic
        # Priority: prompt_group_id > system > DEFAULT_PROMPT_GROUP_ID > none
        # Note: First compose without tools, then decide based on tool_mode
        composed_system, tool_prompts = compose_with_fallback(
            group_id=prompt_group_id,
            system_prompt=system,
            default_group_id=getattr(
                request.app.state.config, "DEFAULT_PROMPT_GROUP_ID", None
            ),
            proficiency_level=proficiency_level,
            response_style=response_style,
            include_tools=False,  # Don't auto-include tools, decide based on tool_mode
        )

        # Store base system for later use (tool handling done after URL resolution)
        base_system = composed_system if composed_system else system

        # Apply model params to payload (only if params exist)
        if params:
            payload = apply_model_params_to_body_openai(params, payload)

        # Note: System prompt application is deferred until after URL resolution
        # to determine if we should use tool gating (Gemini) or legacy mode (others)

        # Check if user has access to the model
        if not bypass_filter and user.role in {"user", "professor"}:
            if not (
                user.id == model_info.user_id
                or has_access(
                    user.id, type="read", access_control=model_info.access_control
                )
            ):
                raise HTTPException(
                    status_code=403,
                    detail="Model not found",
                )
    elif not bypass_filter:
        if user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail="Model not found",
            )

    await get_all_models(request, user=user)
    model = request.app.state.OPENAI_MODELS.get(model_id)
    if model:
        idx = model["urlIdx"]
    else:
        raise HTTPException(
            status_code=404,
            detail="Model not found",
        )

    # Get the API config for the model
    api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
        str(idx),
        request.app.state.config.OPENAI_API_CONFIGS.get(
            request.app.state.config.OPENAI_API_BASE_URLS[idx], {}
        ),  # Legacy support
    )

    prefix_id = api_config.get("prefix_id", None)
    if prefix_id:
        payload["model"] = payload["model"].replace(f"{prefix_id}.", "")

    # Add user info to the payload if the model is a pipeline
    if "pipeline" in model and model.get("pipeline"):
        payload["user"] = {
            "name": user.name,
            "id": user.id,
            "email": user.email,
            "role": user.role,
        }

    url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
    key = request.app.state.config.OPENAI_API_KEYS[idx]

    # Determine backend type
    is_gemini_backend = "generativelanguage.googleapis.com" in url

    # Get headers and cookies early (needed for tool gating Stage 1)
    headers, cookies = await get_headers_and_cookies(
        request, url, key, api_config, metadata, user=user
    )

    # Build request URL early
    if api_config.get("azure", False):
        api_version = api_config.get("api_version", "2023-03-15-preview")
        azure_url, _ = convert_to_azure_payload(url, payload.copy(), api_version)

        # Only set api-key header if not using Azure Entra ID authentication
        auth_type = api_config.get("auth_type", "bearer")
        if auth_type not in ("azure_ad", "microsoft_entra_id"):
            headers["api-key"] = key

        headers["api-version"] = api_version
        request_url = f"{azure_url}/chat/completions?api-version={api_version}"
    else:
        request_url = f"{url}/chat/completions"

    # Tool handling based on backend type
    # Gemini backend: use FULL two-stage tool gating
    # Other backends: legacy mode (include full tool content)

    final_system = base_system

    # Detect utility requests that should skip tool gating (e.g., title generation)
    # These are identified by:
    # 1. metadata.task == "title_generation" or similar
    # 2. System prompt containing title generation keywords
    # 3. Short utility calls that don't need tool selection
    is_utility_request = False
    if metadata:
        task_type = metadata.get("task", "")
        if task_type in ("title_generation", "summary", "title"):
            is_utility_request = True
            log.info(f"[OPENAI] Utility request detected (task={task_type}), skipping tool gating")

    # Also check system prompt for title generation patterns
    # Use specific phrases to avoid false positives (e.g., "include a title" in graph prompts)
    if not is_utility_request and base_system:
        # More specific patterns for title generation tasks
        title_patterns = [
            "generate a title",
            "create a title",
            "generate title",
            "create title",
            "제목을 생성",
            "제목 생성",
            "제목을 만들",
            "create a concise title",
            "generate a concise title",
        ]
        base_system_lower = base_system.lower()
        matched_pattern = None
        for pattern in title_patterns:
            if pattern.lower() in base_system_lower:
                matched_pattern = pattern
                break

        if matched_pattern:
            is_utility_request = True
            log.info(f"[OPENAI] Title generation detected in system prompt (matched: '{matched_pattern}'), skipping tool gating")
        else:
            # Debug: Log that we checked but didn't find title patterns
            log.debug(f"[OPENAI] No title generation patterns found in base_system (length: {len(base_system)} chars)")

    # Determine tool handling mode based on model settings
    # Priority: model_tool_mode > default behavior
    # - "gating": two-stage tool gating (select tools first, then generate)
    # - "concat": include all tool prompts in system prompt (legacy mode)
    # - "none": no tool prompts included
    # - "inline" or None: inline tool execution with short hints (default)
    effective_tool_mode = model_tool_mode if model_tool_mode else "inline"

    log.info("=" * 80)
    log.info(f"[OPENAI] Tool handling mode: {effective_tool_mode} (model_tool_mode={model_tool_mode})")
    log.info(f"[OPENAI] Available tools: {[t.command for t in tool_prompts]}")
    log.info("=" * 80)

    if is_utility_request:
        # Utility requests skip tool handling
        log.info("[OPENAI] Utility request - skipping tool handling")
        effective_tool_mode = "none"

    if effective_tool_mode == "gating" and tool_prompts:
        # Two-stage tool gating: select tools first, then generate with selected tools
        log.info(f"[OPENAI-TOOL-GATING] Starting two-stage tool gating")

        # Extract user query from messages (last user message)
        user_query = ""
        for msg in reversed(payload.get("messages", [])):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    user_query = content
                elif isinstance(content, list):
                    # Handle multimodal content
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            user_query = part.get("text", "")
                            break
                break

        log.info(f"[OPENAI-TOOL-GATING] User query: {user_query[:100]}...")

        # Stage 1: Tool selection with catalog + JSON instructions
        tool_catalog = build_tool_catalog(tool_prompts)
        stage1_system = build_tool_selection_system_prompt(base_system or "", tool_catalog)

        log.info(f"[OPENAI-TOOL-GATING] Stage 1 System Prompt Length: {len(stage1_system)} chars")

        # Make Stage 1 call
        # Use Gemini native API with cache if Gemini backend, otherwise OpenAI-compatible API
        # Use tool_gating_model if configured, otherwise use main model
        stage1_model = tool_gating_model if tool_gating_model else payload["model"]
        log.info(f"[OPENAI-TOOL-GATING] Stage 1 model: {stage1_model} (tool_gating_model={tool_gating_model})")

        if is_gemini_backend:
            log.info("[OPENAI-TOOL-GATING] Using Gemini native API for Stage 1 with Pydantic response schema")
            cache_manager = get_or_create_gemini_cache_manager(request, key)

            # Convert recent chat history to Gemini format for better context
            # Include last 6 messages (3 turns) to provide context
            recent_messages = payload.get("messages", [])[-6:]
            gemini_contents = convert_openai_messages_to_gemini_contents(recent_messages, filter_code=False)
            log.info(f"[OPENAI-TOOL-GATING] Stage 1 - Using {len(recent_messages)} recent messages for context")

            stage1_result = await make_gemini_native_call_with_cache(
                api_key=key,
                model=stage1_model,  # Use tool_gating_model if available
                system_prompt=stage1_system,
                contents=gemini_contents,  # Use chat history for context
                cache_stage="gating",
                cache_manager=cache_manager,
                temperature=payload.get("temperature", 0.2),
                cache_strategy=cache_strategy,
                response_schema=ToolSelectionResponse,  # Enforce structured JSON output
            )
        else:
            log.info("[OPENAI-TOOL-GATING] Using OpenAI-compatible API for Stage 1")
            stage1_payload = payload.copy()
            stage1_payload["model"] = stage1_model  # Use tool_gating_model if available
            stage1_result = await make_gemini_llm_call(
                request_url=request_url,
                headers=headers.copy(),
                cookies=cookies,
                base_payload=stage1_payload,
                system_prompt=stage1_system,
                query=user_query,
            )

        if not stage1_result.get("success"):
            log.error(f"[OPENAI-TOOL-GATING] Stage 1 failed: {stage1_result.get('error')}")
            # Fallback: use base system without tools
            final_system = base_system
        else:
            stage1_text = stage1_result.get("text", "")
            log.info(f"[OPENAI-TOOL-GATING] Stage 1 response: {stage1_text[:300]}...")

            # Parse tool selection
            selected_tools, direct_answer = parse_tool_selection_response(stage1_text)

            if not selected_tools:
                # No tools needed - proceed to Stage 2 with base system only
                log.info("[OPENAI-TOOL-GATING] No tools needed, proceeding with base system only")
                final_system = base_system
            else:
                # Stage 2: Use selected tools' full content
                log.info(f"[OPENAI-TOOL-GATING] Stage 2 - Tools selected: {selected_tools}")

                selected_tool_prompts = get_tool_prompts_by_commands(tool_prompts, selected_tools)
                final_system = compose_stage2_system_prompt(base_system or "", selected_tool_prompts)

                log.info(f"[OPENAI-TOOL-GATING] Stage 2 System Prompt Length: {len(final_system)} chars")
                log.info(f"[OPENAI-TOOL-GATING] Selected tools: {[t.command for t in selected_tool_prompts]}")

                # Enable inline tool execution for Stage 2 (for streaming with tool markers)
                if metadata is None:
                    metadata = {}
                metadata["enable_tool_notifications"] = True
                metadata["tool_commands"] = {t.command for t in selected_tool_prompts}
                metadata["tool_prompts_dict"] = {
                    t.command.lstrip('/'): t.content for t in selected_tool_prompts
                }
                metadata["tool_validation_rules"] = {
                    t.command.lstrip('/'): t.validation_rules
                    for t in selected_tool_prompts
                    if t.prompt_type == "json_tool" and t.validation_rules
                }
                metadata["api_request_url"] = request_url
                metadata["api_headers"] = dict(headers)
                metadata["api_cookies"] = dict(cookies) if cookies else {}

                # Pass Gemini info for native SDK usage in inline tool execution
                metadata["is_gemini_backend"] = is_gemini_backend
                if is_gemini_backend:
                    metadata["gemini_api_key"] = key
                    metadata["gemini_model_id"] = payload["model"]
                    # Use tool_gating_model (Flash) for tool execution if configured
                    metadata["gemini_tool_model"] = tool_gating_model if tool_gating_model else payload["model"]
                    log.info(f"[OPENAI-TOOL-GATING] Stage 2 inline tool execution will use Gemini native SDK")
                    log.info(f"[OPENAI-TOOL-GATING] Tool execution model: {metadata['gemini_tool_model']}")

                log.info(f"[OPENAI-TOOL-GATING] Stage 2 inline tool execution enabled for: {metadata['tool_commands']}")
                log.info(f"[OPENAI-TOOL-GATING] Tool prompts dict keys: {list(metadata['tool_prompts_dict'].keys())}")

                # Store metadata in form_data for middleware access
                form_data["metadata"] = metadata
                log.info(f"[OPENAI-TOOL-GATING] Updated metadata stored in form_data")

    elif effective_tool_mode == "concat" and tool_prompts:
        # Legacy mode: include all tool prompts in system prompt
        final_system = compose_stage2_system_prompt(base_system or "", tool_prompts)
        log.info(f"[OPENAI] Concat mode: all {len(tool_prompts)} tool prompts included")
        log.info(f"[OPENAI] Final system prompt length: {len(final_system)} chars")

    elif effective_tool_mode == "none" or not tool_prompts:
        # No tools mode: just use base system
        final_system = base_system
        log.info(f"[OPENAI] No tools mode: base system only")

    else:
        # Default: Inline tool execution mode with short hints
        # When tool markers are detected in stream, ToolInlineExecutor will call LLM with full prompt
        tool_hints = build_tool_hints(tool_prompts)
        final_system = f"{base_system}\n\n{tool_hints}" if base_system else tool_hints
        log.info(f"[OPENAI] Inline tool execution mode with {len(tool_prompts)} tools (short hints)")
        log.info(f"[OPENAI] Tool hints length: {len(tool_hints)} chars")

    # Enable inline tool execution for streaming if using inline mode
    if effective_tool_mode == "inline" and tool_prompts:
        if metadata is None:
            metadata = {}
        metadata["enable_tool_notifications"] = True
        metadata["tool_commands"] = {t.command for t in tool_prompts}
        # Pass full tool prompts dict for inline execution
        metadata["tool_prompts_dict"] = {
            t.command.lstrip('/'): t.content for t in tool_prompts
        }
        # Pass validation rules for json_tool types
        metadata["tool_validation_rules"] = {
            t.command.lstrip('/'): t.validation_rules
            for t in tool_prompts
            if t.prompt_type == "json_tool" and t.validation_rules
        }
        # Pass API info for inline LLM calls
        metadata["api_request_url"] = request_url
        metadata["api_headers"] = dict(headers)
        metadata["api_cookies"] = dict(cookies) if cookies else {}

        # Pass Gemini info for native SDK usage in inline tool execution
        metadata["is_gemini_backend"] = is_gemini_backend
        if is_gemini_backend:
            metadata["gemini_api_key"] = key
            metadata["gemini_model_id"] = payload["model"]
            # Use tool_gating_model (Flash) for tool execution if configured
            metadata["gemini_tool_model"] = tool_gating_model if tool_gating_model else payload["model"]
            log.info(f"[OPENAI] Inline tool execution will use Gemini native SDK")
            log.info(f"[OPENAI] Tool execution model: {metadata['gemini_tool_model']}")

        log.info(f"[OPENAI] Inline tool execution enabled for: {metadata['tool_commands']}")
        log.info(f"[OPENAI] Tool prompts dict keys: {list(metadata['tool_prompts_dict'].keys())}")
        log.info(f"[OPENAI] Tool validation rules keys: {list(metadata['tool_validation_rules'].keys())}")

        # Store updated metadata back in form_data for middleware access
        form_data["metadata"] = metadata
        log.info(f"[OPENAI] Updated metadata stored in form_data")

    # Apply system prompt to payload
    payload = apply_system_prompt_to_body(final_system, payload, metadata, user)

    # Debug: Log the final system prompt being sent
    log.info("=" * 80)
    log.info(f"[OPENAI] Final system prompt length: {len(final_system) if final_system else 0} chars")
    log.info(f"[OPENAI] Backend URL: {url}")
    log.info(f"[OPENAI] Is Gemini backend: {is_gemini_backend}")
    log.info(f"[OPENAI] Tool prompts count: {len(tool_prompts)}")
    log.info(f"[OPENAI] Inline tool execution: {tool_prompts and not is_utility_request}")
    log.info("=" * 80)

    # CRITICAL: If Gemini backend, use native SDK for ALL requests
    # This enables context caching and improves performance
    if is_gemini_backend:
        log.info("[OPENAI] Gemini backend detected - routing to native SDK")

        # Determine cache stage based on tool mode
        # - "gating" mode: Stage 1 already used "gating" cache, Stage 2 uses "execution" cache
        # - "concat" mode: uses "execution" cache (includes all tools)
        # - "none"/"inline" mode: uses "execution" cache (no tools or short hints)
        cache_stage = "execution"

        # Use tool_gating_model (Flash) for inline mode to improve speed
        selected_model = payload["model"]
        if effective_tool_mode == "inline" and tool_gating_model:
            selected_model = tool_gating_model
            log.info(f"[OPENAI] Inline mode: using Flash model for first call: {selected_model}")

        return await handle_gemini_native_request(
            request=request,
            api_key=key,
            model_id=selected_model,
            payload=payload,
            final_system=final_system,
            cache_stage=cache_stage,
            metadata=metadata,
        )

    # For non-Gemini backends, continue with OpenAI-compatible flow
    log.info("[OPENAI] Using OpenAI-compatible API flow")

    # Check if model is a reasoning model that needs special handling
    if is_openai_reasoning_model(payload["model"]):
        payload = openai_reasoning_model_handler(payload)
    elif "api.openai.com" not in url:
        # Remove "max_completion_tokens" from the payload for backward compatibility
        if "max_completion_tokens" in payload:
            payload["max_tokens"] = payload["max_completion_tokens"]
            del payload["max_completion_tokens"]

    if "max_tokens" in payload and "max_completion_tokens" in payload:
        del payload["max_tokens"]

    # Convert the modified body back to JSON
    if "logit_bias" in payload:
        payload["logit_bias"] = json.loads(
            convert_logit_bias_input_to_json(payload["logit_bias"])
        )

    # Re-apply Azure conversion if needed (payload was modified)
    if api_config.get("azure", False):
        api_version = api_config.get("api_version", "2023-03-15-preview")
        request_url, payload = convert_to_azure_payload(url, payload, api_version)
        request_url = f"{request_url}/chat/completions?api-version={api_version}"

    payload = json.dumps(payload)

    r = None
    session = None
    streaming = False
    response = None

    try:
        session = aiohttp.ClientSession(
            trust_env=True, timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
        )

        r = await session.request(
            method="POST",
            url=request_url,
            data=payload,
            headers=headers,
            cookies=cookies,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        )

        # Check if response is SSE
        if "text/event-stream" in r.headers.get("Content-Type", ""):
            streaming = True
            # Filter out encoding headers to prevent ERR_CONTENT_DECODING_FAILED
            # aiohttp already handles decompression, so we shouldn't pass these headers
            filtered_headers = {
                k: v for k, v in r.headers.items()
                if k.lower() not in ('content-encoding', 'transfer-encoding', 'content-length')
            }
            return StreamingResponse(
                stream_chunks_handler(r.content),
                status_code=r.status,
                headers=filtered_headers,
                background=BackgroundTask(
                    cleanup_response, response=r, session=session
                ),
            )
        else:
            try:
                response = await r.json()
            except Exception as e:
                log.error(e)
                response = await r.text()

            if r.status >= 400:
                if isinstance(response, (dict, list)):
                    return JSONResponse(status_code=r.status, content=response)
                else:
                    return PlainTextResponse(status_code=r.status, content=response)

            return response
    except Exception as e:
        log.exception(e)

        raise HTTPException(
            status_code=r.status if r else 500,
            detail="Open WebUI: Server Connection Error",
        )
    finally:
        if not streaming:
            await cleanup_response(r, session)


async def embeddings(request: Request, form_data: dict, user):
    """
    Calls the embeddings endpoint for OpenAI-compatible providers.

    Args:
        request (Request): The FastAPI request context.
        form_data (dict): OpenAI-compatible embeddings payload.
        user (UserModel): The authenticated user.

    Returns:
        dict: OpenAI-compatible embeddings response.
    """
    idx = 0
    # Prepare payload/body
    body = json.dumps(form_data)
    # Find correct backend url/key based on model
    await get_all_models(request, user=user)
    model_id = form_data.get("model")
    models = request.app.state.OPENAI_MODELS
    if model_id in models:
        idx = models[model_id]["urlIdx"]

    url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
    key = request.app.state.config.OPENAI_API_KEYS[idx]
    api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
        str(idx),
        request.app.state.config.OPENAI_API_CONFIGS.get(url, {}),  # Legacy support
    )

    r = None
    session = None
    streaming = False

    headers, cookies = await get_headers_and_cookies(
        request, url, key, api_config, user=user
    )
    try:
        session = aiohttp.ClientSession(trust_env=True)
        r = await session.request(
            method="POST",
            url=f"{url}/embeddings",
            data=body,
            headers=headers,
            cookies=cookies,
        )

        if "text/event-stream" in r.headers.get("Content-Type", ""):
            streaming = True
            return StreamingResponse(
                r.content,
                status_code=r.status,
                headers=dict(r.headers),
                background=BackgroundTask(
                    cleanup_response, response=r, session=session
                ),
            )
        else:
            try:
                response_data = await r.json()
            except Exception:
                response_data = await r.text()

            if r.status >= 400:
                if isinstance(response_data, (dict, list)):
                    return JSONResponse(status_code=r.status, content=response_data)
                else:
                    return PlainTextResponse(
                        status_code=r.status, content=response_data
                    )

            return response_data
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=r.status if r else 500,
            detail="Open WebUI: Server Connection Error",
        )
    finally:
        if not streaming:
            await cleanup_response(r, session)


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(path: str, request: Request, user=Depends(get_verified_user)):
    """
    Deprecated: proxy all requests to OpenAI API
    """

    body = await request.body()

    idx = 0
    url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
    key = request.app.state.config.OPENAI_API_KEYS[idx]
    api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
        str(idx),
        request.app.state.config.OPENAI_API_CONFIGS.get(
            request.app.state.config.OPENAI_API_BASE_URLS[idx], {}
        ),  # Legacy support
    )

    r = None
    session = None
    streaming = False

    try:
        headers, cookies = await get_headers_and_cookies(
            request, url, key, api_config, user=user
        )

        if api_config.get("azure", False):
            api_version = api_config.get("api_version", "2023-03-15-preview")

            # Only set api-key header if not using Azure Entra ID authentication
            auth_type = api_config.get("auth_type", "bearer")
            if auth_type not in ("azure_ad", "microsoft_entra_id"):
                headers["api-key"] = key

            headers["api-version"] = api_version

            payload = json.loads(body)
            url, payload = convert_to_azure_payload(url, payload, api_version)
            body = json.dumps(payload).encode()

            request_url = f"{url}/{path}?api-version={api_version}"
        else:
            request_url = f"{url}/{path}"

        session = aiohttp.ClientSession(trust_env=True)
        r = await session.request(
            method=request.method,
            url=request_url,
            data=body,
            headers=headers,
            cookies=cookies,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        )

        # Check if response is SSE
        if "text/event-stream" in r.headers.get("Content-Type", ""):
            streaming = True
            return StreamingResponse(
                r.content,
                status_code=r.status,
                headers=dict(r.headers),
                background=BackgroundTask(
                    cleanup_response, response=r, session=session
                ),
            )
        else:
            try:
                response_data = await r.json()
            except Exception:
                response_data = await r.text()

            if r.status >= 400:
                if isinstance(response_data, (dict, list)):
                    return JSONResponse(status_code=r.status, content=response_data)
                else:
                    return PlainTextResponse(
                        status_code=r.status, content=response_data
                    )

            return response_data

    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=r.status if r else 500,
            detail="Open WebUI: Server Connection Error",
        )
    finally:
        if not streaming:
            await cleanup_response(r, session)


# ============================================================
# Gemini Cache Management API
# ============================================================

@router.get("/gemini/cache/stats")
@get_role_based_limit
async def get_gemini_cache_stats(
    request: Request,
    user=Depends(get_admin_user)
):
    """
    Get Gemini global cache statistics.

    Admin only endpoint to monitor cache usage for Gemini native SDK.

    Returns:
        - total_caches: Total number of cached contents
        - max_caches: Maximum allowed caches
        - by_stage: Count of caches by stage (gating/execution)
        - by_model: Count of caches by model ID
        - tool_spec_version: Current tool spec version
    """
    if not hasattr(request.app.state, "gemini_cache_managers"):
        return {
            "status": "ok",
            "total_caches": 0,
            "max_caches": 50,
            "by_stage": {"gating": 0, "execution": 0},
            "by_model": {},
            "tool_spec_version": "v1.0.0",
            "message": "No cache managers initialized yet"
        }

    # Aggregate stats from all cache managers
    total_caches = 0
    by_stage = {"gating": 0, "execution": 0}
    by_model = {}

    for cache_manager in request.app.state.gemini_cache_managers.values():
        stats = cache_manager.get_stats()
        total_caches += stats["total_caches"]
        for stage, count in stats["by_stage"].items():
            by_stage[stage] = by_stage.get(stage, 0) + count
        for model, count in stats["by_model"].items():
            by_model[model] = by_model.get(model, 0) + count

    return {
        "status": "ok",
        "total_caches": total_caches,
        "max_caches": 50,
        "by_stage": by_stage,
        "by_model": by_model,
        "tool_spec_version": "v1.0.0",
        "cache_managers_count": len(request.app.state.gemini_cache_managers)
    }


@router.delete("/gemini/cache")
@get_write_operation_limit
async def clear_all_gemini_caches(
    request: Request,
    user=Depends(get_admin_user)
):
    """
    Clear all Gemini cached system prompts.

    Admin only endpoint. Use this when you modify prompts and want to
    force cache regeneration across all cache managers.

    Returns:
        - deleted_count: Number of caches successfully deleted
        - failed_count: Number of caches that failed to delete
        - errors: List of error messages (if any)
    """
    if not hasattr(request.app.state, "gemini_cache_managers"):
        return {
            "status": "ok",
            "deleted_count": 0,
            "failed_count": 0,
            "errors": [],
            "message": "No cache managers initialized yet"
        }

    total_deleted = 0
    total_failed = 0
    all_errors = []

    for key_hash, cache_manager in request.app.state.gemini_cache_managers.items():
        log.info(f"[CACHE] Clearing caches for manager: {key_hash}")
        result = cache_manager.clear_all_caches()
        total_deleted += result["deleted_count"]
        total_failed += result["failed_count"]
        all_errors.extend(result["errors"])

    return {
        "status": "ok",
        "deleted_count": total_deleted,
        "failed_count": total_failed,
        "errors": all_errors,
        "cache_managers_count": len(request.app.state.gemini_cache_managers)
    }


@router.delete("/gemini/cache/{stage}")
@get_write_operation_limit
async def clear_gemini_caches_by_stage(
    request: Request,
    stage: str,
    user=Depends(get_admin_user)
):
    """
    Clear Gemini caches for a specific stage.

    Admin only endpoint. Clears only caches for the specified stage
    (gating or execution) across all cache managers.

    Args:
        stage: Stage to clear ("gating" or "execution")

    Returns:
        - stage: The stage that was cleared
        - deleted_count: Number of caches successfully deleted
        - failed_count: Number of caches that failed to delete
        - errors: List of error messages (if any)
    """
    if stage not in ("gating", "execution"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stage: {stage}. Must be 'gating' or 'execution'"
        )

    if not hasattr(request.app.state, "gemini_cache_managers"):
        return {
            "status": "ok",
            "stage": stage,
            "deleted_count": 0,
            "failed_count": 0,
            "errors": [],
            "message": "No cache managers initialized yet"
        }

    total_deleted = 0
    total_failed = 0
    all_errors = []

    for key_hash, cache_manager in request.app.state.gemini_cache_managers.items():
        log.info(f"[CACHE] Clearing {stage} caches for manager: {key_hash}")
        result = cache_manager.clear_caches_by_stage(stage)
        total_deleted += result["deleted_count"]
        total_failed += result["failed_count"]
        all_errors.extend(result["errors"])

    return {
        "status": "ok",
        "stage": stage,
        "deleted_count": total_deleted,
        "failed_count": total_failed,
        "errors": all_errors,
        "cache_managers_count": len(request.app.state.gemini_cache_managers)
    }
