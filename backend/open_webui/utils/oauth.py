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
from authlib.jose.errors import BadSignatureError
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
    OAUTH_REFRESH_TOKEN_INCLUDE_SCOPE,
    OAUTH_MERGE_ACCOUNTS_BY_EMAIL,
    OAUTH_PROVIDERS,
    ENABLE_OAUTH_ROLE_MANAGEMENT,
    ENABLE_OAUTH_GROUP_MANAGEMENT,
    ENABLE_OAUTH_GROUP_CREATION,
    OAUTH_GROUP_DEFAULT_SHARE,
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
    OAUTH_UPDATE_NAME_ON_LOGIN,
    OAUTH_UPDATE_EMAIL_ON_LOGIN,
    OAUTH_ACCESS_TOKEN_REQUEST_INCLUDE_CLIENT_ID,
    OAUTH_AUDIENCE,
    OAUTH_AUTHORIZE_PARAMS,
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
    OAUTH_MAX_SESSIONS_PER_USER,
    REDIS_KEY_PREFIX,
)
from open_webui.utils.misc import parse_duration
from open_webui.utils.auth import get_password_hash, create_token
from open_webui.utils.webhook import post_webhook
from open_webui.utils.groups import apply_default_group_assignment
from open_webui.retrieval.web.utils import validate_url

from mcp.shared.auth import (
    OAuthClientMetadata as MCPOAuthClientMetadata,
    OAuthMetadata,
)

from authlib.oauth2.rfc6749.errors import OAuth2Error


class OAuthClientMetadata(MCPOAuthClientMetadata):
    token_endpoint_auth_method: Literal['none', 'client_secret_basic', 'client_secret_post'] = 'client_secret_post'
    pass


class OAuthClientInformationFull(OAuthClientMetadata):
    issuer: Optional[str] = None  # URL of the OAuth server that issued this client

    client_id: str
    client_secret: str | None = None
    client_id_issued_at: int | None = None
    client_secret_expires_at: int | None = None

    server_metadata: Optional[OAuthMetadata] = None  # Fetched from the OAuth server


from open_webui.env import GLOBAL_LOG_LEVEL

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)

auth_manager_config = AppConfig()
auth_manager_config.DEFAULT_USER_ROLE = DEFAULT_USER_ROLE
auth_manager_config.ENABLE_OAUTH_SIGNUP = ENABLE_OAUTH_SIGNUP
auth_manager_config.OAUTH_REFRESH_TOKEN_INCLUDE_SCOPE = OAUTH_REFRESH_TOKEN_INCLUDE_SCOPE
auth_manager_config.OAUTH_MERGE_ACCOUNTS_BY_EMAIL = OAUTH_MERGE_ACCOUNTS_BY_EMAIL
auth_manager_config.ENABLE_OAUTH_ROLE_MANAGEMENT = ENABLE_OAUTH_ROLE_MANAGEMENT
auth_manager_config.ENABLE_OAUTH_GROUP_MANAGEMENT = ENABLE_OAUTH_GROUP_MANAGEMENT
auth_manager_config.ENABLE_OAUTH_GROUP_CREATION = ENABLE_OAUTH_GROUP_CREATION
auth_manager_config.OAUTH_GROUP_DEFAULT_SHARE = OAUTH_GROUP_DEFAULT_SHARE
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
auth_manager_config.OAUTH_UPDATE_NAME_ON_LOGIN = OAUTH_UPDATE_NAME_ON_LOGIN
auth_manager_config.OAUTH_UPDATE_EMAIL_ON_LOGIN = OAUTH_UPDATE_EMAIL_ON_LOGIN
auth_manager_config.OAUTH_AUDIENCE = OAUTH_AUDIENCE


# Conservative default when the provider omits both expires_in and expires_at.
# Matches the value recommended by Authlib's compliance_fix documentation.
DEFAULT_TOKEN_EXPIRY_SECONDS = 3600


def _normalize_token_expiry(token: dict) -> dict:
    """Ensure a token dict always has a numeric ``expires_at``.

    Resolution order:
    1. If *expires_at* is already present and non-None, trust it.
    2. Else if *expires_in* is present and non-None, compute *expires_at*.
    3. Otherwise fall back to ``DEFAULT_TOKEN_EXPIRY_SECONDS`` and log a
       warning so operators can identify providers that omit expiration.

    Also stamps *issued_at* for auditing.
    """
    token['issued_at'] = datetime.now().timestamp()

    if token.get('expires_at') is not None:
        token['expires_at'] = int(token['expires_at'])
        return token

    if token.get('expires_in') is not None:
        token['expires_at'] = int(datetime.now().timestamp() + token['expires_in'])
        return token

    # Neither field present — conservative fallback
    log.warning(
        "OAuth token response missing both 'expires_in' and 'expires_at'; "
        f'defaulting to {DEFAULT_TOKEN_EXPIRY_SECONDS}s from now'
    )
    token['expires_at'] = int(datetime.now().timestamp() + DEFAULT_TOKEN_EXPIRY_SECONDS)
    return token


FERNET = None

if len(OAUTH_CLIENT_INFO_ENCRYPTION_KEY) != 44:
    key_bytes = hashlib.sha256(OAUTH_CLIENT_INFO_ENCRYPTION_KEY.encode()).digest()
    OAUTH_CLIENT_INFO_ENCRYPTION_KEY = base64.urlsafe_b64encode(key_bytes)
else:
    OAUTH_CLIENT_INFO_ENCRYPTION_KEY = OAUTH_CLIENT_INFO_ENCRYPTION_KEY.encode()

try:
    FERNET = Fernet(OAUTH_CLIENT_INFO_ENCRYPTION_KEY)
except Exception as e:
    log.error(f'Error initializing Fernet with provided key: {e}')
    raise


def encrypt_data(data) -> str:
    """Encrypt data for storage"""
    try:
        data_json = json.dumps(data)
        encrypted = FERNET.encrypt(data_json.encode()).decode()
        return encrypted
    except Exception as e:
        log.error(f'Error encrypting data: {e}')
        raise


def decrypt_data(data: str):
    """Decrypt data from storage"""
    try:
        decrypted = FERNET.decrypt(data.encode()).decode()
        return json.loads(decrypted)
    except Exception as e:
        log.error(f'Error decrypting data: {e}')
        raise


def _build_oauth_callback_error_message(e: Exception) -> str:
    """
    Produce a user-facing callback error string with actionable context.
    Keeps the message short and strips newlines for safe redirect usage.
    """
    if isinstance(e, OAuth2Error):
        parts = [p for p in [e.error, e.description] if p]
        detail = ' - '.join(parts)
    elif isinstance(e, HTTPException):
        detail = e.detail if isinstance(e.detail, str) else str(e.detail)
    elif isinstance(e, aiohttp.ClientResponseError):
        detail = f'Upstream provider returned {e.status}: {e.message}'
    elif isinstance(e, aiohttp.ClientError):
        detail = str(e)
    elif isinstance(e, KeyError):
        missing = str(e).strip("'")
        if missing.lower() == 'state':
            detail = 'Missing state parameter in callback (session may have expired)'
        else:
            detail = f"Missing expected key '{missing}' in OAuth response"
    else:
        detail = str(e)

    detail = detail.replace('\n', ' ').strip()
    if not detail:
        detail = e.__class__.__name__

    message = f'OAuth callback failed: {detail}'
    return message[:197] + '...' if len(message) > 200 else message


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
        if any(char in group_pattern for char in ['^', '$', '[', ']', '(', ')', '{', '}', '+', '\\', '|']):
            try:
                # Use the original pattern as-is for regex matching
                if re.search(group_pattern, group_name):
                    return True
            except re.error:
                # If regex is invalid, fall through to wildcard check
                pass

        # Shell-style wildcard match (supports * and ?)
        if '*' in group_pattern or '?' in group_pattern:
            if fnmatch.fnmatch(group_name, group_pattern):
                return True

    return False


def get_parsed_and_base_url(server_url) -> tuple[urllib.parse.ParseResult, str]:
    parsed = urllib.parse.urlparse(server_url)
    base_url = f'{parsed.scheme}://{parsed.netloc}'
    return parsed, base_url


async def get_authorization_server_discovery_urls(server_url: str) -> list[str]:
    """
    https://modelcontextprotocol.io/specification/2025-03-26/basic/authorization
    """

    authorization_servers = []
    try:
        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.post(
                server_url,
                json={'jsonrpc': '2.0', 'method': 'initialize', 'params': {}, 'id': 1},
                headers={'Content-Type': 'application/json'},
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as response:
                if response.status == 401:
                    resource_metadata_urls = []
                    match = re.search(
                        r'resource_metadata=(?:"([^"]+)"|([^\s,]+))',
                        response.headers.get('WWW-Authenticate', ''),
                    )
                    if match:
                        resource_metadata_urls = [match.group(1) or match.group(2)]
                        log.debug(f'Found resource_metadata URL: {resource_metadata_urls[0]}')
                    else:
                        # Fall back to well-known resource metadata URIs (RFC 9728 §4.2)
                        parsed, base_url = get_parsed_and_base_url(server_url)
                        if parsed.path and parsed.path != '/':
                            path = parsed.path.rstrip('/')
                            resource_metadata_urls.append(
                                urllib.parse.urljoin(base_url, f'/.well-known/oauth-protected-resource{path}')
                            )
                        resource_metadata_urls.append(
                            urllib.parse.urljoin(base_url, '/.well-known/oauth-protected-resource')
                        )
                        log.debug(f'No resource_metadata in header, trying well-known URIs: {resource_metadata_urls}')

                    # Fetch Protected Resource metadata from candidate URLs
                    for resource_metadata_url in resource_metadata_urls:
                        try:
                            async with session.get(
                                resource_metadata_url, ssl=AIOHTTP_CLIENT_SESSION_SSL
                            ) as resource_response:
                                if resource_response.status == 200:
                                    resource_metadata = await resource_response.json()

                                    servers = resource_metadata.get('authorization_servers', [])
                                    if servers:
                                        authorization_servers = servers
                                        log.debug(f'Discovered authorization servers: {servers}')
                                        break
                        except Exception as e:
                            log.debug(f'Failed to fetch resource metadata from {resource_metadata_url}: {e}')
                            continue
    except Exception as e:
        log.debug(f'MCP Protected Resource discovery failed: {e}')

    discovery_urls = []
    for auth_server in authorization_servers:
        auth_server = auth_server.rstrip('/')
        discovery_urls.extend(_build_well_known_urls(auth_server))

    return discovery_urls


def _build_well_known_urls(server_url: str) -> list[str]:
    """Build RFC 8414 / OIDC Discovery well-known URLs for a server URL."""
    parsed, base_url = get_parsed_and_base_url(server_url)
    urls = []

    if parsed.path and parsed.path != '/':
        path = parsed.path.rstrip('/')
        urls.extend(
            [
                urllib.parse.urljoin(base_url, f'/.well-known/oauth-authorization-server{path}'),
                urllib.parse.urljoin(base_url, f'/.well-known/openid-configuration{path}'),
                urllib.parse.urljoin(base_url, f'{path}/.well-known/openid-configuration'),
            ]
        )

    urls.extend(
        [
            urllib.parse.urljoin(base_url, '/.well-known/oauth-authorization-server'),
            urllib.parse.urljoin(base_url, '/.well-known/openid-configuration'),
        ]
    )

    return urls


async def get_discovery_urls(server_url) -> list[str]:
    urls = await get_authorization_server_discovery_urls(server_url)
    urls.extend(_build_well_known_urls(server_url))
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

        redirect_base_url = (str(request.app.state.config.WEBUI_URL or request.base_url)).rstrip('/')

        oauth_client_metadata = OAuthClientMetadata(
            client_name='Open WebUI',
            redirect_uris=[f'{redirect_base_url}/oauth/clients/{client_id}/callback'],
            grant_types=['authorization_code', 'refresh_token'],
            response_types=['code'],
        )

        # Attempt to fetch OAuth server metadata to get registration endpoint & scopes
        discovery_urls = await get_discovery_urls(oauth_server_url)
        for url in discovery_urls:
            async with aiohttp.ClientSession(trust_env=True) as session:
                async with session.get(url, ssl=AIOHTTP_CLIENT_SESSION_SSL) as oauth_server_metadata_response:
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
                                oauth_client_metadata.scope = ' '.join(oauth_server_metadata.scopes_supported)

                            if (
                                oauth_server_metadata.token_endpoint_auth_methods_supported
                                and oauth_client_metadata.token_endpoint_auth_method
                                not in oauth_server_metadata.token_endpoint_auth_methods_supported
                            ):
                                # Pick the first supported method from the server
                                oauth_client_metadata.token_endpoint_auth_method = (
                                    oauth_server_metadata.token_endpoint_auth_methods_supported[0]
                                )

                            break
                        except Exception as e:
                            log.error(f'Error parsing OAuth metadata from {url}: {e}')
                            continue

        registration_url = None
        if oauth_server_metadata and oauth_server_metadata.registration_endpoint:
            registration_url = str(oauth_server_metadata.registration_endpoint)
        else:
            _, base_url = get_parsed_and_base_url(oauth_server_url)
            registration_url = urllib.parse.urljoin(base_url, '/register')

        registration_data = oauth_client_metadata.model_dump(
            exclude_none=True,
            mode='json',
            by_alias=True,
        )

        # Perform dynamic client registration and return client info
        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.post(
                registration_url, json=registration_data, ssl=AIOHTTP_CLIENT_SESSION_SSL
            ) as oauth_client_registration_response:
                try:
                    registration_response_json = await oauth_client_registration_response.json()

                    # The mcp package requires optional unset values to be None. If an empty string is passed, it gets validated and fails.
                    # This replaces all empty strings with None.
                    registration_response_json = {
                        k: (None if v == '' else v) for k, v in registration_response_json.items()
                    }
                    oauth_client_info = OAuthClientInformationFull.model_validate(
                        {
                            **registration_response_json,
                            **{'issuer': oauth_server_metadata_url},
                            **{'server_metadata': oauth_server_metadata},
                        }
                    )
                    log.info(
                        f'Dynamic client registration successful at {registration_url}, client_id: {oauth_client_info.client_id}'
                    )
                    return oauth_client_info
                except Exception as e:
                    error_text = None
                    try:
                        error_text = await oauth_client_registration_response.text()
                        log.error(
                            f'Dynamic client registration failed at {registration_url}: {oauth_client_registration_response.status} - {error_text}'
                        )
                    except Exception as e:
                        pass

                    log.error(f'Error parsing client registration response: {e}')
                    raise Exception(
                        f'Dynamic client registration failed: {error_text}'
                        if error_text
                        else 'Error parsing client registration response'
                    )
        raise Exception('Dynamic client registration failed')
    except Exception as e:
        log.error(f'Exception during dynamic client registration: {e}')
        raise e


async def get_oauth_client_info_with_static_credentials(
    request,
    client_id: str,
    oauth_server_url: str,
    oauth_client_id: str,
    oauth_client_secret: str,
) -> OAuthClientInformationFull:
    """
    Build an OAuthClientInformationFull from user-provided static credentials.
    Performs server metadata discovery to resolve authorization/token endpoints,
    but skips dynamic client registration entirely.
    """
    try:
        oauth_server_metadata = None
        oauth_server_metadata_url = None

        redirect_base_url = (str(request.app.state.config.WEBUI_URL or request.base_url)).rstrip('/')
        redirect_uri = f'{redirect_base_url}/oauth/clients/{client_id}/callback'

        # Discover server metadata (authorization endpoint, token endpoint, scopes, etc.)
        discovery_urls = await get_discovery_urls(oauth_server_url)
        for url in discovery_urls:
            async with aiohttp.ClientSession(trust_env=True) as session:
                async with session.get(url, ssl=AIOHTTP_CLIENT_SESSION_SSL) as resp:
                    if resp.status == 200:
                        try:
                            oauth_server_metadata = OAuthMetadata.model_validate(await resp.json())
                            oauth_server_metadata_url = url
                            break
                        except Exception as e:
                            log.error(f'Error parsing OAuth metadata from {url}: {e}')
                            continue

        # Let the OAuth provider apply its default scopes.
        # We intentionally do NOT join all scopes_supported here — that list
        # represents every scope the server *can* grant, not what the client
        # should request.  Requesting all of them is almost always wrong and
        # can break providers like Entra ID that require resource-specific scopes.
        scope = None

        # Determine token_endpoint_auth_method
        token_endpoint_auth_method = 'client_secret_post'
        if (
            oauth_server_metadata
            and oauth_server_metadata.token_endpoint_auth_methods_supported
            and token_endpoint_auth_method not in oauth_server_metadata.token_endpoint_auth_methods_supported
        ):
            token_endpoint_auth_method = oauth_server_metadata.token_endpoint_auth_methods_supported[0]

        oauth_client_info = OAuthClientInformationFull(
            client_id=oauth_client_id,
            client_secret=oauth_client_secret,
            redirect_uris=[redirect_uri],
            grant_types=['authorization_code', 'refresh_token'],
            response_types=['code'],
            scope=scope,
            token_endpoint_auth_method=token_endpoint_auth_method,
            issuer=oauth_server_metadata_url,
            server_metadata=oauth_server_metadata,
        )

        log.info(
            f'Static OAuth client info built for {oauth_client_id} using metadata from {oauth_server_metadata_url}'
        )
        return oauth_client_info
    except Exception as e:
        log.error(f'Exception building static OAuth client info: {e}')
        raise e


def resolve_oauth_client_info(connection: dict) -> dict:
    """
    Decrypt OAuth client info from a tool server connection config.

    For oauth_2.1_static, overlays admin-provided credentials from
    info.oauth_client_id and info.oauth_client_secret onto the blob.
    """
    info = connection.get('info', {})
    data = decrypt_data(info.get('oauth_client_info', ''))

    if connection.get('auth_type') == 'oauth_2.1_static':
        if info.get('oauth_client_id') and info.get('oauth_client_secret'):
            data['client_id'] = info['oauth_client_id']
            data['client_secret'] = info['oauth_client_secret']

    return data


class OAuthClientManager:
    def __init__(self, app):
        self.oauth = OAuth()
        self.app = app
        self.clients = {}

    def add_client(self, client_id, oauth_client_info: OAuthClientInformationFull):
        kwargs = {
            'name': client_id,
            'client_id': oauth_client_info.client_id,
            'client_secret': oauth_client_info.client_secret,
            'client_kwargs': {
                'follow_redirects': True,
                **({'scope': oauth_client_info.scope} if oauth_client_info.scope else {}),
                **(
                    {'token_endpoint_auth_method': oauth_client_info.token_endpoint_auth_method}
                    if oauth_client_info.token_endpoint_auth_method
                    else {}
                ),
            },
            'server_metadata_url': (oauth_client_info.issuer if oauth_client_info.issuer else None),
        }

        # Default to S256 for OAuth 2.1 (PKCE is mandatory per RFC 9700)
        kwargs['code_challenge_method'] = 'S256'

        # Only remove PKCE if metadata explicitly excludes S256
        if (
            oauth_client_info.server_metadata
            and oauth_client_info.server_metadata.code_challenge_methods_supported
            and isinstance(
                oauth_client_info.server_metadata.code_challenge_methods_supported,
                list,
            )
            and 'S256' not in oauth_client_info.server_metadata.code_challenge_methods_supported
        ):
            del kwargs['code_challenge_method']

        self.clients[client_id] = {
            'client': self.oauth.register(**kwargs),
            'client_info': oauth_client_info,
        }
        return self.clients[client_id]

    def ensure_client_from_config(self, client_id):
        """
        Lazy-load an OAuth client from the current TOOL_SERVER_CONNECTIONS
        config if it hasn't been registered on this node yet.
        """
        if client_id in self.clients:
            return self.clients[client_id]['client']

        try:
            connections = getattr(self.app.state.config, 'TOOL_SERVER_CONNECTIONS', [])
        except Exception:
            connections = []

        for connection in connections or []:
            if connection.get('type', 'openapi') != 'mcp':
                continue
            if connection.get('auth_type', 'none') not in ('oauth_2.1', 'oauth_2.1_static'):
                continue

            server_id = connection.get('info', {}).get('id')
            if not server_id:
                continue

            expected_client_id = f'mcp:{server_id}'
            if client_id != expected_client_id:
                continue

            oauth_client_info = connection.get('info', {}).get('oauth_client_info', '')
            if not oauth_client_info:
                continue

            try:
                oauth_client_info = resolve_oauth_client_info(connection)
                return self.add_client(expected_client_id, OAuthClientInformationFull(**oauth_client_info))['client']
            except Exception as e:
                log.error(f'Failed to lazily add OAuth client {expected_client_id} from config: {e}')
                continue

        return None

    def remove_client(self, client_id):
        if client_id in self.clients:
            del self.clients[client_id]
            log.info(f'Removed OAuth client {client_id}')

        if hasattr(self.oauth, '_clients'):
            if client_id in self.oauth._clients:
                self.oauth._clients.pop(client_id, None)

        if hasattr(self.oauth, '_registry'):
            if client_id in self.oauth._registry:
                self.oauth._registry.pop(client_id, None)

        return True

    async def _preflight_authorization_url(self, client, client_info: OAuthClientInformationFull) -> bool:
        # TODO: Replace this logic with a more robust OAuth client registration validation
        # Only perform preflight checks for Starlette OAuth clients
        if not hasattr(client, 'create_authorization_url'):
            return True

        redirect_uri = None
        if client_info.redirect_uris:
            redirect_uri = str(client_info.redirect_uris[0])

        try:
            auth_data = await client.create_authorization_url(redirect_uri=redirect_uri)
            authorization_url = auth_data.get('url')

            if not authorization_url:
                return True
        except Exception as e:
            log.debug(
                f'Skipping OAuth preflight for client {client_info.client_id}: {e}',
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
                    error_description = ''

                    content_type = resp.headers.get('content-type', '')
                    if 'application/json' in content_type:
                        try:
                            payload = json.loads(response_text)
                            error = payload.get('error')
                            error_description = payload.get('error_description', '')
                        except Exception:
                            pass
                    else:
                        error_description = response_text

                    error_message = f'{error or ""} {error_description or ""}'.lower()

                    if any(keyword in error_message for keyword in ('invalid_client', 'invalid client', 'client id')):
                        log.warning(
                            f'OAuth client preflight detected invalid registration for {client_info.client_id}: {error} {error_description}'
                        )

                        return False
        except Exception as e:
            log.debug(f'Skipping OAuth preflight network check for client {client_info.client_id}: {e}')

        return True

    def get_client(self, client_id):
        if client_id not in self.clients:
            self.ensure_client_from_config(client_id)

        client = self.clients.get(client_id)
        return client['client'] if client else None

    def get_client_info(self, client_id):
        if client_id not in self.clients:
            self.ensure_client_from_config(client_id)

        client = self.clients.get(client_id)
        return client['client_info'] if client else None

    def get_server_metadata_url(self, client_id):
        client = self.get_client(client_id)
        if not client:
            return None

        return client._server_metadata_url if hasattr(client, '_server_metadata_url') else None

    async def get_oauth_token(self, user_id: str, client_id: str, force_refresh: bool = False):
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
            session = await OAuthSessions.get_session_by_provider_and_user_id(client_id, user_id)
            if not session:
                log.warning(f'No OAuth session found for user {user_id}, client_id {client_id}')
                return None

            if (
                force_refresh
                or session.expires_at is None
                or datetime.now() + timedelta(minutes=5) >= datetime.fromtimestamp(session.expires_at)
            ):
                log.debug(f'Token refresh needed for user {user_id}, client_id {session.provider}')
                refreshed_token = await self._refresh_token(session)
                if refreshed_token:
                    return refreshed_token
                else:
                    log.warning(
                        f'Token refresh failed for user {user_id}, client_id {session.provider}, deleting session {session.id}'
                    )
                    await OAuthSessions.delete_session_by_id(session.id)
                    return None
            return session.token

        except Exception as e:
            log.error(f'Error getting OAuth token for user {user_id}: {e}')
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
                session = await OAuthSessions.update_session_by_id(session.id, refreshed_token)
                log.info(f'Successfully refreshed token for session {session.id}')
                return session.token
            else:
                log.error(f'Failed to refresh token for session {session.id}')
                return None

        except Exception as e:
            log.error(f'Error refreshing token for session {session.id}: {e}')
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

        if not token_data.get('refresh_token'):
            log.warning(f'No refresh token available for session {session.id}')
            return None

        try:
            client = self.get_client(client_id)
            if not client:
                log.error(f'No OAuth client found for provider {client_id}')
                return None

            token_endpoint = None
            async with aiohttp.ClientSession(trust_env=True) as session_http:
                async with session_http.get(self.get_server_metadata_url(client_id)) as r:
                    if r.status == 200:
                        openid_data = await r.json()
                        token_endpoint = openid_data.get('token_endpoint')
                    else:
                        log.error(f'Failed to fetch OpenID configuration for client_id {client_id}')
            if not token_endpoint:
                log.error(f'No token endpoint found for client_id {client_id}')
                return None

            # Prepare refresh request
            refresh_data = {
                'grant_type': 'refresh_token',
                'refresh_token': token_data['refresh_token'],
                'client_id': client.client_id,
            }
            if hasattr(client, 'client_secret') and client.client_secret:
                refresh_data['client_secret'] = client.client_secret

            # Add scope if available in client kwargs (some providers require it on refresh)
            if (
                hasattr(client, 'client_kwargs')
                and client.client_kwargs.get('scope')
                and getattr(self.app.state.config, 'OAUTH_REFRESH_TOKEN_INCLUDE_SCOPE', False)
            ):
                refresh_data['scope'] = client.client_kwargs['scope']

            # Make refresh request
            async with aiohttp.ClientSession(trust_env=True) as session_http:
                async with session_http.post(
                    token_endpoint,
                    data=refresh_data,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as r:
                    if r.status == 200:
                        new_token_data = await r.json()

                        # Merge with existing token data (preserve refresh_token if not provided)
                        if 'refresh_token' not in new_token_data:
                            new_token_data['refresh_token'] = token_data['refresh_token']

                        _normalize_token_expiry(new_token_data)

                        log.debug(f'Token refresh successful for client_id {client_id}')
                        return new_token_data
                    else:
                        error_text = await r.text()
                        log.error(f'Token refresh failed for client_id {client_id}: {r.status} - {error_text}')
                        return None

        except Exception as e:
            log.error(f'Exception during token refresh for client_id {client_id}: {e}')
            return None

    async def handle_authorize(self, request, client_id: str) -> RedirectResponse:
        client = self.get_client(client_id) or self.ensure_client_from_config(client_id)
        if client is None:
            raise HTTPException(404)
        client_info = self.get_client_info(client_id)
        if client_info is None:
            # ensure_client_from_config registers client_info too
            client_info = self.get_client_info(client_id)
        if client_info is None:
            raise HTTPException(404)

        redirect_uri = client_info.redirect_uris[0] if client_info.redirect_uris else None
        redirect_uri_str = str(redirect_uri) if redirect_uri else None
        return await client.authorize_redirect(request, redirect_uri_str)

    async def handle_callback(self, request, client_id: str, user_id: str, response):
        client = self.get_client(client_id) or self.ensure_client_from_config(client_id)
        if client is None:
            raise HTTPException(404)

        error_message = None
        try:
            client_info = self.get_client_info(client_id)

            # Note: Do NOT pass client_id/client_secret explicitly here.
            # The Authlib client already has these configured during add_client().
            # Passing them again causes Authlib to concatenate them (e.g., "ID1,ID1"),
            # which results in 401 errors from the token endpoint. (Fix for #19823)
            token = await client.authorize_access_token(request)

            # Validate that we received a proper token response
            # If token exchange failed (e.g., 401), we may get an error response instead
            if token and not token.get('access_token'):
                error_desc = token.get('error_description', token.get('error', 'Unknown error'))
                error_message = f'Token exchange failed: {error_desc}'
                log.error(f'Invalid token response for client_id {client_id}: {token}')
                token = None

            if token:
                try:
                    _normalize_token_expiry(token)

                    # Clean up any existing sessions for this user/client_id first
                    sessions = await OAuthSessions.get_sessions_by_user_id(user_id)
                    for session in sessions:
                        if session.provider == client_id:
                            await OAuthSessions.delete_session_by_id(session.id)

                    session = await OAuthSessions.create_session(
                        user_id=user_id,
                        provider=client_id,
                        token=token,
                    )
                    log.info(f'Stored OAuth session server-side for user {user_id}, client_id {client_id}')
                except Exception as e:
                    error_message = 'Failed to store OAuth session server-side'
                    log.error(f'Failed to store OAuth session server-side: {e}')
            else:
                if not error_message:
                    error_message = 'Failed to obtain OAuth token'
                log.warning(error_message)
        except Exception as e:
            error_message = _build_oauth_callback_error_message(e)
            log.warning(
                'OAuth callback error for user_id=%s client_id=%s: %s',
                user_id,
                client_id,
                error_message,
                exc_info=True,
            )

        redirect_url = (str(request.app.state.config.WEBUI_URL or request.base_url)).rstrip('/')

        if error_message:
            log.debug(error_message)
            redirect_url = f'{redirect_url}/?error={urllib.parse.quote_plus(error_message)}'
            return RedirectResponse(url=redirect_url, headers=response.headers)

        response = RedirectResponse(url=redirect_url, headers=response.headers)
        return response


class OAuthManager:
    def __init__(self, app):
        self.oauth = OAuth()
        self.app = app

        self._clients = {}

        for name, provider_config in OAUTH_PROVIDERS.items():
            if 'register' not in provider_config:
                log.error(f'OAuth provider {name} missing register function')
                continue

            client = provider_config['register'](self.oauth)
            self._clients[name] = client

    def get_client(self, provider_name):
        if provider_name not in self._clients:
            self._clients[provider_name] = self.oauth.create_client(provider_name)
        return self._clients[provider_name]

    def get_server_metadata_url(self, provider_name):
        if provider_name in self._clients:
            client = self._clients[provider_name]
            return client._server_metadata_url if hasattr(client, '_server_metadata_url') else None
        return None

    async def get_oauth_token(self, user_id: str, session_id: str, force_refresh: bool = False):
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
            session = await OAuthSessions.get_session_by_id_and_user_id(session_id, user_id)
            if not session:
                log.warning(f'No OAuth session found for user {user_id}, session {session_id}')
                return None

            if (
                force_refresh
                or session.expires_at is None
                or datetime.now() + timedelta(minutes=5) >= datetime.fromtimestamp(session.expires_at)
            ):
                log.debug(f'Token refresh needed for user {user_id}, provider {session.provider}')
                refreshed_token = await self._refresh_token(session)
                if refreshed_token:
                    return refreshed_token
                else:
                    log.warning(
                        f'Token refresh failed for user {user_id}, provider {session.provider}, deleting session {session.id}'
                    )
                    await OAuthSessions.delete_session_by_id(session.id)

                    return None
            return session.token

        except Exception as e:
            log.error(f'Error getting OAuth token for user {user_id}: {e}')
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
                session = await OAuthSessions.update_session_by_id(session.id, refreshed_token)
                log.info(f'Successfully refreshed token for session {session.id}')
                return session.token
            else:
                log.error(f'Failed to refresh token for session {session.id}')
                return None

        except Exception as e:
            log.error(f'Error refreshing token for session {session.id}: {e}')
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

        if not token_data.get('refresh_token'):
            log.warning(f'No refresh token available for session {session.id}')
            return None

        try:
            client = self.get_client(provider)
            if not client:
                log.error(f'No OAuth client found for provider {provider}')
                return None

            server_metadata_url = self.get_server_metadata_url(provider)
            token_endpoint = None
            async with aiohttp.ClientSession(trust_env=True) as session_http:
                async with session_http.get(server_metadata_url) as r:
                    if r.status == 200:
                        openid_data = await r.json()
                        token_endpoint = openid_data.get('token_endpoint')
                    else:
                        log.error(f'Failed to fetch OpenID configuration for provider {provider}')
            if not token_endpoint:
                log.error(f'No token endpoint found for provider {provider}')
                return None

            # Prepare refresh request
            refresh_data = {
                'grant_type': 'refresh_token',
                'refresh_token': token_data['refresh_token'],
                'client_id': client.client_id,
            }
            # Add client_secret if available (some providers require it)
            if hasattr(client, 'client_secret') and client.client_secret:
                refresh_data['client_secret'] = client.client_secret

            # Add scope if available in client kwargs (some providers require it on refresh)
            if (
                hasattr(client, 'client_kwargs')
                and client.client_kwargs.get('scope')
                and auth_manager_config.OAUTH_REFRESH_TOKEN_INCLUDE_SCOPE
            ):
                refresh_data['scope'] = client.client_kwargs['scope']

            # Make refresh request
            async with aiohttp.ClientSession(trust_env=True) as session_http:
                async with session_http.post(
                    token_endpoint,
                    data=refresh_data,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as r:
                    if r.status == 200:
                        new_token_data = await r.json()

                        # Merge with existing token data (preserve refresh_token if not provided)
                        if 'refresh_token' not in new_token_data:
                            new_token_data['refresh_token'] = token_data['refresh_token']

                        _normalize_token_expiry(new_token_data)

                        log.debug(f'Token refresh successful for provider {provider}')
                        return new_token_data
                    else:
                        error_text = await r.text()
                        log.error(f'Token refresh failed for provider {provider}: {r.status} - {error_text}')
                        return None

        except Exception as e:
            log.error(f'Exception during token refresh for provider {provider}: {e}')
            return None

    async def get_user_role(self, user, user_data):
        user_count = await Users.get_num_users()
        if user and user_count == 1:
            # If the user is the only user, assign the role "admin" - actually repairs role for single user on login
            log.debug('Assigning the only user the admin role')
            return 'admin'
        if not user and user_count == 0:
            # First-user bootstrap: skip role management gating so the
            # instance can be initialized.  We intentionally return the
            # default role here (not 'admin') — admin promotion happens
            # race-safely *after* insert via get_num_users() == 1.
            log.debug('First user bootstrap: using default role (admin promotion deferred to post-insert)')
            return auth_manager_config.DEFAULT_USER_ROLE

        if auth_manager_config.ENABLE_OAUTH_ROLE_MANAGEMENT:
            log.debug('Running OAUTH Role management')
            oauth_claim = auth_manager_config.OAUTH_ROLES_CLAIM
            oauth_allowed_roles = auth_manager_config.OAUTH_ALLOWED_ROLES
            oauth_admin_roles = auth_manager_config.OAUTH_ADMIN_ROLES
            oauth_roles = []
            # Default/fallback role if no matching roles are found
            role = auth_manager_config.DEFAULT_USER_ROLE

            # Next block extracts the roles from the user data, accepting nested claims of any depth
            if oauth_claim and oauth_allowed_roles and oauth_admin_roles:
                claim_data = user_data
                nested_claims = oauth_claim.split('.')
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

            log.debug(f'Oauth Roles claim: {oauth_claim}')
            log.debug(f'User roles from oauth: {oauth_roles}')
            log.debug(f'Accepted user roles: {oauth_allowed_roles}')
            log.debug(f'Accepted admin roles: {oauth_admin_roles}')

            # If roles are present in the token, they must match; otherwise deny access
            if oauth_roles:
                matched = False
                for allowed_role in oauth_allowed_roles:
                    if allowed_role in oauth_roles:
                        log.debug('Assigned user the user role')
                        role = 'user'
                        matched = True
                        break
                for admin_role in oauth_admin_roles:
                    if admin_role in oauth_roles:
                        log.debug('Assigned user the admin role')
                        role = 'admin'
                        matched = True
                        break
                if not matched:
                    log.warning(
                        f'OAuth role management enabled but user roles do not match any allowed/admin roles. '
                        f'User roles: {oauth_roles}, allowed: {oauth_allowed_roles}, admin: {oauth_admin_roles}'
                    )
                    raise HTTPException(
                        status.HTTP_403_FORBIDDEN,
                        detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
                    )
        else:
            if not user:
                # If role management is disabled, use the default role for new users
                role = auth_manager_config.DEFAULT_USER_ROLE
            else:
                # If role management is disabled, use the existing role for existing users
                role = user.role

        return role

    async def update_user_groups(self, user, user_data, default_permissions, db=None):
        log.debug('Running OAUTH Group management')
        oauth_claim = auth_manager_config.OAUTH_GROUPS_CLAIM

        try:
            blocked_groups = json.loads(auth_manager_config.OAUTH_BLOCKED_GROUPS)
        except Exception as e:
            log.exception(f'Error loading OAUTH_BLOCKED_GROUPS: {e}')
            blocked_groups = []

        user_oauth_groups = []
        # Nested claim search for groups claim
        if oauth_claim:
            claim_data = user_data
            nested_claims = oauth_claim.split('.')
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

        user_current_groups: list[GroupModel] = await Groups.get_groups_by_member_id(user.id, db=db)
        all_available_groups: list[GroupModel] = await Groups.get_all_groups(db=db)

        # Create groups if they don't exist and creation is enabled
        if auth_manager_config.ENABLE_OAUTH_GROUP_CREATION:
            log.debug('Checking for missing groups to create...')
            all_group_names = {g.name for g in all_available_groups}
            groups_created = False
            # Determine creator ID: Prefer admin, fallback to current user if no admin exists
            admin_user = await Users.get_super_admin_user()
            creator_id = admin_user.id if admin_user else user.id
            log.debug(f'Using creator ID {creator_id} for potential group creation.')

            for group_name in user_oauth_groups:
                if group_name not in all_group_names:
                    log.info(f"Group '{group_name}' not found via OAuth claim. Creating group...")
                    try:
                        new_group_form = GroupForm(
                            name=group_name,
                            description=f"Group '{group_name}' created automatically via OAuth.",
                            permissions=default_permissions,  # Use default permissions from function args
                            data={'config': {'share': auth_manager_config.OAUTH_GROUP_DEFAULT_SHARE}},
                        )
                        # Use determined creator ID (admin or fallback to current user)
                        created_group = await Groups.insert_new_group(creator_id, new_group_form, db=db)
                        if created_group:
                            log.info(
                                f"Successfully created group '{group_name}' with ID {created_group.id} using creator ID {creator_id}"
                            )
                            groups_created = True
                            # Add to local set to prevent duplicate creation attempts in this run
                            all_group_names.add(group_name)
                        else:
                            log.error(f"Failed to create group '{group_name}' via OAuth.")
                    except Exception as e:
                        log.error(f"Error creating group '{group_name}' via OAuth: {e}")

            # Refresh the list of all available groups if any were created
            if groups_created:
                all_available_groups = await Groups.get_all_groups(db=db)
                log.debug('Refreshed list of all available groups after creation.')

        log.debug(f'Oauth Groups claim: {oauth_claim}')
        log.debug(f'User oauth groups: {user_oauth_groups}')
        log.debug(f"User's current groups: {[g.name for g in user_current_groups]}")
        log.debug(f'All groups available in OpenWebUI: {[g.name for g in all_available_groups]}')

        # Remove groups that user is no longer a part of
        for group_model in user_current_groups:
            if (
                user_oauth_groups
                and group_model.name not in user_oauth_groups
                and not is_in_blocked_groups(group_model.name, blocked_groups)
            ):
                # Remove group from user
                log.debug(f'Removing user from group {group_model.name} as it is no longer in their oauth groups')
                await Groups.remove_users_from_group(group_model.id, [user.id], db=db)

                # In case a group is created, but perms are never assigned to the group by hitting "save"
                group_permissions = group_model.permissions
                if not group_permissions:
                    group_permissions = default_permissions

                await Groups.update_group_by_id(
                    id=group_model.id,
                    form_data=GroupUpdateForm(
                        name=group_model.name,
                        description=group_model.description,
                        permissions=group_permissions,
                    ),
                    overwrite=False,
                    db=db,
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
                log.debug(f'Adding user to group {group_model.name} as it was found in their oauth groups')

                await Groups.add_users_to_group(group_model.id, [user.id], db=db)

                # In case a group is created, but perms are never assigned to the group by hitting "save"
                group_permissions = group_model.permissions
                if not group_permissions:
                    group_permissions = default_permissions

                await Groups.update_group_by_id(
                    id=group_model.id,
                    form_data=GroupUpdateForm(
                        name=group_model.name,
                        description=group_model.description,
                        permissions=group_permissions,
                    ),
                    overwrite=False,
                    db=db,
                )

    async def _process_picture_url(self, picture_url: str, access_token: str = None) -> str:
        """Process a picture URL and return a base64 encoded data URL.

        Args:
            picture_url: The URL of the picture to process
            access_token: Optional OAuth access token for authenticated requests

        Returns:
            A data URL containing the base64 encoded picture, or "/user.png" if processing fails
        """
        if not picture_url:
            return '/user.png'

        try:
            validate_url(picture_url)

            get_kwargs = {}
            if access_token:
                get_kwargs['headers'] = {
                    'Authorization': f'Bearer {access_token}',
                }
            async with aiohttp.ClientSession(trust_env=True) as session:
                async with session.get(picture_url, **get_kwargs, ssl=AIOHTTP_CLIENT_SESSION_SSL) as resp:
                    if resp.ok:
                        picture = await resp.read()
                        base64_encoded_picture = base64.b64encode(picture).decode('utf-8')
                        guessed_mime_type = mimetypes.guess_type(picture_url)[0]
                        if guessed_mime_type is None:
                            guessed_mime_type = 'image/jpeg'
                        return f'data:{guessed_mime_type};base64,{base64_encoded_picture}'
                    else:
                        log.warning(f'Failed to fetch profile picture from {picture_url}')
                        return '/user.png'
        except Exception as e:
            log.error(f"Error processing profile picture '{picture_url}': {e}")
            return '/user.png'

    async def handle_login(self, request, provider):
        if provider not in OAUTH_PROVIDERS:
            raise HTTPException(404)
        # If the provider has a custom redirect URL, use that, otherwise automatically generate one
        client = self.get_client(provider)
        if client is None:
            raise HTTPException(404)
        redirect_uri = (client.server_metadata or {}).get('redirect_uri') or request.url_for(
            'oauth_login_callback', provider=provider
        )

        kwargs = {}
        if auth_manager_config.OAUTH_AUDIENCE:
            kwargs['audience'] = auth_manager_config.OAUTH_AUDIENCE
        if OAUTH_AUTHORIZE_PARAMS:
            kwargs.update(OAUTH_AUTHORIZE_PARAMS)

        return await client.authorize_redirect(request, redirect_uri, **kwargs)

    async def handle_callback(self, request, provider, response, db=None):
        if provider not in OAUTH_PROVIDERS:
            raise HTTPException(404)

        error_message = None
        try:
            client = self.get_client(provider)

            auth_params = {}

            if client:
                if hasattr(client, 'client_id') and OAUTH_ACCESS_TOKEN_REQUEST_INCLUDE_CLIENT_ID:
                    auth_params['client_id'] = client.client_id

            try:
                token = await client.authorize_access_token(request, **auth_params)
            except BadSignatureError:
                # The IdP likely rotated its signing keys and the cached JWKS
                # is stale.  Evict the cached key set so the next attempt
                # fetches fresh keys from the jwks_uri.
                log.warning(
                    'OIDC bad_signature for provider %s — evicting cached JWKS and retrying',
                    provider,
                )
                if hasattr(client, 'server_metadata') and isinstance(client.server_metadata, dict):
                    client.server_metadata.pop('jwks', None)
                try:
                    token = await client.authorize_access_token(request, **auth_params)
                except Exception as retry_exc:
                    detailed_error = _build_oauth_callback_error_message(retry_exc)
                    log.warning(
                        'OAuth callback error during authorize_access_token retry for provider %s: %s',
                        provider,
                        detailed_error,
                        exc_info=True,
                    )
                    raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)
            except Exception as e:
                detailed_error = _build_oauth_callback_error_message(e)
                log.warning(
                    'OAuth callback error during authorize_access_token for provider %s: %s',
                    provider,
                    detailed_error,
                    exc_info=True,
                )
                raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)

            # Try to get userinfo from the token first, some providers include it there
            user_data: UserInfo = token.get('userinfo')
            # Preserve extra claims from the ID token (e.g. roles, groups for
            # Microsoft Entra ID) before the userinfo endpoint possibly overwrites them.
            id_token_claims = dict(user_data) if user_data else {}
            if (
                (not user_data)
                or (auth_manager_config.OAUTH_EMAIL_CLAIM not in user_data)
                or (auth_manager_config.OAUTH_USERNAME_CLAIM not in user_data)
            ):
                user_data: UserInfo = await client.userinfo(token=token)
                # Merge back ID token claims that the userinfo endpoint doesn't
                # return.  Only backfill missing keys so userinfo always wins.
                if user_data and id_token_claims:
                    for key, value in id_token_claims.items():
                        if key not in user_data:
                            user_data[key] = value
            if provider == 'feishu' and isinstance(user_data, dict) and 'data' in user_data:
                user_data = user_data['data']
            if not user_data:
                log.warning(f'OAuth callback failed, user data is missing: {token}')
                raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)

            # Extract the "sub" claim, using custom claim if configured
            if auth_manager_config.OAUTH_SUB_CLAIM:
                sub = user_data.get(auth_manager_config.OAUTH_SUB_CLAIM)
            else:
                # Fallback to the default sub claim if not configured
                sub = user_data.get(OAUTH_PROVIDERS[provider].get('sub_claim', 'sub'))
            if not sub:
                log.warning(f'OAuth callback failed, sub is missing: {user_data}')
                raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)

            oauth_data = {}
            oauth_data[provider] = {
                'sub': sub,
            }

            # Email extraction
            email_claim = auth_manager_config.OAUTH_EMAIL_CLAIM
            email = user_data.get(email_claim, '')
            # We currently mandate that email addresses are provided
            if not email:
                # If the provider is GitHub,and public email is not provided, we can use the access token to fetch the user's email
                if provider == 'github':
                    try:
                        access_token = token.get('access_token')
                        headers = {'Authorization': f'Bearer {access_token}'}
                        async with aiohttp.ClientSession(trust_env=True) as session:
                            async with session.get(
                                'https://api.github.com/user/emails',
                                headers=headers,
                                ssl=AIOHTTP_CLIENT_SESSION_SSL,
                            ) as resp:
                                if resp.ok:
                                    emails = await resp.json()
                                    # use the primary email as the user's email
                                    primary_email = next(
                                        (e['email'] for e in emails if e.get('primary')),
                                        None,
                                    )
                                    if primary_email:
                                        email = primary_email
                                    else:
                                        log.warning('No primary email found in GitHub response')
                                        raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)
                                else:
                                    log.warning('Failed to fetch GitHub email')
                                    raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)
                    except Exception as e:
                        log.warning(f'Error fetching GitHub email: {e}')
                        raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)
                elif ENABLE_OAUTH_EMAIL_FALLBACK:
                    email = f'{provider}@{sub}.local'
                else:
                    log.warning(f'OAuth callback failed, email is missing: {user_data}')
                    raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)

            email = email.lower()
            # If allowed domains are configured, check if the email domain is in the list
            if (
                '*' not in auth_manager_config.OAUTH_ALLOWED_DOMAINS
                and email.split('@')[-1] not in auth_manager_config.OAUTH_ALLOWED_DOMAINS
            ):
                log.warning(f'OAuth callback failed, e-mail domain is not in the list of allowed domains: {user_data}')
                raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)

            # Check if the user exists
            user = await Users.get_user_by_oauth_sub(provider, sub, db=db)
            if not user:
                # If the user does not exist, check if merging is enabled
                if auth_manager_config.OAUTH_MERGE_ACCOUNTS_BY_EMAIL:
                    # Check if the user exists by email
                    user = await Users.get_user_by_email(email, db=db)
                    if user:
                        # Update the user with the new oauth sub
                        await Users.update_user_oauth_by_id(user.id, provider, sub, db=db)

            if user:
                determined_role = await self.get_user_role(user, user_data)
                if user.role != determined_role:
                    await Users.update_user_role_by_id(user.id, determined_role, db=db)
                    # Update the user object in memory as well,
                    # to avoid problems with the ENABLE_OAUTH_GROUP_MANAGEMENT check below
                    user.role = determined_role

                if auth_manager_config.OAUTH_UPDATE_NAME_ON_LOGIN:
                    username_claim = auth_manager_config.OAUTH_USERNAME_CLAIM
                    if username_claim:
                        new_name = user_data.get(username_claim)
                        if new_name and new_name != user.name:
                            await Users.update_user_by_id(user.id, {'name': new_name}, db=db)
                            user.name = new_name
                            log.debug(f'Updated name for user {user.email}')

                if auth_manager_config.OAUTH_UPDATE_EMAIL_ON_LOGIN:
                    email_claim = auth_manager_config.OAUTH_EMAIL_CLAIM
                    if email_claim:
                        new_email = user_data.get(email_claim)
                        if new_email and new_email.lower() != user.email.lower():
                            existing_user = await Users.get_user_by_email(new_email, db=db)
                            if existing_user:
                                log.error(
                                    f'Cannot update email to {new_email} for user {user.id} because it is already taken.'
                                )
                            else:
                                await Auths.update_email_by_id(user.id, new_email.lower(), db=db)
                                user.email = new_email.lower()
                                log.debug(f'Updated email for user {user.id}')

                # Update profile picture if enabled and different from current
                if auth_manager_config.OAUTH_UPDATE_PICTURE_ON_LOGIN:
                    picture_claim = auth_manager_config.OAUTH_PICTURE_CLAIM
                    if picture_claim:
                        new_picture_url = user_data.get(
                            picture_claim,
                            OAUTH_PROVIDERS[provider].get('picture_url', ''),
                        )
                        processed_picture_url = await self._process_picture_url(
                            new_picture_url, token.get('access_token')
                        )
                        if processed_picture_url != user.profile_image_url:
                            await Users.update_user_profile_image_url_by_id(user.id, processed_picture_url, db=db)
                            log.debug(f'Updated profile picture for user {user.email}')
            else:
                # If the user does not exist, check if signups are enabled
                if auth_manager_config.ENABLE_OAUTH_SIGNUP:
                    # Check if an existing user with the same email already exists
                    existing_user = await Users.get_user_by_email(email, db=db)
                    if existing_user:
                        raise HTTPException(400, detail=ERROR_MESSAGES.EMAIL_TAKEN)

                    picture_claim = auth_manager_config.OAUTH_PICTURE_CLAIM
                    if picture_claim:
                        picture_url = user_data.get(
                            picture_claim,
                            OAUTH_PROVIDERS[provider].get('picture_url', ''),
                        )
                        picture_url = await self._process_picture_url(picture_url, token.get('access_token'))
                    else:
                        picture_url = '/user.png'
                    username_claim = auth_manager_config.OAUTH_USERNAME_CLAIM

                    name = user_data.get(username_claim)
                    if not name:
                        log.warning('Username claim is missing, using email as name')
                        name = email

                    user = await Auths.insert_new_auth(
                        email=email,
                        password=get_password_hash(str(uuid.uuid4())),  # Random password, not used
                        name=name,
                        profile_image_url=picture_url,
                        role=await self.get_user_role(None, user_data),
                        oauth=oauth_data,
                        db=db,
                    )

                    if not user:
                        raise HTTPException(500, detail=ERROR_MESSAGES.CREATE_USER_ERROR)

                    # Atomically check if this is the only user *after* the
                    # insert to avoid TOCTOU race on first-user registration.
                    # Matches signup_handler pattern.
                    if await Users.get_num_users(db=db) == 1:
                        await Users.update_user_role_by_id(user.id, 'admin', db=db)
                        user = await Users.get_user_by_id(user.id, db=db)

                    if auth_manager_config.WEBHOOK_URL:
                        await post_webhook(
                            WEBUI_NAME,
                            auth_manager_config.WEBHOOK_URL,
                            WEBHOOK_MESSAGES.USER_SIGNUP(user.name),
                            {
                                'action': 'signup',
                                'message': WEBHOOK_MESSAGES.USER_SIGNUP(user.name),
                                'user': user.model_dump_json(exclude_none=True),
                            },
                        )

                    await apply_default_group_assignment(request.app.state.config.DEFAULT_GROUP_ID, user.id, db=db)

                else:
                    raise HTTPException(
                        status.HTTP_403_FORBIDDEN,
                        detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
                    )

            jwt_token = create_token(
                data={'id': user.id},
                expires_delta=parse_duration(auth_manager_config.JWT_EXPIRES_IN),
            )
            if auth_manager_config.ENABLE_OAUTH_GROUP_MANAGEMENT:
                await self.update_user_groups(
                    user=user,
                    user_data=user_data,
                    default_permissions=request.app.state.config.USER_PERMISSIONS,
                    db=db,
                )

        except Exception as e:
            log.error(f'Error during OAuth process: {e}')
            error_message = (
                e.detail
                if isinstance(e, HTTPException) and e.detail
                else ERROR_MESSAGES.DEFAULT('Error during OAuth process')
            )

        redirect_base_url = (str(request.app.state.config.WEBUI_URL or request.base_url)).rstrip('/')
        redirect_url = f'{redirect_base_url}/auth'

        if error_message:
            redirect_url = f'{redirect_url}?error={urllib.parse.quote_plus(error_message)}'
            return RedirectResponse(url=redirect_url, headers=response.headers)

        response = RedirectResponse(url=redirect_url, headers=response.headers)

        # Compute cookie expiry from JWT lifetime
        expires_delta = parse_duration(auth_manager_config.JWT_EXPIRES_IN)
        cookie_max_age = int(expires_delta.total_seconds()) if expires_delta else None

        # Set the cookie token
        # Redirect back to the frontend with the JWT token
        response.set_cookie(
            key='token',
            value=jwt_token,
            httponly=False,  # Required for frontend access
            samesite=WEBUI_AUTH_COOKIE_SAME_SITE,
            secure=WEBUI_AUTH_COOKIE_SECURE,
            **({'max_age': cookie_max_age} if cookie_max_age is not None else {}),
        )

        # Legacy cookies for compatibility with older frontend versions
        if ENABLE_OAUTH_ID_TOKEN_COOKIE:
            response.set_cookie(
                key='oauth_id_token',
                value=token.get('id_token'),
                httponly=True,
                samesite=WEBUI_AUTH_COOKIE_SAME_SITE,
                secure=WEBUI_AUTH_COOKIE_SECURE,
                **({'max_age': cookie_max_age} if cookie_max_age is not None else {}),
            )

        try:
            _normalize_token_expiry(token)

            # Enforce max concurrent sessions per user/provider to prevent
            # unbounded growth while allowing multi-device usage
            sessions = await OAuthSessions.get_sessions_by_user_id(user.id, db=db)
            provider_sessions = sorted(
                [session for session in sessions if session.provider == provider],
                key=lambda session: session.created_at,
                reverse=True,
            )
            # Keep the newest sessions up to the limit, prune the rest
            if len(provider_sessions) >= OAUTH_MAX_SESSIONS_PER_USER:
                for old_session in provider_sessions[OAUTH_MAX_SESSIONS_PER_USER - 1 :]:
                    await OAuthSessions.delete_session_by_id(old_session.id, db=db)

            session = await OAuthSessions.create_session(
                user_id=user.id,
                provider=provider,
                token=token,
                db=db,
            )

            if session:
                response.set_cookie(
                    key='oauth_session_id',
                    value=session.id,
                    httponly=True,
                    samesite=WEBUI_AUTH_COOKIE_SAME_SITE,
                    secure=WEBUI_AUTH_COOKIE_SECURE,
                    **({'max_age': cookie_max_age} if cookie_max_age is not None else {}),
                )

                log.info(f'Stored OAuth session server-side for user {user.id}, provider {provider}')
            else:
                log.warning(f'Failed to create OAuth session for user {user.id}, provider {provider}')
        except Exception as e:
            log.error(f'Failed to store OAuth session server-side: {e}')

        return response

    async def handle_backchannel_logout(self, request, db=None):
        """
        Handle an OIDC Back-Channel Logout request.
        Validates the logout_token, identifies the user, revokes their
        sessions via Redis, and deletes their OAuth sessions.
        Returns a JSONResponse per the OIDC Back-Channel Logout 1.0 spec.
        """
        import jwt as pyjwt
        from fastapi.responses import JSONResponse

        # 1. Extract logout_token from form body
        try:
            form = await request.form()
            logout_token = form.get('logout_token')
        except Exception:
            logout_token = None

        if not logout_token:
            return JSONResponse(
                status_code=400,
                content={'error': 'invalid_request', 'error_description': 'Missing logout_token parameter'},
            )

        # 2. Peek at unverified issuer to match against configured providers
        try:
            unverified_claims = pyjwt.decode(logout_token, options={'verify_signature': False})
            token_issuer = unverified_claims.get('iss')
        except Exception as e:
            log.warning(f'Back-channel logout: cannot decode logout_token: {e}')
            return JSONResponse(
                status_code=400,
                content={'error': 'invalid_request', 'error_description': 'Malformed logout_token'},
            )

        if not token_issuer:
            return JSONResponse(
                status_code=400,
                content={'error': 'invalid_request', 'error_description': 'logout_token missing iss claim'},
            )

        # 3. Find the configured provider whose issuer matches the token
        matched_provider = None
        matched_client_id = None
        matched_jwks_uri = None
        matched_issuer = None

        for provider_name in OAUTH_PROVIDERS:
            server_metadata_url = self.get_server_metadata_url(provider_name)
            if not server_metadata_url:
                continue

            try:
                async with aiohttp.ClientSession(trust_env=True) as session:
                    async with session.get(server_metadata_url, ssl=AIOHTTP_CLIENT_SESSION_SSL) as r:
                        if r.status != 200:
                            continue
                        oidc_config = await r.json()

                provider_issuer = oidc_config.get('issuer')
                if provider_issuer and provider_issuer == token_issuer:
                    client = self.get_client(provider_name)
                    matched_provider = provider_name
                    matched_client_id = client.client_id if client else None
                    matched_jwks_uri = oidc_config.get('jwks_uri')
                    matched_issuer = provider_issuer
                    break
            except Exception as e:
                log.debug(f'Back-channel logout: error checking provider {provider_name}: {e}')
                continue

        if not matched_provider or not matched_client_id or not matched_jwks_uri:
            log.warning(f'Back-channel logout: no configured provider matches issuer {token_issuer}')
            return JSONResponse(
                status_code=400,
                content={
                    'error': 'invalid_request',
                    'error_description': 'No configured provider matches token issuer',
                },
            )

        # 4. Validate the logout_token signature and claims
        try:
            jwks_client = pyjwt.PyJWKClient(matched_jwks_uri)
            signing_key = jwks_client.get_signing_key_from_jwt(logout_token)

            claims = pyjwt.decode(
                logout_token,
                signing_key.key,
                algorithms=['RS256', 'RS384', 'RS512', 'ES256', 'ES384', 'ES512'],
                audience=matched_client_id,
                issuer=matched_issuer,
                options={
                    'require': ['iss', 'aud', 'iat', 'events'],
                },
            )
        except pyjwt.InvalidTokenError as e:
            log.warning(f'Back-channel logout: invalid logout_token: {e}')
            return JSONResponse(
                status_code=400,
                content={'error': 'invalid_request', 'error_description': f'Invalid logout_token: {e}'},
            )
        except Exception as e:
            log.error(f'Back-channel logout: error validating logout_token: {e}')
            return JSONResponse(
                status_code=400,
                content={'error': 'invalid_request', 'error_description': 'Failed to validate logout_token'},
            )

        # 5. Validate events claim per spec
        events = claims.get('events', {})
        if 'http://schemas.openid.net/event/backchannel-logout' not in events:
            log.warning('Back-channel logout: missing required backchannel-logout event claim')
            return JSONResponse(
                status_code=400,
                content={'error': 'invalid_request', 'error_description': 'Missing backchannel-logout event claim'},
            )

        # 6. Per spec, back-channel logout tokens MUST NOT contain a nonce
        if 'nonce' in claims:
            log.warning('Back-channel logout: logout_token contains nonce (rejected per spec)')
            return JSONResponse(
                status_code=400,
                content={'error': 'invalid_request', 'error_description': 'logout_token must not contain nonce'},
            )

        # 7. Extract sub and/or sid — at least one must be present
        sub = claims.get('sub')
        sid = claims.get('sid')

        if not sub and not sid:
            log.warning('Back-channel logout: logout_token contains neither sub nor sid')
            return JSONResponse(
                status_code=400,
                content={'error': 'invalid_request', 'error_description': 'logout_token must contain sub or sid'},
            )

        # 8. Identify users to log out
        users_to_logout = []
        if sub:
            user = await Users.get_user_by_oauth_sub(matched_provider, sub, db=db)
            if user:
                users_to_logout.append(user)

        if not users_to_logout and sid:
            log.debug(f'Back-channel logout: no user found by sub, sid-based lookup not yet supported (sid={sid})')

        if not users_to_logout:
            log.debug(f'Back-channel logout: no matching user for provider={matched_provider}, sub={sub}, sid={sid}')
            return JSONResponse(status_code=200, content={})

        # 9. Revoke tokens and delete sessions
        redis = request.app.state.redis
        if not redis:
            log.warning(
                'Back-channel logout: Redis not configured, cannot revoke JWT tokens. '
                'OAuth sessions will be deleted but existing JWTs will remain valid until expiry.'
            )

        revoked_count = 0
        for user in users_to_logout:
            sessions = await OAuthSessions.get_sessions_by_user_id(user.id, db=db)
            for oauth_session in sessions:
                await OAuthSessions.delete_session_by_id(oauth_session.id, db=db)

            if redis:
                revocation_key = f'{REDIS_KEY_PREFIX}:auth:user:{user.id}:revoked_at'
                await redis.set(
                    revocation_key,
                    str(int(time.time())),
                    ex=60 * 60 * 24 * 30,
                )
                revoked_count += 1

            log.info(
                f'Back-channel logout: revoked sessions for user {user.id} '
                f'(email={user.email}, provider={matched_provider}, sessions_deleted={len(sessions)})'
            )

        log.info(
            f'Back-channel logout: completed for {len(users_to_logout)} user(s), {revoked_count} revocation(s) set'
        )
        return JSONResponse(status_code=200, content={})
