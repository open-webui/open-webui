"""
SharePoint/OneDrive API Router for OpenWebUI

Provides:
1. OAuth PKCE authentication flow for Microsoft Graph API
2. File browsing for OneDrive and SharePoint
3. File download to OpenWebUI storage
"""

import json
import logging
import time
import uuid
from typing import Optional, List

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from open_webui.utils.auth import get_verified_user
from open_webui.utils.microsoft_auth import (
    MSGraphAuth,
    MSGraphTokens,
    PkceChallenge,
)
from open_webui.models.oauth_sessions import OAuthSessions
from open_webui.models.users import UserModel
from open_webui.models.files import Files, FileForm
from open_webui.models.groups import Groups
from open_webui.storage.provider import Storage

from open_webui.config import (
    SHAREPOINT_CLIENT_ID,
    SHAREPOINT_CLIENT_SECRET,
    SHAREPOINT_TENANT_ID,
    SHAREPOINT_TENANTS,
    ENABLE_SHAREPOINT_INTEGRATION,
)

log = logging.getLogger(__name__)

router = APIRouter()

# Provider name for OAuth sessions
SHAREPOINT_PROVIDER = "microsoft_sharepoint"

# Microsoft Graph API base URL
MS_GRAPH_API_URL = "https://graph.microsoft.com/v1.0"


# ============================================================================
# Pydantic Models
# ============================================================================


class DriveItem(BaseModel):
    id: str
    name: str
    size: Optional[int] = None
    is_folder: bool = False
    mime_type: Optional[str] = None
    web_url: Optional[str] = None
    modified_at: Optional[str] = None
    drive_id: Optional[str] = None


class DriveInfo(BaseModel):
    id: str
    name: str
    drive_type: str  # "personal", "business", "documentLibrary"
    web_url: Optional[str] = None
    owner: Optional[str] = None


class DownloadRequest(BaseModel):
    filename: Optional[str] = None


class TenantConfig(BaseModel):
    """Configuration for a SharePoint tenant."""

    id: str  # Unique identifier for this tenant config
    name: str  # Display name (e.g., "Foundations", "Magellan")
    tenant_id: str  # Azure AD tenant ID
    client_id: str  # Azure AD app client ID
    client_secret: str  # Azure AD app client secret


class TenantInfo(BaseModel):
    """Public info about a tenant (no secrets)."""

    id: str
    name: str


class SiteInfo(BaseModel):
    """Info about a SharePoint site (department)."""

    id: str
    name: str
    display_name: str
    web_url: Optional[str] = None


# ============================================================================
# Multi-Tenant Helpers
# ============================================================================


def get_tenants_config() -> List[TenantConfig]:
    """
    Get all configured SharePoint tenants.

    Combines legacy single-tenant config with new multi-tenant config.
    """
    tenants = []

    # Parse multi-tenant config (JSON array)
    try:
        tenants_json = SHAREPOINT_TENANTS.value
        if tenants_json and tenants_json != "[]":
            import json

            tenants_list = (
                json.loads(tenants_json)
                if isinstance(tenants_json, str)
                else tenants_json
            )
            for t in tenants_list:
                tenants.append(TenantConfig(**t))
    except Exception as e:
        log.error(f"Failed to parse SHAREPOINT_TENANTS: {e}")

    # Add legacy single-tenant config if present and not duplicated
    if (
        SHAREPOINT_CLIENT_ID.value
        and SHAREPOINT_CLIENT_SECRET.value
        and SHAREPOINT_TENANT_ID.value
    ):
        legacy_id = f"legacy_{SHAREPOINT_TENANT_ID.value[:8]}"
        # Check if already in tenants list
        if not any(t.tenant_id == SHAREPOINT_TENANT_ID.value for t in tenants):
            tenants.append(
                TenantConfig(
                    id=legacy_id,
                    name="Default",
                    tenant_id=SHAREPOINT_TENANT_ID.value,
                    client_id=SHAREPOINT_CLIENT_ID.value,
                    client_secret=SHAREPOINT_CLIENT_SECRET.value,
                )
            )

    return tenants


def get_tenant_by_id(tenant_id: str) -> Optional[TenantConfig]:
    """Get a specific tenant config by its ID."""
    tenants = get_tenants_config()
    for t in tenants:
        if t.id == tenant_id:
            return t
    return None


def get_default_tenant() -> Optional[TenantConfig]:
    """Get the first available tenant (for backward compatibility)."""
    tenants = get_tenants_config()
    return tenants[0] if tenants else None


# Per-tenant token cache: {tenant_id: MSGraphTokens}
_tenant_token_cache: dict[str, MSGraphTokens] = {}


# Per-tenant drives cache: {tenant_id: (drives_list, cache_time)}
_tenant_drives_cache: dict[str, tuple[List[DriveInfo], float]] = {}

# Per-tenant sites cache: {tenant_id: (sites_list, cache_time)}
_tenant_sites_cache: dict[str, tuple[List[SiteInfo], float]] = {}


# ============================================================================
# Utility Functions
# ============================================================================


def get_redirect_uri(request: Request) -> str:
    """
    Builds the OAuth callback URI based on the current request.
    """
    webui_url = getattr(request.app.state.config, "WEBUI_URL", None)
    if webui_url:
        return f"{webui_url}/sharepoint/auth/callback"

    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.url.netloc)
    return f"{scheme}://{host}/sharepoint/auth/callback"


def get_auth_client(request: Request) -> MSGraphAuth:
    """Creates an MSGraphAuth client with current config."""
    return MSGraphAuth(
        client_id=SHAREPOINT_CLIENT_ID.value,
        client_secret=SHAREPOINT_CLIENT_SECRET.value,
        tenant_id=SHAREPOINT_TENANT_ID.value,
        redirect_uri=get_redirect_uri(request),
    )


async def get_user_tokens(user: UserModel, request: Request) -> Optional[MSGraphTokens]:
    """
    Gets Microsoft Graph tokens for a user, refreshing if expired.

    Returns None if user has no SharePoint OAuth session.
    Raises HTTPException if tokens are expired and cannot be refreshed.
    """
    session = OAuthSessions.get_session_by_provider_and_user_id(
        SHAREPOINT_PROVIDER, user.id
    )

    if not session:
        return None

    tokens = MSGraphTokens.from_dict(session.token)

    # Check if tokens need refresh (expired or expiring within 5 minutes)
    if tokens.expires_within(300):  # 5 minutes buffer
        log.info(f"Refreshing SharePoint tokens for user {user.id}")

        if not tokens.refresh_token:
            # No refresh token, user needs to re-authenticate
            OAuthSessions.delete_session_by_id(session.id)
            raise HTTPException(
                status_code=401,
                detail="SharePoint session expired. Please re-authenticate.",
            )

        try:
            auth = get_auth_client(request)
            new_tokens = await auth.refresh_token(tokens.refresh_token)

            # Update stored tokens
            OAuthSessions.update_session_by_id(session.id, new_tokens.to_dict())
            tokens = new_tokens
            log.info(f"Successfully refreshed SharePoint tokens for user {user.id}")

        except Exception as e:
            log.error(f"Failed to refresh SharePoint tokens for user {user.id}: {e}")
            OAuthSessions.delete_session_by_id(session.id)
            raise HTTPException(
                status_code=401,
                detail="Failed to refresh SharePoint tokens. Please re-authenticate.",
            )

    return tokens


# Cache for client credentials token (avoid requesting new token for every request)
# Legacy single-tenant cache (backward compatibility)
_client_credentials_cache: Optional[MSGraphTokens] = None

# Cache for drives list (avoid fetching 90+ sites on every request)
_drives_cache: Optional[List[DriveInfo]] = None
_drives_cache_time: Optional[float] = None
DRIVES_CACHE_TTL_SECONDS = 300  # 5 minutes


async def get_client_credentials_tokens_for_tenant(
    tenant: TenantConfig,
) -> Optional[MSGraphTokens]:
    """
    Gets Microsoft Graph tokens using client credentials flow for a specific tenant.

    Args:
        tenant: The tenant configuration to use

    Returns:
        MSGraphTokens if successful, None otherwise.
        Caches the token per-tenant and refreshes when expired.
    """
    global _tenant_token_cache

    # Check if cached token is still valid (with 5 minute buffer)
    cached = _tenant_token_cache.get(tenant.id)
    if cached and not cached.expires_within(300):
        return cached

    # Get new token
    log.info(
        f"Getting new client credentials token for tenant '{tenant.name}' ({tenant.id})"
    )
    auth = MSGraphAuth(
        client_id=tenant.client_id,
        client_secret=tenant.client_secret,
        tenant_id=tenant.tenant_id,
        redirect_uri="",  # Not needed for client credentials
    )

    try:
        tokens = await auth.get_client_credentials_token()
        _tenant_token_cache[tenant.id] = tokens
        log.info(
            f"Got client credentials token for tenant '{tenant.name}', expires at {tokens.expires_at}"
        )
        return tokens
    except Exception as e:
        log.error(
            f"Failed to get client credentials token for tenant '{tenant.name}': {e}"
        )
        return None


async def get_client_credentials_tokens() -> Optional[MSGraphTokens]:
    """
    Gets Microsoft Graph tokens using client credentials flow (app-only auth).

    LEGACY: Uses the default/first configured tenant.
    For multi-tenant, use get_client_credentials_tokens_for_tenant() instead.

    Returns None if client credentials are not configured.
    Caches the token and refreshes when expired.
    """
    tenant = get_default_tenant()
    if not tenant:
        return None
    return await get_client_credentials_tokens_for_tenant(tenant)


async def get_tokens_for_tenant(
    tenant: TenantConfig, user: UserModel, request: Request
) -> MSGraphTokens:
    """
    Gets Microsoft Graph tokens for a specific tenant.

    This is the main function to use for accessing SharePoint resources in multi-tenant mode.
    Uses client credentials for the specified tenant.

    Args:
        tenant: The tenant configuration to use
        user: The current user (for potential fallback to OAuth)
        request: The FastAPI request

    Returns:
        MSGraphTokens for API access

    Raises:
        HTTPException if no valid tokens available
    """
    tokens = await get_client_credentials_tokens_for_tenant(tenant)
    if tokens:
        return tokens

    raise HTTPException(
        status_code=401,
        detail=f"Failed to authenticate with SharePoint tenant '{tenant.name}'. Please check tenant configuration.",
    )


async def get_tokens(user: UserModel, request: Request) -> MSGraphTokens:
    """
    Gets Microsoft Graph tokens, preferring client credentials over user tokens.

    LEGACY: Uses the default/first configured tenant.
    For multi-tenant, use get_tokens_for_tenant() instead.

    This is the main function to use for accessing SharePoint resources.
    It tries client credentials first (app-only), then falls back to user tokens.

    Returns:
        MSGraphTokens for API access

    Raises:
        HTTPException if no valid tokens available
    """
    # Try client credentials first (no user login required)
    tokens = await get_client_credentials_tokens()
    if tokens:
        return tokens

    # Fall back to user OAuth tokens
    tokens = await get_user_tokens(user, request)
    if tokens:
        return tokens

    raise HTTPException(
        status_code=401,
        detail="Not authenticated with SharePoint. Please connect your Microsoft account or configure client credentials.",
    )


async def graph_api_request(
    method: str,
    endpoint: str,
    tokens: MSGraphTokens,
    params: Optional[dict] = None,
    json_body: Optional[dict] = None,
) -> dict:
    """
    Makes a request to the Microsoft Graph API.

    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint (e.g., "/me/drives")
        tokens: Valid MSGraphTokens
        params: Query parameters
        json_body: JSON body for POST/PUT requests

    Returns:
        JSON response from the API

    Raises:
        HTTPException: If the API request fails
    """
    url = f"{MS_GRAPH_API_URL}{endpoint}"
    headers = {
        "Authorization": tokens.authorization_header(),
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        async with session.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=json_body,
        ) as response:
            if response.status == 401:
                raise HTTPException(
                    status_code=401,
                    detail="SharePoint authentication expired. Please re-authenticate.",
                )

            if response.status >= 400:
                try:
                    error_data = await response.json()
                    error_msg = error_data.get("error", {}).get(
                        "message", str(response.status)
                    )
                except Exception:
                    error_msg = await response.text()

                log.error(f"Graph API error: {response.status} - {error_msg}")
                raise HTTPException(
                    status_code=response.status,
                    detail=f"Microsoft Graph API error: {error_msg}",
                )

            return await response.json()


async def graph_api_download(
    endpoint: str,
    tokens: MSGraphTokens,
) -> tuple[bytes, str]:
    """
    Downloads a file from Microsoft Graph API.

    Args:
        endpoint: API endpoint for file content
        tokens: Valid MSGraphTokens

    Returns:
        Tuple of (file_bytes, content_type)

    Raises:
        HTTPException: If the download fails
    """
    url = f"{MS_GRAPH_API_URL}{endpoint}"
    headers = {
        "Authorization": tokens.authorization_header(),
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, allow_redirects=True) as response:
            if response.status >= 400:
                try:
                    error_data = await response.json()
                    error_msg = error_data.get("error", {}).get(
                        "message", str(response.status)
                    )
                except Exception:
                    error_msg = await response.text()

                log.error(f"Graph API download error: {response.status} - {error_msg}")
                raise HTTPException(
                    status_code=response.status,
                    detail=f"Failed to download file: {error_msg}",
                )

            content_type = response.headers.get(
                "Content-Type", "application/octet-stream"
            )
            file_bytes = await response.read()

            return file_bytes, content_type


async def graph_api_batch_request(
    tokens: MSGraphTokens,
    requests: list[dict],
) -> dict:
    """
    Makes a batch request to the Microsoft Graph API.

    Batch requests allow combining up to 20 individual requests into a single HTTP call,
    significantly reducing latency when fetching data from multiple endpoints.

    Args:
        tokens: Valid MSGraphTokens
        requests: List of request objects, each with 'id', 'method', and 'url'

    Returns:
        JSON response with 'responses' array containing individual results

    Raises:
        HTTPException: If the batch request fails
    """
    url = f"{MS_GRAPH_API_URL}/$batch"
    headers = {
        "Authorization": tokens.authorization_header(),
        "Content-Type": "application/json",
    }

    body = {"requests": requests}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=body) as response:
            if response.status >= 400:
                try:
                    error_data = await response.json()
                    error_msg = error_data.get("error", {}).get(
                        "message", str(response.status)
                    )
                except Exception:
                    error_msg = await response.text()

                log.error(f"Graph API batch error: {response.status} - {error_msg}")
                raise HTTPException(
                    status_code=response.status,
                    detail=f"Batch request failed: {error_msg}",
                )

            return await response.json()


# ============================================================================
# OAuth Routes
# ============================================================================


@router.get("/auth/login")
async def sharepoint_auth_login(request: Request, user=Depends(get_verified_user)):
    """
    Initiates the Microsoft Graph OAuth PKCE flow.

    Generates a PKCE challenge, stores the verifier in the session,
    and returns the authorization URL for the frontend to open.

    Returns JSON with the OAuth URL - frontend should open this with window.open()
    to avoid CORS issues.
    """
    if not ENABLE_SHAREPOINT_INTEGRATION.value:
        raise HTTPException(
            status_code=403,
            detail="SharePoint integration is disabled",
        )

    if (
        not SHAREPOINT_CLIENT_ID.value
        or not SHAREPOINT_CLIENT_SECRET.value
        or not SHAREPOINT_TENANT_ID.value
    ):
        raise HTTPException(
            status_code=500,
            detail="SharePoint integration is not configured. Missing client credentials.",
        )

    # Generate PKCE challenge
    pkce = PkceChallenge.generate()

    # Build authorization URL
    auth = get_auth_client(request)
    auth_url, state = auth.build_authorization_url(pkce)

    # Store PKCE verifier in session for callback validation
    request.session["sharepoint_pkce_verifier"] = pkce.verifier
    request.session["sharepoint_pkce_state"] = state
    request.session["sharepoint_user_id"] = user.id

    log.info(f"Initiating SharePoint OAuth for user {user.id}")

    # Return URL as JSON - frontend opens with window.open() to avoid CORS
    return {"url": auth_url, "state": state}


@router.get("/auth/callback")
async def sharepoint_auth_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
):
    """
    Handles the OAuth callback from Microsoft.

    Exchanges the authorization code for tokens and stores them
    in the OAuth sessions table.
    """
    # Check for errors from OAuth provider
    if error:
        log.error(f"OAuth error: {error} - {error_description}")
        return RedirectResponse(
            url=f"/?error=sharepoint_auth_failed&message={error_description or error}"
        )

    if not code or not state:
        log.error("Missing code or state in callback")
        return RedirectResponse(
            url="/?error=sharepoint_auth_failed&message=Missing+authorization+code"
        )

    # Retrieve stored PKCE data from session
    stored_verifier = request.session.get("sharepoint_pkce_verifier")
    stored_state = request.session.get("sharepoint_pkce_state")
    user_id = request.session.get("sharepoint_user_id")

    if not stored_verifier or not stored_state or not user_id:
        log.error("Missing PKCE data in session")
        return RedirectResponse(
            url="/?error=sharepoint_auth_failed&message=Session+expired"
        )

    # Validate state matches
    if state != stored_state:
        log.error(f"State mismatch: {state} != {stored_state}")
        return RedirectResponse(
            url="/?error=sharepoint_auth_failed&message=Invalid+state"
        )

    try:
        # Exchange code for tokens
        auth = get_auth_client(request)
        tokens = await auth.exchange_code(code, stored_verifier, state)

        # Delete any existing SharePoint session for this user
        existing = OAuthSessions.get_session_by_provider_and_user_id(
            SHAREPOINT_PROVIDER, user_id
        )
        if existing:
            OAuthSessions.delete_session_by_id(existing.id)

        # Store new tokens
        OAuthSessions.create_session(
            user_id=user_id,
            provider=SHAREPOINT_PROVIDER,
            token=tokens.to_dict(),
        )

        log.info(f"Successfully authenticated SharePoint for user {user_id}")

        # Clean up session
        request.session.pop("sharepoint_pkce_verifier", None)
        request.session.pop("sharepoint_pkce_state", None)
        request.session.pop("sharepoint_user_id", None)

        # Redirect to success page
        return RedirectResponse(url="/?sharepoint_auth=success")

    except Exception as e:
        log.exception(f"Failed to exchange SharePoint auth code: {e}")
        return RedirectResponse(url=f"/?error=sharepoint_auth_failed&message={str(e)}")


@router.get("/auth/status")
async def sharepoint_auth_status(request: Request, user=Depends(get_verified_user)):
    """
    Returns the authentication status for the current user.

    With client credentials flow enabled (when all credentials are configured),
    users don't need to authenticate - the app authenticates as itself.
    """
    if not ENABLE_SHAREPOINT_INTEGRATION.value:
        return {
            "enabled": False,
            "authenticated": False,
            "provider": SHAREPOINT_PROVIDER,
        }

    # Check for configured tenants (multi-tenant or legacy)
    tenants = get_tenants_config()
    has_tenants = len(tenants) > 0

    if has_tenants:
        # Multi-tenant or client credentials flow - no user login required
        # The app authenticates as itself
        return {
            "enabled": True,
            "authenticated": True,  # Always authenticated with client credentials
            "provider": SHAREPOINT_PROVIDER,
            "auth_method": "client_credentials",
            "tenant_count": len(tenants),
        }

    # Fallback to delegated flow (user OAuth session)
    session = OAuthSessions.get_session_by_provider_and_user_id(
        SHAREPOINT_PROVIDER, user.id
    )

    if not session:
        return {
            "enabled": True,
            "authenticated": False,
            "provider": SHAREPOINT_PROVIDER,
        }

    tokens = MSGraphTokens.from_dict(session.token)

    return {
        "enabled": True,
        "authenticated": True,
        "provider": SHAREPOINT_PROVIDER,
        "auth_method": "delegated",
        "expires_at": int(tokens.expires_at.timestamp()),
        "scopes": tokens.scopes,
    }


@router.get("/tenants")
async def list_tenants(
    request: Request, user=Depends(get_verified_user)
) -> List[TenantInfo]:
    """
    Lists all configured SharePoint tenants.

    Returns tenant info (id, name) without secrets.
    """
    if not ENABLE_SHAREPOINT_INTEGRATION.value:
        raise HTTPException(
            status_code=403, detail="SharePoint integration is disabled"
        )

    tenants = get_tenants_config()
    return [TenantInfo(id=t.id, name=t.name) for t in tenants]


@router.post("/auth/logout")
async def sharepoint_auth_logout(request: Request, user=Depends(get_verified_user)):
    """
    Logs out the user from SharePoint by deleting their OAuth session.
    """
    session = OAuthSessions.get_session_by_provider_and_user_id(
        SHAREPOINT_PROVIDER, user.id
    )

    if session:
        OAuthSessions.delete_session_by_id(session.id)
        log.info(f"Logged out SharePoint for user {user.id}")

    return {"status": "ok"}


# ============================================================================
# Client Credentials Flow (App-Only Authentication)
# ============================================================================


@router.get("/test-client-credentials")
async def test_client_credentials(request: Request, user=Depends(get_verified_user)):
    """
    Tests the client credentials flow (app-only authentication).

    This does NOT require user OAuth login - it uses the app's credentials
    directly to authenticate with Microsoft Graph.

    Requires the Azure AD app to have Application permissions (not Delegated):
    - Files.Read.All (Application)
    - Sites.Read.All (Application)

    And admin consent must be granted.
    """
    log.info("DEBUG [test-client-credentials]: Starting")
    log.info(f"DEBUG [test-client-credentials]: User={user.id}")

    # Check if SharePoint integration is enabled
    log.info(
        f"DEBUG [test-client-credentials]: ENABLE_SHAREPOINT_INTEGRATION={ENABLE_SHAREPOINT_INTEGRATION.value}"
    )
    if not ENABLE_SHAREPOINT_INTEGRATION.value:
        log.info("DEBUG [test-client-credentials]: Integration disabled")
        raise HTTPException(
            status_code=403,
            detail="SharePoint integration is disabled",
        )

    # Check credentials are configured
    log.info(
        f"DEBUG [test-client-credentials]: CLIENT_ID set={bool(SHAREPOINT_CLIENT_ID.value)}"
    )
    log.info(
        f"DEBUG [test-client-credentials]: CLIENT_SECRET set={bool(SHAREPOINT_CLIENT_SECRET.value)}"
    )
    log.info(
        f"DEBUG [test-client-credentials]: TENANT_ID set={bool(SHAREPOINT_TENANT_ID.value)}"
    )

    if (
        not SHAREPOINT_CLIENT_ID.value
        or not SHAREPOINT_CLIENT_SECRET.value
        or not SHAREPOINT_TENANT_ID.value
    ):
        log.info("DEBUG [test-client-credentials]: Missing credentials")
        raise HTTPException(
            status_code=500,
            detail="SharePoint integration is not configured. Missing client credentials.",
        )

    log.info(
        f"DEBUG [test-client-credentials]: CLIENT_ID={SHAREPOINT_CLIENT_ID.value[:8]}..."
    )
    log.info(f"DEBUG [test-client-credentials]: TENANT_ID={SHAREPOINT_TENANT_ID.value}")

    # Create auth client (redirect_uri not needed for client credentials)
    log.info("DEBUG [test-client-credentials]: Creating MSGraphAuth client")
    auth = MSGraphAuth(
        client_id=SHAREPOINT_CLIENT_ID.value,
        client_secret=SHAREPOINT_CLIENT_SECRET.value,
        tenant_id=SHAREPOINT_TENANT_ID.value,
        redirect_uri="",  # Not needed for client credentials
    )

    # Get token using client credentials
    log.info("DEBUG [test-client-credentials]: Calling get_client_credentials_token()")
    try:
        tokens = await auth.get_client_credentials_token()
        log.info(
            f"DEBUG [test-client-credentials]: Got token, expires_at={tokens.expires_at}"
        )
    except Exception as e:
        log.error(f"DEBUG [test-client-credentials]: Token request failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get client credentials token: {str(e)}",
        )

    # Try to list drives using the app token
    log.info("DEBUG [test-client-credentials]: Attempting to list organization drives")
    try:
        # With client credentials, we can't use /me - we need to query sites directly
        # Try getting the root SharePoint site
        log.info("DEBUG [test-client-credentials]: Calling Graph API /sites/root")
        response = await graph_api_request("GET", "/sites/root", tokens)
        log.info(
            f"DEBUG [test-client-credentials]: Got root site: {response.get('displayName', 'unknown')}"
        )

        site_info = {
            "id": response.get("id"),
            "name": response.get("displayName"),
            "webUrl": response.get("webUrl"),
        }

        # Try to get drives for the root site
        log.info(
            "DEBUG [test-client-credentials]: Calling Graph API /sites/root/drives"
        )
        drives_response = await graph_api_request("GET", "/sites/root/drives", tokens)
        log.info(
            f"DEBUG [test-client-credentials]: Got {len(drives_response.get('value', []))} drives"
        )

        drives = []
        for drive in drives_response.get("value", []):
            drives.append(
                {
                    "id": drive.get("id"),
                    "name": drive.get("name"),
                    "driveType": drive.get("driveType"),
                    "webUrl": drive.get("webUrl"),
                }
            )

        return {
            "status": "success",
            "auth_method": "client_credentials",
            "token_expires_at": int(tokens.expires_at.timestamp()),
            "root_site": site_info,
            "drives": drives,
        }

    except HTTPException as e:
        log.error(
            f"DEBUG [test-client-credentials]: Graph API request failed: {e.detail}"
        )
        # Return partial success - we got the token but couldn't access resources
        return {
            "status": "partial",
            "auth_method": "client_credentials",
            "token_obtained": True,
            "token_expires_at": int(tokens.expires_at.timestamp()),
            "api_error": e.detail,
            "hint": "Token obtained but API access failed. Check Azure AD Application permissions (not Delegated). Required: Sites.Read.All, Files.Read.All (Application type). Admin consent required.",
        }
    except Exception as e:
        log.error(f"DEBUG [test-client-credentials]: Unexpected error: {e}")
        return {
            "status": "partial",
            "auth_method": "client_credentials",
            "token_obtained": True,
            "token_expires_at": int(tokens.expires_at.timestamp()),
            "error": str(e),
        }


# ============================================================================
# Drive/File Routes
# ============================================================================

SITES_CACHE_TTL_SECONDS = 300  # 5 minutes


def _filter_sites_for_user(sites: list, user) -> list:
    """Filter sites using default-deny access control.

    Access is determined by merging user-level and group-level policies:
    1. If user has allow_all: true → return all sites (admin override)
    2. Collect allowed_sites from user.info.sharepoint.allowed_sites
    3. Collect allowed_sites from each group's data.sharepoint.allowed_sites
    4. Return union of all allowed sites (empty if none configured)
    """
    user_info = user.info if user.info else {}
    sp_config = user_info.get("sharepoint", {}) if isinstance(user_info, dict) else {}

    # Admins always see all sites; regular users filtered by allow_all / allowed_sites
    # Admin role bypass: admins always see all sites
    if getattr(user, 'role', None) == 'admin':
        return sites

    if sp_config.get("allow_all"):
        return sites

    # Collect user-level allowed sites
    allowed: set = set(sp_config.get("allowed_sites", []))

    # Collect group-level allowed sites
    try:
        user_groups = Groups.get_groups_by_member_id(user.id)
        for group in user_groups:
            group_data = group.data if group.data else {}
            group_sp = (
                group_data.get("sharepoint", {}) if isinstance(group_data, dict) else {}
            )
            # Check for group-level allow_all
            if group_sp.get("allow_all"):
                return sites
            group_sites = group_sp.get("allowed_sites", [])
            if isinstance(group_sites, list):
                allowed.update(group_sites)
    except Exception as e:
        log.warning(f"Failed to load group SharePoint policies for user {user.id}: {e}")

    # Default-deny: no config = no access
    if not allowed:
        return []

    return [s for s in sites if s.display_name in allowed]


@router.get("/tenants/{tenant_id}/sites")
async def list_sites(
    request: Request,
    tenant_id: str,
    user=Depends(get_verified_user),
) -> List[SiteInfo]:
    """
    Lists all SharePoint sites (departments) available for a specific tenant.

    Args:
        tenant_id: The tenant ID to get sites for.

    Returns filtered list of sites excluding system sites like Designer, My workspace, etc.
    """
    if not ENABLE_SHAREPOINT_INTEGRATION.value:
        raise HTTPException(
            status_code=403, detail="SharePoint integration is disabled"
        )

    # Get the tenant config
    tenant = get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_id}' not found")

    # Get tokens for this tenant
    tokens = await get_tokens_for_tenant(tenant, user, request)

    # Check if we have a valid cache for this tenant
    global _tenant_sites_cache

    cache_key = tenant.id
    if cache_key in _tenant_sites_cache:
        cached_sites, cache_time = _tenant_sites_cache[cache_key]
        cache_age = time.time() - cache_time
        if cache_age < SITES_CACHE_TTL_SECONDS:
            log.info(
                f"Returning cached sites for tenant '{tenant.name}' ({len(cached_sites)} sites, {int(cache_age)}s old)"
            )
            return _filter_sites_for_user(cached_sites, user)

    sites = []

    try:
        log.info("Fetching all SharePoint sites")
        response = await graph_api_request(
            "GET", "/sites", tokens, params={"search": "*"}
        )

        all_sites = response.get("value", [])
        log.info(f"Found {len(all_sites)} SharePoint sites")

        # Filter out only system/internal sites
        for s in all_sites:
            display_name = s.get("displayName", "")
            web_url = s.get("webUrl", "")

            # Skip content storage URLs (internal SharePoint storage)
            if "/contentstorage/" in web_url:
                continue

            # Skip known system site names
            if display_name in ("Designer", "My workspace", "Pages"):
                continue

            # Skip sites with GUID-like names (internal/system sites)
            if len(display_name) == 36 and "-" in display_name:
                continue

            sites.append(
                SiteInfo(
                    id=s["id"],
                    name=s.get("name", ""),
                    display_name=s.get("displayName", s.get("name", "Unknown")),
                    web_url=s.get("webUrl"),
                )
            )

        # Sort by display name
        sites.sort(key=lambda x: x.display_name.lower())

        log.info(
            f"Filtered to {len(sites)} real sites (excluding Designer/Workspace/System) for tenant '{tenant.name}'"
        )

        # Update cache
        _tenant_sites_cache[cache_key] = (sites, time.time())

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Failed to fetch SharePoint sites for tenant '{tenant.name}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch sites: {str(e)}")

    return _filter_sites_for_user(sites, user)


@router.get("/tenants/{tenant_id}/sites/{site_id}/drives")
async def list_site_drives(
    request: Request,
    tenant_id: str,
    site_id: str,
    user=Depends(get_verified_user),
) -> List[DriveInfo]:
    """
    Lists document libraries (drives) for a specific SharePoint site.

    Args:
        tenant_id: The tenant ID.
        site_id: The SharePoint site ID.

    Returns list of drives for that site.
    """
    if not ENABLE_SHAREPOINT_INTEGRATION.value:
        raise HTTPException(
            status_code=403, detail="SharePoint integration is disabled"
        )

    # Get the tenant config
    tenant = get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_id}' not found")

    # Get tokens for this tenant
    tokens = await get_tokens_for_tenant(tenant, user, request)

    drives = []

    try:
        log.info(f"Fetching drives for site {site_id}")
        response = await graph_api_request("GET", f"/sites/{site_id}/drives", tokens)

        for drive in response.get("value", []):
            drives.append(
                DriveInfo(
                    id=drive["id"],
                    name=drive.get("name", "Documents"),
                    drive_type=drive.get("driveType", "documentLibrary"),
                    web_url=drive.get("webUrl"),
                    owner=None,
                )
            )

        log.info(f"Found {len(drives)} drives for site {site_id}")

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Failed to fetch drives for site {site_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch drives: {str(e)}")

    return drives


@router.get("/tenants/{tenant_id}/drives")
async def list_drives(
    request: Request,
    tenant_id: str,
    user=Depends(get_verified_user),
) -> List[DriveInfo]:
    """
    Lists all drives available for a specific tenant.

    Args:
        tenant_id: The tenant ID to get drives for.

    With client credentials: Returns SharePoint document libraries accessible to the app.
    With user OAuth: Returns user's OneDrive and SharePoint document libraries.
    """
    if not ENABLE_SHAREPOINT_INTEGRATION.value:
        raise HTTPException(
            status_code=403, detail="SharePoint integration is disabled"
        )

    # Get the tenant config
    tenant = get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_id}' not found")

    # Get tokens for this tenant
    tokens = await get_tokens_for_tenant(tenant, user, request)

    drives = []

    # Check if we have a valid cache for this tenant
    global _tenant_drives_cache

    cache_key = tenant.id
    if cache_key in _tenant_drives_cache:
        cached_drives, cache_time = _tenant_drives_cache[cache_key]
        cache_age = time.time() - cache_time
        if cache_age < DRIVES_CACHE_TTL_SECONDS:
            log.info(
                f"Returning cached drives for tenant '{tenant.name}' ({len(cached_drives)} drives, {int(cache_age)}s old)"
            )
            return cached_drives

    # Get SharePoint sites and fetch drives using batch API
    try:
        log.info("Fetching all SharePoint sites")
        response = await graph_api_request(
            "GET", "/sites", tokens, params={"search": "*"}
        )

        sites = response.get("value", [])
        log.info(f"Found {len(sites)} SharePoint sites")

        # Filter out Designer/Workspace sites (internal MS sites)
        real_sites = [
            s
            for s in sites
            if not s.get("webUrl", "").startswith(
                "https://fiwealth.sharepoint.com/contentstorage/"
            )
            and s.get("displayName") not in ("Designer", "My workspace", "Pages")
            # Filter out sites with GUID-like names (internal/system sites)
            and not (
                len(s.get("displayName", "")) == 36 and "-" in s.get("displayName", "")
            )
        ]
        log.info(
            f"Filtered to {len(real_sites)} real sites (excluding Designer/Workspace/System)"
        )

        # Use Microsoft Graph batch API to fetch drives (up to 20 requests per batch)
        # This reduces 90 HTTP calls to ~5 batch calls
        BATCH_SIZE = 20

        for batch_start in range(0, len(real_sites), BATCH_SIZE):
            batch_sites = real_sites[batch_start : batch_start + BATCH_SIZE]

            # Build batch request
            batch_requests = []
            for i, site in enumerate(batch_sites):
                batch_requests.append(
                    {
                        "id": str(i),
                        "method": "GET",
                        "url": f"/sites/{site['id']}/drives",
                    }
                )

            # Execute batch request
            try:
                batch_response = await graph_api_batch_request(tokens, batch_requests)

                # Process batch responses
                for resp in batch_response.get("responses", []):
                    resp_id = int(resp.get("id", 0))
                    site = batch_sites[resp_id]
                    site_name = site.get("displayName", "SharePoint")

                    if resp.get("status") == 200:
                        body = resp.get("body", {})
                        for drive in body.get("value", []):
                            drives.append(
                                DriveInfo(
                                    id=drive["id"],
                                    name=f"{site_name} - {drive.get('name', 'Documents')}",
                                    drive_type="documentLibrary",
                                    web_url=drive.get("webUrl"),
                                    owner=site_name,
                                )
                            )
                    else:
                        log.debug(
                            f"Batch request for site {site_name} failed: {resp.get('status')}"
                        )

            except Exception as e:
                log.warning(
                    f"Batch request failed: {e}, falling back to individual requests"
                )
                # Fallback: fetch remaining sites individually
                for site in batch_sites:
                    site_id = site["id"]
                    site_name = site.get("displayName", "SharePoint")
                    try:
                        site_drives = await graph_api_request(
                            "GET", f"/sites/{site_id}/drives", tokens
                        )
                        for drive in site_drives.get("value", []):
                            drives.append(
                                DriveInfo(
                                    id=drive["id"],
                                    name=f"{site_name} - {drive.get('name', 'Documents')}",
                                    drive_type="documentLibrary",
                                    web_url=drive.get("webUrl"),
                                    owner=site_name,
                                )
                            )
                    except Exception:
                        pass

        log.info(
            f"Retrieved {len(drives)} total drives from {len(real_sites)} sites for tenant '{tenant.name}'"
        )

        # Update per-tenant cache
        _tenant_drives_cache[cache_key] = (drives, time.time())

    except HTTPException as e:
        log.warning(
            f"Could not fetch SharePoint sites for tenant '{tenant.name}': {e.detail}"
        )

    return drives


@router.get("/tenants/{tenant_id}/drives/{drive_id}/files")
async def list_files(
    request: Request,
    tenant_id: str,
    drive_id: str,
    folder_id: Optional[str] = None,
    user=Depends(get_verified_user),
) -> List[DriveItem]:
    """
    Lists files in a drive or folder.

    Args:
        tenant_id: The tenant ID.
        drive_id: The ID of the drive to list files from.
        folder_id: Optional folder ID. If not provided, lists root folder.

    Returns:
        List of files and folders
    """
    if not ENABLE_SHAREPOINT_INTEGRATION.value:
        raise HTTPException(
            status_code=403, detail="SharePoint integration is disabled"
        )

    # Get the tenant config
    tenant = get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_id}' not found")

    # Get tokens for this tenant
    tokens = await get_tokens_for_tenant(tenant, user, request)

    # Build the endpoint
    if folder_id:
        endpoint = f"/drives/{drive_id}/items/{folder_id}/children"
    else:
        endpoint = f"/drives/{drive_id}/root/children"

    # Request with select to limit response size
    params = {
        "$select": "id,name,size,folder,file,webUrl,lastModifiedDateTime",
        "$top": "100",
    }

    response = await graph_api_request("GET", endpoint, tokens, params=params)

    items = []
    for item in response.get("value", []):
        is_folder = "folder" in item
        mime_type = None
        if "file" in item:
            mime_type = item["file"].get("mimeType")

        items.append(
            DriveItem(
                id=item["id"],
                name=item["name"],
                size=item.get("size"),
                is_folder=is_folder,
                mime_type=mime_type,
                web_url=item.get("webUrl"),
                modified_at=item.get("lastModifiedDateTime"),
                drive_id=drive_id,
            )
        )

    return items


@router.get("/tenants/{tenant_id}/drives/{drive_id}/files/recursive")
async def list_files_recursive(
    request: Request,
    tenant_id: str,
    drive_id: str,
    folder_id: Optional[str] = None,
    max_depth: int = 10,
    user=Depends(get_verified_user),
) -> List[DriveItem]:
    """
    Recursively lists all files in a drive or folder.

    Uses BFS to traverse folder hierarchy and returns only files (not folders).
    Handles pagination within each folder.

    Args:
        tenant_id: The tenant ID.
        drive_id: The ID of the drive to list files from.
        folder_id: Optional folder ID. If not provided, starts from root.
        max_depth: Maximum folder depth to traverse (default 10, max 20).

    Returns:
        List of all files in the folder hierarchy
    """
    if not ENABLE_SHAREPOINT_INTEGRATION.value:
        raise HTTPException(
            status_code=403, detail="SharePoint integration is disabled"
        )

    # Get the tenant config
    tenant = get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_id}' not found")

    # Get tokens for this tenant
    tokens = await get_tokens_for_tenant(tenant, user, request)

    # Clamp max_depth
    max_depth = min(max(1, max_depth), 20)

    all_files: List[DriveItem] = []
    # Queue: (folder_id or None for root, current_depth)
    queue: list[tuple[Optional[str], int]] = [(folder_id, 0)]

    async def fetch_folder_contents(
        fid: Optional[str],
    ) -> tuple[List[dict], Optional[str]]:
        """Fetch contents of a folder, handling pagination."""
        if fid:
            endpoint = f"/drives/{drive_id}/items/{fid}/children"
        else:
            endpoint = f"/drives/{drive_id}/root/children"

        params = {
            "$select": "id,name,size,folder,file,webUrl,lastModifiedDateTime",
            "$top": "200",  # Increased for efficiency
        }

        items = []
        next_link = None

        response = await graph_api_request("GET", endpoint, tokens, params=params)
        items.extend(response.get("value", []))
        next_link = response.get("@odata.nextLink")

        # Handle pagination
        while next_link:
            # For pagination, we need to call the nextLink directly
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {tokens.access_token}"}
                async with session.get(next_link, headers=headers) as resp:
                    if resp.status >= 400:
                        break
                    data = await resp.json()
                    items.extend(data.get("value", []))
                    next_link = data.get("@odata.nextLink")

        return items, None

    # BFS traversal
    while queue:
        current_folder_id, depth = queue.pop(0)

        if depth > max_depth:
            continue

        try:
            items, _ = await fetch_folder_contents(current_folder_id)
        except Exception as e:
            log.warning(f"Failed to fetch folder {current_folder_id}: {e}")
            continue

        for item in items:
            is_folder = "folder" in item

            if is_folder:
                # Add subfolder to queue for traversal
                queue.append((item["id"], depth + 1))
            else:
                # It's a file - add to results
                mime_type = None
                if "file" in item:
                    mime_type = item["file"].get("mimeType")

                all_files.append(
                    DriveItem(
                        id=item["id"],
                        name=item["name"],
                        size=item.get("size"),
                        is_folder=False,
                        mime_type=mime_type,
                        web_url=item.get("webUrl"),
                        modified_at=item.get("lastModifiedDateTime"),
                        drive_id=drive_id,
                    )
                )

    return all_files


@router.post("/tenants/{tenant_id}/drives/{drive_id}/files/{file_id}/download")
async def download_file(
    request: Request,
    tenant_id: str,
    drive_id: str,
    file_id: str,
    download_request: Optional[DownloadRequest] = None,
    user=Depends(get_verified_user),
):
    """
    Downloads a file from SharePoint/OneDrive and stores it in OpenWebUI storage.

    Args:
        tenant_id: The tenant ID.
        drive_id: The ID of the drive containing the file.
        file_id: The ID of the file to download.
        download_request: Optional request body with filename override.

    Returns the created file model.
    """
    if not ENABLE_SHAREPOINT_INTEGRATION.value:
        raise HTTPException(
            status_code=403, detail="SharePoint integration is disabled"
        )

    # Get the tenant config
    tenant = get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_id}' not found")

    # Get tokens for this tenant
    tokens = await get_tokens_for_tenant(tenant, user, request)

    item_id = file_id

    # Check for existing file with same SharePoint item_id (deduplication)
    log.info(f"[SharePoint Download] Checking for existing file with sharepoint_item_id={item_id}")
    existing_file = Files.get_file_by_sharepoint_item_id(item_id)
    if existing_file:
        log.info(f"[SharePoint Download] REUSING existing file: id={existing_file.id}, filename={existing_file.filename}")
        return {
            "id": existing_file.id,
            "filename": existing_file.filename,
            "meta": existing_file.meta,
            "created_at": existing_file.created_at,
        }

    log.info(f"[SharePoint Download] No existing file found, downloading new: drive_id={drive_id}, item_id={item_id}")

    metadata_endpoint = f"/drives/{drive_id}/items/{item_id}"
    params = {"$select": "id,name,size,file,@microsoft.graph.downloadUrl"}

    try:
        metadata = await graph_api_request(
            "GET", metadata_endpoint, tokens, params=params
        )
    except HTTPException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=f"Failed to get file metadata: {e.detail}",
        )

    filename = (
        download_request.filename if download_request else None
    ) or metadata.get("name", f"file_{item_id}")
    file_size = metadata.get("size", 0)
    mime_type = metadata.get("file", {}).get("mimeType", "application/octet-stream")

    download_url = metadata.get("@microsoft.graph.downloadUrl")

    if download_url:
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url) as response:
                if response.status >= 400:
                    raise HTTPException(
                        status_code=response.status,
                        detail="Failed to download file from SharePoint",
                    )
                file_bytes = await response.read()
    else:
        content_endpoint = f"/drives/{drive_id}/items/{item_id}/content"
        file_bytes, content_type = await graph_api_download(content_endpoint, tokens)
        if content_type and content_type != "application/octet-stream":
            mime_type = content_type

    file_id = str(uuid.uuid4())

    import io

    file_obj = io.BytesIO(file_bytes)
    storage_tags = {
        "source": "sharepoint",
        "content_type": mime_type,
    }
    contents, file_path = Storage.upload_file(file_obj, filename, storage_tags)

    file_form = FileForm(
        id=file_id,
        filename=filename,
        path=file_path,
        meta={
            "name": filename,
            "content_type": mime_type,
            "size": file_size,
            "source": "sharepoint",
            "sharepoint_drive_id": drive_id,
            "sharepoint_item_id": item_id,
        },
    )

    file_record = Files.insert_new_file(user.id, file_form)

    if not file_record:
        raise HTTPException(
            status_code=500,
            detail="Failed to create file record",
        )

    log.info(
        f"Downloaded file from SharePoint: {filename} ({file_id}) for user {user.id}"
    )

    return {
        "id": file_record.id,
        "filename": file_record.filename,
        "meta": file_record.meta,
        "created_at": file_record.created_at,
    }
