import base64
import copy
import hashlib
import logging
import mimetypes
import sys
import urllib
import uuid
import json
from datetime import datetime, timedelta

import re
import fnmatch
import time
import secrets
from cryptography.fernet import Fernet
from typing import Literal

import aiohttp
from authlib.integrations.starlette_client import OAuth
from authlib.oidc.core import UserInfo
from fastapi import (
    HTTPException,
    status,
)
from starlette.responses import RedirectResponse
from typing import Optional


from open_webui.models.auths import Auths
from open_webui.models.oauth_sessions import OAuthSessions
from open_webui.models.users import Users


from open_webui.models.groups import Groups, GroupModel, GroupUpdateForm, GroupForm
from open_webui.config import (
    DEFAULT_USER_ROLE,
    ENABLE_OAUTH_SIGNUP,
    OAUTH_MERGE_ACCOUNTS_BY_EMAIL,
    OAUTH_PROVIDERS,
    ENABLE_OAUTH_ROLE_MANAGEMENT,
    ENABLE_OAUTH_GROUP_MANAGEMENT,
    ENABLE_OAUTH_GROUP_CREATION,
    OAUTH_BLOCKED_GROUPS,
    OAUTH_GROUPS_SEPARATOR,
    OAUTH_ROLES_SEPARATOR,
    OAUTH_ROLES_CLAIM,
    OAUTH_SUB_CLAIM,
    OAUTH_GROUPS_CLAIM,
    OAUTH_EMAIL_CLAIM,
    OAUTH_PICTURE_CLAIM,
    OAUTH_USERNAME_CLAIM,
    OAUTH_ALLOWED_ROLES,
    OAUTH_ADMIN_ROLES,
    OAUTH_ALLOWED_DOMAINS,
    OAUTH_UPDATE_PICTURE_ON_LOGIN,
    OAUTH_ACCESS_TOKEN_REQUEST_INCLUDE_CLIENT_ID,
    WEBHOOK_URL,
    JWT_EXPIRES_IN,
    AppConfig,
)
from open_webui.constants import ERROR_MESSAGES, WEBHOOK_MESSAGES
from open_webui.env import (
    AIOHTTP_CLIENT_SESSION_SSL,
    WEBUI_NAME,
    WEBUI_AUTH_COOKIE_SAME_SITE,
    WEBUI_AUTH_COOKIE_SECURE,
    ENABLE_OAUTH_ID_TOKEN_COOKIE,
    ENABLE_OAUTH_EMAIL_FALLBACK,
    OAUTH_CLIENT_INFO_ENCRYPTION_KEY,
)
from open_webui.utils.misc import parse_duration
from open_webui.utils.auth import get_password_hash, create_token
from open_webui.utils.webhook import post_webhook
from open_webui.utils.groups import apply_default_group_assignment

from mcp.shared.auth import (
    OAuthClientMetadata as MCPOAuthClientMetadata,
    OAuthMetadata,
)

from authlib.oauth2.rfc6749.errors import OAuth2Error


class OAuthClientMetadata(MCPOAuthClientMetadata):
    token_endpoint_auth_method: Literal[
        "none", "client_secret_basic", "client_secret_post"
    ] = "client_secret_post"
    pass


class OAuthClientInformationFull(OAuthClientMetadata):
    issuer: Optional[str] = None  # URL of the OAuth server that issued this client

    client_id: str
    client_secret: str | None = None
    client_id_issued_at: int | None = None
    client_secret_expires_at: int | None = None

    server_metadata: Optional[OAuthMetadata] = None  # Fetched from the OAuth server


from open_webui.env import SRC_LOG_LEVELS, GLOBAL_LOG_LEVEL

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["OAUTH"])

auth_manager_config = AppConfig()
auth_manager_config.DEFAULT_USER_ROLE = DEFAULT_USER_ROLE
auth_manager_config.ENABLE_OAUTH_SIGNUP = ENABLE_OAUTH_SIGNUP
auth_manager_config.OAUTH_MERGE_ACCOUNTS_BY_EMAIL = OAUTH_MERGE_ACCOUNTS_BY_EMAIL
auth_manager_config.ENABLE_OAUTH_ROLE_MANAGEMENT = ENABLE_OAUTH_ROLE_MANAGEMENT
auth_manager_config.ENABLE_OAUTH_GROUP_MANAGEMENT = ENABLE_OAUTH_GROUP_MANAGEMENT
auth_manager_config.ENABLE_OAUTH_GROUP_CREATION = ENABLE_OAUTH_GROUP_CREATION
auth_manager_config.OAUTH_BLOCKED_GROUPS = OAUTH_BLOCKED_GROUPS
auth_manager_config.OAUTH_ROLES_CLAIM = OAUTH_ROLES_CLAIM
auth_manager_config.OAUTH_SUB_CLAIM = OAUTH_SUB_CLAIM
auth_manager_config.OAUTH_GROUPS_CLAIM = OAUTH_GROUPS_CLAIM
auth_manager_config.OAUTH_EMAIL_CLAIM = OAUTH_EMAIL_CLAIM
auth_manager_config.OAUTH_PICTURE_CLAIM = OAUTH_PICTURE_CLAIM
auth_manager_config.OAUTH_USERNAME_CLAIM = OAUTH_USERNAME_CLAIM
auth_manager_config.OAUTH_ALLOWED_ROLES = OAUTH_ALLOWED_ROLES
auth_manager_config.OAUTH_ADMIN_ROLES = OAUTH_ADMIN_ROLES
auth_manager_config.OAUTH_ALLOWED_DOMAINS = OAUTH_ALLOWED_DOMAINS
auth_manager_config.WEBHOOK_URL = WEBHOOK_URL
auth_manager_config.JWT_EXPIRES_IN = JWT_EXPIRES_IN
auth_manager_config.OAUTH_UPDATE_PICTURE_ON_LOGIN = OAUTH_UPDATE_PICTURE_ON_LOGIN


FERNET = None

if len(OAUTH_CLIENT_INFO_ENCRYPTION_KEY) != 44:
    key_bytes = hashlib.sha256(OAUTH_CLIENT_INFO_ENCRYPTION_KEY.encode()).digest()
    OAUTH_CLIENT_INFO_ENCRYPTION_KEY = base64.urlsafe_b64encode(key_bytes)
else:
    OAUTH_CLIENT_INFO_ENCRYPTION_KEY = OAUTH_CLIENT_INFO_ENCRYPTION_KEY.encode()

try:
    FERNET = Fernet(OAUTH_CLIENT_INFO_ENCRYPTION_KEY)
except Exception as e:
    log.error(f"Error initializing Fernet with provided key: {e}")
    raise


def encrypt_data(data) -> str:
    """Encrypt data for storage"""
    try:
        data_json = json.dumps(data)
        encrypted = FERNET.encrypt(data_json.encode()).decode()
        return encrypted
    except Exception as e:
        log.error(f"Error encrypting data: {e}")
        raise


def decrypt_data(data: str):
    """Decrypt data from storage"""
    try:
        decrypted = FERNET.decrypt(data.encode()).decode()
        return json.loads(decrypted)
    except Exception as e:
        log.error(f"Error decrypting data: {e}")
        raise


def _build_oauth_callback_error_message(e: Exception) -> str:
    """
    Produce a user-facing callback error string with actionable context.
    Keeps the message short and strips newlines for safe redirect usage.
    """
    if isinstance(e, OAuth2Error):
        parts = [p for p in [e.error, e.description] if p]
        detail = " - ".join(parts)
    elif isinstance(e, HTTPException):
        detail = e.detail if isinstance(e.detail, str) else str(e.detail)
    elif isinstance(e, aiohttp.ClientResponseError):
        detail = f"Upstream provider returned {e.status}: {e.message}"
    elif isinstance(e, aiohttp.ClientError):
        detail = str(e)
    elif isinstance(e, KeyError):
        missing = str(e).strip("'")
        if missing.lower() == "state":
            detail = "Missing state parameter in callback (session may have expired)"
        else:
            detail = f"Missing expected key '{missing}' in OAuth response"
    else:
        detail = str(e)

    detail = detail.replace("\n", " ").strip()
    if not detail:
        detail = e.__class__.__name__

    message = f"OAuth callback failed: {detail}"
    return message[:197] + "..." if len(message) > 200 else message


def is_in_blocked_groups(group_name: str, groups: list) -> bool:
    """
    Check if a group name matches any blocked pattern.
    Supports exact matches, shell-style wildcards (*, ?), and regex patterns.

    Args:
        group_name: The group name to check
        groups: List of patterns to match against

    Returns:
        True if the group is blocked, False otherwise
    """
    if not groups:
        return False

    for group_pattern in groups:
        if not group_pattern:  # Skip empty patterns
            continue

        # Exact match
        if group_name == group_pattern:
            return True

        # Try as regex pattern first if it contains regex-specific characters
        if any(
            char in group_pattern
            for char in ["^", "$", "[", "]", "(", ")", "{", "}", "+", "\\", "|"]
        ):
            try:
                # Use the original pattern as-is for regex matching
                if re.search(group_pattern, group_name):
                    return True
            except re.error:
                # If regex is invalid, fall through to wildcard check
                pass

        # Shell-style wildcard match (supports * and ?)
        if "*" in group_pattern or "?" in group_pattern:
            if fnmatch.fnmatch(group_name, group_pattern):
                return True

    return False


def get_parsed_and_base_url(server_url) -> tuple[urllib.parse.ParseResult, str]:
    parsed = urllib.parse.urlparse(server_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    return parsed, base_url


def get_discovery_urls(server_url) -> list[str]:
    parsed, base_url = get_parsed_and_base_url(server_url)

    urls = []

    if parsed.path and parsed.path != "/":
        # Generate discovery URLs based on https://modelcontextprotocol.io/specification/draft/basic/authorization#authorization-server-metadata-discovery
        tenant = parsed.path.rstrip("/")
        urls.extend(
            [
                urllib.parse.urljoin(
                    base_url,
                    f"/.well-known/oauth-authorization-server{tenant}",
                ),
                urllib.parse.urljoin(
                    base_url, f"/.well-known/openid-configuration{tenant}"
                ),
                urllib.parse.urljoin(
                    base_url, f"{tenant}/.well-known/openid-configuration"
                ),
            ]
        )

    urls.extend(
        [
            urllib.parse.urljoin(base_url, "/.well-known/oauth-authorization-server"),
            urllib.parse.urljoin(base_url, "/.well-known/openid-configuration"),
        ]
    )

    return urls


# TODO: Some OAuth providers require Initial Access Tokens (IATs) for dynamic client registration.
# This is not currently supported.
async def get_oauth_client_info_with_dynamic_client_registration(
    request,
    client_id: str,
    oauth_server_url: str,
    oauth_server_key: Optional[str] = None,
) -> OAuthClientInformationFull:
    try:
        oauth_server_metadata = None
        oauth_server_metadata_url = None

        redirect_base_url = (
            str(request.app.state.config.WEBUI_URL or request.base_url)
        ).rstrip("/")

        oauth_client_metadata = OAuthClientMetadata(
            client_name="Open WebUI",
            redirect_uris=[f"{redirect_base_url}/oauth/clients/{client_id}/callback"],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
        )

        # Attempt to fetch OAuth server metadata to get registration endpoint & scopes
        discovery_urls = get_discovery_urls(oauth_server_url)
        for url in discovery_urls:
            async with aiohttp.ClientSession(trust_env=True) as session:
                async with session.get(
                    url, ssl=AIOHTTP_CLIENT_SESSION_SSL
                ) as oauth_server_metadata_response:
                    if oauth_server_metadata_response.status == 200:
                        try:
                            oauth_server_metadata = OAuthMetadata.model_validate(
                                await oauth_server_metadata_response.json()
                            )
                            oauth_server_metadata_url = url
                            if (
                                oauth_client_metadata.scope is None
                                and oauth_server_metadata.scopes_supported is not None
                            ):
                                oauth_client_metadata.scope = " ".join(
                                    oauth_server_metadata.scopes_supported
                                )

                            if (
                                oauth_server_metadata.token_endpoint_auth_methods_supported
                                and oauth_client_metadata.token_endpoint_auth_method
                                not in oauth_server_metadata.token_endpoint_auth_methods_supported
                            ):
                                # Pick the first supported method from the server
                                oauth_client_metadata.token_endpoint_auth_method = oauth_server_metadata.token_endpoint_auth_methods_supported[
                                    0
                                ]

                            break
                        except Exception as e:
                            log.error(f"Error parsing OAuth metadata from {url}: {e}")
                            continue

        registration_url = None
        if oauth_server_metadata and oauth_server_metadata.registration_endpoint:
            registration_url = str(oauth_server_metadata.registration_endpoint)
        else:
            _, base_url = get_parsed_and_base_url(oauth_server_url)
            registration_url = urllib.parse.urljoin(base_url, "/register")

        registration_data = oauth_client_metadata.model_dump(
            exclude_none=True,
            mode="json",
            by_alias=True,
        )

        # Perform dynamic client registration and return client info
        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.post(
                registration_url, json=registration_data, ssl=AIOHTTP_CLIENT_SESSION_SSL
            ) as oauth_client_registration_response:
                try:
                    registration_response_json = (
                        await oauth_client_registration_response.json()
                    )

                    # The mcp package requires optional unset values to be None. If an empty string is passed, it gets validated and fails.
                    # This replaces all empty strings with None.
                    registration_response_json = {
                        k: (None if v == "" else v)
                        for k, v in registration_response_json.items()
                    }
                    oauth_client_info = OAuthClientInformationFull.model_validate(
                        {
                            **registration_response_json,
                            **{"issuer": oauth_server_metadata_url},
                            **{"server_metadata": oauth_server_metadata},
                        }
                    )
                    log.info(
                        f"Dynamic client registration successful at {registration_url}, client_id: {oauth_client_info.client_id}"
                    )
                    return oauth_client_info
                except Exception as e:
                    error_text = None
                    try:
                        error_text = await oauth_client_registration_response.text()
                        log.error(
                            f"Dynamic client registration failed at {registration_url}: {oauth_client_registration_response.status} - {error_text}"
                        )
                    except Exception as e:
                        pass

                    log.error(f"Error parsing client registration response: {e}")
                    raise Exception(
                        f"Dynamic client registration failed: {error_text}"
                        if error_text
                        else "Error parsing client registration response"
                    )
        raise Exception("Dynamic client registration failed")
    except Exception as e:
        log.error(f"Exception during dynamic client registration: {e}")
        raise e


class OAuthClientManager:
    def __init__(self, app):
        self.oauth = OAuth()
        self.app = app
        self.clients = {}

    def add_client(self, client_id, oauth_client_info: OAuthClientInformationFull):
        kwargs = {
            "name": client_id,
            "client_id": oauth_client_info.client_id,
            "client_secret": oauth_client_info.client_secret,
            "client_kwargs": {
                **(
                    {"scope": oauth_client_info.scope}
                    if oauth_client_info.scope
                    else {}
                ),
                **(
                    {
                        "token_endpoint_auth_method": oauth_client_info.token_endpoint_auth_method
                    }
                    if oauth_client_info.token_endpoint_auth_method
                    else {}
                ),
            },
            "server_metadata_url": (
                oauth_client_info.issuer if oauth_client_info.issuer else None
            ),
        }

        if (
            oauth_client_info.server_metadata
            and oauth_client_info.server_metadata.code_challenge_methods_supported
        ):
            if (
                isinstance(
                    oauth_client_info.server_metadata.code_challenge_methods_supported,
                    list,
                )
                and "S256"
                in oauth_client_info.server_metadata.code_challenge_methods_supported
            ):
                kwargs["code_challenge_method"] = "S256"

        self.clients[client_id] = {
            "client": self.oauth.register(**kwargs),
            "client_info": oauth_client_info,
        }
        return self.clients[client_id]

    def remove_client(self, client_id):
        if client_id in self.clients:
            del self.clients[client_id]
            log.info(f"Removed OAuth client {client_id}")

        if hasattr(self.oauth, "_clients"):
            if client_id in self.oauth._clients:
                self.oauth._clients.pop(client_id, None)

        if hasattr(self.oauth, "_registry"):
            if client_id in self.oauth._registry:
                self.oauth._registry.pop(client_id, None)

        return True

    async def _preflight_authorization_url(
        self, client, client_info: OAuthClientInformationFull
    ) -> bool:
        # TODO: Replace this logic with a more robust OAuth client registration validation
        # Only perform preflight checks for Starlette OAuth clients
        if not hasattr(client, "create_authorization_url"):
            return True

        redirect_uri = None
        if client_info.redirect_uris:
            redirect_uri = str(client_info.redirect_uris[0])

        try:
            auth_data = await client.create_authorization_url(redirect_uri=redirect_uri)
            authorization_url = auth_data.get("url")

            if not authorization_url:
                return True
        except Exception as e:
            log.debug(
                f"Skipping OAuth preflight for client {client_info.client_id}: {e}",
            )
            return True

        try:
            async with aiohttp.ClientSession(trust_env=True) as session:
                async with session.get(
                    authorization_url,
                    allow_redirects=False,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as resp:
                    if resp.status < 400:
                        return True
                    response_text = await resp.text()

                    error = None
                    error_description = ""

                    content_type = resp.headers.get("content-type", "")
                    if "application/json" in content_type:
                        try:
                            payload = json.loads(response_text)
                            error = payload.get("error")
                            error_description = payload.get("error_description", "")
                        except:
                            pass
                    else:
                        error_description = response_text

                    error_message = f"{error or ''} {error_description or ''}".lower()

                    if any(
                        keyword in error_message
                        for keyword in ("invalid_client", "invalid client", "client id")
                    ):
                        log.warning(
                            f"OAuth client preflight detected invalid registration for {client_info.client_id}: {error} {error_description}"
                        )

                        return False
        except Exception as e:
            log.debug(
                f"Skipping OAuth preflight network check for client {client_info.client_id}: {e}"
            )

        return True

    def get_client(self, client_id):
        client = self.clients.get(client_id)
        return client["client"] if client else None

    def get_client_info(self, client_id):
        client = self.clients.get(client_id)
        return client["client_info"] if client else None

    def get_server_metadata_url(self, client_id):
        if client_id in self.clients:
            client = self.clients[client_id]
            return (
                client._server_metadata_url
                if hasattr(client, "_server_metadata_url")
                else None
            )
        return None

    async def get_oauth_token(
        self, user_id: str, client_id: str, force_refresh: bool = False
    ):
        """
        Get a valid OAuth token for the user, automatically refreshing if needed.

        Args:
            user_id: The user ID
            client_id: The OAuth client ID (provider)
            force_refresh: Force token refresh even if current token appears valid

        Returns:
            dict: OAuth token data with access_token, or None if no valid token available
        """
        try:
            # Get the OAuth session
            session = OAuthSessions.get_session_by_provider_and_user_id(
                client_id, user_id
            )
            if not session:
                log.warning(
                    f"No OAuth session found for user {user_id}, client_id {client_id}"
                )
                return None

            if force_refresh or datetime.now() + timedelta(
                minutes=5
            ) >= datetime.fromtimestamp(session.expires_at):
                log.debug(
                    f"Token refresh needed for user {user_id}, client_id {session.provider}"
                )
                refreshed_token = await self._refresh_token(session)
                if refreshed_token:
                    return refreshed_token
                else:
                    log.warning(
                        f"Token refresh failed for user {user_id}, client_id {session.provider}, deleting session {session.id}"
                    )
                    OAuthSessions.delete_session_by_id(session.id)
                    return None
            return session.token

        except Exception as e:
            log.error(f"Error getting OAuth token for user {user_id}: {e}")
            return None

    async def _refresh_token(self, session) -> dict:
        """
        Refresh an OAuth token if needed, with concurrency protection.

        Args:
            session: The OAuth session object

        Returns:
            dict: Refreshed token data, or None if refresh failed
        """
        try:
            # Perform the actual refresh
            refreshed_token = await self._perform_token_refresh(session)

            if refreshed_token:
                # Update the session with new token data
                session = OAuthSessions.update_session_by_id(
                    session.id, refreshed_token
                )
                log.info(f"Successfully refreshed token for session {session.id}")
                return session.token
            else:
                log.error(f"Failed to refresh token for session {session.id}")
                return None

        except Exception as e:
            log.error(f"Error refreshing token for session {session.id}: {e}")
            return None

    async def _perform_token_refresh(self, session) -> dict:
        """
        Perform the actual OAuth token refresh.

        Args:
            session: The OAuth session object

        Returns:
            dict: New token data, or None if refresh failed
        """
        client_id = session.provider
        token_data = session.token

        if not token_data.get("refresh_token"):
            log.warning(f"No refresh token available for session {session.id}")
            return None

        try:
            client = self.get_client(client_id)
            if not client:
                log.error(f"No OAuth client found for provider {client_id}")
                return None

            token_endpoint = None
            async with aiohttp.ClientSession(trust_env=True) as session_http:
                async with session_http.get(
                    self.get_server_metadata_url(client_id)
                ) as r:
                    if r.status == 200:
                        openid_data = await r.json()
                        token_endpoint = openid_data.get("token_endpoint")
                    else:
                        log.error(
                            f"Failed to fetch OpenID configuration for client_id {client_id}"
                        )
            if not token_endpoint:
                log.error(f"No token endpoint found for client_id {client_id}")
                return None

            # Prepare refresh request
            refresh_data = {
                "grant_type": "refresh_token",
                "refresh_token": token_data["refresh_token"],
                "client_id": client.client_id,
            }
            if hasattr(client, "client_secret") and client.client_secret:
                refresh_data["client_secret"] = client.client_secret

            # Make refresh request
            async with aiohttp.ClientSession(trust_env=True) as session_http:
                async with session_http.post(
                    token_endpoint,
                    data=refresh_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as r:
                    if r.status == 200:
                        new_token_data = await r.json()

                        # Merge with existing token data (preserve refresh_token if not provided)
                        if "refresh_token" not in new_token_data:
                            new_token_data["refresh_token"] = token_data[
                                "refresh_token"
                            ]

                        # Add timestamp for tracking
                        new_token_data["issued_at"] = datetime.now().timestamp()

                        # Calculate expires_at if we have expires_in
                        if (
                            "expires_in" in new_token_data
                            and "expires_at" not in new_token_data
                        ):
                            new_token_data["expires_at"] = int(
                                datetime.now().timestamp()
                                + new_token_data["expires_in"]
                            )

                        log.debug(f"Token refresh successful for client_id {client_id}")
                        return new_token_data
                    else:
                        error_text = await r.text()
                        log.error(
                            f"Token refresh failed for client_id {client_id}: {r.status} - {error_text}"
                        )
                        return None

        except Exception as e:
            log.error(f"Exception during token refresh for client_id {client_id}: {e}")
            return None

    async def handle_authorize(self, request, client_id: str) -> RedirectResponse:
        client = self.get_client(client_id)
        if client is None:
            raise HTTPException(404)
        client_info = self.get_client_info(client_id)
        if client_info is None:
            raise HTTPException(404)

        redirect_uri = (
            client_info.redirect_uris[0] if client_info.redirect_uris else None
        )
        redirect_uri_str = str(redirect_uri) if redirect_uri else None
        return await client.authorize_redirect(request, redirect_uri_str)

    async def handle_callback(self, request, client_id: str, user_id: str, response):
        client = self.get_client(client_id)
        if client is None:
            raise HTTPException(404)

        error_message = None
        try:
            client_info = self.get_client_info(client_id)

            auth_params = {}
            if (
                client_info
                and hasattr(client_info, "client_id")
                and hasattr(client_info, "client_secret")
            ):
                auth_params["client_id"] = client_info.client_id
                auth_params["client_secret"] = client_info.client_secret

            token = await client.authorize_access_token(request, **auth_params)
            if token:
                try:
                    # Add timestamp for tracking
                    token["issued_at"] = datetime.now().timestamp()

                    # Calculate expires_at if we have expires_in
                    if "expires_in" in token and "expires_at" not in token:
                        token["expires_at"] = (
                            datetime.now().timestamp() + token["expires_in"]
                        )

                    # Clean up any existing sessions for this user/client_id first
                    sessions = OAuthSessions.get_sessions_by_user_id(user_id)
                    for session in sessions:
                        if session.provider == client_id:
                            OAuthSessions.delete_session_by_id(session.id)

                    session = OAuthSessions.create_session(
                        user_id=user_id,
                        provider=client_id,
                        token=token,
                    )
                    log.info(
                        f"Stored OAuth session server-side for user {user_id}, client_id {client_id}"
                    )
                except Exception as e:
                    error_message = "Failed to store OAuth session server-side"
                    log.error(f"Failed to store OAuth session server-side: {e}")
            else:
                error_message = "Failed to obtain OAuth token"
                log.warning(error_message)
        except Exception as e:
            error_message = _build_oauth_callback_error_message(e)
            log.warning(
                "OAuth callback error for user_id=%s client_id=%s: %s",
                user_id,
                client_id,
                error_message,
                exc_info=True,
            )

        redirect_url = (
            str(request.app.state.config.WEBUI_URL or request.base_url)
        ).rstrip("/")

        if error_message:
            log.debug(error_message)
            redirect_url = (
                f"{redirect_url}/?error={urllib.parse.quote_plus(error_message)}"
            )
            return RedirectResponse(url=redirect_url, headers=response.headers)

        response = RedirectResponse(url=redirect_url, headers=response.headers)
        return response


class OAuthManager:
    def __init__(self, app):
        self.oauth = OAuth()
        self.app = app

        self._clients = {}

        for name, provider_config in OAUTH_PROVIDERS.items():
            if "register" not in provider_config:
                log.error(f"OAuth provider {name} missing register function")
                continue

            client = provider_config["register"](self.oauth)
            self._clients[name] = client

    def get_client(self, provider_name):
        if provider_name not in self._clients:
            self._clients[provider_name] = self.oauth.create_client(provider_name)
        return self._clients[provider_name]

    def get_server_metadata_url(self, provider_name):
        if provider_name in self._clients:
            client = self._clients[provider_name]
            return (
                client._server_metadata_url
                if hasattr(client, "_server_metadata_url")
                else None
            )
        return None

    async def get_oauth_token(
        self, user_id: str, session_id: str, force_refresh: bool = False
    ):
        """
        Get a valid OAuth token for the user, automatically refreshing if needed.

        Args:
            user_id: The user ID
            provider: Optional provider name. If None, gets the most recent session.
            force_refresh: Force token refresh even if current token appears valid

        Returns:
            dict: OAuth token data with access_token, or None if no valid token available
        """
        try:
            # Get the OAuth session
            session = OAuthSessions.get_session_by_id_and_user_id(session_id, user_id)
            if not session:
                log.warning(
                    f"No OAuth session found for user {user_id}, session {session_id}"
                )
                return None

            if force_refresh or datetime.now() + timedelta(
                minutes=5
            ) >= datetime.fromtimestamp(session.expires_at):
                log.debug(
                    f"Token refresh needed for user {user_id}, provider {session.provider}"
                )
                refreshed_token = await self._refresh_token(session)
                if refreshed_token:
                    return refreshed_token
                else:
                    log.warning(
                        f"Token refresh failed for user {user_id}, provider {session.provider}, deleting session {session.id}"
                    )
                    OAuthSessions.delete_session_by_id(session.id)

                    return None
            return session.token

        except Exception as e:
            log.error(f"Error getting OAuth token for user {user_id}: {e}")
            return None

    async def _refresh_token(self, session) -> dict:
        """
        Refresh an OAuth token if needed, with concurrency protection.

        Args:
            session: The OAuth session object

        Returns:
            dict: Refreshed token data, or None if refresh failed
        """
        try:
            # Perform the actual refresh
            refreshed_token = await self._perform_token_refresh(session)

            if refreshed_token:
                # Update the session with new token data
                session = OAuthSessions.update_session_by_id(
                    session.id, refreshed_token
                )
                log.info(f"Successfully refreshed token for session {session.id}")
                return session.token
            else:
                log.error(f"Failed to refresh token for session {session.id}")
                return None

        except Exception as e:
            log.error(f"Error refreshing token for session {session.id}: {e}")
            return None

    async def _perform_token_refresh(self, session) -> dict:
        """
        Perform the actual OAuth token refresh.

        Args:
            session: The OAuth session object

        Returns:
            dict: New token data, or None if refresh failed
        """
        provider = session.provider
        token_data = session.token

        if not token_data.get("refresh_token"):
            log.warning(f"No refresh token available for session {session.id}")
            return None

        try:
            client = self.get_client(provider)
            if not client:
                log.error(f"No OAuth client found for provider {provider}")
                return None

            server_metadata_url = self.get_server_metadata_url(provider)
            token_endpoint = None
            async with aiohttp.ClientSession(trust_env=True) as session_http:
                async with session_http.get(server_metadata_url) as r:
                    if r.status == 200:
                        openid_data = await r.json()
                        token_endpoint = openid_data.get("token_endpoint")
                    else:
                        log.error(
                            f"Failed to fetch OpenID configuration for provider {provider}"
                        )
            if not token_endpoint:
                log.error(f"No token endpoint found for provider {provider}")
                return None

            # Prepare refresh request
            refresh_data = {
                "grant_type": "refresh_token",
                "refresh_token": token_data["refresh_token"],
                "client_id": client.client_id,
            }
            # Add client_secret if available (some providers require it)
            if hasattr(client, "client_secret") and client.client_secret:
                refresh_data["client_secret"] = client.client_secret

            # Make refresh request
            async with aiohttp.ClientSession(trust_env=True) as session_http:
                async with session_http.post(
                    token_endpoint,
                    data=refresh_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as r:
                    if r.status == 200:
                        new_token_data = await r.json()

                        # Merge with existing token data (preserve refresh_token if not provided)
                        if "refresh_token" not in new_token_data:
                            new_token_data["refresh_token"] = token_data[
                                "refresh_token"
                            ]

                        # Add timestamp for tracking
                        new_token_data["issued_at"] = datetime.now().timestamp()

                        # Calculate expires_at if we have expires_in
                        if (
                            "expires_in" in new_token_data
                            and "expires_at" not in new_token_data
                        ):
                            new_token_data["expires_at"] = int(
                                datetime.now().timestamp()
                                + new_token_data["expires_in"]
                            )

                        log.debug(f"Token refresh successful for provider {provider}")
                        return new_token_data
                    else:
                        error_text = await r.text()
                        log.error(
                            f"Token refresh failed for provider {provider}: {r.status} - {error_text}"
                        )
                        return None

        except Exception as e:
            log.error(f"Exception during token refresh for provider {provider}: {e}")
            return None

    def get_user_role(self, user, user_data):
        user_count = Users.get_num_users()
        if user and user_count == 1:
            # If the user is the only user, assign the role "admin" - actually repairs role for single user on login
            log.debug("Assigning the only user the admin role")
            return "admin"
        if not user and user_count == 0:
            # If there are no users, assign the role "admin", as the first user will be an admin
            log.debug("Assigning the first user the admin role")
            return "admin"

        if auth_manager_config.ENABLE_OAUTH_ROLE_MANAGEMENT:
            log.debug("Running OAUTH Role management")
            oauth_claim = auth_manager_config.OAUTH_ROLES_CLAIM
            oauth_allowed_roles = auth_manager_config.OAUTH_ALLOWED_ROLES
            oauth_admin_roles = auth_manager_config.OAUTH_ADMIN_ROLES
            oauth_roles = []
            # Default/fallback role if no matching roles are found
            role = auth_manager_config.DEFAULT_USER_ROLE

            # Next block extracts the roles from the user data, accepting nested claims of any depth
            if oauth_claim and oauth_allowed_roles and oauth_admin_roles:
                claim_data = user_data
                nested_claims = oauth_claim.split(".")
                for nested_claim in nested_claims:
                    claim_data = claim_data.get(nested_claim, {})

                # Try flat claim structure as alternative
                if not claim_data:
                    claim_data = user_data.get(oauth_claim, {})

                oauth_roles = []

                if isinstance(claim_data, list):
                    oauth_roles = claim_data
                elif isinstance(claim_data, str):
                    # Split by the configured separator if present
                    if OAUTH_ROLES_SEPARATOR and OAUTH_ROLES_SEPARATOR in claim_data:
                        oauth_roles = claim_data.split(OAUTH_ROLES_SEPARATOR)
                    else:
                        oauth_roles = [claim_data]
                elif isinstance(claim_data, int):
                    oauth_roles = [str(claim_data)]

            log.debug(f"Oauth Roles claim: {oauth_claim}")
            log.debug(f"User roles from oauth: {oauth_roles}")
            log.debug(f"Accepted user roles: {oauth_allowed_roles}")
            log.debug(f"Accepted admin roles: {oauth_admin_roles}")

            # If any roles are found, check if they match the allowed or admin roles
            if oauth_roles:
                # If role management is enabled, and matching roles are provided, use the roles
                for allowed_role in oauth_allowed_roles:
                    # If the user has any of the allowed roles, assign the role "user"
                    if allowed_role in oauth_roles:
                        log.debug("Assigned user the user role")
                        role = "user"
                        break
                for admin_role in oauth_admin_roles:
                    # If the user has any of the admin roles, assign the role "admin"
                    if admin_role in oauth_roles:
                        log.debug("Assigned user the admin role")
                        role = "admin"
                        break
        else:
            if not user:
                # If role management is disabled, use the default role for new users
                role = auth_manager_config.DEFAULT_USER_ROLE
            else:
                # If role management is disabled, use the existing role for existing users
                role = user.role

        return role

    def update_user_groups(self, user, user_data, default_permissions):
        log.debug("Running OAUTH Group management")
        oauth_claim = auth_manager_config.OAUTH_GROUPS_CLAIM

        try:
            blocked_groups = json.loads(auth_manager_config.OAUTH_BLOCKED_GROUPS)
        except Exception as e:
            log.exception(f"Error loading OAUTH_BLOCKED_GROUPS: {e}")
            blocked_groups = []

        user_oauth_groups = []
        # Nested claim search for groups claim
        if oauth_claim:
            claim_data = user_data
            nested_claims = oauth_claim.split(".")
            for nested_claim in nested_claims:
                claim_data = claim_data.get(nested_claim, {})

            if isinstance(claim_data, list):
                user_oauth_groups = claim_data
            elif isinstance(claim_data, str):
                # Split by the configured separator if present
                if OAUTH_GROUPS_SEPARATOR in claim_data:
                    user_oauth_groups = claim_data.split(OAUTH_GROUPS_SEPARATOR)
                else:
                    user_oauth_groups = [claim_data]
            else:
                user_oauth_groups = []

        user_current_groups: list[GroupModel] = Groups.get_groups_by_member_id(user.id)
        all_available_groups: list[GroupModel] = Groups.get_all_groups()

        # Create groups if they don't exist and creation is enabled
        if auth_manager_config.ENABLE_OAUTH_GROUP_CREATION:
            log.debug("Checking for missing groups to create...")
            all_group_names = {g.name for g in all_available_groups}
            groups_created = False
            # Determine creator ID: Prefer admin, fallback to current user if no admin exists
            admin_user = Users.get_super_admin_user()
            creator_id = admin_user.id if admin_user else user.id
            log.debug(f"Using creator ID {creator_id} for potential group creation.")

            for group_name in user_oauth_groups:
                if group_name not in all_group_names:
                    log.info(
                        f"Group '{group_name}' not found via OAuth claim. Creating group..."
                    )
                    try:
                        new_group_form = GroupForm(
                            name=group_name,
                            description=f"Group '{group_name}' created automatically via OAuth.",
                            permissions=default_permissions,  # Use default permissions from function args
                            user_ids=[],  # Start with no users, user will be added later by subsequent logic
                        )
                        # Use determined creator ID (admin or fallback to current user)
                        created_group = Groups.insert_new_group(
                            creator_id, new_group_form
                        )
                        if created_group:
                            log.info(
                                f"Successfully created group '{group_name}' with ID {created_group.id} using creator ID {creator_id}"
                            )
                            groups_created = True
                            # Add to local set to prevent duplicate creation attempts in this run
                            all_group_names.add(group_name)
                        else:
                            log.error(
                                f"Failed to create group '{group_name}' via OAuth."
                            )
                    except Exception as e:
                        log.error(f"Error creating group '{group_name}' via OAuth: {e}")

            # Refresh the list of all available groups if any were created
            if groups_created:
                all_available_groups = Groups.get_all_groups()
                log.debug("Refreshed list of all available groups after creation.")

        log.debug(f"Oauth Groups claim: {oauth_claim}")
        log.debug(f"User oauth groups: {user_oauth_groups}")
        log.debug(f"User's current groups: {[g.name for g in user_current_groups]}")
        log.debug(
            f"All groups available in OpenWebUI: {[g.name for g in all_available_groups]}"
        )

        # Remove groups that user is no longer a part of
        for group_model in user_current_groups:
            if (
                user_oauth_groups
                and group_model.name not in user_oauth_groups
                and not is_in_blocked_groups(group_model.name, blocked_groups)
            ):
                # Remove group from user
                log.debug(
                    f"Removing user from group {group_model.name} as it is no longer in their oauth groups"
                )
                Groups.remove_users_from_group(group_model.id, [user.id])

                # In case a group is created, but perms are never assigned to the group by hitting "save"
                group_permissions = group_model.permissions
                if not group_permissions:
                    group_permissions = default_permissions

                Groups.update_group_by_id(
                    id=group_model.id,
                    form_data=GroupUpdateForm(
                        name=group_model.name,
                        description=group_model.description,
                        permissions=group_permissions,
                    ),
                    overwrite=False,
                )

        # Add user to new groups
        for group_model in all_available_groups:
            if (
                user_oauth_groups
                and group_model.name in user_oauth_groups
                and not any(gm.name == group_model.name for gm in user_current_groups)
                and not is_in_blocked_groups(group_model.name, blocked_groups)
            ):
                # Add user to group
                log.debug(
                    f"Adding user to group {group_model.name} as it was found in their oauth groups"
                )

                Groups.add_users_to_group(group_model.id, [user.id])

                # In case a group is created, but perms are never assigned to the group by hitting "save"
                group_permissions = group_model.permissions
                if not group_permissions:
                    group_permissions = default_permissions

                Groups.update_group_by_id(
                    id=group_model.id,
                    form_data=GroupUpdateForm(
                        name=group_model.name,
                        description=group_model.description,
                        permissions=group_permissions,
                    ),
                    overwrite=False,
                )

    async def _process_picture_url(
        self, picture_url: str, access_token: str = None
    ) -> str:
        """Process a picture URL and return a base64 encoded data URL.

        Args:
            picture_url: The URL of the picture to process
            access_token: Optional OAuth access token for authenticated requests

        Returns:
            A data URL containing the base64 encoded picture, or "/user.png" if processing fails
        """
        if not picture_url:
            return "/user.png"

        try:
            get_kwargs = {}
            if access_token:
                get_kwargs["headers"] = {
                    "Authorization": f"Bearer {access_token}",
                }
            async with aiohttp.ClientSession(trust_env=True) as session:
                async with session.get(
                    picture_url, **get_kwargs, ssl=AIOHTTP_CLIENT_SESSION_SSL
                ) as resp:
                    if resp.ok:
                        picture = await resp.read()
                        base64_encoded_picture = base64.b64encode(picture).decode(
                            "utf-8"
                        )
                        guessed_mime_type = mimetypes.guess_type(picture_url)[0]
                        if guessed_mime_type is None:
                            guessed_mime_type = "image/jpeg"
                        return (
                            f"data:{guessed_mime_type};base64,{base64_encoded_picture}"
                        )
                    else:
                        log.warning(
                            f"Failed to fetch profile picture from {picture_url}"
                        )
                        return "/user.png"
        except Exception as e:
            log.error(f"Error processing profile picture '{picture_url}': {e}")
            return "/user.png"

    async def handle_login(self, request, provider):
        if provider not in OAUTH_PROVIDERS:
            raise HTTPException(404)
        # If the provider has a custom redirect URL, use that, otherwise automatically generate one
        redirect_uri = OAUTH_PROVIDERS[provider].get("redirect_uri") or request.url_for(
            "oauth_login_callback", provider=provider
        )
        client = self.get_client(provider)
        if client is None:
            raise HTTPException(404)
        return await client.authorize_redirect(request, redirect_uri)

    async def handle_callback(self, request, provider, response):
        if provider not in OAUTH_PROVIDERS:
            raise HTTPException(404)

        error_message = None
        try:
            client = self.get_client(provider)

            auth_params = {}

            if client:
                if (
                    hasattr(client, "client_id")
                    and OAUTH_ACCESS_TOKEN_REQUEST_INCLUDE_CLIENT_ID
                ):
                    auth_params["client_id"] = client.client_id

            try:
                token = await client.authorize_access_token(request, **auth_params)
            except Exception as e:
                detailed_error = _build_oauth_callback_error_message(e)
                log.warning(
                    "OAuth callback error during authorize_access_token for provider %s: %s",
                    provider,
                    detailed_error,
                    exc_info=True,
                )
                raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)

            # Try to get userinfo from the token first, some providers include it there
            user_data: UserInfo = token.get("userinfo")
            if (
                (not user_data)
                or (auth_manager_config.OAUTH_EMAIL_CLAIM not in user_data)
                or (auth_manager_config.OAUTH_USERNAME_CLAIM not in user_data)
            ):
                user_data: UserInfo = await client.userinfo(token=token)
            if (
                provider == "feishu"
                and isinstance(user_data, dict)
                and "data" in user_data
            ):
                user_data = user_data["data"]
            if not user_data:
                log.warning(f"OAuth callback failed, user data is missing: {token}")
                raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)

            # Extract the "sub" claim, using custom claim if configured
            if auth_manager_config.OAUTH_SUB_CLAIM:
                sub = user_data.get(auth_manager_config.OAUTH_SUB_CLAIM)
            else:
                # Fallback to the default sub claim if not configured
                sub = user_data.get(OAUTH_PROVIDERS[provider].get("sub_claim", "sub"))
            if not sub:
                log.warning(f"OAuth callback failed, sub is missing: {user_data}")
                raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)

            oauth_data = {}
            oauth_data[provider] = {
                "sub": sub,
            }

            # Email extraction
            email_claim = auth_manager_config.OAUTH_EMAIL_CLAIM
            email = user_data.get(email_claim, "")
            # We currently mandate that email addresses are provided
            if not email:
                # If the provider is GitHub,and public email is not provided, we can use the access token to fetch the user's email
                if provider == "github":
                    try:
                        access_token = token.get("access_token")
                        headers = {"Authorization": f"Bearer {access_token}"}
                        async with aiohttp.ClientSession(trust_env=True) as session:
                            async with session.get(
                                "https://api.github.com/user/emails",
                                headers=headers,
                                ssl=AIOHTTP_CLIENT_SESSION_SSL,
                            ) as resp:
                                if resp.ok:
                                    emails = await resp.json()
                                    # use the primary email as the user's email
                                    primary_email = next(
                                        (
                                            e["email"]
                                            for e in emails
                                            if e.get("primary")
                                        ),
                                        None,
                                    )
                                    if primary_email:
                                        email = primary_email
                                    else:
                                        log.warning(
                                            "No primary email found in GitHub response"
                                        )
                                        raise HTTPException(
                                            400, detail=ERROR_MESSAGES.INVALID_CRED
                                        )
                                else:
                                    log.warning("Failed to fetch GitHub email")
                                    raise HTTPException(
                                        400, detail=ERROR_MESSAGES.INVALID_CRED
                                    )
                    except Exception as e:
                        log.warning(f"Error fetching GitHub email: {e}")
                        raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)
                elif ENABLE_OAUTH_EMAIL_FALLBACK:
                    email = f"{provider}@{sub}.local"
                else:
                    log.warning(f"OAuth callback failed, email is missing: {user_data}")
                    raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)

            email = email.lower()
            # If allowed domains are configured, check if the email domain is in the list
            if (
                "*" not in auth_manager_config.OAUTH_ALLOWED_DOMAINS
                and email.split("@")[-1]
                not in auth_manager_config.OAUTH_ALLOWED_DOMAINS
            ):
                log.warning(
                    f"OAuth callback failed, e-mail domain is not in the list of allowed domains: {user_data}"
                )
                raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)

            # Check if the user exists
            user = Users.get_user_by_oauth_sub(provider, sub)
            if not user:
                # If the user does not exist, check if merging is enabled
                if auth_manager_config.OAUTH_MERGE_ACCOUNTS_BY_EMAIL:
                    # Check if the user exists by email
                    user = Users.get_user_by_email(email)
                    if user:
                        # Update the user with the new oauth sub
                        Users.update_user_oauth_by_id(user.id, provider, sub)

            if user:
                determined_role = self.get_user_role(user, user_data)
                if user.role != determined_role:
                    Users.update_user_role_by_id(user.id, determined_role)
                    # Update the user object in memory as well,
                    # to avoid problems with the ENABLE_OAUTH_GROUP_MANAGEMENT check below
                    user.role = determined_role
                # Update profile picture if enabled and different from current
                if auth_manager_config.OAUTH_UPDATE_PICTURE_ON_LOGIN:
                    picture_claim = auth_manager_config.OAUTH_PICTURE_CLAIM
                    if picture_claim:
                        new_picture_url = user_data.get(
                            picture_claim,
                            OAUTH_PROVIDERS[provider].get("picture_url", ""),
                        )
                        processed_picture_url = await self._process_picture_url(
                            new_picture_url, token.get("access_token")
                        )
                        if processed_picture_url != user.profile_image_url:
                            Users.update_user_profile_image_url_by_id(
                                user.id, processed_picture_url
                            )
                            log.debug(f"Updated profile picture for user {user.email}")
            else:
                # If the user does not exist, check if signups are enabled
                if auth_manager_config.ENABLE_OAUTH_SIGNUP:
                    # Check if an existing user with the same email already exists
                    existing_user = Users.get_user_by_email(email)
                    if existing_user:
                        raise HTTPException(400, detail=ERROR_MESSAGES.EMAIL_TAKEN)

                    picture_claim = auth_manager_config.OAUTH_PICTURE_CLAIM
                    if picture_claim:
                        picture_url = user_data.get(
                            picture_claim,
                            OAUTH_PROVIDERS[provider].get("picture_url", ""),
                        )
                        picture_url = await self._process_picture_url(
                            picture_url, token.get("access_token")
                        )
                    else:
                        picture_url = "/user.png"
                    username_claim = auth_manager_config.OAUTH_USERNAME_CLAIM

                    name = user_data.get(username_claim)
                    if not name:
                        log.warning("Username claim is missing, using email as name")
                        name = email

                    user = Auths.insert_new_auth(
                        email=email,
                        password=get_password_hash(
                            str(uuid.uuid4())
                        ),  # Random password, not used
                        name=name,
                        profile_image_url=picture_url,
                        role=self.get_user_role(None, user_data),
                        oauth=oauth_data,
                    )

                    if auth_manager_config.WEBHOOK_URL:
                        await post_webhook(
                            WEBUI_NAME,
                            auth_manager_config.WEBHOOK_URL,
                            WEBHOOK_MESSAGES.USER_SIGNUP(user.name),
                            {
                                "action": "signup",
                                "message": WEBHOOK_MESSAGES.USER_SIGNUP(user.name),
                                "user": user.model_dump_json(exclude_none=True),
                            },
                        )

                    apply_default_group_assignment(
                        request.app.state.config.DEFAULT_GROUP_ID,
                        user.id,
                    )

                else:
                    raise HTTPException(
                        status.HTTP_403_FORBIDDEN,
                        detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
                    )

            jwt_token = create_token(
                data={"id": user.id},
                expires_delta=parse_duration(auth_manager_config.JWT_EXPIRES_IN),
            )
            if (
                auth_manager_config.ENABLE_OAUTH_GROUP_MANAGEMENT
                and user.role != "admin"
            ):
                self.update_user_groups(
                    user=user,
                    user_data=user_data,
                    default_permissions=request.app.state.config.USER_PERMISSIONS,
                )

        except Exception as e:
            log.error(f"Error during OAuth process: {e}")
            error_message = (
                e.detail
                if isinstance(e, HTTPException) and e.detail
                else ERROR_MESSAGES.DEFAULT("Error during OAuth process")
            )

        redirect_base_url = (
            str(request.app.state.config.WEBUI_URL or request.base_url)
        ).rstrip("/")
        redirect_url = f"{redirect_base_url}/auth"

        if error_message:
            redirect_url = f"{redirect_url}?error={error_message}"
            return RedirectResponse(url=redirect_url, headers=response.headers)

        response = RedirectResponse(url=redirect_url, headers=response.headers)

        # Set the cookie token
        # Redirect back to the frontend with the JWT token
        response.set_cookie(
            key="token",
            value=jwt_token,
            httponly=False,  # Required for frontend access
            samesite=WEBUI_AUTH_COOKIE_SAME_SITE,
            secure=WEBUI_AUTH_COOKIE_SECURE,
        )

        # Legacy cookies for compatibility with older frontend versions
        if ENABLE_OAUTH_ID_TOKEN_COOKIE:
            response.set_cookie(
                key="oauth_id_token",
                value=token.get("id_token"),
                httponly=True,
                samesite=WEBUI_AUTH_COOKIE_SAME_SITE,
                secure=WEBUI_AUTH_COOKIE_SECURE,
            )

        try:
            # Add timestamp for tracking
            token["issued_at"] = datetime.now().timestamp()

            # Calculate expires_at if we have expires_in
            if "expires_in" in token and "expires_at" not in token:
                token["expires_at"] = datetime.now().timestamp() + token["expires_in"]

            # Clean up any existing sessions for this user/provider first
            sessions = OAuthSessions.get_sessions_by_user_id(user.id)
            for session in sessions:
                if session.provider == provider:
                    OAuthSessions.delete_session_by_id(session.id)

            session = OAuthSessions.create_session(
                user_id=user.id,
                provider=provider,
                token=token,
            )

            response.set_cookie(
                key="oauth_session_id",
                value=session.id,
                httponly=True,
                samesite=WEBUI_AUTH_COOKIE_SAME_SITE,
                secure=WEBUI_AUTH_COOKIE_SECURE,
            )

            log.info(
                f"Stored OAuth session server-side for user {user.id}, provider {provider}"
            )
        except Exception as e:
            log.error(f"Failed to store OAuth session server-side: {e}")

        return response
