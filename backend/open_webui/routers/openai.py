from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import re
import time
from typing import Optional
from urllib.parse import quote, urlencode, urlparse

import aiohttp
from aiocache import cached
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import (
    FileResponse,
    JSONResponse,
    PlainTextResponse,
    StreamingResponse,
)
from open_webui.config import (
    CACHE_DIR,
)
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import (
    AIOHTTP_CLIENT_SESSION_SSL,
    AIOHTTP_CLIENT_TIMEOUT,
    AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST,
    BYPASS_MODEL_ACCESS_CONTROL,
    ENABLE_FORWARD_USER_INFO_HEADERS,
    ENABLE_OPENAI_API_PASSTHROUGH,
    FORWARD_SESSION_INFO_HEADER_CHAT_ID,
    MODELS_CACHE_TTL,
)
from open_webui.internal.db import get_async_session
from open_webui.models.access_grants import AccessGrants
from open_webui.models.groups import Groups
from open_webui.models.models import Models
from open_webui.models.oauth_sessions import OAuthSessions
from open_webui.models.users import UserModel
from open_webui.utils.access_control import check_model_access, has_connection_access
from open_webui.utils.anthropic import get_anthropic_models, is_anthropic_url
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.headers import get_custom_headers, include_user_info_headers
from open_webui.utils.misc import (
    convert_logit_bias_input_to_json,
    stream_chunks_handler,
)
from open_webui.utils.payload import (
    apply_model_params_to_body_openai,
    apply_system_prompt_to_body,
)
from open_webui.utils.session_pool import (
    cleanup_response,
    get_session,
    stream_wrapper,
)
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


##########################################
#
# Utility functions
# Let the responses returned through this gate be worth
# the question that summoned them.
#
##########################################

# Headers that become stale after aiohttp auto-decompresses the upstream
# response body.  Forwarding them verbatim causes desktop / programmatic
# clients to attempt decompression of an already-decoded payload, resulting
# in ZlibError.  See https://github.com/aio-libs/aiohttp/issues/4462.
_STRIP_PROXY_HEADERS = frozenset({'Content-Encoding', 'Content-Length', 'Transfer-Encoding'})


def _clean_proxy_headers(raw_headers) -> dict:
    """Return a copy of *raw_headers* with stale encoding headers removed."""
    return {k: v for k, v in raw_headers.items() if k not in _STRIP_PROXY_HEADERS}


async def send_get_request(
    request: Request = None,
    url=None,
    key=None,
    user: UserModel = None,
    config=None,
):
    timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST)
    try:
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            if request and config:
                headers, cookies = await get_headers_and_cookies(request, url, key, config, user=user)
            else:
                headers = {
                    **({'Authorization': f'Bearer {key}'} if key else {}),
                }
                cookies = None

                if ENABLE_FORWARD_USER_INFO_HEADERS and user:
                    headers = include_user_info_headers(headers, user)

            async with session.get(
                url,
                headers=headers,
                cookies=cookies,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as response:
                return await response.json()
    except Exception as e:
        # Handle connection error here
        if is_openai_codex_web_auth_config(config):
            log.warning(
                'OpenAI web auth model request failed for host=%s error=%s',
                urlparse(url).hostname if url else None,
                e,
            )
        log.error(f'Connection error: {e}')
        return None


async def get_models_request(
    request: Request = None,
    url=None,
    key=None,
    user: UserModel = None,
    config=None,
):
    if is_anthropic_url(url):
        return await get_anthropic_models(url, key, user=user)
    try:
        return await send_get_request(request, f'{url}/models', key, user=user, config=config)
    except HTTPException as e:
        if is_openai_codex_web_auth_config(config):
            log.warning(
                'OpenAI web auth model request failed for host=%s status=%s detail=%s',
                urlparse(url).hostname,
                e.status_code,
                e.detail,
            )
        raise


def is_empty_native_openai_bearer_connection(
    url: str,
    key: str = '',
    config: Optional[dict] = None,
) -> bool:
    config = config or {}
    auth_type = config.get('auth_type')
    return (
        urlparse(url).hostname == 'api.openai.com'
        and not key
        and (auth_type == 'bearer' or auth_type is None)
    )


def openai_reasoning_model_handler(payload):
    """
    Handle reasoning model specific parameters
    """
    if 'max_tokens' in payload:
        # Convert "max_tokens" to "max_completion_tokens" for all reasoning models
        payload['max_completion_tokens'] = payload['max_tokens']
        del payload['max_tokens']

    # Handle system role conversion based on model type
    if payload['messages'][0]['role'] == 'system':
        model_lower = payload['model'].lower()
        # Legacy models use "user" role instead of "system"
        if model_lower.startswith('o1-mini') or model_lower.startswith('o1-preview'):
            payload['messages'][0]['role'] = 'user'
        else:
            payload['messages'][0]['role'] = 'developer'

    return payload


async def get_headers_and_cookies(
    request: Request,
    url,
    key=None,
    config=None,
    metadata: dict | None = None,
    user: UserModel = None,
):
    cookies = {}
    headers = {
        'Content-Type': 'application/json',
        **(
            {
                'HTTP-Referer': 'https://openwebui.com/',
                'X-Title': 'Open WebUI',
            }
            if 'openrouter.ai' in url
            else {}
        ),
    }

    if ENABLE_FORWARD_USER_INFO_HEADERS and user:
        headers = include_user_info_headers(headers, user)
        if metadata and metadata.get('chat_id'):
            headers[FORWARD_SESSION_INFO_HEADER_CHAT_ID] = metadata.get('chat_id')

    token = None
    auth_type = config.get('auth_type')

    if auth_type == 'bearer' or auth_type is None:
        # Default to bearer if not specified
        token = f'{key}'
    elif auth_type == 'none':
        token = None
    elif auth_type == 'session':
        cookies = request.cookies
        token = request.state.token.credentials
    elif auth_type == 'system_oauth':
        cookies = request.cookies

        oauth_token = None
        try:
            if request.cookies.get('oauth_session_id', None):
                oauth_token = await request.app.state.oauth_manager.get_oauth_token(
                    user.id,
                    request.cookies.get('oauth_session_id', None),
                )
        except Exception as e:
            log.error(f'Error getting OAuth token: {e}')

        if oauth_token:
            token = f'{oauth_token.get("access_token", "")}'

    elif is_openai_codex_web_auth_config(config):
        token = await get_openai_web_auth_access_token()
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='OpenAI web auth credential is not connected or requires reconnection',
            )

    elif auth_type in ('azure_ad', 'microsoft_entra_id'):
        token = get_microsoft_entra_id_access_token()

    if token:
        headers['Authorization'] = f'Bearer {token}'

    if config.get('headers') and isinstance(config.get('headers'), dict):
        custom_headers = get_custom_headers(config.get('headers'), user, metadata)
        headers.update(custom_headers)

    if is_openai_codex_web_auth_config(config) and token:
        headers['Authorization'] = f'Bearer {token}'
        session = await get_openai_web_auth_session()
        apply_openai_codex_web_auth_headers(
            headers,
            account_id=(session.token or {}).get('account_id') if session else None,
            metadata=metadata,
        )

    return headers, cookies


def get_microsoft_entra_id_access_token():
    """
    Get Microsoft Entra ID access token using DefaultAzureCredential for Azure OpenAI.
    Returns the token string or None if authentication fails.
    """
    try:
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(), 'https://cognitiveservices.azure.com/.default'
        )
        return token_provider()
    except Exception as e:
        log.error(f'Error getting Microsoft Entra ID access token: {e}')
        return None


##########################################
#
# API routes
#
##########################################

router = APIRouter()

OPENAI_WEB_AUTH_DEVICE_SESSION_PROVIDER = 'openai_web_auth_device'
OPENAI_WEB_AUTH_CREDENTIAL_PROVIDER = 'openai_web_auth_credential'
OPENAI_WEB_AUTH_STORAGE_USER_ID = '__openai_web_auth__'
OPENAI_WEB_AUTH_ISSUER = 'https://auth.openai.com'
OPENAI_WEB_AUTH_CLIENT_ID = 'app_EMoamEEZ73f0CkXaXp7hrann'
OPENAI_WEB_AUTH_VERIFICATION_URL = f'{OPENAI_WEB_AUTH_ISSUER}/codex/device'
OPENAI_WEB_AUTH_REDIRECT_URI = f'{OPENAI_WEB_AUTH_ISSUER}/deviceauth/callback'
OPENAI_WEB_AUTH_DEFAULT_EXPIRES_IN = 3600
OPENAI_WEB_AUTH_REFRESH_SKEW_SECONDS = 300
OPENAI_CODEX_WEB_AUTH_TYPE = 'openai_codex_web_auth'
OPENAI_CODEX_WEB_AUTH_LEGACY_TYPE = 'openai_web_auth'
OPENAI_CODEX_API_ENDPOINT = 'https://chatgpt.com/backend-api/codex/responses'
OPENAI_CODEX_WEB_AUTH_MODEL_IDS = [
    'gpt-5.5',
    'gpt-5.2',
    'gpt-5.3-codex',
    'gpt-5.3-codex-spark',
    'gpt-5.4',
    'gpt-5.4-mini',
]


class OpenAIWebAuthStartResponse(BaseModel):
    verification_url: str
    user_code: str
    session_id: str
    interval: int
    expires_at: int


class OpenAIWebAuthCompleteForm(BaseModel):
    session_id: str


class OpenAIWebAuthStatusResponse(BaseModel):
    credential_type: str
    connected: bool
    has_credential: bool
    status: str
    expires_at: Optional[int] = None


def is_openai_codex_web_auth_config(config: Optional[dict] = None) -> bool:
    return (config or {}).get('auth_type') in (
        OPENAI_CODEX_WEB_AUTH_TYPE,
        OPENAI_CODEX_WEB_AUTH_LEGACY_TYPE,
    )


def build_openai_codex_web_auth_models(url_idx: int) -> dict:
    return {
        'object': 'list',
        'data': [
            {
                'id': model_id,
                'name': model_id,
                'owned_by': 'openai',
                'openai': {'id': model_id},
                'urlIdx': url_idx,
                'connection_type': 'external',
                'provider': 'OpenAI Account Auth',
            }
            for model_id in OPENAI_CODEX_WEB_AUTH_MODEL_IDS
        ],
    }


async def build_openai_codex_web_auth_models_if_connected(url_idx: int) -> Optional[dict]:
    token = await get_openai_web_auth_access_token()
    if not token:
        return None
    return build_openai_codex_web_auth_models(url_idx)


def apply_openai_codex_web_auth_headers(headers: dict, account_id: Optional[str] = None, metadata: Optional[dict] = None):
    if account_id:
        headers['ChatGPT-Account-Id'] = account_id
    headers['originator'] = 'open-webui'
    headers['User-Agent'] = 'Open WebUI'
    session_id = metadata.get('chat_id') if metadata else None
    if session_id:
        headers['session_id'] = str(session_id)


def prepare_openai_codex_web_auth_request(
    payload: dict,
    is_responses: bool = False,
) -> tuple[str, dict, bool]:
    """Return the Codex account-auth endpoint and Responses-compatible payload."""

    responses_payload = payload if is_responses else convert_to_responses_payload(payload)
    if not responses_payload.get('instructions'):
        responses_payload['instructions'] = 'You are ChatGPT, a helpful assistant.'
    responses_payload['store'] = False
    responses_payload['stream'] = True

    return (
        OPENAI_CODEX_API_ENDPOINT,
        responses_payload,
        True,
    )


def iter_openai_codex_sse_payloads(text: str):
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith('data:'):
            continue
        data = line.removeprefix('data:').strip()
        if not data or data == '[DONE]':
            continue
        try:
            yield json.loads(data)
        except Exception:
            continue


def parse_openai_codex_sse_response(text: str):
    last_payload = None
    for payload in iter_openai_codex_sse_payloads(text):
        last_payload = payload
    return last_payload


def build_openai_codex_error_payload(payload: Optional[dict]) -> dict:
    payload = payload or {}
    details = payload.get('error') or payload.get('status_details') or payload.get('response') or payload

    if isinstance(details, dict):
        message = details.get('message') or details.get('error') or details.get('detail') or 'OpenAI account auth request failed'
        code = details.get('code') or payload.get('type') or 'openai_codex_web_auth_error'
        error_type = details.get('type') or payload.get('type') or 'upstream_error'
    else:
        message = str(details) if details else 'OpenAI account auth request failed'
        code = payload.get('type') or 'openai_codex_web_auth_error'
        error_type = payload.get('type') or 'upstream_error'

    return {
        'error': {
            'message': message,
            'type': error_type,
            'code': code,
        }
    }


def convert_openai_codex_sse_payload(payload: dict) -> Optional[bytes]:
    event_type = payload.get('type')
    if event_type == 'response.output_text.delta':
        delta = payload.get('delta') or payload.get('text') or ''
        chunk = {
            'id': payload.get('response_id') or payload.get('id') or '',
            'object': 'chat.completion.chunk',
            'model': payload.get('model') or '',
            'choices': [
                {
                    'index': 0,
                    'delta': {'content': delta},
                    'finish_reason': None,
                }
            ],
        }
        return f'data: {json.dumps(chunk)}\n\n'.encode()

    if event_type in ('response.failed', 'response.incomplete'):
        return (
            f'data: {json.dumps(build_openai_codex_error_payload(payload))}\n\n'
            'data: [DONE]\n\n'
        ).encode()

    if event_type == 'response.completed':
        return b'data: [DONE]\n\n'

    return None


async def openai_codex_stream_chunks_handler(stream: aiohttp.StreamReader):
    buffer = b''
    async for data, _ in stream.iter_chunks():
        if not data:
            continue
        lines = (buffer + data).split(b'\n')
        buffer = lines[-1]
        for raw_line in lines[:-1]:
            line = raw_line.decode('utf-8', 'replace').strip()
            if not line.startswith('data:'):
                continue
            event_data = line.removeprefix('data:').strip()
            if not event_data:
                continue
            if event_data == '[DONE]':
                yield b'data: [DONE]\n\n'
                continue
            try:
                converted = convert_openai_codex_sse_payload(json.loads(event_data))
            except Exception:
                converted = None
            if converted:
                yield converted

    if buffer:
        line = buffer.decode('utf-8', 'replace').strip()
        if line.startswith('data:'):
            event_data = line.removeprefix('data:').strip()
            try:
                converted = convert_openai_codex_sse_payload(json.loads(event_data))
            except Exception:
                converted = None
            if converted:
                yield converted


def _parse_openai_web_auth_positive_int(value, default: int, field_name: str) -> int:
    if value is None:
        return default

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=502,
            detail=f'OpenAI web auth response contained an invalid {field_name}',
        )

    if parsed < 1:
        raise HTTPException(
            status_code=502,
            detail=f'OpenAI web auth response contained an invalid {field_name}',
        )
    return parsed


def _decode_jwt_payload(token: str) -> dict:
    try:
        payload = token.split('.')[1]
        payload += '=' * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload.encode()).decode())
    except Exception:
        return {}


def _extract_openai_account_id(tokens: dict) -> Optional[str]:
    claims = _decode_jwt_payload(tokens.get('id_token') or tokens.get('access_token') or '')
    if not claims:
        return None

    api_auth = claims.get('https://api.openai.com/auth')
    if isinstance(claims.get('chatgpt_account_id'), str):
        return claims['chatgpt_account_id']
    if isinstance(api_auth, dict) and isinstance(api_auth.get('chatgpt_account_id'), str):
        return api_auth['chatgpt_account_id']

    organizations = claims.get('organizations')
    if isinstance(organizations, list):
        for organization in organizations:
            if isinstance(organization, dict) and isinstance(organization.get('id'), str):
                return organization['id']
    return None


def _openai_web_auth_status_from_session(session) -> OpenAIWebAuthStatusResponse:
    if not session:
        return OpenAIWebAuthStatusResponse(
            credential_type='none',
            connected=False,
            has_credential=False,
            status='not_configured',
        )

    status_value = 'connected' if session.expires_at > int(time.time()) else 'reconnect_required'
    return OpenAIWebAuthStatusResponse(
        credential_type='web_auth',
        connected=status_value == 'connected',
        has_credential=True,
        status=status_value,
        expires_at=session.expires_at,
    )


async def _post_openai_web_auth_json(url: str, json_payload: dict) -> tuple[int, dict]:
    async with aiohttp.ClientSession(
        trust_env=True,
        timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT),
    ) as session:
        async with session.post(
            url,
            json=json_payload,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'Open WebUI',
            },
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        ) as response:
            try:
                payload = await response.json()
            except Exception:
                payload = {}
            return response.status, payload


async def _post_openai_web_auth_form(url: str, form_payload: dict) -> tuple[int, dict]:
    async with aiohttp.ClientSession(
        trust_env=True,
        timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT),
    ) as session:
        async with session.post(
            url,
            data=urlencode(form_payload),
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        ) as response:
            try:
                payload = await response.json()
            except Exception:
                payload = {}
            return response.status, payload


async def start_openai_web_auth_device_flow() -> dict:
    status_code, data = await _post_openai_web_auth_json(
        f'{OPENAI_WEB_AUTH_ISSUER}/api/accounts/deviceauth/usercode',
        {'client_id': OPENAI_WEB_AUTH_CLIENT_ID},
    )
    if status_code >= 400:
        raise HTTPException(status_code=502, detail='OpenAI web auth start failed')

    device_auth_id = data.get('device_auth_id')
    user_code = data.get('user_code')
    if not isinstance(device_auth_id, str) or not isinstance(user_code, str):
        raise HTTPException(status_code=502, detail='OpenAI web auth start response was incomplete')

    interval = _parse_openai_web_auth_positive_int(data.get('interval'), 5, 'interval')
    expires_in = _parse_openai_web_auth_positive_int(data.get('expires_in'), 600, 'expiration')
    return {
        'device_auth_id': device_auth_id,
        'user_code': user_code,
        'interval': interval,
        'expires_at': int(time.time()) + expires_in,
    }


async def complete_openai_web_auth_device_flow(device_auth_id: str, user_code: str) -> dict:
    device_status, device_data = await _post_openai_web_auth_json(
        f'{OPENAI_WEB_AUTH_ISSUER}/api/accounts/deviceauth/token',
        {
            'device_auth_id': device_auth_id,
            'user_code': user_code,
        },
    )
    if device_status in (403, 404):
        raise HTTPException(status_code=409, detail='OpenAI authorization is not complete yet')
    if device_status >= 400:
        raise HTTPException(status_code=502, detail='OpenAI web auth completion failed')

    authorization_code = device_data.get('authorization_code')
    code_verifier = device_data.get('code_verifier')
    if not isinstance(authorization_code, str) or not isinstance(code_verifier, str):
        raise HTTPException(status_code=502, detail='OpenAI web auth completion response was incomplete')

    token_status, tokens = await _post_openai_web_auth_form(
        f'{OPENAI_WEB_AUTH_ISSUER}/oauth/token',
        {
            'grant_type': 'authorization_code',
            'code': authorization_code,
            'redirect_uri': OPENAI_WEB_AUTH_REDIRECT_URI,
            'client_id': OPENAI_WEB_AUTH_CLIENT_ID,
            'code_verifier': code_verifier,
        },
    )
    if token_status >= 400:
        raise HTTPException(status_code=502, detail='OpenAI web auth token exchange failed')
    if not tokens.get('access_token') or not tokens.get('refresh_token'):
        raise HTTPException(status_code=502, detail='OpenAI web auth token response was incomplete')

    expires_in = _parse_openai_web_auth_positive_int(
        tokens.get('expires_in'),
        OPENAI_WEB_AUTH_DEFAULT_EXPIRES_IN,
        'expiration',
    )
    return {
        'access_token': tokens['access_token'],
        'refresh_token': tokens['refresh_token'],
        'id_token': tokens.get('id_token'),
        'expires_at': int(time.time()) + expires_in,
        # Stored server-side only. Not exposed in public status DTOs until product confirms it is safe metadata.
        'account_id': _extract_openai_account_id(tokens),
    }


async def refresh_openai_web_auth_credential(token: dict) -> Optional[dict]:
    refresh_token = token.get('refresh_token')
    if not refresh_token:
        return None

    token_status, tokens = await _post_openai_web_auth_form(
        f'{OPENAI_WEB_AUTH_ISSUER}/oauth/token',
        {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': OPENAI_WEB_AUTH_CLIENT_ID,
        },
    )
    if token_status >= 400 or not tokens.get('access_token'):
        return None

    try:
        expires_in = _parse_openai_web_auth_positive_int(
            tokens.get('expires_in'),
            OPENAI_WEB_AUTH_DEFAULT_EXPIRES_IN,
            'expiration',
        )
        merged = {
            **token,
            'access_token': tokens['access_token'],
            'refresh_token': tokens.get('refresh_token') or refresh_token,
            'id_token': tokens.get('id_token') or token.get('id_token'),
            'expires_at': int(time.time()) + expires_in,
        }
    except HTTPException:
        return None
    merged['account_id'] = _extract_openai_account_id(merged) or token.get('account_id')
    return merged


async def get_openai_web_auth_session():
    return await OAuthSessions.get_session_by_provider_and_user_id(
        OPENAI_WEB_AUTH_CREDENTIAL_PROVIDER,
        OPENAI_WEB_AUTH_STORAGE_USER_ID,
    )


async def get_openai_web_auth_access_token() -> Optional[str]:
    session = await get_openai_web_auth_session()
    if not session:
        return None

    if session.expires_at <= int(time.time()) + OPENAI_WEB_AUTH_REFRESH_SKEW_SECONDS:
        refreshed_token = await refresh_openai_web_auth_credential(session.token)
        if not refreshed_token:
            return None
        session = await OAuthSessions.update_session_by_id(session.id, refreshed_token)
        if not session:
            return None

    return session.token.get('access_token')


async def has_connected_openai_web_auth_credential() -> bool:
    try:
        return bool(await get_openai_web_auth_access_token())
    except HTTPException:
        return False


async def build_openai_web_auth_status() -> OpenAIWebAuthStatusResponse:
    return _openai_web_auth_status_from_session(await get_openai_web_auth_session())


async def invalidate_openai_models_cache(request: Optional[Request] = None, user: Optional[UserModel] = None):
    """Clear OpenAI model caches after provider credentials or config change.

    The route-level model list is cached per user by ``get_all_models`` and the
    merged model lookup is also held in ``request.app.state.OPENAI_MODELS`` for
    routing.  Both can otherwise keep an empty/stale model list after an admin
    adds, removes, or switches the native OpenAI credential path.
    """

    cache_keys = ['openai_all_models']
    if user and getattr(user, 'id', None):
        cache_keys.append(f'openai_all_models_{user.id}')

    for cache_key in cache_keys:
        try:
            await get_all_models.cache.delete(cache_key)
        except Exception as e:
            log.debug(f'Failed to invalidate OpenAI models cache key {cache_key}: {e}')

    if request is not None:
        try:
            request.app.state.OPENAI_MODELS = {}
        except Exception as e:
            log.debug(f'Failed to reset OpenAI app-state model cache: {e}')


@router.get('/web-auth/status', response_model=OpenAIWebAuthStatusResponse)
async def get_web_auth_status(user=Depends(get_admin_user)):
    return await build_openai_web_auth_status()


@router.post('/web-auth/start', response_model=OpenAIWebAuthStartResponse)
async def start_web_auth(user=Depends(get_admin_user)):
    started = await start_openai_web_auth_device_flow()
    created = await OAuthSessions.create_session(
        user_id=OPENAI_WEB_AUTH_STORAGE_USER_ID,
        provider=OPENAI_WEB_AUTH_DEVICE_SESSION_PROVIDER,
        token={
            'device_auth_id': started['device_auth_id'],
            'user_code': started['user_code'],
            'expires_at': started['expires_at'],
        },
    )
    if not created:
        raise HTTPException(status_code=500, detail='Failed to store OpenAI web auth session')

    return OpenAIWebAuthStartResponse(
        verification_url=OPENAI_WEB_AUTH_VERIFICATION_URL,
        user_code=started['user_code'],
        session_id=created.id,
        interval=started['interval'],
        expires_at=started['expires_at'],
    )


@router.post('/web-auth/complete', response_model=OpenAIWebAuthStatusResponse)
async def complete_web_auth(
    form_data: OpenAIWebAuthCompleteForm,
    request: Request,
    user=Depends(get_admin_user),
):
    device_session = await OAuthSessions.get_session_by_id(form_data.session_id)
    if not device_session or device_session.provider != OPENAI_WEB_AUTH_DEVICE_SESSION_PROVIDER:
        raise HTTPException(status_code=404, detail='OpenAI web auth session not found')
    if device_session.expires_at <= int(time.time()):
        await OAuthSessions.delete_session_by_id(device_session.id)
        raise HTTPException(status_code=409, detail='OpenAI web auth session expired')

    credential = await complete_openai_web_auth_device_flow(
        device_session.token.get('device_auth_id', ''),
        device_session.token.get('user_code', ''),
    )

    await OAuthSessions.delete_sessions_by_user_id_and_provider(
        OPENAI_WEB_AUTH_STORAGE_USER_ID,
        OPENAI_WEB_AUTH_CREDENTIAL_PROVIDER,
    )
    created = await OAuthSessions.create_session(
        user_id=OPENAI_WEB_AUTH_STORAGE_USER_ID,
        provider=OPENAI_WEB_AUTH_CREDENTIAL_PROVIDER,
        token=credential,
    )
    await OAuthSessions.delete_session_by_id(device_session.id)
    if not created:
        raise HTTPException(status_code=500, detail='Failed to store OpenAI web auth credential')

    await invalidate_openai_models_cache(request, user)

    return _openai_web_auth_status_from_session(created)


@router.post('/web-auth/disconnect', response_model=OpenAIWebAuthStatusResponse)
async def disconnect_web_auth(request: Request, user=Depends(get_admin_user)):
    await OAuthSessions.delete_sessions_by_user_id_and_provider(
        OPENAI_WEB_AUTH_STORAGE_USER_ID,
        OPENAI_WEB_AUTH_CREDENTIAL_PROVIDER,
    )
    await OAuthSessions.delete_sessions_by_user_id_and_provider(
        OPENAI_WEB_AUTH_STORAGE_USER_ID,
        OPENAI_WEB_AUTH_DEVICE_SESSION_PROVIDER,
    )
    await invalidate_openai_models_cache(request, user)
    return await build_openai_web_auth_status()


@router.get('/config')
async def get_config(request: Request, user=Depends(get_admin_user)):
    return {
        'ENABLE_OPENAI_API': request.app.state.config.ENABLE_OPENAI_API,
        'OPENAI_API_BASE_URLS': request.app.state.config.OPENAI_API_BASE_URLS,
        'OPENAI_API_KEYS': request.app.state.config.OPENAI_API_KEYS,
        'OPENAI_API_CONFIGS': request.app.state.config.OPENAI_API_CONFIGS,
    }


class OpenAIConfigForm(BaseModel):
    ENABLE_OPENAI_API: bool | None = None
    OPENAI_API_BASE_URLS: list[str]
    OPENAI_API_KEYS: list[str]
    OPENAI_API_CONFIGS: dict


@router.post('/config/update')
async def update_config(request: Request, form_data: OpenAIConfigForm, user=Depends(get_admin_user)):
    request.app.state.config.ENABLE_OPENAI_API = form_data.ENABLE_OPENAI_API
    request.app.state.config.OPENAI_API_BASE_URLS = form_data.OPENAI_API_BASE_URLS
    request.app.state.config.OPENAI_API_KEYS = form_data.OPENAI_API_KEYS

    # Check if API KEYS length is same than API URLS length
    if len(request.app.state.config.OPENAI_API_KEYS) != len(request.app.state.config.OPENAI_API_BASE_URLS):
        if len(request.app.state.config.OPENAI_API_KEYS) > len(request.app.state.config.OPENAI_API_BASE_URLS):
            request.app.state.config.OPENAI_API_KEYS = request.app.state.config.OPENAI_API_KEYS[
                : len(request.app.state.config.OPENAI_API_BASE_URLS)
            ]
        else:
            request.app.state.config.OPENAI_API_KEYS += [''] * (
                len(request.app.state.config.OPENAI_API_BASE_URLS) - len(request.app.state.config.OPENAI_API_KEYS)
            )

    request.app.state.config.OPENAI_API_CONFIGS = form_data.OPENAI_API_CONFIGS

    # Remove the API configs that are not in the API URLS
    keys = list(map(str, range(len(request.app.state.config.OPENAI_API_BASE_URLS))))
    request.app.state.config.OPENAI_API_CONFIGS = {
        key: value for key, value in request.app.state.config.OPENAI_API_CONFIGS.items() if key in keys
    }

    await invalidate_openai_models_cache(request, user)

    return {
        'ENABLE_OPENAI_API': request.app.state.config.ENABLE_OPENAI_API,
        'OPENAI_API_BASE_URLS': request.app.state.config.OPENAI_API_BASE_URLS,
        'OPENAI_API_KEYS': request.app.state.config.OPENAI_API_KEYS,
        'OPENAI_API_CONFIGS': request.app.state.config.OPENAI_API_CONFIGS,
    }


@router.post('/audio/speech')
async def speech(request: Request, user=Depends(get_verified_user)):
    idx = None
    try:
        idx = request.app.state.config.OPENAI_API_BASE_URLS.index('https://api.openai.com/v1')

        body = await request.body()
        name = hashlib.sha256(body).hexdigest()

        SPEECH_CACHE_DIR = CACHE_DIR / 'audio' / 'speech'
        SPEECH_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        file_path = SPEECH_CACHE_DIR.joinpath(f'{name}.mp3')
        file_body_path = SPEECH_CACHE_DIR.joinpath(f'{name}.json')

        # Check if the file already exists in the cache
        if file_path.is_file():
            return FileResponse(file_path)

        url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
        key = request.app.state.config.OPENAI_API_KEYS[idx]
        api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
            str(idx),
            request.app.state.config.OPENAI_API_CONFIGS.get(url, {}),  # Legacy support
        )

        headers, cookies = await get_headers_and_cookies(request, url, key, api_config, user=user)

        r = None
        try:
            session = await get_session()
            r = await session.post(
                url=f'{url}/audio/speech',
                data=body,
                headers=headers,
                cookies=cookies,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            )

            r.raise_for_status()

            # Save the streaming content to a file
            with open(file_path, 'wb') as f:
                async for chunk in r.content.iter_chunked(8192):
                    f.write(chunk)

            with open(file_body_path, 'w') as f:
                json.dump(json.loads(body.decode('utf-8')), f)

            # Return the saved file
            return FileResponse(file_path)

        except Exception as e:
            log.exception(e)

            detail = None
            if r is not None:
                try:
                    res = await r.json()
                    if 'error' in res:
                        detail = f'External: {res["error"]}'
                except Exception:
                    detail = f'External: {e}'

            raise HTTPException(
                status_code=r.status if r else 500,
                detail=detail if detail else 'Open WebUI: Server Connection Error',
            )

    except ValueError:
        raise HTTPException(status_code=401, detail=ERROR_MESSAGES.OPENAI_NOT_FOUND)


async def get_all_models_responses(request: Request, user: UserModel) -> list:
    if not request.app.state.config.ENABLE_OPENAI_API:
        return []

    # Cache config values locally to avoid repeated Redis lookups.
    # Each access to request.app.state.config.<KEY> triggers a Redis GET;
    # caching here avoids hundreds of redundant round-trips.
    api_base_urls = request.app.state.config.OPENAI_API_BASE_URLS
    api_keys = list(request.app.state.config.OPENAI_API_KEYS)
    api_configs = request.app.state.config.OPENAI_API_CONFIGS

    # Check if API KEYS length is same than API URLS length
    num_urls = len(api_base_urls)
    num_keys = len(api_keys)

    if num_keys != num_urls:
        # if there are more keys than urls, remove the extra keys
        if num_keys > num_urls:
            api_keys = api_keys[:num_urls]
            request.app.state.config.OPENAI_API_KEYS = api_keys
        # if there are more urls than keys, add empty keys
        else:
            api_keys += [''] * (num_urls - num_keys)
            request.app.state.config.OPENAI_API_KEYS = api_keys

    request_tasks = []
    for idx, url in enumerate(api_base_urls):
        if (str(idx) not in api_configs) and (url not in api_configs):  # Legacy support
            if is_empty_native_openai_bearer_connection(url, api_keys[idx]):
                log.info('Skipping empty native OpenAI bearer connection at index %s during model listing', idx)
                request_tasks.append(asyncio.ensure_future(asyncio.sleep(0, None)))
                continue
            request_tasks.append(get_models_request(request, url, api_keys[idx], user=user))
        else:
            api_config = api_configs.get(
                str(idx),
                api_configs.get(url, {}),  # Legacy support
            )

            enable = api_config.get('enable', True)
            model_ids = api_config.get('model_ids', [])

            if enable:
                if is_openai_codex_web_auth_config(api_config):
                    request_tasks.append(
                        asyncio.ensure_future(build_openai_codex_web_auth_models_if_connected(idx))
                    )
                    continue
                if is_empty_native_openai_bearer_connection(url, api_keys[idx], api_config):
                    log.info('Skipping empty native OpenAI bearer connection at index %s during model listing', idx)
                    request_tasks.append(asyncio.ensure_future(asyncio.sleep(0, None)))
                    continue
                if len(model_ids) == 0:
                    request_tasks.append(get_models_request(request, url, api_keys[idx], user=user, config=api_config))
                else:
                    model_list = {
                        'object': 'list',
                        'data': [
                            {
                                'id': model_id,
                                'name': model_id,
                                'owned_by': 'openai',
                                'openai': {'id': model_id},
                                'urlIdx': idx,
                            }
                            for model_id in model_ids
                        ],
                    }

                    request_tasks.append(asyncio.ensure_future(asyncio.sleep(0, model_list)))
            else:
                request_tasks.append(asyncio.ensure_future(asyncio.sleep(0, None)))

    responses = await asyncio.gather(*request_tasks)

    for idx, response in enumerate(responses):
        if response:
            url = api_base_urls[idx]
            api_config = api_configs.get(
                str(idx),
                api_configs.get(url, {}),  # Legacy support
            )

            connection_type = api_config.get('connection_type', 'external')
            prefix_id = api_config.get('prefix_id', None)
            tags = api_config.get('tags', [])
            provider = api_config.get('provider', '')

            model_list = response if isinstance(response, list) else response.get('data', [])
            if not isinstance(model_list, list):
                # Catch non-list responses
                model_list = []

            for model in model_list:
                # Remove name key if its value is None #16689
                if 'name' in model and model['name'] is None:
                    del model['name']

                if prefix_id:
                    model['id'] = f'{prefix_id}.{model.get("id", model.get("name", ""))}'

                if tags:
                    model['tags'] = tags

                if connection_type:
                    model['connection_type'] = connection_type

                if provider:
                    model['provider'] = provider

    log.debug(f'get_all_models:responses() {responses}')
    return responses


async def get_filtered_models(models, user, db=None):
    # Filter models based on user access control
    model_ids = [model['id'] for model in models.get('data', [])]
    model_infos = {model_info.id: model_info for model_info in await Models.get_models_by_ids(model_ids, db=db)}
    user_group_ids = {group.id for group in await Groups.get_groups_by_member_id(user.id, db=db)}

    # Batch-fetch accessible resource IDs in a single query instead of N has_access calls
    accessible_model_ids = await AccessGrants.get_accessible_resource_ids(
        user_id=user.id,
        resource_type='model',
        resource_ids=list(model_infos.keys()),
        permission='read',
        user_group_ids=user_group_ids,
        db=db,
    )

    filtered_models = []
    for model in models.get('data', []):
        model_info = model_infos.get(model['id'])
        if model_info:
            if user.id == model_info.user_id or model_info.id in accessible_model_ids:
                filtered_models.append(model)
    return filtered_models


@cached(
    ttl=MODELS_CACHE_TTL,
    key=lambda _, user: f'openai_all_models_{user.id}' if user else 'openai_all_models',
)
async def get_all_models(request: Request, user: UserModel) -> dict[str, list]:
    log.info('get_all_models()')

    if not request.app.state.config.ENABLE_OPENAI_API:
        return {'data': []}

    # Cache config value locally to avoid repeated Redis lookups inside
    # the nested loop in get_merged_models (one GET per model otherwise).
    api_base_urls = request.app.state.config.OPENAI_API_BASE_URLS

    responses = await get_all_models_responses(request, user=user)

    def extract_data(response):
        if response and 'data' in response:
            return response['data']
        if isinstance(response, list):
            return response
        return None

    def is_supported_openai_models(model_id):
        if any(
            name in model_id
            for name in [
                'babbage',
                'dall-e',
                'davinci',
                'embedding',
                'tts',
                'whisper',
            ]
        ):
            return False
        return True

    def get_merged_models(model_lists):
        log.debug(f'merge_models_lists {model_lists}')
        models = {}

        for idx, model_list in enumerate(model_lists):
            if model_list is not None and 'error' not in model_list:
                for model in model_list:
                    model_id = model.get('id') or model.get('name')

                    base_url = api_base_urls[idx]
                    hostname = urlparse(base_url).hostname if base_url else None
                    if hostname == 'api.openai.com' and not is_supported_openai_models(model_id):
                        # Skip unwanted OpenAI models
                        continue

                    if model_id and model_id not in models:
                        merged = {
                            **model,
                            'name': model.get('name', model_id),
                            'owned_by': 'openai',
                            'openai': model,
                            'connection_type': model.get('connection_type', 'external'),
                            'provider': model.get('provider', ''),
                            'urlIdx': idx,
                        }

                        # llama.cpp router mode: derive loaded state from
                        # the status object returned by GET /v1/models.
                        status = model.get('status')
                        if isinstance(status, dict) and 'value' in status:
                            merged['loaded'] = status['value'] in ('loaded', 'sleeping')

                        models[model_id] = merged

        return models

    models = get_merged_models(map(extract_data, responses))
    log.debug(f'models: {models}')

    request.app.state.OPENAI_MODELS = models
    return {'data': list(models.values())}


@router.get('/models')
@router.get('/models/{url_idx}')
async def get_models(request: Request, url_idx: int | None = None, user=Depends(get_verified_user)):
    if not request.app.state.config.ENABLE_OPENAI_API:
        raise HTTPException(status_code=503, detail='OpenAI API is disabled')

    models = {
        'data': [],
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

        if is_empty_native_openai_bearer_connection(url, key, api_config):
            log.info('Skipping empty native OpenAI bearer connection at index %s during direct model listing', url_idx)
            return models

        if is_openai_codex_web_auth_config(api_config):
            models = await build_openai_codex_web_auth_models_if_connected(url_idx)
            return models or {'data': []}

        r = None
        async with aiohttp.ClientSession(
            trust_env=True,
            timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST),
        ) as session:
            try:
                headers, cookies = await get_headers_and_cookies(request, url, key, api_config, user=user)

                if api_config.get('azure') or api_config.get('provider') == 'azure':
                    models = {
                        'data': api_config.get('model_ids', []) or [],
                        'object': 'list',
                    }
                elif is_anthropic_url(url):
                    models = await get_anthropic_models(url, key, user=user)
                    if models is None:
                        raise Exception('Failed to connect to Anthropic API')
                else:
                    async with session.get(
                        f'{url}/models',
                        headers=headers,
                        cookies=cookies,
                        ssl=AIOHTTP_CLIENT_SESSION_SSL,
                    ) as r:
                        if r.status != 200:
                            error_detail = f'HTTP Error: {r.status}'
                            try:
                                res = await r.json()
                                if 'error' in res:
                                    error_detail = f'External Error: {res["error"]}'
                            except Exception:
                                pass

                            if is_openai_codex_web_auth_config(api_config):
                                log.warning(
                                    'OpenAI web auth model request failed for host=%s status=%s detail=%s',
                                    urlparse(url).hostname,
                                    r.status,
                                    error_detail,
                                )
                            raise Exception(error_detail)

                        response_data = await r.json()

                        if 'api.openai.com' in url:
                            response_data['data'] = [
                                model
                                for model in response_data.get('data', [])
                                if not any(
                                    name in model['id']
                                    for name in [
                                        'babbage',
                                        'dall-e',
                                        'davinci',
                                        'embedding',
                                        'tts',
                                        'whisper',
                                    ]
                                )
                            ]

                        models = response_data
            except aiohttp.ClientError as e:
                # ClientError covers all aiohttp requests issues
                log.exception(f'Client error: {str(e)}')
                raise HTTPException(status_code=500, detail='Open WebUI: Server Connection Error')
            except Exception as e:
                log.exception(f'Unexpected error: {e}')
                error_detail = f'Unexpected error: {str(e)}'
                raise HTTPException(status_code=500, detail=error_detail)

    if user.role == 'user' and not BYPASS_MODEL_ACCESS_CONTROL:
        models['data'] = await get_filtered_models(models, user)

    return models


class ConnectionVerificationForm(BaseModel):
    url: str
    key: str

    config: dict | None = None


@router.post('/verify')
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
            headers, cookies = await get_headers_and_cookies(request, url, key, api_config, user=user)

            if api_config.get('azure') or api_config.get('provider') == 'azure':
                # Only set api-key header if not using Azure Entra ID authentication
                auth_type = api_config.get('auth_type', 'bearer')
                if auth_type not in ('azure_ad', 'microsoft_entra_id'):
                    headers['api-key'] = key

                # Azure v1 format: base URL already ends with /openai/v1,
                # use standard /models endpoint without api-version.
                is_azure_v1 = bool(re.search(r'/openai/v1(?:/|$)', url))

                if is_azure_v1:
                    verify_url = f'{url.rstrip("/")}/models'
                else:
                    api_version = api_config.get('api_version', '') or '2023-03-15-preview'
                    verify_url = f'{url}/openai/models?api-version={api_version}'

                async with session.get(
                    url=verify_url,
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
                            return JSONResponse(status_code=r.status, content=response_data)
                        else:
                            return PlainTextResponse(status_code=r.status, content=response_data)

                    return response_data
            elif is_anthropic_url(url):
                result = await get_anthropic_models(url, key)
                if result is None:
                    raise HTTPException(status_code=500, detail=ERROR_MESSAGES.SERVER_CONNECTION_ERROR)
                if 'error' in result:
                    raise HTTPException(status_code=500, detail=result['error'])
                return result
            else:
                async with session.get(
                    f'{url}/models',
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
                            return JSONResponse(status_code=r.status, content=response_data)
                        else:
                            return PlainTextResponse(status_code=r.status, content=response_data)

                    return response_data

        except aiohttp.ClientError as e:
            # ClientError covers all aiohttp requests issues
            log.exception(f'Client error: {str(e)}')
            raise HTTPException(status_code=500, detail=ERROR_MESSAGES.SERVER_CONNECTION_ERROR)
        except Exception as e:
            log.exception(f'Unexpected error: {e}')
            raise HTTPException(status_code=500, detail=ERROR_MESSAGES.SERVER_CONNECTION_ERROR)


def get_azure_allowed_params(api_version: str) -> set[str]:
    allowed_params = {
        'messages',
        'temperature',
        'role',
        'content',
        'contentPart',
        'contentPartImage',
        'enhancements',
        'dataSources',
        'n',
        'stream',
        'stop',
        'max_tokens',
        'presence_penalty',
        'frequency_penalty',
        'logit_bias',
        'user',
        'function_call',
        'functions',
        'tools',
        'tool_choice',
        'top_p',
        'log_probs',
        'top_logprobs',
        'response_format',
        'seed',
        'max_completion_tokens',
        'reasoning_effort',
    }

    try:
        if api_version >= '2024-09-01-preview':
            allowed_params.add('stream_options')
    except ValueError:
        log.debug(f'Invalid API version {api_version} for Azure OpenAI. Defaulting to allowed parameters.')

    return allowed_params


def is_openai_new_model(model: str) -> bool:
    model_lower = model.lower()
    # o-series models (o1, o3, o4, o5, ...)
    if re.match(r'^o\d+', model_lower):
        return True
    # gpt-N where N >= 5 (gpt-5, gpt-5.2, gpt-6, ...)
    m = re.match(r'^gpt-(\d+)', model_lower)
    if m and int(m.group(1)) >= 5:
        return True
    return False


def _sanitize_model_for_url(model: str) -> str:
    """Sanitize a model name before interpolating it into a URL path.

    Rejects path traversal attempts (../, /, \\) and percent-encodes
    the name so it is safe to use as a single URL path segment
    (e.g. Azure deployment name).
    """
    if not model or '..' in model or '/' in model or '\\' in model:
        raise HTTPException(
            status_code=400,
            detail='Invalid model name: must not be empty or contain path separators or traversal sequences',
        )
    return quote(model, safe='')


def convert_to_azure_payload(url, payload: dict, api_version: str):
    model = payload.get('model', '')

    # Filter allowed parameters based on Azure OpenAI API
    allowed_params = get_azure_allowed_params(api_version)

    # Special handling for o-series models
    if is_openai_new_model(model):
        # Convert max_tokens to max_completion_tokens for o-series models
        if 'max_tokens' in payload:
            payload['max_completion_tokens'] = payload['max_tokens']
            del payload['max_tokens']

        # Remove temperature if not 1 for o-series models
        if 'temperature' in payload and payload['temperature'] != 1:
            log.debug(
                f'Removing temperature parameter for o-series model {model} as only default value (1) is supported'
            )
            del payload['temperature']

    # Filter out unsupported parameters
    payload = {k: v for k, v in payload.items() if k in allowed_params}

    # Sanitize model name to prevent path traversal in the deployment URL
    model = _sanitize_model_for_url(model)

    url = f'{url}/openai/deployments/{model}'
    return url, payload


# Fields accepted by the Responses API for each input item type.
RESPONSES_ALLOWED_FIELDS: dict[str, set[str]] = {
    'message': {'type', 'role', 'content'},
    'function_call': {'type', 'call_id', 'name', 'arguments', 'id'},
    'function_call_output': {'type', 'call_id', 'output'},
}


def _normalize_stored_item(item: dict) -> dict:
    """Strip local-only fields from a stored output item before replaying it.

    Open WebUI stores extra bookkeeping fields (``id``, ``status``,
    ``started_at``, ``ended_at``, ``duration``, ``_tag_type``,
    ``attributes``, ``summary``, etc.) that the Responses API does
    not accept.  This helper returns a copy containing only the
    fields the API understands.
    """
    item_type = item.get('type', '')
    allowed = RESPONSES_ALLOWED_FIELDS.get(item_type)
    if allowed is None:
        # Unknown type — pass through as-is (e.g. reasoning, extension items).
        return item
    return {k: v for k, v in item.items() if k in allowed}


def convert_to_responses_payload(payload: dict) -> dict:
    """
    Convert Chat Completions payload to Responses API format.

    Chat Completions: { messages: [{role, content}], ... }
    Responses API: { input: [{type: "message", role, content: [...]}], instructions: "system" }
    """
    messages = payload.pop('messages', [])

    system_content = ''
    input_items = []

    for msg in messages:
        role = msg.get('role', 'user')
        content = msg.get('content', '')

        # Check for stored output items (from previous Responses API turn)
        stored_output = msg.get('output')
        if stored_output and isinstance(stored_output, list):
            input_items.extend(_normalize_stored_item(item) for item in stored_output)
            continue

        if role == 'system':
            if isinstance(content, str):
                system_content = content
            elif isinstance(content, list):
                system_content = '\n'.join(p.get('text', '') for p in content if p.get('type') == 'text')
            continue

        # Handle assistant messages with tool_calls (from convert_output_to_messages)
        if role == 'assistant' and msg.get('tool_calls'):
            # Add text content as message if present
            if content:
                text = (
                    content
                    if isinstance(content, str)
                    else '\n'.join(p.get('text', '') for p in content if p.get('type') == 'text')
                )
                if text.strip():
                    input_items.append(
                        {
                            'type': 'message',
                            'role': 'assistant',
                            'content': [{'type': 'output_text', 'text': text}],
                        }
                    )
            # Convert each tool_call to a function_call input item
            for tool_call in msg['tool_calls']:
                func = tool_call.get('function', {})
                input_items.append(
                    {
                        'type': 'function_call',
                        'call_id': tool_call.get('id', ''),
                        'name': func.get('name', ''),
                        'arguments': func.get('arguments', '{}'),
                    }
                )
            continue

        # Handle tool result messages
        if role == 'tool':
            input_items.append(
                {
                    'type': 'function_call_output',
                    'call_id': msg.get('tool_call_id', ''),
                    'output': msg.get('content', ''),
                }
            )
            continue

        # Convert content format
        text_type = 'output_text' if role == 'assistant' else 'input_text'

        if isinstance(content, str):
            content_parts = [{'type': text_type, 'text': content}]
        elif isinstance(content, list):
            content_parts = []
            for part in content:
                if part.get('type') == 'text':
                    content_parts.append({'type': text_type, 'text': part.get('text', '')})
                elif part.get('type') == 'image_url':
                    url_data = part.get('image_url', {})
                    url = url_data.get('url', '') if isinstance(url_data, dict) else url_data
                    content_parts.append({'type': 'input_image', 'image_url': url})
        else:
            content_parts = [{'type': text_type, 'text': str(content)}]

        input_items.append({'type': 'message', 'role': role, 'content': content_parts})

    responses_payload = {**payload, 'input': input_items}

    # Forward previous_response_id when the middleware has set it
    # (only used when ENABLE_RESPONSES_API_STATEFUL is enabled).
    previous_response_id = responses_payload.pop('previous_response_id', None)
    if previous_response_id:
        responses_payload['previous_response_id'] = previous_response_id

    if system_content:
        responses_payload['instructions'] = system_content

    if 'max_tokens' in responses_payload:
        responses_payload['max_output_tokens'] = responses_payload.pop('max_tokens')

    if 'max_completion_tokens' in responses_payload:
        responses_payload['max_output_tokens'] = responses_payload.pop('max_completion_tokens')

    # Remove Chat Completions-only parameters not supported by the Responses API
    for unsupported_key in (
        'stream_options',
        'logit_bias',
        'frequency_penalty',
        'presence_penalty',
        'stop',
    ):
        responses_payload.pop(unsupported_key, None)

    # Convert Chat Completions tools format to Responses API format
    # Chat Completions: {"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}
    # Responses API:    {"type": "function", "name": ..., "description": ..., "parameters": ...}
    if 'tools' in responses_payload and isinstance(responses_payload['tools'], list):
        converted_tools = []
        for tool in responses_payload['tools']:
            if isinstance(tool, dict) and 'function' in tool:
                func = tool['function']
                converted_tool = {'type': tool.get('type', 'function')}
                if isinstance(func, dict):
                    converted_tool['name'] = func.get('name', '')
                    if 'description' in func:
                        converted_tool['description'] = func['description']
                    if 'parameters' in func:
                        converted_tool['parameters'] = func['parameters']
                    if 'strict' in func:
                        converted_tool['strict'] = func['strict']
                converted_tools.append(converted_tool)
            else:
                # Already in correct format or unknown format, pass through
                converted_tools.append(tool)
        responses_payload['tools'] = converted_tools

    return responses_payload


def convert_responses_result(response: dict) -> dict:
    """
    Convert non-streaming Responses API result to Chat Completions format.

    Extracts text from message output items so all downstream consumers
    (frontend tasks, get_content_from_response) work without modification.
    """
    output_items = response.get('output', [])

    content = ''
    for item in output_items:
        if item.get('type') == 'message':
            for part in item.get('content', []):
                if part.get('type') == 'output_text':
                    content += part.get('text', '')

    return {
        'id': response.get('id', ''),
        'object': 'chat.completion',
        'model': response.get('model', ''),
        'choices': [
            {
                'index': 0,
                'message': {
                    'role': 'assistant',
                    'content': content,
                },
                'finish_reason': 'stop',
            }
        ],
        'usage': response.get('usage', {}),
    }


@router.post('/chat/completions')
async def generate_chat_completion(
    request: Request,
    form_data: dict,
    user=Depends(get_verified_user),
):
    # NOTE: We intentionally do NOT use Depends(get_async_session) here.
    # Database operations (get_model_by_id, AccessGrants.has_access) manage their own short-lived sessions.
    # This prevents holding a connection during the entire LLM call (30-60+ seconds),
    # which would exhaust the connection pool under concurrent load.

    # bypass_filter and bypass_system_prompt are read from request.state to prevent
    # external clients from setting them via query parameter. Only internal
    # server-side callers (e.g. utils/chat.py) should set
    # request.state.bypass_filter / request.state.bypass_system_prompt = True.
    bypass_filter = getattr(request.state, 'bypass_filter', False)
    if BYPASS_MODEL_ACCESS_CONTROL:
        bypass_filter = True
    bypass_system_prompt = getattr(request.state, 'bypass_system_prompt', False)

    idx = 0

    payload = {**form_data}
    metadata = payload.pop('metadata', None)

    model_id = form_data.get('model')
    model_info = await Models.get_model_by_id(model_id)

    # Check model info and override the payload
    if model_info:
        if model_info.base_model_id:
            base_model_id = (
                request.base_model_id if hasattr(request, 'base_model_id') else model_info.base_model_id
            )  # Use request's base_model_id if available
            payload['model'] = base_model_id
            model_id = base_model_id

        params = model_info.params.model_dump()

        if params:
            system = params.pop('system', None)

            payload = apply_model_params_to_body_openai(params, payload)
            if not bypass_system_prompt:
                payload = await apply_system_prompt_to_body(system, payload, metadata, user)

        await check_model_access(user, model_info, bypass_filter)
    else:
        await check_model_access(user, None, bypass_filter)

    # Check if model is already in app state cache to avoid expensive get_all_models() call
    models = request.app.state.OPENAI_MODELS
    if not models or model_id not in models:
        await get_all_models(request, user=user)
        models = request.app.state.OPENAI_MODELS
    model = models.get(model_id)

    if model:
        idx = model['urlIdx']
    else:
        raise HTTPException(
            status_code=404,
            detail=ERROR_MESSAGES.MODEL_NOT_FOUND(),
        )

    # Get the API config for the model
    api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
        str(idx),
        request.app.state.config.OPENAI_API_CONFIGS.get(
            request.app.state.config.OPENAI_API_BASE_URLS[idx], {}
        ),  # Legacy support
    )

    prefix_id = api_config.get('prefix_id', None)
    if prefix_id:
        payload['model'] = payload['model'].replace(f'{prefix_id}.', '')

    # Add user info to the payload if the model is a pipeline
    if 'pipeline' in model and model.get('pipeline'):
        payload['user'] = {
            'name': user.name,
            'id': user.id,
            'email': user.email,
            'role': user.role,
        }

    url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
    key = request.app.state.config.OPENAI_API_KEYS[idx]

    # Check if model is a reasoning model that needs special handling
    if is_openai_new_model(payload['model']):
        payload = openai_reasoning_model_handler(payload)
    elif 'api.openai.com' not in url:
        # Remove "max_completion_tokens" from the payload for backward compatibility
        if 'max_completion_tokens' in payload:
            payload['max_tokens'] = payload['max_completion_tokens']
            del payload['max_completion_tokens']

    if 'max_tokens' in payload and 'max_completion_tokens' in payload:
        del payload['max_tokens']

    # Convert the modified body back to JSON
    if 'logit_bias' in payload and payload['logit_bias']:
        logit_bias = convert_logit_bias_input_to_json(payload['logit_bias'])

        if logit_bias:
            payload['logit_bias'] = json.loads(logit_bias)

    requested_stream = bool(payload.get('stream'))
    headers, cookies = await get_headers_and_cookies(request, url, key, api_config, metadata, user=user)

    is_responses = api_config.get('api_type') == 'responses'
    is_codex_web_auth = is_openai_codex_web_auth_config(api_config)

    if is_codex_web_auth:
        request_url, payload, is_responses = prepare_openai_codex_web_auth_request(payload, is_responses)
    elif api_config.get('azure') or api_config.get('provider') == 'azure':
        # Only set api-key header if not using Azure Entra ID authentication
        auth_type = api_config.get('auth_type', 'bearer')
        if auth_type not in ('azure_ad', 'microsoft_entra_id'):
            headers['api-key'] = key

        # Azure v1 format: base URL already ends with /openai/v1,
        # model stays in the payload, no deployment URL rewriting.
        is_azure_v1 = bool(re.search(r'/openai/v1(?:/|$)', url))

        if is_azure_v1:
            if is_responses:
                payload = convert_to_responses_payload(payload)
                request_url = f'{url.rstrip("/")}/responses'
            else:
                request_url = f'{url.rstrip("/")}/chat/completions'
        else:
            api_version = api_config.get('api_version', '2023-03-15-preview')
            request_url, payload = convert_to_azure_payload(url, payload, api_version)
            headers['api-version'] = api_version

            if is_responses:
                payload = convert_to_responses_payload(payload)
                request_url = f'{request_url}/responses?api-version={api_version}'
            else:
                request_url = f'{request_url}/chat/completions?api-version={api_version}'
    else:
        if is_responses:
            payload = convert_to_responses_payload(payload)
            request_url = f'{url}/responses'
        else:
            request_url = f'{url}/chat/completions'
    # For Chat Completions, strip image parts from multimodal tool messages
    # (Chat Completions doesn't support images in tool content).
    if not is_responses and 'messages' in payload:
        for message in payload['messages']:
            if message.get('role') == 'tool' and isinstance(message.get('content'), list):
                message['content'] = ''.join(
                    part.get('text', '') for part in message['content'] if part.get('type') in ('input_text', 'text')
                )

    payload = json.dumps(payload)

    r = None
    streaming = False
    response = None

    try:
        session = await get_session()

        r = await session.request(
            method='POST',
            url=request_url,
            data=payload,
            headers=headers,
            cookies=cookies,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
            timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT),
        )

        if is_codex_web_auth and 'text/event-stream' in r.headers.get('Content-Type', ''):
            if r.status >= 400:
                error_body = await r.text()
                log.error(
                    'OpenAI account auth returned HTTP %d with SSE content-type: %s',
                    r.status,
                    error_body[:1000],
                )
                parsed_error = parse_openai_codex_sse_response(error_body)
                error_content = build_openai_codex_error_payload(parsed_error)
                return JSONResponse(status_code=r.status, content=error_content)

            if requested_stream:
                streaming = True
                return StreamingResponse(
                    stream_wrapper(r, content_handler=openai_codex_stream_chunks_handler),
                    status_code=r.status,
                    media_type='text/event-stream',
                    headers=_clean_proxy_headers(r.headers),
                )

            response_text = await r.text()
            parsed_response = parse_openai_codex_sse_response(response_text)
            if parsed_response is None:
                raise HTTPException(status_code=502, detail='OpenAI account auth response could not be parsed')

            if parsed_response.get('type') in ('response.failed', 'response.incomplete'):
                return JSONResponse(
                    status_code=502,
                    content=build_openai_codex_error_payload(parsed_response),
                )

            response = convert_responses_result(parsed_response)
            return response

        # Check if response is SSE
        if 'text/event-stream' in r.headers.get('Content-Type', ''):
            # If the provider returned an error status with SSE content-type,
            # read the body and return a proper error response instead of
            # streaming the error back (which hides the error from logs).
            if r.status >= 400:
                error_body = await r.text()
                log.error(
                    'Provider returned HTTP %d with SSE content-type: %s',
                    r.status,
                    error_body[:1000],
                )
                try:
                    error_json = json.loads(error_body)
                    return JSONResponse(status_code=r.status, content=error_json)
                except json.JSONDecodeError:
                    return JSONResponse(
                        status_code=r.status,
                        content={'error': {'message': error_body, 'code': r.status}},
                    )

            streaming = True
            return StreamingResponse(
                stream_wrapper(r, content_handler=stream_chunks_handler),
                status_code=r.status,
                headers=_clean_proxy_headers(r.headers),
            )
        else:
            try:
                response = await r.json()
            except Exception as e:
                response_text = await r.text()
                if is_codex_web_auth:
                    parsed_response = parse_openai_codex_sse_response(response_text)
                    if parsed_response is not None:
                        if parsed_response.get('type') in ('response.failed', 'response.incomplete'):
                            response = build_openai_codex_error_payload(parsed_response)
                        else:
                            response = parsed_response
                    else:
                        log.error(e)
                        response = response_text
                else:
                    log.error(e)
                    response = response_text

            if r.status >= 400:
                if isinstance(response, (dict, list)):
                    return JSONResponse(status_code=r.status, content=response)
                else:
                    return PlainTextResponse(status_code=r.status, content=response)

            # Convert Responses API result to simple format
            if is_responses and isinstance(response, dict):
                response = convert_responses_result(response)

            return response
    except Exception as e:
        log.exception(e)

        raise HTTPException(
            status_code=r.status if r else 500,
            detail=ERROR_MESSAGES.SERVER_CONNECTION_ERROR,
        )
    finally:
        if not streaming:
            await cleanup_response(r)


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
    model_id = form_data.get('model')
    # Check if model is already in app state cache to avoid expensive get_all_models() call
    models = request.app.state.OPENAI_MODELS
    if not models or model_id not in models:
        await get_all_models(request, user=user)
        models = request.app.state.OPENAI_MODELS
    if model_id in models:
        idx = models[model_id]['urlIdx']

    url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
    key = request.app.state.config.OPENAI_API_KEYS[idx]
    api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
        str(idx),
        request.app.state.config.OPENAI_API_CONFIGS.get(url, {}),  # Legacy support
    )

    r = None
    streaming = False

    headers, cookies = await get_headers_and_cookies(request, url, key, api_config, user=user)

    if api_config.get('azure') or api_config.get('provider') == 'azure':
        # Only set api-key header if not using Azure Entra ID authentication
        auth_type = api_config.get('auth_type', 'bearer')
        if auth_type not in ('azure_ad', 'microsoft_entra_id'):
            headers['api-key'] = key

        # Azure v1 format: base URL already ends with /openai/v1,
        # model stays in the payload, no deployment URL rewriting.
        is_azure_v1 = bool(re.search(r'/openai/v1(?:/|$)', url))

        if is_azure_v1:
            embeddings_url = f'{url.rstrip("/")}/embeddings'
        else:
            api_version = api_config.get('api_version', '2023-03-15-preview')
            model = _sanitize_model_for_url(form_data.get('model', ''))
            embeddings_url = f'{url}/openai/deployments/{model}/embeddings?api-version={api_version}'
            headers['api-version'] = api_version
    else:
        embeddings_url = f'{url}/embeddings'

    try:
        session = await get_session()
        r = await session.request(
            method='POST',
            url=embeddings_url,
            data=body,
            headers=headers,
            cookies=cookies,
            timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT),
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        )

        if 'text/event-stream' in r.headers.get('Content-Type', ''):
            streaming = True
            return StreamingResponse(
                stream_wrapper(r),
                status_code=r.status,
                headers=_clean_proxy_headers(r.headers),
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
                    return PlainTextResponse(status_code=r.status, content=response_data)

            return response_data
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=r.status if r else 500,
            detail=ERROR_MESSAGES.SERVER_CONNECTION_ERROR,
        )
    finally:
        if not streaming:
            await cleanup_response(r)


class ResponsesForm(BaseModel):
    model_config = ConfigDict(extra='allow')

    model: str
    input: list | str | None = None
    instructions: str | None = None
    stream: bool | None = None
    temperature: float | None = None
    max_output_tokens: int | None = None
    top_p: float | None = None
    tools: list | None = None
    tool_choice: str | dict | None = None
    text: dict | None = None
    truncation: str | None = None
    metadata: dict | None = None
    store: bool | None = None
    reasoning: dict | None = None
    previous_response_id: str | None = None


@router.post('/responses')
async def responses(
    request: Request,
    form_data: ResponsesForm,
    user=Depends(get_verified_user),
):
    """
    Forward requests to the OpenAI Responses API endpoint.
    Routes to the correct upstream backend based on the model field.
    """
    payload = form_data.model_dump(exclude_none=True)

    idx = 0
    model_id = form_data.model

    # Enforce per-model access control
    await check_model_access(user, await Models.get_model_by_id(model_id), BYPASS_MODEL_ACCESS_CONTROL)

    body = json.dumps(payload)

    if model_id:
        models = request.app.state.OPENAI_MODELS
        if not models or model_id not in models:
            await get_all_models(request, user=user)
            models = request.app.state.OPENAI_MODELS
        if model_id in models:
            idx = models[model_id]['urlIdx']

    url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
    key = request.app.state.config.OPENAI_API_KEYS[idx]
    api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
        str(idx),
        request.app.state.config.OPENAI_API_CONFIGS.get(url, {}),  # Legacy support
    )

    r = None
    streaming = False

    try:
        headers, cookies = await get_headers_and_cookies(request, url, key, api_config, user=user)

        if is_openai_codex_web_auth_config(api_config):
            request_url = OPENAI_CODEX_API_ENDPOINT
        elif api_config.get('azure') or api_config.get('provider') == 'azure':
            auth_type = api_config.get('auth_type', 'bearer')
            if auth_type not in ('azure_ad', 'microsoft_entra_id'):
                headers['api-key'] = key

            is_azure_v1 = bool(re.search(r'/openai/v1(?:/|$)', url))

            if is_azure_v1:
                request_url = f'{url.rstrip("/")}/responses'
            else:
                api_version = api_config.get('api_version', '2023-03-15-preview')
                headers['api-version'] = api_version
                model = _sanitize_model_for_url(payload.get('model', ''))
                request_url = f'{url}/openai/deployments/{model}/responses?api-version={api_version}'
        else:
            request_url = f'{url}/responses'

        session = await get_session()
        r = await session.request(
            method='POST',
            url=request_url,
            data=body,
            headers=headers,
            cookies=cookies,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
            timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT),
        )

        # Check if response is SSE
        if 'text/event-stream' in r.headers.get('Content-Type', ''):
            streaming = True
            return StreamingResponse(
                stream_wrapper(r),
                status_code=r.status,
                headers=_clean_proxy_headers(r.headers),
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
                    return PlainTextResponse(status_code=r.status, content=response_data)

            return response_data

    except HTTPException:
        raise
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=r.status if r else 500,
            detail=ERROR_MESSAGES.SERVER_CONNECTION_ERROR,
        )
    finally:
        if not streaming:
            await cleanup_response(r)


@router.api_route('/{path:path}', methods=['GET', 'POST', 'PUT', 'DELETE'])
async def proxy(path: str, request: Request, user=Depends(get_verified_user)):
    """
    Deprecated: proxy all requests to OpenAI API.
    Disabled by default. Set ENABLE_OPENAI_API_PASSTHROUGH=True to enable.
    """

    if not ENABLE_OPENAI_API_PASSTHROUGH:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Direct API passthrough is disabled. Set ENABLE_OPENAI_API_PASSTHROUGH=True to enable.',
        )

    body = await request.body()

    # Parse JSON body to resolve model-based routing
    payload = None
    if body:
        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, ValueError):
            payload = None

    idx = 0
    model_id = payload.get('model') if isinstance(payload, dict) else None
    if model_id:
        models = request.app.state.OPENAI_MODELS
        if not models or model_id not in models:
            await get_all_models(request, user=user)
            models = request.app.state.OPENAI_MODELS
        if model_id in models:
            idx = models[model_id]['urlIdx']

    url = request.app.state.config.OPENAI_API_BASE_URLS[idx]
    key = request.app.state.config.OPENAI_API_KEYS[idx]
    api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
        str(idx),
        request.app.state.config.OPENAI_API_CONFIGS.get(
            request.app.state.config.OPENAI_API_BASE_URLS[idx], {}
        ),  # Legacy support
    )

    r = None
    streaming = False

    try:
        headers, cookies = await get_headers_and_cookies(request, url, key, api_config, user=user)

        if api_config.get('azure') or api_config.get('provider') == 'azure':
            # Only set api-key header if not using Azure Entra ID authentication
            auth_type = api_config.get('auth_type', 'bearer')
            if auth_type not in ('azure_ad', 'microsoft_entra_id'):
                headers['api-key'] = key

            is_azure_v1 = bool(re.search(r'/openai/v1(?:/|$)', url))

            if is_azure_v1:
                qs = request.url.query
                request_url = f'{url.rstrip("/")}/{path}' + (f'?{qs}' if qs else '')
            else:
                api_version = api_config.get('api_version', '2023-03-15-preview')
                headers['api-version'] = api_version

                payload = json.loads(body)
                url, payload = convert_to_azure_payload(url, payload, api_version)
                body = json.dumps(payload).encode()

                request_url = f'{url}/{path}?api-version={api_version}'
        else:
            request_url = f'{url}/{path}'

        session = await get_session()
        r = await session.request(
            method=request.method,
            url=request_url,
            data=body,
            headers=headers,
            cookies=cookies,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
            timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT),
        )

        # Check if response is SSE
        if 'text/event-stream' in r.headers.get('Content-Type', ''):
            streaming = True
            return StreamingResponse(
                stream_wrapper(r),
                status_code=r.status,
                headers=_clean_proxy_headers(r.headers),
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
                    return PlainTextResponse(status_code=r.status, content=response_data)

            return response_data

    except HTTPException:
        raise
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=r.status if r else 500,
            detail='Open WebUI: Server Connection Error',
        )
    finally:
        if not streaming:
            await cleanup_response(r)
