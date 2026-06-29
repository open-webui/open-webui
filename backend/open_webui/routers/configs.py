from __future__ import annotations

import copy
import logging
from typing import Optional

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request
from mcp.shared.auth import OAuthMetadata
from open_webui.config import BannerModel
from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL, AIOHTTP_CLIENT_TIMEOUT
from open_webui.events import EVENTS, publish_event
from open_webui.models.config import Config
from open_webui.models.oauth_sessions import OAuthSessions
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.headers import get_custom_headers
from open_webui.utils.mcp.client import MCPClient
from open_webui.utils.oauth import (
    OAuthClientInformationFull,
    apply_connection_oauth_options,
    decrypt_data,
    encrypt_data,
    get_discovery_urls,
    get_oauth_client_info_with_dynamic_client_registration,
    get_oauth_client_info_with_static_credentials,
    recover_static_oauth_client_metadata,
    resolve_oauth_client_info,
)
from open_webui.utils.tools import (
    bearer_auth_header,
    get_tool_server_data,
    get_tool_server_url,
    set_terminal_servers,
    set_tool_servers,
)
from pydantic import BaseModel, ConfigDict

router = APIRouter()

log = logging.getLogger(__name__)

CONNECTIONS_CONFIG_KEYS = {
    'ENABLE_DIRECT_CONNECTIONS': 'direct.enable',
    'ENABLE_BASE_MODELS_CACHE': 'models.base_models_cache',
}
CODE_EXECUTION_CONFIG_KEYS = {
    'ENABLE_CODE_EXECUTION': 'code_execution.enable',
    'CODE_EXECUTION_ENGINE': 'code_execution.engine',
    'CODE_EXECUTION_JUPYTER_URL': 'code_execution.jupyter.url',
    'CODE_EXECUTION_JUPYTER_AUTH': 'code_execution.jupyter.auth',
    'CODE_EXECUTION_JUPYTER_AUTH_TOKEN': 'code_execution.jupyter.auth_token',
    'CODE_EXECUTION_JUPYTER_AUTH_PASSWORD': 'code_execution.jupyter.auth_password',
    'CODE_EXECUTION_JUPYTER_TIMEOUT': 'code_execution.jupyter.timeout',
    'ENABLE_CODE_INTERPRETER': 'code_interpreter.enable',
    'CODE_INTERPRETER_ENGINE': 'code_interpreter.engine',
    'CODE_INTERPRETER_PROMPT_TEMPLATE': 'code_interpreter.prompt_template',
    'CODE_INTERPRETER_JUPYTER_URL': 'code_interpreter.jupyter.url',
    'CODE_INTERPRETER_JUPYTER_AUTH': 'code_interpreter.jupyter.auth',
    'CODE_INTERPRETER_JUPYTER_AUTH_TOKEN': 'code_interpreter.jupyter.auth_token',
    'CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD': 'code_interpreter.jupyter.auth_password',
    'CODE_INTERPRETER_JUPYTER_TIMEOUT': 'code_interpreter.jupyter.timeout',
}
MODELS_CONFIG_KEYS = {
    'DEFAULT_MODELS': 'ui.default_models',
    'DEFAULT_PINNED_MODELS': 'ui.default_pinned_models',
    'MODEL_ORDER_LIST': 'ui.model_order_list',
    'DEFAULT_MODEL_METADATA': 'models.default_metadata',
    'DEFAULT_MODEL_PARAMS': 'models.default_params',
}


async def get_config_values(key_map: dict[str, str]) -> dict:
    values = await Config.get_many(*key_map.values())
    return {field: values[storage_key] for field, storage_key in key_map.items() if storage_key in values}


def config_updates(data: dict, key_map: dict[str, str]) -> dict:
    return {key_map[field]: value for field, value in data.items() if field in key_map}


############################
# ImportConfig
# Thy configuration come, thy settings be done,
# in production as it is in development.
############################


class ImportConfigForm(BaseModel):
    config: dict


@router.post('/import', response_model=dict)
async def import_config(request: Request, form_data: ImportConfigForm, user=Depends(get_admin_user)):
    await Config.upsert(form_data.config)
    await publish_event(
        request,
        EVENTS.CONFIG_IMPORTED,
        actor=user,
        subject_id='import',
        data={'keys': list(form_data.config.keys())},
    )
    return await Config.get_all()


############################
# ExportConfig
############################


@router.get('/export', response_model=dict)
async def export_config(user=Depends(get_admin_user)):
    return await Config.get_all()


@router.get('/namespace/{namespace}', response_model=dict)
async def get_config_namespace(namespace: str, user=Depends(get_admin_user)):
    return await Config.get_namespace(namespace)


############################
# Connections Config
############################


class ConnectionsConfigForm(BaseModel):
    ENABLE_DIRECT_CONNECTIONS: bool
    ENABLE_BASE_MODELS_CACHE: bool


@router.get('/connections', response_model=ConnectionsConfigForm)
async def get_connections_config(request: Request, user=Depends(get_admin_user)):
    return await get_config_values(CONNECTIONS_CONFIG_KEYS)


@router.post('/connections', response_model=ConnectionsConfigForm)
async def set_connections_config(
    request: Request,
    form_data: ConnectionsConfigForm,
    user=Depends(get_admin_user),
):
    await Config.upsert(config_updates(form_data.model_dump(), CONNECTIONS_CONFIG_KEYS))
    values = await get_config_values(CONNECTIONS_CONFIG_KEYS)
    await publish_event(
        request,
        EVENTS.CONFIG_CONNECTIONS_UPDATED,
        actor=user,
        subject_id='connections',
        subject_type='config',
        data=values,
    )
    return values


class OAuthClientRegistrationForm(BaseModel):
    url: str
    client_id: str
    client_name: str | None = None
    client_secret: str | None = None
    oauth_server_url: str | None = None
    oauth_scope: str | None = None


@router.post('/oauth/clients/register')
async def register_oauth_client(
    request: Request,
    form_data: OAuthClientRegistrationForm,
    type: str | None = None,
    user=Depends(get_admin_user),
):
    try:
        oauth_client_id = form_data.client_id
        if type:
            oauth_client_id = f'{type}:{form_data.client_id}'

        oauth_server_url = form_data.oauth_server_url if form_data.oauth_server_url else form_data.url

        if form_data.client_secret:
            # Static credentials: skip dynamic registration, build from provided credentials
            oauth_client_info = await get_oauth_client_info_with_static_credentials(
                request,
                oauth_client_id,
                oauth_server_url,
                oauth_client_id=form_data.client_id,
                oauth_client_secret=form_data.client_secret,
                oauth_scope=form_data.oauth_scope,
            )
        else:
            oauth_client_info = await get_oauth_client_info_with_dynamic_client_registration(
                request, oauth_client_id, oauth_server_url, oauth_scope=form_data.oauth_scope
            )
        return {
            'status': True,
            'oauth_client_info': encrypt_data(oauth_client_info.model_dump(mode='json')),
        }
    except Exception as e:
        log.debug(f'Failed to register OAuth client: {e}')
        raise HTTPException(
            status_code=400,
            detail=f'Failed to register OAuth client',
        )


############################
# ToolServers Config
############################


class ToolServerConnection(BaseModel):
    url: str
    path: str
    type: str | None = 'openapi'  # openapi, mcp
    auth_type: str | None
    headers: dict | str | None = None
    key: str | None
    config: dict | None
    info: dict | None = None

    model_config = ConfigDict(extra='allow')


class ToolServersConfigForm(BaseModel):
    TOOL_SERVER_CONNECTIONS: list[ToolServerConnection]


@router.get('/tool_servers', response_model=ToolServersConfigForm)
async def get_tool_servers_config(request: Request, user=Depends(get_admin_user)):
    return {'TOOL_SERVER_CONNECTIONS': await Config.get('tool_server.connections')}


@router.post('/tool_servers', response_model=ToolServersConfigForm)
async def set_tool_servers_config(
    request: Request,
    form_data: ToolServersConfigForm,
    user=Depends(get_admin_user),
):
    existing_connections = await Config.get('tool_server.connections', []) or []
    for connection in existing_connections:
        server_type = connection.get('type', 'openapi')
        auth_type = connection.get('auth_type', 'none')

        if auth_type in ('oauth_2.1', 'oauth_2.1_static'):
            # Remove existing OAuth clients for tool servers
            server_id = (connection.get('info') or {}).get('id')
            client_key = f'{server_type}:{server_id}'

            try:
                request.app.state.oauth_client_manager.remove_client(client_key)
            except Exception:
                pass

    # Set new tool server connections
    connections = [connection.model_dump() for connection in form_data.TOOL_SERVER_CONNECTIONS]
    await Config.upsert({'tool_server.connections': connections})

    await set_tool_servers(request)

    for connection in connections:
        server_type = connection.get('type', 'openapi')
        if server_type == 'mcp':
            server_id = (connection.get('info') or {}).get('id')
            auth_type = connection.get('auth_type', 'none')

            if auth_type in ('oauth_2.1', 'oauth_2.1_static') and server_id:
                try:
                    oauth_client_info = resolve_oauth_client_info(connection)
                    oauth_client_info = await recover_static_oauth_client_metadata(connection, oauth_client_info)
                    oauth_client_info = apply_connection_oauth_options(connection, oauth_client_info)
                    request.app.state.oauth_client_manager.add_client(
                        f'{server_type}:{server_id}',
                        OAuthClientInformationFull(**oauth_client_info),
                    )
                except Exception as e:
                    log.debug(f'Failed to add OAuth client for MCP tool server: {e}')
                    continue

    await publish_event(
        request,
        EVENTS.CONFIG_TOOL_SERVERS_UPDATED,
        actor=user,
        subject_id='tool_server.connections',
        subject_type='config',
        data={'count': len(connections), 'types': [connection.get('type', 'openapi') for connection in connections]},
    )
    return {'TOOL_SERVER_CONNECTIONS': connections}


class TerminalServerConnection(BaseModel):
    id: str | None = ''
    name: str | None = ''

    enabled: bool | None = True

    url: str
    path: str | None = '/openapi.json'

    key: str | None = ''
    auth_type: str | None = 'bearer'

    config: dict | None = None

    # Orchestrator policy fields
    server_type: str | None = None  # "orchestrator", "terminal"
    policy_id: str | None = None
    policy: dict | None = None  # cached policy data

    model_config = ConfigDict(extra='allow')


class TerminalServersConfigForm(BaseModel):
    TERMINAL_SERVER_CONNECTIONS: list[TerminalServerConnection]


@router.get('/terminal_servers')
async def get_terminal_servers_config(request: Request, user=Depends(get_admin_user)):
    return {'TERMINAL_SERVER_CONNECTIONS': await Config.get('terminal_server.connections')}


@router.post('/terminal_servers')
async def set_terminal_servers_config(
    request: Request,
    form_data: TerminalServersConfigForm,
    user=Depends(get_admin_user),
):
    connections = [connection.model_dump() for connection in form_data.TERMINAL_SERVER_CONNECTIONS]
    await Config.upsert({'terminal_server.connections': connections})

    await set_terminal_servers(request)

    await publish_event(
        request,
        EVENTS.CONFIG_TERMINAL_SERVERS_UPDATED,
        actor=user,
        subject_id='terminal_server.connections',
        subject_type='config',
        data={'count': len(connections)},
    )
    return {'TERMINAL_SERVER_CONNECTIONS': connections}


@router.post('/terminal_servers/verify')
async def verify_terminal_server_connection(
    request: Request, form_data: TerminalServerConnection, user=Depends(get_admin_user)
):
    """
    Verify the connection to a terminal server by detecting its type.

    Tries GET {url}/api/v1/policies (orchestrator) then GET {url}/api/config
    (plain terminal).  Returns ``{status: true, type: "orchestrator"|"terminal"}``.
    """
    base_url = (form_data.url or '').rstrip('/')
    if not base_url:
        raise HTTPException(status_code=400, detail='Terminal server URL is required')

    headers = {}
    if form_data.auth_type == 'bearer' and form_data.key:
        headers.update(bearer_auth_header(form_data.key))

    try:
        async with aiohttp.ClientSession(
            trust_env=True,
            timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT),
        ) as session:
            # Orchestrators expose a policies API; plain terminals don't.
            try:
                async with session.get(
                    f'{base_url}/api/v1/policies', headers=headers, ssl=AIOHTTP_CLIENT_SESSION_SSL
                ) as resp:
                    if resp.ok:
                        return {'status': True, 'type': 'orchestrator'}
            except Exception:
                pass

            # Fall back to open-terminal config endpoint.
            try:
                async with session.get(
                    f'{base_url}/api/config', headers=headers, ssl=AIOHTTP_CLIENT_SESSION_SSL
                ) as resp:
                    if resp.ok:
                        return {'status': True, 'type': 'terminal'}
            except Exception:
                pass

    except Exception as e:
        log.debug(f'Failed to connect to the terminal server: {e}')

    raise HTTPException(status_code=400, detail='Failed to connect to the terminal server')


class TerminalServerPolicyForm(BaseModel):
    url: str
    key: str | None = ''
    auth_type: str | None = 'bearer'
    policy_id: str
    policy_data: dict


class TerminalServerLifecycleForm(BaseModel):
    url: str
    key: str | None = ''
    auth_type: str | None = 'bearer'
    policy_id: str
    lifecycle_data: dict


class TerminalServerRefreshForm(BaseModel):
    url: str
    key: str | None = ''
    auth_type: str | None = 'bearer'
    user_id: str | None = None
    policy_id: str | None = None
    only_idle: bool = True
    reset: bool = False


@router.post('/terminal_servers/policy')
async def put_terminal_server_policy(
    request: Request, form_data: TerminalServerPolicyForm, user=Depends(get_admin_user)
):
    """
    Proxy a policy PUT to an orchestrator terminal server.
    """
    base_url = (form_data.url or '').rstrip('/')
    if not base_url:
        raise HTTPException(status_code=400, detail='Terminal server URL is required')

    headers = {'Content-Type': 'application/json'}
    if form_data.auth_type == 'bearer' and form_data.key:
        headers.update(bearer_auth_header(form_data.key))

    try:
        async with aiohttp.ClientSession(
            trust_env=True,
            timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT),
        ) as session:
            policy_url = f'{base_url}/api/v1/policies/{form_data.policy_id}'
            async with session.put(
                policy_url, headers=headers, json=form_data.policy_data, ssl=AIOHTTP_CLIENT_SESSION_SSL
            ) as resp:
                if resp.ok:
                    return await resp.json()
                detail = await resp.text()
                raise HTTPException(status_code=resp.status, detail=detail)
    except HTTPException:
        raise
    except Exception as e:
        log.debug(f'Failed to save policy to terminal server: {e}')
        raise HTTPException(status_code=400, detail='Failed to save policy to terminal server')


@router.post('/terminal_servers/lifecycle')
async def put_terminal_server_lifecycle(
    request: Request, form_data: TerminalServerLifecycleForm, user=Depends(get_admin_user)
):
    """
    Proxy a policy lifecycle PUT to an orchestrator terminal server.
    """
    base_url = (form_data.url or '').rstrip('/')
    if not base_url:
        raise HTTPException(status_code=400, detail='Terminal server URL is required')

    headers = {'Content-Type': 'application/json'}
    if form_data.auth_type == 'bearer' and form_data.key:
        headers.update(bearer_auth_header(form_data.key))

    try:
        async with aiohttp.ClientSession(
            trust_env=True,
            timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT),
        ) as session:
            lifecycle_url = f'{base_url}/api/v1/policies/{form_data.policy_id}/lifecycle'
            async with session.put(
                lifecycle_url,
                headers=headers,
                json=form_data.lifecycle_data,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as resp:
                if resp.ok:
                    return await resp.json()
                detail = await resp.text()
                raise HTTPException(status_code=resp.status, detail=detail)
    except HTTPException:
        raise
    except Exception as e:
        log.debug(f'Failed to save lifecycle to terminal server: {e}')
        raise HTTPException(status_code=400, detail='Failed to save lifecycle to terminal server')


@router.post('/terminal_servers/refresh')
async def refresh_terminal_server_terminals(
    request: Request, form_data: TerminalServerRefreshForm, user=Depends(get_admin_user)
):
    """
    Proxy a terminal refresh request to an orchestrator terminal server.
    """
    base_url = (form_data.url or '').rstrip('/')
    if not base_url:
        raise HTTPException(status_code=400, detail='Terminal server URL is required')

    headers = {'Content-Type': 'application/json'}
    if form_data.auth_type == 'bearer' and form_data.key:
        headers.update(bearer_auth_header(form_data.key))

    body = {
        'only_idle': form_data.only_idle,
        'reset': form_data.reset,
    }
    if form_data.user_id:
        body['user_id'] = form_data.user_id
    if form_data.policy_id:
        body['policy_id'] = form_data.policy_id

    try:
        async with aiohttp.ClientSession(
            trust_env=True,
            timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT),
        ) as session:
            refresh_url = f'{base_url}/api/v1/terminals/refresh'
            async with session.post(
                refresh_url,
                headers=headers,
                json=body,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as resp:
                if resp.ok:
                    return await resp.json()
                detail = await resp.text()
                raise HTTPException(status_code=resp.status, detail=detail)
    except HTTPException:
        raise
    except Exception as e:
        log.debug(f'Failed to refresh terminals: {e}')
        raise HTTPException(status_code=400, detail='Failed to refresh terminals')


@router.post('/tool_servers/verify')
async def verify_tool_servers_config(request: Request, form_data: ToolServerConnection, user=Depends(get_admin_user)):
    """
    Verify the connection to the tool server.
    """
    try:
        if form_data.type == 'mcp':
            if form_data.auth_type in ('oauth_2.1', 'oauth_2.1_static'):
                oauth_server_url = (
                    form_data.info.get('oauth_server_url')
                    if form_data.info and form_data.info.get('oauth_server_url')
                    else form_data.url
                )
                discovery_urls = await get_discovery_urls(oauth_server_url)
                for discovery_url in discovery_urls:
                    log.debug(f'Trying to fetch OAuth 2.1 discovery document from {discovery_url}')
                    async with aiohttp.ClientSession(
                        trust_env=True,
                        timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT),
                    ) as session:
                        async with session.get(
                            discovery_url, ssl=AIOHTTP_CLIENT_SESSION_SSL
                        ) as oauth_server_metadata_response:
                            if oauth_server_metadata_response.status == 200:
                                try:
                                    oauth_server_metadata = OAuthMetadata.model_validate(
                                        await oauth_server_metadata_response.json()
                                    )
                                    return {
                                        'status': True,
                                        'oauth_server_metadata': oauth_server_metadata.model_dump(mode='json'),
                                    }
                                except Exception as e:
                                    log.info(f'Failed to parse OAuth 2.1 discovery document: {e}')
                                    raise HTTPException(
                                        status_code=400,
                                        detail=f'Failed to parse OAuth 2.1 discovery document from {discovery_url}',
                                    )

                raise HTTPException(
                    status_code=400,
                    detail=f'Failed to fetch OAuth 2.1 discovery document from {discovery_urls}',
                )
            else:
                try:
                    client = MCPClient()
                    headers = None

                    token = None
                    if form_data.auth_type == 'bearer':
                        token = form_data.key
                    elif form_data.auth_type == 'session':
                        token = request.state.token.credentials
                    elif form_data.auth_type == 'system_oauth':
                        oauth_token = None
                        try:
                            if request.cookies.get('oauth_session_id', None):
                                oauth_token = await request.app.state.oauth_manager.get_oauth_token(
                                    user.id,
                                    request.cookies.get('oauth_session_id', None),
                                )

                                if oauth_token:
                                    token = oauth_token.get('access_token', '')
                        except Exception as e:
                            pass
                    if token:
                        headers = {'Authorization': f'Bearer {token}'}

                    if form_data.headers and isinstance(form_data.headers, dict):
                        if headers is None:
                            headers = {}
                        custom_headers = get_custom_headers(form_data.headers, user)
                        headers.update(custom_headers)

                    await client.connect(form_data.url, headers=headers)
                    specs = await client.list_tool_specs()
                    return {
                        'status': True,
                        'specs': specs,
                    }
                except Exception as e:
                    log.debug(f'Failed to create MCP client: {e}')
                    raise HTTPException(
                        status_code=400,
                        detail=f'Failed to create MCP client',
                    )
                finally:
                    if client:
                        await client.disconnect()
        else:  # openapi
            token = None
            headers = None
            if form_data.auth_type == 'bearer':
                token = form_data.key
            elif form_data.auth_type == 'session':
                token = request.state.token.credentials
            elif form_data.auth_type == 'system_oauth':
                try:
                    if request.cookies.get('oauth_session_id', None):
                        oauth_token = await request.app.state.oauth_manager.get_oauth_token(
                            user.id,
                            request.cookies.get('oauth_session_id', None),
                        )

                        if oauth_token:
                            token = oauth_token.get('access_token', '')

                except Exception as e:
                    pass

            if token:
                headers = {'Authorization': f'Bearer {token}'}

            if form_data.headers and isinstance(form_data.headers, dict):
                if headers is None:
                    headers = {}
                custom_headers = get_custom_headers(form_data.headers, user)
                headers.update(custom_headers)

            url = get_tool_server_url(form_data.url, form_data.path)
            return await get_tool_server_data(url, headers=headers)
    except HTTPException as e:
        raise e
    except Exception as e:
        log.debug(f'Failed to connect to the tool server: {e}')
        raise HTTPException(
            status_code=400,
            detail=f'Failed to connect to the tool server',
        )


############################
# CodeInterpreterConfig
############################
class CodeInterpreterConfigForm(BaseModel):
    ENABLE_CODE_EXECUTION: bool
    CODE_EXECUTION_ENGINE: str
    CODE_EXECUTION_JUPYTER_URL: str | None
    CODE_EXECUTION_JUPYTER_AUTH: str | None
    CODE_EXECUTION_JUPYTER_AUTH_TOKEN: str | None
    CODE_EXECUTION_JUPYTER_AUTH_PASSWORD: str | None
    CODE_EXECUTION_JUPYTER_TIMEOUT: int | None
    ENABLE_CODE_INTERPRETER: bool
    CODE_INTERPRETER_ENGINE: str
    CODE_INTERPRETER_PROMPT_TEMPLATE: str | None
    CODE_INTERPRETER_JUPYTER_URL: str | None
    CODE_INTERPRETER_JUPYTER_AUTH: str | None
    CODE_INTERPRETER_JUPYTER_AUTH_TOKEN: str | None
    CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD: str | None
    CODE_INTERPRETER_JUPYTER_TIMEOUT: int | None


@router.get('/code_execution', response_model=CodeInterpreterConfigForm)
async def get_code_execution_config(request: Request, user=Depends(get_admin_user)):
    return await get_config_values(CODE_EXECUTION_CONFIG_KEYS)


@router.post('/code_execution', response_model=CodeInterpreterConfigForm)
async def set_code_execution_config(
    request: Request, form_data: CodeInterpreterConfigForm, user=Depends(get_admin_user)
):
    await Config.upsert(config_updates(form_data.model_dump(), CODE_EXECUTION_CONFIG_KEYS))
    values = await get_config_values(CODE_EXECUTION_CONFIG_KEYS)
    await publish_event(
        request,
        EVENTS.CONFIG_CODE_EXECUTION_UPDATED,
        actor=user,
        subject_id='code_execution',
        subject_type='config',
        data={
            'code_execution_enabled': values.get('ENABLE_CODE_EXECUTION'),
            'code_execution_engine': values.get('CODE_EXECUTION_ENGINE'),
            'code_interpreter_enabled': values.get('ENABLE_CODE_INTERPRETER'),
            'code_interpreter_engine': values.get('CODE_INTERPRETER_ENGINE'),
        },
    )
    return values


############################
# SetDefaultModels
############################
class ModelsConfigForm(BaseModel):
    DEFAULT_MODELS: str | None
    DEFAULT_PINNED_MODELS: str | None
    MODEL_ORDER_LIST: list[str | None]
    DEFAULT_MODEL_METADATA: dict | None = None
    DEFAULT_MODEL_PARAMS: dict | None = None


@router.get('/models/defaults')
async def get_models_defaults(request: Request, user=Depends(get_verified_user)):
    return {
        'DEFAULT_MODEL_METADATA': await Config.get('models.default_metadata'),
    }


@router.get('/models', response_model=ModelsConfigForm)
async def get_models_config(request: Request, user=Depends(get_admin_user)):
    return await get_config_values(MODELS_CONFIG_KEYS)


@router.post('/models', response_model=ModelsConfigForm)
async def set_models_config(request: Request, form_data: ModelsConfigForm, user=Depends(get_admin_user)):
    await Config.upsert(config_updates(form_data.model_dump(), MODELS_CONFIG_KEYS))
    values = await get_config_values(MODELS_CONFIG_KEYS)
    await publish_event(
        request,
        EVENTS.CONFIG_MODELS_UPDATED,
        actor=user,
        subject_id='models',
        subject_type='config',
        data={
            'default_models': values.get('DEFAULT_MODELS'),
            'default_pinned_models': values.get('DEFAULT_PINNED_MODELS'),
            'model_order_count': len(values.get('MODEL_ORDER_LIST') or []),
        },
    )
    return values


class PromptSuggestion(BaseModel):
    title: list[str]
    content: str


class SetDefaultSuggestionsForm(BaseModel):
    suggestions: list[PromptSuggestion]


@router.post('/suggestions', response_model=list[PromptSuggestion])
async def set_default_suggestions(
    request: Request,
    form_data: SetDefaultSuggestionsForm,
    user=Depends(get_admin_user),
):
    data = form_data.model_dump()
    await Config.upsert({'ui.prompt_suggestions': data['suggestions']})
    suggestions = await Config.get('ui.prompt_suggestions')
    await publish_event(
        request,
        EVENTS.CONFIG_SUGGESTIONS_UPDATED,
        actor=user,
        subject_id='ui.prompt_suggestions',
        subject_type='config',
        data={'count': len(suggestions or [])},
    )
    return suggestions


############################
# SetBanners
############################


class SetBannersForm(BaseModel):
    banners: list[BannerModel]


@router.post('/banners', response_model=list[BannerModel])
async def set_banners(
    request: Request,
    form_data: SetBannersForm,
    user=Depends(get_admin_user),
):
    data = form_data.model_dump()
    await Config.upsert({'ui.banners': data['banners']})
    banners = await Config.get('ui.banners')
    await publish_event(
        request,
        EVENTS.CONFIG_BANNERS_UPDATED,
        actor=user,
        subject_id='ui.banners',
        subject_type='config',
        data={'count': len(banners or [])},
    )
    return banners


@router.get('/banners', response_model=list[BannerModel])
async def get_banners(
    request: Request,
    user=Depends(get_verified_user),
):
    return await Config.get('ui.banners')
