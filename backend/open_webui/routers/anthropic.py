"""
Anthropic/Claude API Router for OpenWebUI

Provides:
1. OAuth PKCE authentication flow for Claude Pro/Max accounts
2. Chat completions proxy with OpenAI → Anthropic format translation
3. Model listing for authenticated users
4. Automatic token refresh
"""

import asyncio
import base64
import hashlib
import json
import logging
import random
import re
import time
import uuid as _uuid
from typing import Optional, Union, List
from urllib.parse import urlencode

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.anthropic_auth import (
    ClaudeAuth,
    ClaudeTokens,
    PkceChallenge,
    TokenExpiredError,
    NoRefreshTokenError,
    CLAUDE_API_URL,
    CLAUDE_HOSTED_CALLBACK_URI,
    DEFAULT_SCOPES,
)
from open_webui.models.oauth_sessions import OAuthSessions, OAuthSessionModel
from open_webui.models.users import UserModel

from open_webui.env import (
    AIOHTTP_CLIENT_TIMEOUT,
    AIOHTTP_CLIENT_SESSION_SSL,
)


log = logging.getLogger(__name__)

router = APIRouter()

# Provider name for OAuth sessions
ANTHROPIC_PROVIDER = "anthropic"

# Anthropic API version header
ANTHROPIC_API_VERSION = "2023-06-01"

# OAuth-specific beta features (REQUIRED for OAuth to work)
# Added web-search for built-in search capability ($0.01/request)
# Beta features from Claude Code CLI v2.1.33
# Status legend:
#   [WORKS] - Just adding the flag enables it
#   [NEEDS IMPL] - Requires additional code/UI to actually use
#   [UNKNOWN] - Need to test if it works or needs implementation
ANTHROPIC_OAUTH_BETA = (
    "claude-code-20250219,"  # [REQUIRED] Claude Code OAuth session identification
    "oauth-2025-04-20,"  # [WORKS] OAuth support - already implemented
    "interleaved-thinking-2025-05-14,"  # [WORKS] Extended thinking in responses
    "web-search-2025-03-05,"  # [NEEDS IMPL] Requires sending web_search tool in request
    "files-api-2025-04-14,"  # [NEEDS IMPL] Requires file upload endpoint + content blocks
    "structured-outputs-2025-12-15,"  # [WORKS] Converts OpenAI response_format to Anthropic output_format
    "prompt-caching-scope-2026-01-05,"  # [UNKNOWN] May need cache_control blocks in messages
    "context-management-2025-06-27,"  # [UNKNOWN] Context window management
    "tool-examples-2025-10-29,"  # [WORKS] Allows examples in tool definitions
    "advanced-tool-use-2025-11-20,"  # [WORKS] Enhanced tool calling capabilities
    "tool-search-tool-2025-10-19,"  # [NEEDS IMPL] Built-in tool search - needs tool definition
    "effort-2025-11-24,"  # [NEEDS IMPL] Thinking effort control - needs UI param
    "adaptive-thinking-2026-01-28"  # [WORKS] reasoning_effort="adaptive" for opus-4-6
)

# User agent to mimic Claude CLI (required for OAuth)
# Version is dynamically fetched — this is the fallback
ANTHROPIC_USER_AGENT_TEMPLATE = "claude-cli/{version} (external, cli)"

# ============================================================================
# Dynamic Version Fetching (cached, matching opencode-anthropic-auth)
# ============================================================================

_version_cache: dict = {}
_version_cache_time: float = 0
VERSION_CACHE_TTL = 3600  # 1 hour


async def get_claude_cli_version() -> str:
    """Fetch latest Claude CLI version from npm registry (cached 1hr)."""
    global _version_cache, _version_cache_time
    now = time.time()
    if _version_cache.get("cli") and now - _version_cache_time < VERSION_CACHE_TTL:
        return _version_cache["cli"]
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://registry.npmjs.org/@anthropic-ai/claude-code/latest",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.ok:
                    data = await resp.json()
                    ver = data.get("version", "2.1.36")
                    _version_cache["cli"] = ver
                    _version_cache_time = now
                    return ver
    except Exception:
        pass
    return _version_cache.get("cli", "2.1.36")


async def get_stainless_sdk_version() -> str:
    """Fetch latest Anthropic SDK version from npm registry (cached 1hr)."""
    global _version_cache, _version_cache_time
    now = time.time()
    if _version_cache.get("sdk") and now - _version_cache_time < VERSION_CACHE_TTL:
        return _version_cache["sdk"]
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://registry.npmjs.org/@anthropic-ai/sdk/latest",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.ok:
                    data = await resp.json()
                    ver = data.get("version", "0.70.0")
                    _version_cache["sdk"] = ver
                    return ver
    except Exception:
        pass
    return _version_cache.get("sdk", "0.70.0")


# ============================================================================
# Billing Hash (matching opencode-anthropic-auth computeBillingHash)
# ============================================================================


def compute_billing_hash(first_user_message: str, version: str) -> str:
    """
    Compute billing hash matching official CLI's N8A function.

    Extracts chars at positions 4, 7, 20 from first user message,
    combines with salt and version, then SHA-256 hashes to 3-char hex.
    """
    salt = "59cf53e54c78"
    # Extract chars at positions 4, 7, 20 (0-indexed) from first user message
    chars = "".join(
        first_user_message[i] if i < len(first_user_message) else "0"
        for i in [4, 7, 20]
    )
    hash_input = salt + chars + version
    return hashlib.sha256(hash_input.encode()).hexdigest()[:3]


# ============================================================================
# Retry Constants (matching opencode-anthropic-auth)
# ============================================================================

MAX_OVERLOAD_RETRIES = 5
BASE_RETRY_DELAY_MS = 1000
MAX_RETRY_DELAY_MS = 32000


# ============================================================================
# Token Pool — Multi-account rotation on rate limits
# ============================================================================


# Module-level pool state — persists across requests within the same process
_token_cooldowns: dict[str, float] = {}  # session_id -> cooldown_until epoch


class TokenPool:
    """
    Manages multiple Claude OAuth tokens for round-robin rotation.

    On 429 rate limits, the current token is marked as rate-limited with
    its retry-after duration, and the next available token is selected.

    Token state (cooldowns) persists in module-level dict across requests
    so rate-limit info carries over between different user requests.
    """

    def __init__(self, entries: list[tuple[str, str, "ClaudeTokens"]]):
        """
        Args:
            entries: List of (session_id, user_id, ClaudeTokens) tuples
        """
        self._entries: list[tuple[str, str, "ClaudeTokens"]] = entries
        self._index = 0  # round-robin pointer

    @property
    def size(self) -> int:
        return len(self._entries)

    @property
    def has_tokens(self) -> bool:
        return self.size > 0

    def get_next_available(self) -> Optional[tuple[str, "ClaudeTokens"]]:
        """
        Get the next available (non-rate-limited) token.

        Returns (session_id, ClaudeTokens) or None if all tokens are
        currently rate-limited.

        Uses round-robin starting from the last-used index, skipping
        tokens that are in cooldown.
        """
        if not self._entries:
            return None

        now = time.time()

        # Try each token starting from current index
        for i in range(self.size):
            idx = (self._index + i) % self.size
            session_id, user_id, tokens = self._entries[idx]
            cooldown_until = _token_cooldowns.get(session_id, 0.0)

            if now >= cooldown_until:
                self._index = (idx + 1) % self.size  # advance for next call
                log.debug(
                    f"Token pool: selected session {session_id[:8]}… "
                    f"(account {idx + 1}/{self.size})"
                )
                return session_id, tokens

        # All tokens are rate-limited — find the one that recovers soonest
        log.warning(
            f"Token pool: all {self.size} tokens rate-limited, "
            "returning soonest-available"
        )
        soonest_idx = min(
            range(self.size),
            key=lambda i: _token_cooldowns.get(self._entries[i][0], 0.0),
        )
        session_id, user_id, tokens = self._entries[soonest_idx]
        self._index = (soonest_idx + 1) % self.size
        return session_id, tokens

    @staticmethod
    def mark_rate_limited(session_id: str, retry_after_ms: int) -> None:
        """Mark a token as rate-limited for the given duration."""
        cooldown_until = time.time() + (retry_after_ms / 1000.0)
        _token_cooldowns[session_id] = cooldown_until
        log.info(
            f"Token pool: session {session_id[:8]}… rate-limited "
            f"for {retry_after_ms}ms (cooldown until "
            f"{time.strftime('%H:%M:%S', time.localtime(cooldown_until))})"
        )

    @staticmethod
    def clear_cooldown(session_id: str) -> None:
        """Clear rate-limit cooldown for a token (e.g., after successful request)."""
        _token_cooldowns.pop(session_id, None)

    @staticmethod
    def get_pool_status() -> list[dict]:
        """Get status of all tracked token cooldowns (for admin endpoint)."""
        now = time.time()
        return [
            {
                "session_id": sid,
                "cooldown_until": until,
                "is_available": now >= until,
                "seconds_remaining": max(0, until - now),
            }
            for sid, until in _token_cooldowns.items()
        ]


async def get_token_pool(user: "UserModel", request: Request) -> TokenPool:
    """
    Build a TokenPool with all available Claude OAuth tokens.

    Priority order:
    1. User's own token (if they have one)
    2. All admin tokens (org-wide shared accounts)

    Tokens that need refresh are refreshed inline.
    Tokens that fail refresh are skipped.
    """
    entries: list[tuple[str, str, ClaudeTokens]] = []
    seen_session_ids: set[str] = set()

    # Get user's own session first (highest priority)
    user_session = OAuthSessions.get_session_by_provider_and_user_id(
        ANTHROPIC_PROVIDER, user.id
    )
    if user_session:
        tokens = await _refresh_if_needed(user_session, request)
        if tokens:
            entries.append((user_session.id, user_session.user_id, tokens))
            seen_session_ids.add(user_session.id)

    # Get all org sessions (for pool rotation)
    all_sessions = OAuthSessions.get_all_sessions_by_provider(ANTHROPIC_PROVIDER)
    for session in all_sessions:
        if session.id in seen_session_ids:
            continue
        tokens = await _refresh_if_needed(session, request)
        if tokens:
            entries.append((session.id, session.user_id, tokens))
            seen_session_ids.add(session.id)

    if entries:
        log.info(
            f"Token pool: built pool with {len(entries)} account(s) for user {user.id}"
        )

    return TokenPool(entries)


async def _refresh_if_needed(
    session: "OAuthSessionModel", request: Request
) -> Optional[ClaudeTokens]:
    """Refresh a session's tokens if expired. Returns None if unrecoverable."""
    try:
        tokens = ClaudeTokens.from_dict(session.token)

        if tokens.expires_within(300):  # 5 min buffer
            if not tokens.refresh_token:
                log.warning(
                    f"Token pool: session {session.id[:8]}… expired, no refresh token"
                )
                OAuthSessions.delete_session_by_id(session.id)
                return None

            auth = ClaudeAuth(get_redirect_uri(request))
            new_tokens = await auth.refresh_token(tokens.refresh_token)
            OAuthSessions.update_session_by_id(session.id, new_tokens.to_dict())
            log.info(f"Token pool: refreshed session {session.id[:8]}…")
            return new_tokens

        return tokens
    except Exception as e:
        log.error(f"Token pool: failed to prepare session {session.id[:8]}…: {e}")
        return None


# Available Claude models (fetched dynamically when possible)
# Updated with Claude 4 family models from Claude Code CLI v2.1.33
CLAUDE_MODELS = [
    # Claude 4 Opus family (most capable)
    {
        "id": "claude-opus-4-6",
        "name": "Claude Opus 4.6",
        "description": "Latest Opus with 1M context support",
        "context_window": 200000,  # 1M available with beta flag
        "max_output": 64000,
    },
    {
        "id": "claude-opus-4-5-20251101",
        "name": "Claude Opus 4.5",
        "description": "Enhanced Opus with 64K output",
        "context_window": 200000,
        "max_output": 64000,
    },
    {
        "id": "claude-opus-4-1-20250805",
        "name": "Claude Opus 4.1",
        "description": "Improved Opus model",
        "context_window": 200000,
        "max_output": 32000,
    },
    {
        "id": "claude-opus-4-20250514",
        "name": "Claude Opus 4",
        "description": "Original Claude 4 Opus",
        "context_window": 200000,
        "max_output": 32000,
    },
    # Claude 4 Sonnet family (balanced)
    {
        "id": "claude-sonnet-4-5-20250929",
        "name": "Claude Sonnet 4.5",
        "description": "Enhanced Sonnet with 64K output",
        "context_window": 200000,
        "max_output": 64000,
    },
    {
        "id": "claude-sonnet-4-20250514",
        "name": "Claude Sonnet 4",
        "description": "Claude 4 Sonnet - balanced performance",
        "context_window": 200000,
        "max_output": 64000,
    },
    # Claude 4 Haiku family (fast)
    {
        "id": "claude-haiku-4-5-20251001",
        "name": "Claude Haiku 4.5",
        "description": "Fast and efficient with 64K output",
        "context_window": 200000,
        "max_output": 64000,
    },
    # Claude 3.x family (legacy)
    {
        "id": "claude-3-7-sonnet-20250219",
        "name": "Claude 3.7 Sonnet",
        "description": "Claude 3.7 Sonnet with extended thinking",
        "context_window": 200000,
        "max_output": 128000,
    },
    {
        "id": "claude-3-5-sonnet-20241022",
        "name": "Claude 3.5 Sonnet",
        "description": "Previous Claude 3.5 Sonnet",
        "context_window": 200000,
        "max_output": 8192,
    },
    {
        "id": "claude-3-5-haiku-20241022",
        "name": "Claude 3.5 Haiku",
        "description": "Fast and efficient Claude 3.5 model",
        "context_window": 200000,
        "max_output": 8192,
    },
]


# ============================================================================
# Utility Functions
# ============================================================================


def get_redirect_uri(request: Request) -> str:
    """
    Returns the OAuth redirect URI for Anthropic's hosted callback flow.

    Claude's OAuth client (client_id 9d1c250a-...) only accepts:
    - https://platform.claude.com/oauth/code/callback (hosted callback)
    - http://localhost:54545/callback (local CLI only)

    Since we're a hosted web app (not localhost), we MUST use the hosted
    callback URI. The user will see the auth code on Anthropic's page and
    paste it back into our UI.
    """
    return CLAUDE_HOSTED_CALLBACK_URI


async def get_user_tokens(user: UserModel, request: Request) -> Optional[ClaudeTokens]:
    """
    Gets Claude tokens for a user, refreshing if expired.

    Uses org-wide fallback: if user has no personal Anthropic session,
    falls back to any admin's session (org-wide shared token).

    Returns None if no session exists (neither personal nor org-wide).
    Raises HTTPException if tokens are expired and cannot be refreshed.
    """
    # Try user's own session first
    session = OAuthSessions.get_session_by_provider_and_user_id(
        ANTHROPIC_PROVIDER, user.id
    )

    # Fallback to org-wide admin session
    if not session:
        session = OAuthSessions.get_org_session_by_provider(ANTHROPIC_PROVIDER)
        if session:
            log.info(
                f"User {user.id} using org-wide Anthropic session from user {session.user_id}"
            )

    if not session:
        return None

    tokens = ClaudeTokens.from_dict(session.token)

    # Check if tokens need refresh (expired or expiring within 5 minutes)
    if tokens.expires_within(300):  # 5 minutes buffer
        log.info(f"Refreshing tokens for user {user.id}")

        if not tokens.refresh_token:
            # No refresh token, user needs to re-authenticate
            OAuthSessions.delete_session_by_id(session.id)
            raise HTTPException(
                status_code=401,
                detail="Anthropic session expired. Please re-authenticate.",
            )

        try:
            auth = ClaudeAuth(get_redirect_uri(request))
            new_tokens = await auth.refresh_token(tokens.refresh_token)

            # Update stored tokens
            OAuthSessions.update_session_by_id(session.id, new_tokens.to_dict())
            tokens = new_tokens
            log.info(f"Successfully refreshed tokens for user {user.id}")

        except Exception as e:
            log.error(f"Failed to refresh tokens for user {user.id}: {e}")
            OAuthSessions.delete_session_by_id(session.id)
            raise HTTPException(
                status_code=401,
                detail="Failed to refresh Anthropic tokens. Please re-authenticate.",
            )

    return tokens


# Supported image media types for Anthropic
SUPPORTED_IMAGE_TYPES = {
    "image/jpeg": "image/jpeg",
    "image/png": "image/png",
    "image/gif": "image/gif",
    "image/webp": "image/webp",
}

# Supported document types for Anthropic (PDF support)
SUPPORTED_DOCUMENT_TYPES = {
    "application/pdf": "application/pdf",
}


def parse_data_url(data_url: str) -> tuple[Optional[str], Optional[str]]:
    """
    Parses a data URL and returns (media_type, base64_data).
    Returns (None, None) if not a valid data URL.
    """
    match = re.match(r"data:([^;]+);base64,(.+)", data_url)
    if match:
        return match.group(1), match.group(2)
    return None, None


def convert_openai_image_to_anthropic(image_block: dict) -> Optional[dict]:
    """
    Converts an OpenAI image_url block to Anthropic image/document format.

    OpenAI format:
        {"type": "image_url", "image_url": {"url": "..."}}

    Anthropic image format:
        {"type": "image", "source": {"type": "base64", "media_type": "...", "data": "..."}}
        or
        {"type": "image", "source": {"type": "url", "url": "..."}}

    Anthropic document format (for PDFs):
        {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": "..."}}
    """
    image_url_obj = image_block.get("image_url", {})
    url = image_url_obj.get("url", "")

    if not url:
        return None

    # Handle data URLs (base64 encoded)
    if url.startswith("data:"):
        media_type, base64_data = parse_data_url(url)
        if not media_type or not base64_data:
            log.warning(f"Invalid data URL format")
            return None

        # Check if it's a PDF
        if media_type in SUPPORTED_DOCUMENT_TYPES:
            return {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64_data,
                },
            }

        # Check if it's a supported image type
        if media_type in SUPPORTED_IMAGE_TYPES:
            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64_data,
                },
            }

        log.warning(f"Unsupported media type: {media_type}")
        return None

    # Handle HTTP(S) URLs - Anthropic supports URL source type
    if url.startswith("http://") or url.startswith("https://"):
        return {
            "type": "image",
            "source": {
                "type": "url",
                "url": url,
            },
        }

    # Handle local file URLs (/api/v1/files/{id}/content)
    # Return a placeholder that will be resolved by async processing
    if url.startswith("/api/v1/files/"):
        # Extract file ID from URL
        match = re.match(r"/api/v1/files/([^/]+)/content", url)
        if match:
            file_id = match.group(1)
            return {
                "type": "__local_file__",
                "file_id": file_id,
                "url": url,
            }
        log.warning(f"Could not extract file ID from URL: {url}")
        return None

    log.warning(f"Unsupported URL format: {url[:50]}...")
    return None


def convert_openai_content_to_anthropic(content: Union[str, List[dict]]) -> List[dict]:
    """
    Converts OpenAI message content to Anthropic content blocks.

    OpenAI content can be:
    - A simple string
    - A list of content blocks: [{"type": "text", "text": "..."}, {"type": "image_url", ...}]

    Anthropic content is always a list of blocks:
    - [{"type": "text", "text": "..."}, {"type": "image", "source": {...}}]
    """
    # Simple string content
    if isinstance(content, str):
        return [{"type": "text", "text": content}]

    # List of content blocks
    if isinstance(content, list):
        anthropic_blocks = []

        for block in content:
            block_type = block.get("type", "")

            if block_type == "text":
                text = block.get("text", "")
                if text:
                    anthropic_blocks.append({"type": "text", "text": text})

            elif block_type == "image_url":
                anthropic_block = convert_openai_image_to_anthropic(block)
                if anthropic_block:
                    anthropic_blocks.append(anthropic_block)

            # Handle tool_result blocks (for tool responses)
            elif block_type == "tool_result":
                anthropic_blocks.append(block)

            else:
                log.warning(f"Unknown content block type: {block_type}")

        return anthropic_blocks if anthropic_blocks else [{"type": "text", "text": ""}]

    # Fallback for unexpected content types
    return [{"type": "text", "text": str(content)}]


async def resolve_local_files_in_messages(
    messages: List[dict], request: Request, user
) -> List[dict]:
    """
    Resolves local file references in Anthropic messages.

    Finds __local_file__ placeholders and fetches the actual file content,
    converting to base64 for Anthropic.
    """
    from open_webui.models.files import Files
    from open_webui.storage.provider import Storage

    resolved_messages = []

    for msg in messages:
        content = msg.get("content", [])
        if not isinstance(content, list):
            resolved_messages.append(msg)
            continue

        resolved_content = []
        for block in content:
            if block.get("type") == "__local_file__":
                file_id = block.get("file_id")
                try:
                    file = Files.get_file_by_id(file_id)
                    if not file or not file.path:
                        log.warning(f"File not found or has no path: {file_id}")
                        continue

                    # Get file content
                    file_path = Storage.get_file(file.path)
                    with open(file_path, "rb") as f:
                        file_data = f.read()

                    # Get media type from file metadata
                    media_type = "application/octet-stream"
                    if file.meta:
                        media_type = file.meta.get("content_type", media_type)
                    base64_data = base64.b64encode(file_data).decode("utf-8")

                    # Determine if it's an image or document
                    if media_type in SUPPORTED_IMAGE_TYPES:
                        resolved_content.append(
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": base64_data,
                                },
                            }
                        )
                    elif media_type in SUPPORTED_DOCUMENT_TYPES:
                        resolved_content.append(
                            {
                                "type": "document",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": base64_data,
                                },
                            }
                        )
                    else:
                        log.warning(f"Unsupported file type: {media_type}")

                except Exception as e:
                    log.error(f"Failed to fetch file {file_id}: {e}")
            else:
                resolved_content.append(block)

        resolved_messages.append(
            {
                **msg,
                "content": resolved_content
                if resolved_content
                else [{"type": "text", "text": ""}],
            }
        )

    return resolved_messages


def convert_openai_to_anthropic(openai_payload: dict) -> dict:
    """
    Converts OpenAI chat completion format to Anthropic Messages API format.

    Key differences:
    - System message is a top-level parameter in Anthropic
    - Message format is similar but Anthropic uses 'content' as list of blocks
    - max_tokens is required in Anthropic
    - Different parameter names (stop → stop_sequences, etc.)
    """
    messages = openai_payload.get("messages", [])

    # Extract system message (Anthropic requires it as top-level param)
    system_message = None
    anthropic_messages = []

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "system":
            # Anthropic takes system as a separate parameter
            # System messages are always text, extract if it's a list
            if isinstance(content, list):
                text_parts = [
                    b.get("text", "") for b in content if b.get("type") == "text"
                ]
                content = "\n".join(text_parts)
            if system_message:
                system_message += "\n\n" + content
            else:
                system_message = content
        elif role in ("user", "assistant"):
            # Convert content (handles text, images, PDFs)
            anthropic_content = convert_openai_content_to_anthropic(content)
            anthropic_messages.append(
                {
                    "role": role,
                    "content": anthropic_content,
                }
            )
        elif role == "tool":
            # Tool responses need special handling
            anthropic_messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.get("tool_call_id", ""),
                            "content": content
                            if isinstance(content, str)
                            else str(content),
                        }
                    ],
                }
            )

    # Build Anthropic payload
    anthropic_payload = {
        "model": openai_payload.get("model", "claude-sonnet-4-20250514"),
        "messages": anthropic_messages,
        "max_tokens": openai_payload.get("max_tokens", 4096),
    }

    # Build system parameter as array with billing header (required for OAuth)
    # The billing header MUST be first - this is how Anthropic tracks OAuth usage
    # NOTE: billing text is a placeholder here — the actual dynamic hash is injected
    # in generate_chat_completion() after we have the CLI version cached.
    system_blocks = [
        {"type": "text", "text": "__BILLING_PLACEHOLDER__"},
    ]

    if system_message:
        system_blocks.append({"type": "text", "text": system_message})

    anthropic_payload["system"] = system_blocks

    # Optional parameters
    if "temperature" in openai_payload:
        anthropic_payload["temperature"] = openai_payload["temperature"]

    if "top_p" in openai_payload:
        anthropic_payload["top_p"] = openai_payload["top_p"]

    if "stop" in openai_payload:
        stop = openai_payload["stop"]
        if isinstance(stop, str):
            anthropic_payload["stop_sequences"] = [stop]
        elif isinstance(stop, list):
            anthropic_payload["stop_sequences"] = stop

    if openai_payload.get("stream", False):
        anthropic_payload["stream"] = True

    # Handle tools/functions if present
    anthropic_tools = []
    if "tools" in openai_payload:
        anthropic_tools = convert_openai_tools_to_anthropic(openai_payload["tools"])

    # Check for web_search feature (OpenWebUI features object or direct flag)
    # OpenWebUI sends features in the payload when enabled
    features = openai_payload.get("features", {})
    web_search_enabled = features.get("web_search", False)

    # Also check for direct web_search flag (for API compatibility)
    if openai_payload.get("web_search", False):
        web_search_enabled = True

    if web_search_enabled:
        # Inject Anthropic's built-in web search tool
        # This is a "server tool" that Anthropic runs server-side
        # Cost: ~$0.01 per search request
        web_search_tool = {
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": 8,  # Default max searches per request
        }
        # Check for domain restrictions
        if openai_payload.get("web_search_allowed_domains"):
            web_search_tool["allowed_domains"] = openai_payload[
                "web_search_allowed_domains"
            ]
        if openai_payload.get("web_search_blocked_domains"):
            web_search_tool["blocked_domains"] = openai_payload[
                "web_search_blocked_domains"
            ]

        anthropic_tools.append(web_search_tool)
        log.debug("Web search tool injected into request")

    if anthropic_tools:
        anthropic_payload["tools"] = anthropic_tools

    # Handle thinking/reasoning effort (extended thinking feature)
    # OpenWebUI uses reasoning_effort in params, we convert to Anthropic's thinking format
    # Two modes:
    #   - Enabled: {"thinking": {"type": "enabled", "budget_tokens": N}} - you set the budget
    #   - Adaptive: {"thinking": {"type": "adaptive"}} - Claude decides (opus-4-6 only)
    reasoning_effort = openai_payload.get("reasoning_effort")
    thinking_budget = openai_payload.get("thinking_budget") or openai_payload.get(
        "budget_tokens"
    )
    model = anthropic_payload.get("model", "")

    # Check if model supports adaptive thinking (only opus-4-6)
    supports_adaptive = "opus-4-6" in model.lower()

    # Map reasoning_effort strings to budget tokens
    EFFORT_TO_BUDGET = {
        "low": 4000,
        "medium": 10000,
        "high": 32000,
        "max": 64000,
    }

    if thinking_budget:
        # Direct budget_tokens specified
        try:
            budget = int(thinking_budget)
            if budget > 0:
                anthropic_payload["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": budget,
                }
                log.debug(f"Thinking enabled with budget: {budget} tokens")
        except (ValueError, TypeError):
            log.warning(f"Invalid thinking_budget value: {thinking_budget}")
    elif reasoning_effort:
        effort_str = str(reasoning_effort).lower().strip()

        # Check for adaptive mode
        if effort_str == "adaptive" or effort_str == "auto":
            if supports_adaptive:
                anthropic_payload["thinking"] = {"type": "adaptive"}
                log.debug("Adaptive thinking enabled (Claude decides budget)")
            else:
                # Fall back to high budget for non-adaptive models
                anthropic_payload["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": EFFORT_TO_BUDGET["high"],
                }
                log.debug(
                    f"Model {model} doesn't support adaptive thinking, using 'high' budget"
                )
        elif effort_str in EFFORT_TO_BUDGET:
            budget = EFFORT_TO_BUDGET[effort_str]
            anthropic_payload["thinking"] = {
                "type": "enabled",
                "budget_tokens": budget,
            }
            log.debug(f"Thinking enabled with effort '{effort_str}': {budget} tokens")
        elif effort_str.isdigit():
            # Allow numeric string as direct budget
            budget = int(effort_str)
            if budget > 0:
                anthropic_payload["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": budget,
                }
                log.debug(f"Thinking enabled with budget: {budget} tokens")

    # Handle structured outputs (response_format with json_schema)
    # OpenAI format: response_format: {type: "json_schema", json_schema: {name: "...", schema: {...}}}
    # Anthropic format: output_format: {type: "json_schema", schema: {...}}
    response_format = openai_payload.get("response_format", {})
    if response_format.get("type") == "json_schema":
        json_schema_obj = response_format.get("json_schema", {})
        schema = json_schema_obj.get("schema")
        if schema:
            anthropic_payload["output_format"] = {
                "type": "json_schema",
                "schema": schema,
            }
            log.debug("Structured outputs enabled with JSON schema")

    # Also support direct output_format passthrough for API compatibility
    if "output_format" in openai_payload:
        anthropic_payload["output_format"] = openai_payload["output_format"]
        log.debug("Direct output_format passthrough")

    return anthropic_payload


def convert_openai_tools_to_anthropic(openai_tools: list) -> list:
    """Converts OpenAI tool format to Anthropic tool format."""
    anthropic_tools = []

    for tool in openai_tools:
        if tool.get("type") == "function":
            func = tool.get("function", {})
            anthropic_tools.append(
                {
                    "name": func.get("name", ""),
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {"type": "object"}),
                }
            )

    return anthropic_tools


def convert_anthropic_to_openai_response(anthropic_response: dict, model: str) -> dict:
    """
    Converts Anthropic Messages API response to OpenAI chat completion format.

    Handles:
    - text blocks (normal response content)
    - thinking blocks (extended thinking feature)
    - tool_use blocks (function calling)
    - server_tool_use blocks (built-in tools like web_search)
    """
    content = ""
    thinking_content = ""
    tool_calls = []

    for block in anthropic_response.get("content", []):
        block_type = block.get("type", "")

        if block_type == "text":
            content += block.get("text", "")

        elif block_type == "thinking":
            # Extended thinking block - include in response with collapsible format
            thinking_text = block.get("thinking", "")
            if thinking_text:
                thinking_content += thinking_text

        elif block_type == "tool_use":
            tool_calls.append(
                {
                    "id": block.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": block.get("name", ""),
                        "arguments": json.dumps(block.get("input", {})),
                    },
                }
            )

        elif block_type == "server_tool_use":
            # Built-in server tools like web_search
            tool_name = block.get("name", "server_tool")
            tool_input = block.get("input", {})
            # Include as informational text since these are server-side
            if tool_name == "web_search":
                query = tool_input.get("query", "")
                content += f"\n🔍 *Searched: {query}*\n"

    # Prepend thinking content if present
    if thinking_content:
        content = (
            f"<details open>\n<summary>💭 Thinking...</summary>\n\n"
            f"{thinking_content}\n\n</details>\n\n{content}"
        )

    # Map Anthropic stop_reason to OpenAI finish_reason
    stop_reason_map = {
        "end_turn": "stop",
        "stop_sequence": "stop",
        "max_tokens": "length",
        "tool_use": "tool_calls",
    }
    finish_reason = stop_reason_map.get(
        anthropic_response.get("stop_reason", ""), "stop"
    )

    message = {
        "role": "assistant",
        "content": content if content else None,
    }

    if tool_calls:
        message["tool_calls"] = tool_calls

    return {
        "id": anthropic_response.get("id", f"chatcmpl-{int(time.time())}"),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": anthropic_response.get("usage", {}).get("input_tokens", 0),
            "completion_tokens": anthropic_response.get("usage", {}).get(
                "output_tokens", 0
            ),
            "total_tokens": (
                anthropic_response.get("usage", {}).get("input_tokens", 0)
                + anthropic_response.get("usage", {}).get("output_tokens", 0)
            ),
        },
    }


async def convert_anthropic_stream_to_openai(
    response: aiohttp.ClientResponse, model: str
):
    """
    Converts Anthropic SSE stream to OpenAI SSE stream format.

    Anthropic events:
    - message_start: Contains message metadata
    - content_block_start: Start of a content block
    - content_block_delta: Content delta (text or tool input)
    - content_block_stop: End of content block
    - message_delta: Message-level updates (stop_reason, usage)
    - message_stop: End of message

    OpenAI format:
    - data: {"id": ..., "choices": [{"delta": {"content": "..."}}]}
    """
    message_id = f"chatcmpl-{int(time.time())}"
    # Track content block types by index for proper closing
    block_types = {}

    async for line in response.content:
        line = line.decode("utf-8").strip()

        if not line:
            continue

        if line.startswith("event:"):
            event_type = line[6:].strip()
            continue

        if not line.startswith("data:"):
            continue

        data_str = line[5:].strip()
        if data_str == "[DONE]":
            yield "data: [DONE]\n\n"
            break

        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            continue

        event_type = data.get("type", "")

        if event_type == "message_start":
            message_id = data.get("message", {}).get("id", message_id)
            # Send initial chunk with role
            openai_chunk = {
                "id": message_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "content": ""},
                        "finish_reason": None,
                    }
                ],
            }
            yield f"data: {json.dumps(openai_chunk)}\n\n"

        elif event_type == "content_block_start":
            # Handle start of thinking blocks (extended thinking feature)
            content_block = data.get("content_block", {})
            block_type = content_block.get("type", "")
            block_index = data.get("index", 0)
            block_types[block_index] = block_type

            if block_type == "thinking":
                # Start thinking block - render with details/summary for collapsible UI
                thinking_header = (
                    "\n<details open>\n<summary>💭 Thinking...</summary>\n\n"
                )
                openai_chunk = {
                    "id": message_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": thinking_header},
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(openai_chunk)}\n\n"

            elif block_type == "server_tool_use":
                # Server tool (e.g., web search) starting
                tool_name = content_block.get("name", "tool")
                tool_header = f"\n🔍 *Using {tool_name}...*\n"
                openai_chunk = {
                    "id": message_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": tool_header},
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(openai_chunk)}\n\n"

        elif event_type == "content_block_stop":
            # Handle end of content blocks
            block_index = data.get("index", 0)
            block_type = block_types.get(block_index, "")

            if block_type == "thinking":
                # Close thinking block details tag
                thinking_footer = "\n\n</details>\n\n"
                openai_chunk = {
                    "id": message_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": thinking_footer},
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(openai_chunk)}\n\n"

            # Clean up tracked block
            block_types.pop(block_index, None)

        elif event_type == "content_block_delta":
            delta = data.get("delta", {})
            delta_type = delta.get("type", "")

            if delta_type == "text_delta":
                text = delta.get("text", "")
                openai_chunk = {
                    "id": message_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": text},
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(openai_chunk)}\n\n"

            elif delta_type == "thinking_delta":
                # Extended thinking content - render as part of thinking block
                thinking_text = delta.get("thinking", "")
                if thinking_text:
                    openai_chunk = {
                        "id": message_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": thinking_text},
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(openai_chunk)}\n\n"

        elif event_type == "message_delta":
            delta = data.get("delta", {})
            stop_reason = delta.get("stop_reason")

            if stop_reason:
                stop_reason_map = {
                    "end_turn": "stop",
                    "stop_sequence": "stop",
                    "max_tokens": "length",
                    "tool_use": "tool_calls",
                }
                finish_reason = stop_reason_map.get(stop_reason, "stop")

                openai_chunk = {
                    "id": message_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": finish_reason,
                        }
                    ],
                }
                yield f"data: {json.dumps(openai_chunk)}\n\n"

        elif event_type == "message_stop":
            yield "data: [DONE]\n\n"


async def cleanup_response(
    response: Optional[aiohttp.ClientResponse],
    session: Optional[aiohttp.ClientSession],
):
    """Cleanup aiohttp resources."""
    if response:
        response.close()
    if session:
        await session.close()


# ============================================================================
# OAuth Routes
# ============================================================================


@router.get("/auth/login")
async def anthropic_auth_login(request: Request, user=Depends(get_verified_user)):
    """
    Initiates the Anthropic OAuth PKCE flow.

    Generates a PKCE challenge, stores the verifier in the session,
    and returns the authorization URL for the frontend to open.

    Returns JSON with the OAuth URL - frontend should open this with window.open()
    to avoid CORS issues (OAuth endpoints don't support cross-origin fetch).
    """
    log.info(f"[AUTH_LOGIN] Starting OAuth login for user {user.id}")
    log.info(
        f"[AUTH_LOGIN] Session ID: {request.session.get('session_id', 'NO_SESSION_ID')}"
    )
    log.info(f"[AUTH_LOGIN] Session keys before: {list(request.session.keys())}")

    if not request.app.state.config.ENABLE_ANTHROPIC_API:
        log.error("[AUTH_LOGIN] Anthropic API is disabled")
        raise HTTPException(
            status_code=403,
            detail="Anthropic API is disabled",
        )

    # Generate PKCE challenge
    pkce = PkceChallenge.generate()
    log.info(
        f"[AUTH_LOGIN] Generated PKCE verifier (first 20 chars): {pkce.verifier[:20]}..."
    )

    # Build authorization URL
    redirect_uri = get_redirect_uri(request)
    log.info(f"[AUTH_LOGIN] Redirect URI: {redirect_uri}")
    auth = ClaudeAuth(redirect_uri)
    auth_url, state = auth.build_authorization_url(pkce)
    log.info(f"[AUTH_LOGIN] State: {state}")
    log.info(f"[AUTH_LOGIN] Auth URL: {auth_url[:100]}...")

    # Store PKCE verifier in session for callback validation
    # We use the state (which equals verifier for Claude) as the key
    # Store it temporarily - it will be used in the callback
    request.session["anthropic_pkce_verifier"] = pkce.verifier
    request.session["anthropic_pkce_state"] = state
    request.session["anthropic_user_id"] = user.id

    log.info(f"[AUTH_LOGIN] Session keys after: {list(request.session.keys())}")
    log.info(
        f"[AUTH_LOGIN] Stored verifier in session: {request.session.get('anthropic_pkce_verifier', 'NOT_FOUND')[:20]}..."
    )

    log.info(f"Initiating Anthropic OAuth for user {user.id}")

    # Return URL as JSON - frontend opens with window.open() to avoid CORS
    # DO NOT use RedirectResponse here - it causes CORS issues when called via fetch()
    return {"url": auth_url, "state": state}


@router.get("/auth/callback")
async def anthropic_auth_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
):
    """
    Handles the OAuth callback from Claude.

    Exchanges the authorization code for tokens and stores them
    in the OAuth sessions table.
    """
    log.info(f"[AUTH_CALLBACK] ========== CALLBACK RECEIVED ==========")
    log.info(
        f"[AUTH_CALLBACK] Code present: {bool(code)}, Code length: {len(code) if code else 0}"
    )
    log.info(f"[AUTH_CALLBACK] State: {state}")
    log.info(f"[AUTH_CALLBACK] Error: {error}, Error desc: {error_description}")
    log.info(f"[AUTH_CALLBACK] Session keys: {list(request.session.keys())}")
    log.info(f"[AUTH_CALLBACK] Full URL: {request.url}")
    log.info(f"[AUTH_CALLBACK] Headers: {dict(request.headers)}")

    # Check for errors from OAuth provider
    if error:
        log.error(
            f"[AUTH_CALLBACK] OAuth error from provider: {error} - {error_description}"
        )
        # Redirect to settings with error
        return RedirectResponse(
            url=f"/?error=anthropic_auth_failed&message={error_description or error}"
        )

    if not code or not state:
        log.error(
            f"[AUTH_CALLBACK] Missing code or state. code={bool(code)}, state={bool(state)}"
        )
        return RedirectResponse(
            url="/?error=anthropic_auth_failed&message=Missing+authorization+code"
        )

    # Retrieve stored PKCE data from session
    stored_verifier = request.session.get("anthropic_pkce_verifier")
    stored_state = request.session.get("anthropic_pkce_state")
    user_id = request.session.get("anthropic_user_id")

    log.info(f"[AUTH_CALLBACK] Stored verifier present: {bool(stored_verifier)}")
    log.info(f"[AUTH_CALLBACK] Stored state: {stored_state}")
    log.info(f"[AUTH_CALLBACK] User ID: {user_id}")
    log.info(f"[AUTH_CALLBACK] State match: {state == stored_state}")

    if not stored_verifier or not stored_state or not user_id:
        log.error(
            f"[AUTH_CALLBACK] Missing PKCE data! verifier={bool(stored_verifier)}, state={bool(stored_state)}, user={bool(user_id)}"
        )
        log.error(
            f"[AUTH_CALLBACK] This usually means session was lost between login and callback"
        )
        log.error(
            f"[AUTH_CALLBACK] Check if cookies are being sent/preserved across redirects"
        )
        return RedirectResponse(
            url="/?error=anthropic_auth_failed&message=Session+expired"
        )

    # Validate state matches
    if state != stored_state:
        log.error(
            f"[AUTH_CALLBACK] State mismatch! received={state}, expected={stored_state}"
        )
        return RedirectResponse(
            url="/?error=anthropic_auth_failed&message=Invalid+state"
        )

    try:
        # Exchange code for tokens
        log.info(f"[AUTH_CALLBACK] Starting token exchange...")
        redirect_uri = get_redirect_uri(request)
        log.info(f"[AUTH_CALLBACK] Using redirect_uri: {redirect_uri}")
        auth = ClaudeAuth(redirect_uri)
        log.info(
            f"[AUTH_CALLBACK] Calling exchange_code with code_length={len(code)}, verifier_length={len(stored_verifier)}"
        )
        tokens = await auth.exchange_code(code, stored_verifier, state)
        log.info(
            f"[AUTH_CALLBACK] Token exchange successful! Got tokens with keys: {list(tokens.to_dict().keys()) if tokens else 'None'}"
        )

        # Delete any existing Anthropic session for this user
        log.info(f"[AUTH_CALLBACK] Checking for existing session for user {user_id}")
        existing = OAuthSessions.get_session_by_provider_and_user_id(
            ANTHROPIC_PROVIDER, user_id
        )
        if existing:
            log.info(f"[AUTH_CALLBACK] Deleting existing session {existing.id}")
            OAuthSessions.delete_session_by_id(existing.id)

        # Store new tokens
        log.info(f"[AUTH_CALLBACK] Creating new OAuth session...")
        OAuthSessions.create_session(
            user_id=user_id,
            provider=ANTHROPIC_PROVIDER,
            token=tokens.to_dict(),
        )
        log.info(f"[AUTH_CALLBACK] Session created successfully!")

        log.info(f"Successfully authenticated Anthropic for user {user_id}")

        # Clean up session
        request.session.pop("anthropic_pkce_verifier", None)
        request.session.pop("anthropic_pkce_state", None)
        request.session.pop("anthropic_user_id", None)
        log.info(f"[AUTH_CALLBACK] Cleaned up session, redirecting to success")

        # Redirect to success page
        return RedirectResponse(url="/?anthropic_auth=success")

    except Exception as e:
        log.exception(f"[AUTH_CALLBACK] Failed to exchange Anthropic auth code: {e}")
        import traceback

        log.error(f"[AUTH_CALLBACK] Full traceback:\n{traceback.format_exc()}")
        return RedirectResponse(url=f"/?error=anthropic_auth_failed&message={str(e)}")


class AuthCodeExchange(BaseModel):
    """Request body for manual OAuth code exchange."""

    code: str
    state: str


@router.post("/auth/exchange")
async def anthropic_auth_exchange(
    request: Request,
    body: AuthCodeExchange,
    user=Depends(get_verified_user),
):
    """
    Manually exchanges an OAuth authorization code for tokens.

    Used with the hosted callback flow where Anthropic redirects to
    platform.claude.com/oauth/code/callback and the user copies the
    auth code back into OpenWebUI.
    """
    log.info(f"[AUTH_EXCHANGE] Manual code exchange for user {user.id}")
    log.info(
        f"[AUTH_EXCHANGE] Code length: {len(body.code)}, State: {body.state[:20]}..."
    )

    if not request.app.state.config.ENABLE_ANTHROPIC_API:
        raise HTTPException(status_code=403, detail="Anthropic API is disabled")

    # Retrieve PKCE data from session
    stored_verifier = request.session.get("anthropic_pkce_verifier")
    stored_state = request.session.get("anthropic_pkce_state")
    stored_user_id = request.session.get("anthropic_user_id")

    log.info(
        f"[AUTH_EXCHANGE] Session: verifier={bool(stored_verifier)}, state={bool(stored_state)}, user={stored_user_id}"
    )

    if not stored_verifier or not stored_state or not stored_user_id:
        raise HTTPException(
            status_code=400,
            detail="Session expired. Please start the OAuth flow again.",
        )

    if stored_user_id != user.id:
        raise HTTPException(
            status_code=400,
            detail="Session user mismatch. Please start the OAuth flow again.",
        )

    if body.state != stored_state:
        raise HTTPException(
            status_code=400,
            detail="State mismatch. Please start the OAuth flow again.",
        )

    try:
        redirect_uri = get_redirect_uri(request)
        log.info(f"[AUTH_EXCHANGE] Using redirect_uri: {redirect_uri}")
        auth = ClaudeAuth(redirect_uri)
        tokens = await auth.exchange_code(body.code, stored_verifier, body.state)
        log.info(f"[AUTH_EXCHANGE] Token exchange successful!")

        # Delete any existing session for this user
        existing = OAuthSessions.get_session_by_provider_and_user_id(
            ANTHROPIC_PROVIDER, user.id
        )
        if existing:
            OAuthSessions.delete_session_by_id(existing.id)

        # Store new tokens
        OAuthSessions.create_session(
            user_id=user.id,
            provider=ANTHROPIC_PROVIDER,
            token=tokens.to_dict(),
        )
        log.info(f"[AUTH_EXCHANGE] Session created for user {user.id}")

        # Clean up session
        request.session.pop("anthropic_pkce_verifier", None)
        request.session.pop("anthropic_pkce_state", None)
        request.session.pop("anthropic_user_id", None)

        return {"success": True, "message": "Successfully authenticated with Claude"}

    except Exception as e:
        log.exception(f"[AUTH_EXCHANGE] Failed to exchange code: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to exchange authorization code: {str(e)}",
        )


@router.get("/auth/status")
async def anthropic_auth_status(request: Request, user=Depends(get_verified_user)):
    """
    Returns the authentication status for the current user.
    """
    # Check user's own session first
    session = OAuthSessions.get_session_by_provider_and_user_id(
        ANTHROPIC_PROVIDER, user.id
    )
    is_shared = False

    # Fallback to org-wide admin session
    if not session:
        session = OAuthSessions.get_org_session_by_provider(ANTHROPIC_PROVIDER)
        is_shared = session is not None

    if not session:
        return {
            "authenticated": False,
            "provider": ANTHROPIC_PROVIDER,
        }

    tokens = ClaudeTokens.from_dict(session.token)

    return {
        "authenticated": True,
        "shared": is_shared,
        "provider": ANTHROPIC_PROVIDER,
        "expires_at": int(tokens.expires_at.timestamp()),
        "scopes": tokens.scopes,
        "organization": {
            "uuid": tokens.organization.uuid,
            "name": tokens.organization.name,
        }
        if tokens.organization
        else None,
        "account": {
            "email": tokens.account.email_address,
        }
        if tokens.account
        else None,
    }


@router.post("/auth/logout")
async def anthropic_auth_logout(request: Request, user=Depends(get_verified_user)):
    """
    Logs out the user from Anthropic by deleting their OAuth session.
    """
    session = OAuthSessions.get_session_by_provider_and_user_id(
        ANTHROPIC_PROVIDER, user.id
    )

    if session:
        OAuthSessions.delete_session_by_id(session.id)
        log.info(f"Logged out Anthropic for user {user.id}")

    return {"status": "ok"}


# ============================================================================
# Config Routes
# ============================================================================


@router.get("/config")
async def get_config(request: Request, user=Depends(get_admin_user)):
    """Returns Anthropic API configuration (admin only)."""
    return {
        "ENABLE_ANTHROPIC_API": request.app.state.config.ENABLE_ANTHROPIC_API,
    }


class AnthropicConfigForm(BaseModel):
    ENABLE_ANTHROPIC_API: Optional[bool] = None


@router.post("/config/update")
async def update_config(
    request: Request,
    form_data: AnthropicConfigForm,
    user=Depends(get_admin_user),
):
    """Updates Anthropic API configuration (admin only)."""
    if form_data.ENABLE_ANTHROPIC_API is not None:
        request.app.state.config.ENABLE_ANTHROPIC_API = form_data.ENABLE_ANTHROPIC_API

    return {
        "ENABLE_ANTHROPIC_API": request.app.state.config.ENABLE_ANTHROPIC_API,
    }


# ============================================================================
# Model Routes
# ============================================================================


@router.get("/models")
async def get_models(request: Request, user=Depends(get_verified_user)):
    """
    Returns available Anthropic models.

    Only returns models if the user is authenticated with Anthropic OAuth.
    """
    if not request.app.state.config.ENABLE_ANTHROPIC_API:
        return {"data": []}

    # Check if user has Anthropic OAuth session
    tokens = await get_user_tokens(user, request)

    if not tokens:
        return {"data": []}

    # Return available models
    models = []
    for model in CLAUDE_MODELS:
        models.append(
            {
                "id": model["id"],
                "name": model["name"],
                "object": "model",
                "created": int(time.time()),
                "owned_by": "anthropic",
                "anthropic": model,
                "connection_type": "external",
            }
        )

    return {"data": models}


# ============================================================================
# Token Pool Admin
# ============================================================================


@router.get("/pool/status")
async def get_pool_status(request: Request, user=Depends(get_admin_user)):
    """
    Admin endpoint: returns the status of all connected Claude accounts
    and their current rate-limit cooldown state.
    """
    all_sessions = OAuthSessions.get_all_sessions_by_provider(ANTHROPIC_PROVIDER)
    now = time.time()

    accounts = []
    for session in all_sessions:
        cooldown_until = _token_cooldowns.get(session.id, 0.0)
        token_data = session.token
        account_info = (
            token_data.get("account", {}) if isinstance(token_data, dict) else {}
        )

        accounts.append(
            {
                "session_id": session.id,
                "user_id": session.user_id,
                "account_email": account_info.get("email_address", "unknown"),
                "is_available": now >= cooldown_until,
                "cooldown_seconds_remaining": max(0, round(cooldown_until - now)),
                "updated_at": session.updated_at,
            }
        )

    return {
        "total_accounts": len(accounts),
        "available_accounts": sum(1 for a in accounts if a["is_available"]),
        "accounts": accounts,
    }


# ============================================================================
# Chat Completions
# ============================================================================


@router.post("/chat/completions")
async def generate_chat_completion(
    request: Request,
    form_data: dict,
    user=Depends(get_verified_user),
):
    """
    Proxies chat completion requests to Anthropic API.

    Accepts OpenAI-compatible format and translates to/from Anthropic format.
    Requires user to be authenticated with Anthropic OAuth.
    """
    if not request.app.state.config.ENABLE_ANTHROPIC_API:
        raise HTTPException(
            status_code=403,
            detail="Anthropic API is disabled",
        )

    # Build token pool (multi-account rotation)
    pool = await get_token_pool(user, request)

    if not pool.has_tokens:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated with Anthropic. Please connect your Claude account.",
        )

    # Get first available token from pool
    pool_entry = pool.get_next_available()
    if not pool_entry:
        raise HTTPException(
            status_code=429,
            detail="All Claude accounts are currently rate-limited. Please try again later.",
        )
    current_session_id, tokens = pool_entry

    # Extract features from metadata (middleware pops it from form_data)
    # Features enable Anthropic's built-in capabilities like web_search
    metadata = form_data.get("metadata", {})
    features = form_data.get("features") or metadata.get("features", {})
    if features:
        form_data["features"] = features
        log.debug(f"Features enabled: {list(features.keys())}")

    # Convert OpenAI format to Anthropic format
    anthropic_payload = convert_openai_to_anthropic(form_data)

    # Resolve local file references (images, PDFs) to base64
    anthropic_payload["messages"] = await resolve_local_files_in_messages(
        anthropic_payload["messages"], request, user
    )

    model = anthropic_payload.get("model", "claude-sonnet-4-20250514")
    is_streaming = anthropic_payload.get("stream", False)

    # ---- Dynamic version + billing hash (matching opencode-anthropic-auth) ----
    cli_version = await get_claude_cli_version()
    sdk_version = await get_stainless_sdk_version()

    # Compute dynamic billing hash from first user message
    first_user_message = ""
    msgs = anthropic_payload.get("messages", [])
    if msgs:
        first_msg = msgs[0]
        content = first_msg.get("content", "")
        if isinstance(content, str):
            first_user_message = content
        elif isinstance(content, list) and content:
            first_user_message = (
                content[0].get("text", "") if isinstance(content[0], dict) else ""
            )

    billing_hash = compute_billing_hash(first_user_message, cli_version)
    billing_header_text = (
        f"x-anthropic-billing-header: cc_version={cli_version}.{billing_hash}; "
        f"cc_entrypoint=cli; cch=00000;"
    )

    # Replace billing placeholder in system blocks
    system_blocks = anthropic_payload.get("system", [])
    for i, block in enumerate(system_blocks):
        if isinstance(block, dict) and block.get("text") == "__BILLING_PLACEHOLDER__":
            system_blocks[i] = {"type": "text", "text": billing_header_text}
            break
    anthropic_payload["system"] = system_blocks

    log.debug(f"Anthropic request: {json.dumps(anthropic_payload)[:500]}")

    # OAuth requires specific headers to work properly
    # See: opencode-anthropic-auth for reference implementation
    headers = {
        "Content-Type": "application/json",
        "Authorization": tokens.authorization_header(),
        "anthropic-version": ANTHROPIC_API_VERSION,
        "anthropic-beta": ANTHROPIC_OAUTH_BETA,  # CRITICAL: enables OAuth auth
        "anthropic-dangerous-direct-browser-access": "true",
        "x-app": "cli",
        "User-Agent": ANTHROPIC_USER_AGENT_TEMPLATE.format(version=cli_version),
        # X-Stainless headers (Anthropic SDK identification — must match JS SDK)
        "X-Stainless-Lang": "js",
        "X-Stainless-Package-Version": sdk_version,
        "X-Stainless-OS": "Linux",
        "X-Stainless-Arch": "x64",
        "X-Stainless-Runtime": "node",
        "X-Stainless-Runtime-Version": "22.13.1",
        "X-Stainless-Helper-Method": "stream",
        "X-Stainless-Timeout": "600",
    }

    # API URL with ?beta=true query parameter (required for OAuth)
    api_url = f"{CLAUDE_API_URL}/messages?beta=true"

    r = None
    session = None

    try:
        session = aiohttp.ClientSession(
            trust_env=True,
            timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT),
        )

        # Retry loop with exponential backoff (matching opencode-anthropic-auth)
        idempotency_key = f"stainless-node-retry-{_uuid.uuid4()}"

        for retry in range(MAX_OVERLOAD_RETRIES + 1):
            if retry > 0:
                headers["x-stainless-retry-count"] = str(retry)
                headers["idempotency-key"] = idempotency_key
                delay = min(
                    BASE_RETRY_DELAY_MS * (2 ** (retry - 1)), MAX_RETRY_DELAY_MS
                )
                jitter = random.random() * 0.25 * delay
                wait_ms = round(delay + jitter)
                log.warning(
                    f"[retry] attempt {retry + 1}/{MAX_OVERLOAD_RETRIES + 1}, "
                    f"waiting {wait_ms}ms"
                )
                await asyncio.sleep(wait_ms / 1000.0)

            r = await session.request(
                method="POST",
                url=api_url,
                json=anthropic_payload,
                headers=headers,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            )

            # 529 — server overloaded
            if r.status == 529:
                should_retry = r.headers.get("x-should-retry")
                if should_retry == "false" or retry >= MAX_OVERLOAD_RETRIES:
                    log.error(f"[529] giving up after {retry + 1} attempts")
                    break
                log.warning(f"[529] server overloaded (x-should-retry={should_retry})")
                await cleanup_response(r, session=None)
                continue

            # 408/409 — retryable
            if r.status in (408, 409):
                if retry < MAX_OVERLOAD_RETRIES:
                    log.warning(f"[{r.status}] retryable, attempt {retry + 1}")
                    await cleanup_response(r, session=None)
                    continue
                break

            # 5xx (not 529) — retry if server says so
            if r.status >= 500 and r.status != 529:
                should_retry = r.headers.get("x-should-retry")
                if should_retry == "true" and retry < MAX_OVERLOAD_RETRIES:
                    log.warning(f"[{r.status}] server error, x-should-retry=true")
                    await cleanup_response(r, session=None)
                    continue

            # 401 — token rejected, attempt refresh + retry
            if r.status == 401 and retry == 0:
                log.warning(
                    f"[401] token rejected for session {current_session_id[:8]}…, "
                    "attempting refresh"
                )
                try:
                    await cleanup_response(r, session=None)
                    auth_client = ClaudeAuth(get_redirect_uri(request))
                    new_tokens = await auth_client.refresh_from_tokens(tokens)
                    # Persist refreshed tokens using the pool's session_id
                    OAuthSessions.update_session_by_id(
                        current_session_id, new_tokens.to_dict()
                    )
                    headers["Authorization"] = new_tokens.authorization_header()
                    tokens = new_tokens
                    log.info(
                        f"[401] token refreshed for session {current_session_id[:8]}…, "
                        "retrying request"
                    )
                    continue
                except Exception as refresh_err:
                    log.error(f"[401] token refresh failed: {refresh_err}")
                    # Try rotating to another token instead
                    next_entry = pool.get_next_available()
                    if next_entry and next_entry[0] != current_session_id:
                        current_session_id, tokens = next_entry
                        headers["Authorization"] = tokens.authorization_header()
                        log.info(
                            f"[401] rotated to session {current_session_id[:8]}… "
                            "after refresh failure"
                        )
                        continue

            # 403 — check for revoked token
            if r.status == 403:
                try:
                    body_403 = await r.text()
                    if "OAuth token has been revoked" in body_403:
                        log.error("[403] OAuth token revoked")
                        await cleanup_response(r, session)
                        raise HTTPException(
                            status_code=403,
                            detail="Anthropic OAuth token has been revoked. Please re-authenticate.",
                        )
                except HTTPException:
                    raise
                except Exception:
                    pass

            # 429 — rate limited: try rotating to another account
            if r.status == 429:
                retry_after_ms_str = r.headers.get("retry-after-ms")
                retry_after_str = r.headers.get("retry-after")
                wait = (
                    int(retry_after_ms_str)
                    if retry_after_ms_str
                    else int(retry_after_str) * 1000
                    if retry_after_str
                    else 60000
                )
                log.warning(
                    f"[429] rate limited on session {current_session_id[:8]}…, "
                    f"retry-after={wait}ms"
                )

                # Mark this token as rate-limited in the pool
                TokenPool.mark_rate_limited(current_session_id, wait)

                # Try rotating to the next available token
                next_entry = pool.get_next_available()
                if next_entry:
                    next_session_id, next_tokens = next_entry
                    # Check if we got the same token back (only 1 in pool)
                    if next_session_id != current_session_id:
                        log.info(
                            f"[429] rotating from session {current_session_id[:8]}… "
                            f"to {next_session_id[:8]}…"
                        )
                        await cleanup_response(r, session=None)
                        current_session_id = next_session_id
                        tokens = next_tokens
                        headers["Authorization"] = tokens.authorization_header()
                        # Don't count this as a retry — it's a fresh account
                        continue

                # No other account available — fall back to original retry behavior
                if wait > MAX_RETRY_DELAY_MS:
                    log.error(
                        f"[429] retry-after ({wait}ms) exceeds max "
                        f"({MAX_RETRY_DELAY_MS}ms) and no other accounts "
                        f"available, returning error to client"
                    )
                    break

                if retry < MAX_OVERLOAD_RETRIES:
                    await cleanup_response(r, session=None)
                    await asyncio.sleep(wait / 1000.0)
                    continue

            # Success — clear any cooldown on this token
            if r.status < 400:
                TokenPool.clear_cooldown(current_session_id)

            break  # Success or non-retryable error

        # Handle error responses
        if r.status >= 400:
            try:
                error_data = await r.json()
                error_message = error_data.get("error", {}).get(
                    "message", str(r.status)
                )
            except Exception:
                error_message = await r.text()

            log.error(f"Anthropic API error: {r.status} - {error_message}")
            await cleanup_response(r, session)

            raise HTTPException(
                status_code=r.status,
                detail=f"Anthropic API error: {error_message}",
            )

        if is_streaming:
            return StreamingResponse(
                convert_anthropic_stream_to_openai(r, model),
                status_code=r.status,
                media_type="text/event-stream",
                background=BackgroundTask(
                    cleanup_response, response=r, session=session
                ),
            )
        else:
            response_data = await r.json()
            await cleanup_response(r, session)

            # Convert to OpenAI format
            openai_response = convert_anthropic_to_openai_response(response_data, model)
            return openai_response

    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error calling Anthropic API: {e}")
        if r:
            await cleanup_response(r, session)
        raise HTTPException(
            status_code=500,
            detail=f"Error calling Anthropic API: {str(e)}",
        )
