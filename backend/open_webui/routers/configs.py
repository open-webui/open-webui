import logging
import copy
from fastapi import APIRouter, Depends, Request, HTTPException, Query
from pydantic import BaseModel, ConfigDict
import aiohttp
import httpx
from urllib.parse import urlparse

from typing import Optional

from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL, AIOHTTP_CLIENT_TIMEOUT
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.headers import get_custom_headers
from open_webui.config import get_config, save_config, async_save_config
from open_webui.config import BannerModel

from open_webui.utils.tools import (
    get_tool_server_data,
    get_tool_server_url,
    set_tool_servers,
    set_terminal_servers,
)
from open_webui.utils.mcp.client import MCPClient
from open_webui.models.oauth_sessions import OAuthSessions

from open_webui.services.gitlab import create_gitlab_client
from open_webui.retrieval.vector.async_client import ASYNC_VECTOR_DB_CLIENT

import json
import os
import uuid
from datetime import datetime


from open_webui.utils.oauth import (
    get_discovery_urls,
    get_oauth_client_info_with_dynamic_client_registration,
    get_oauth_client_info_with_static_credentials,
    encrypt_data,
    decrypt_data,
    resolve_oauth_client_info,
    OAuthClientInformationFull,
)
from mcp.shared.auth import OAuthMetadata

router = APIRouter()

log = logging.getLogger(__name__)


############################
# ImportConfig
# Thy configuration come, thy settings be done,
# in production as it is in development.
############################


class ImportConfigForm(BaseModel):
    config: dict


@router.post('/import', response_model=dict)
async def import_config(request: Request, form_data: ImportConfigForm, user=Depends(get_admin_user)):
    await async_save_config(form_data.config)
    request.app.state.config._sync_to_redis()
    return get_config()


############################
# ExportConfig
############################


@router.get('/export', response_model=dict)
async def export_config(user=Depends(get_admin_user)):
    return get_config()


############################
# Connections Config
############################


class ConnectionsConfigForm(BaseModel):
    ENABLE_DIRECT_CONNECTIONS: bool
    ENABLE_BASE_MODELS_CACHE: bool


@router.get('/connections', response_model=ConnectionsConfigForm)
async def get_connections_config(request: Request, user=Depends(get_admin_user)):
    return {
        'ENABLE_DIRECT_CONNECTIONS': request.app.state.config.ENABLE_DIRECT_CONNECTIONS,
        'ENABLE_BASE_MODELS_CACHE': request.app.state.config.ENABLE_BASE_MODELS_CACHE,
    }


@router.post('/connections', response_model=ConnectionsConfigForm)
async def set_connections_config(
    request: Request,
    form_data: ConnectionsConfigForm,
    user=Depends(get_admin_user),
):
    request.app.state.config.ENABLE_DIRECT_CONNECTIONS = form_data.ENABLE_DIRECT_CONNECTIONS
    request.app.state.config.ENABLE_BASE_MODELS_CACHE = form_data.ENABLE_BASE_MODELS_CACHE

    return {
        'ENABLE_DIRECT_CONNECTIONS': request.app.state.config.ENABLE_DIRECT_CONNECTIONS,
        'ENABLE_BASE_MODELS_CACHE': request.app.state.config.ENABLE_BASE_MODELS_CACHE,
    }


class OAuthClientRegistrationForm(BaseModel):
    url: str
    client_id: str
    client_name: Optional[str] = None
    client_secret: Optional[str] = None
    oauth_server_url: Optional[str] = None


@router.post('/oauth/clients/register')
async def register_oauth_client(
    request: Request,
    form_data: OAuthClientRegistrationForm,
    type: Optional[str] = None,
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
            )
        else:
            oauth_client_info = await get_oauth_client_info_with_dynamic_client_registration(
                request, oauth_client_id, oauth_server_url
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
    type: Optional[str] = 'openapi'  # openapi, mcp
    auth_type: Optional[str]
    headers: Optional[dict | str] = None
    key: Optional[str]
    config: Optional[dict]
    info: Optional[dict] = None

    model_config = ConfigDict(extra='allow')


class ToolServersConfigForm(BaseModel):
    TOOL_SERVER_CONNECTIONS: list[ToolServerConnection]


@router.get('/tool_servers', response_model=ToolServersConfigForm)
async def get_tool_servers_config(request: Request, user=Depends(get_admin_user)):
    return {
        'TOOL_SERVER_CONNECTIONS': request.app.state.config.TOOL_SERVER_CONNECTIONS,
    }


@router.post('/tool_servers', response_model=ToolServersConfigForm)
async def set_tool_servers_config(
    request: Request,
    form_data: ToolServersConfigForm,
    user=Depends(get_admin_user),
):
    for connection in request.app.state.config.TOOL_SERVER_CONNECTIONS:
        server_type = connection.get('type', 'openapi')
        auth_type = connection.get('auth_type', 'none')

        if auth_type in ('oauth_2.1', 'oauth_2.1_static'):
            server_id = connection.get('info', {}).get('id')
            client_key = f'{server_type}:{server_id}'

            try:
                request.app.state.oauth_client_manager.remove_client(client_key)
            except Exception:
                pass

    request.app.state.config.TOOL_SERVER_CONNECTIONS = [
        connection.model_dump() for connection in form_data.TOOL_SERVER_CONNECTIONS
    ]

    await set_tool_servers(request)

    for connection in request.app.state.config.TOOL_SERVER_CONNECTIONS:
        server_type = connection.get('type', 'openapi')
        if server_type == 'mcp':
            server_id = connection.get('info', {}).get('id')
            auth_type = connection.get('auth_type', 'none')

            if auth_type in ('oauth_2.1', 'oauth_2.1_static') and server_id:
                try:
                    oauth_client_info = resolve_oauth_client_info(connection)
                    request.app.state.oauth_client_manager.add_client(
                        f'{server_type}:{server_id}',
                        OAuthClientInformationFull(**oauth_client_info),
                    )
                except Exception as e:
                    log.debug(f'Failed to add OAuth client for MCP tool server: {e}')
                    continue

    return {
        'TOOL_SERVER_CONNECTIONS': request.app.state.config.TOOL_SERVER_CONNECTIONS,
    }


############################
# GitLab Config
############################


class GitLabConnection(BaseModel):
    id: Optional[str] = None
    name: str
    url: str
    token: Optional[str] = None
    owner: Optional[str] = None
    repo: Optional[str] = None
    branch: Optional[str] = None
    wiki_only: Optional[bool] = False
    file_types: Optional[str] = None
    include_wiki: Optional[bool] = False
    exclude_patterns: Optional[str] = None
    enabled: Optional[bool] = True
    auto_sync: Optional[bool] = False
    selected_projects: Optional[list[str]] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(extra='allow')


class GitLabConfigForm(BaseModel):
    GITLAB_CONNECTIONS: list[GitLabConnection]


@router.get('/gitlab', response_model=GitLabConfigForm)
async def get_gitlab_config(request: Request, user=Depends(get_admin_user)):
    return {
        'GITLAB_CONNECTIONS': request.app.state.config.GITLAB_CONNECTIONS,
    }


@router.post('/gitlab', response_model=GitLabConfigForm)
async def set_gitlab_config(
    request: Request,
    form_data: GitLabConfigForm,
    user=Depends(get_admin_user),
):
    old_connections = request.app.state.config.GITLAB_CONNECTIONS
    old_by_id = {c.get('id'): c for c in old_connections if c.get('id')}

    connections = []
    for connection in form_data.GITLAB_CONNECTIONS:
        conn_dict = connection.model_dump()
        if not conn_dict.get('id'):
            conn_dict['id'] = str(uuid.uuid4())
        if not conn_dict.get('created_at'):
            conn_dict['created_at'] = datetime.now().isoformat()
        if conn_dict.get('token'):
            token = conn_dict['token']
            # Check if token is already encrypted (already stored previously)
            try:
                decrypted = decrypt_data(token)
                if isinstance(decrypted, str) and decrypted.startswith('glpat-'):
                    # Already encrypted and valid, keep it
                    pass
                else:
                    # Not a gitlab token after decrypt, might be plaintext
                    conn_dict['token'] = encrypt_data(token)
            except Exception:
                # Decryption failed = plaintext, encrypt it
                conn_dict['token'] = encrypt_data(token)
        connections.append(conn_dict)

    request.app.state.config.GITLAB_CONNECTIONS = connections

    # Clean up orphaned vector DB collections for removed connections
    new_ids = {c.get('id') for c in connections if c.get('id')}
    for old_id, old_conn in old_by_id.items():
        if old_id not in new_ids:
            try:
                await _cleanup_gitlab_connection_collections(old_conn)
            except Exception as e:
                log.warning(f'Failed to clean up collections for removed GitLab connection {old_id}: {e}')

    return {
        'GITLAB_CONNECTIONS': request.app.state.config.GITLAB_CONNECTIONS,
    }


async def _cleanup_gitlab_connection_collections(connection: dict):
    """Delete vector DB collections associated with a removed GitLab connection."""
    collection_names = set()

    # If a specific repo is configured, derive the collection name directly
    owner = connection.get('owner', '')
    repo = connection.get('repo', '')
    if owner and repo:
        collection_names.add(f'gitlab_{owner}_{repo}')

    # Also try to fetch projects via GitLab API to get all synced collections
    token = connection.get('token', '')
    if token:
        try:
            token = decrypt_data(token)
        except Exception:
            token = connection.get('token', '')

    gitlab_id = connection.get('id', '')
    if gitlab_id and token and connection.get('url'):
        try:
            client = create_gitlab_client(connection.get('url', ''), token)
            projects = await client.list_projects(per_page=100)
            for project in projects:
                project_path = project.get('path_with_namespace', str(project.get('id', '')))
                collection_names.add(f'gitlab_{project_path.replace("/", "_")}')
        except Exception as e:
            log.debug(f'Could not fetch projects for removed connection {gitlab_id}: {e}')

    for cname in collection_names:
        try:
            if await ASYNC_VECTOR_DB_CLIENT.has_collection(cname):
                log.info(f'Deleting orphaned GitLab collection: {cname}')
                await ASYNC_VECTOR_DB_CLIENT.delete_collection(cname)
        except Exception as e:
            log.warning(f'Failed to delete collection {cname}: {e}')


@router.post('/gitlab/browse-projects')
async def browse_gitlab_projects(
    request: Request,
    user=Depends(get_admin_user),
):
    """Browse projects on a GitLab instance using a temporary URL/token.
    Used when adding a new connection before it is saved."""
    try:
        body = await request.json()
        url = body.get('url', '').rstrip('/')
        token = body.get('token', '')

        if not url or not token:
            raise HTTPException(status_code=400, detail='URL and token are required')

        client = create_gitlab_client(url, token)
        projects = await client.list_projects(per_page=100)
        return {'projects': projects}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f'Failed to browse GitLab projects: {e}')
        raise HTTPException(status_code=400, detail=f'Failed to fetch projects: {str(e)}')

    try:
        body = await request.json()
        url = body.get('url', '').rstrip('/')
        token = body.get('token', '')

        if not url or not token:
            log.error(f"Verify GitLab failed: url={url}, token={'set' if token else 'empty'}")
            raise HTTPException(status_code=400, detail='URL and token are required')

        # Relax validation to allow any valid URL for self-hosted instances
        if not url.startswith('http'):
            log.error(f"Verify GitLab failed: invalid url format {url}")
            raise HTTPException(status_code=400, detail='Invalid URL. Must start with http:// or https://')

        client = create_gitlab_client(url, token)
        try:
            result = await client.test_connection()
            return {'status': True, 'user': result}
        except Exception as e:
            log.error(f"GitLab connection test failed: {e}")
            raise e
    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e)
        if isinstance(e, httpx.HTTPStatusError):
            try:
                error_data = e.response.json()
                if 'message' in error_data:
                    error_str = error_data['message']
                elif 'error' in error_data:
                    error_str = error_data['error']
            except:
                pass
        
        log.error(f'Failed to verify GitLab connection: {e}')
        
        if '302' in error_str or 'Redirect' in error_str:
            raise HTTPException(
                status_code=400,
                detail='Invalid token or URL. Please check your GitLab URL (use base URL only, e.g., https://gitlab.com) and personal access token.',
            )
        raise HTTPException(
            status_code=400,
            detail=f'Failed to connect to GitLab: {error_str}',
        )


@router.get('/gitlab/{gitlab_id}/projects')
async def get_gitlab_projects(
    request: Request,
    gitlab_id: str,
    page: int = 1,
    per_page: int = 50,
    search: str = '',
    user=Depends(get_admin_user),
):
    """Get all projects the authenticated user has access to on this GitLab connection."""
    connections = request.app.state.config.GITLAB_CONNECTIONS
    connection = next((c for c in connections if c.get('id') == gitlab_id), None)

    if not connection:
        raise HTTPException(status_code=404, detail='GitLab connection not found')

    token = connection.get('token', '')
    if token:
        token = decrypt_data(token)

    client = create_gitlab_client(connection.get('url', ''), token)
    projects = await client.list_projects(per_page=per_page, page=page, search=search)
    
    selected = set(connection.get('selected_projects', []) or [])
    return {'projects': projects, 'selected': selected}



@router.post('/gitlab/{gitlab_id}/sync')
async def trigger_gitlab_sync(
    request: Request,
    gitlab_id: str,
    user=Depends(get_admin_user),
):
    connections = request.app.state.config.GITLAB_CONNECTIONS
    connection = next((c for c in connections if c.get('id') == gitlab_id), None)

    if not connection:
        raise HTTPException(status_code=404, detail='GitLab connection not found')

    project_ids = []
    try:
        body = await request.json()
        project_ids = body.get('project_ids', []) or []
    except Exception:
        pass

    # If no explicit project_ids and connection has selected_projects, use those
    if not project_ids:
        selected = connection.get('selected_projects', [])
        if selected:
            project_ids = selected

    job_id = str(uuid.uuid4())

    try:
        import redis
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url)
        token = ''
        try:
            token = decrypt_data(connection.get('token', '')) if connection.get('token') else ''
        except Exception:
            token = connection.get('token', '')

        job_data = {
            'job_id': job_id,
            'gitlab_id': gitlab_id,
            'connection': {
                'url': connection.get('url', ''),
                'token': token,
                'owner': connection.get('owner', ''),
                'repo': connection.get('repo', ''),
                'branch': connection.get('branch', ''),
                'wiki_only': connection.get('wiki_only', False),
                'file_types': connection.get('file_types', ''),
                'include_wiki': connection.get('include_wiki', False),
                'exclude_patterns': connection.get('exclude_patterns', ''),
            },
            'project_ids': project_ids or [],
            'triggered_by': user.id,
        }
        r.lpush('gitlab_sync_queue', json.dumps(job_data))
    except Exception as e:
        log.debug(f'Failed to enqueue GitLab sync job: {e}')

    return {'job_id': job_id, 'status': 'queued'}


@router.get('/gitlab/jobs/{job_id}/status')
async def get_gitlab_job_status(
    request: Request,
    job_id: str,
    user=Depends(get_admin_user),
):
    try:
        import redis
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url)
        status_key = f'gitlab_job:{job_id}:status'
        status_data = r.get(status_key)
        if status_data:
            import json
            return json.loads(status_data)
        return {'status': 'unknown', 'progress': 0, 'message': 'Job not found'}
    except Exception as e:
        log.debug(f'Failed to get job status: {e}')
        return {'status': 'unknown', 'progress': 0, 'message': str(e)}


class GitLabSearchForm(BaseModel):
    query: str
    project_ids: Optional[list[str]] = None
    limit: Optional[int] = 10


async def get_gitlab_connection_projects(request: Request, gitlab_id: str) -> list:
    """Helper to get all projects for a GitLab connection."""
    connections = request.app.state.config.GITLAB_CONNECTIONS
    connection = next((c for c in connections if c.get('id') == gitlab_id), None)
    if not connection:
        return []
    token = connection.get('token', '')
    if token:
        try:
            token = decrypt_data(token)
        except Exception:
            pass
    try:
        client = create_gitlab_client(connection.get('url', ''), token)
        return await client.list_projects(per_page=100)
    except Exception as e:
        log.debug(f'Failed to get projects for GitLab connection {gitlab_id}: {e}')
        return []


@router.post('/gitlab/search')
async def search_gitlab_knowledge(
    request: Request,
    form_data: GitLabSearchForm,
    user=Depends(get_admin_user),
):
    try:
        query_embedding = await request.app.state.EMBEDDING_FUNCTION(form_data.query)
        
        connections = request.app.state.config.GITLAB_CONNECTIONS
        
        all_results = []
        search_collections = []

        if form_data.project_ids:
            pid_set = set(form_data.project_ids)
            for conn in connections:
                projects = await get_gitlab_connection_projects(request, conn.get('id', ''))
                for project in projects:
                    pid = str(project.get('id', ''))
                    if pid in pid_set:
                        project_path = project.get('path_with_namespace', pid)
                        search_collections.append(f'gitlab_{project_path.replace("/", "_")}')
        else:
            for conn in connections:
                projects = await get_gitlab_connection_projects(request, conn.get('id', ''))
                for project in projects:
                    project_path = project.get('path_with_namespace', str(project.get('id', '')))
                    search_collections.append(f'gitlab_{project_path.replace("/", "_")}')
        
        for collection_name in search_collections:
            try:
                result = await ASYNC_VECTOR_DB_CLIENT.search(
                    collection_name=collection_name,
                    vectors=[query_embedding],
                    limit=form_data.limit or 10,
                )
                if result and result.documents:
                    for i in range(len(result.documents[0])):
                        all_results.append({
                            'collection': collection_name,
                            'text': result.documents[0][i],
                            'metadata': result.metadatas[0][i] if result.metadatas else {},
                            'distance': result.distances[0][i] if result.distances else None,
                        })
            except Exception as e:
                log.debug(f'Search in {collection_name} failed: {e}')
                continue
        
        all_results.sort(key=lambda x: x.get('distance', 9999))
        return {'results': all_results[:form_data.limit or 20]}
    except Exception as e:
        log.debug(f'GitLab search failed: {e}')
        raise HTTPException(status_code=400, detail=f'Search failed: {str(e)}')


@router.get('/gitlab/collections')
async def get_gitlab_collections(
    request: Request,
    user=Depends(get_verified_user),
):
    """Get all synced GitLab collections with metadata.
    Accessible to all verified users; GitLab collections are admin-managed
    but visible to everyone (consistent with filter_accessible_collections)."""
    connections = request.app.state.config.GITLAB_CONNECTIONS
    collections = []
    
    for conn in connections:
        if not conn.get('enabled', True):
            continue
        gitlab_id = conn.get('id', '')
        if not gitlab_id:
            continue
        
        selected = set(conn.get('selected_projects', []) or [])
        projects = await get_gitlab_connection_projects(request, gitlab_id)
        
        for project in projects:
            project_id = str(project.get('id', ''))
            
            # If user has selected specific projects, skip unselected ones
            if selected and project_id not in selected:
                continue
            
            project_path = project.get('path_with_namespace', project_id)
            collection_name = f'gitlab_{project_path.replace("/", "_")}'
            
            try:
                exists = await ASYNC_VECTOR_DB_CLIENT.has_collection(collection_name)
            except Exception:
                exists = False
            
            collections.append({
                'id': f'{gitlab_id}_{project_id}',
                'gitlab_id': gitlab_id,
                'project_id': project_id,
                'name': project.get('name', 'Unknown'),
                'path': project_path,
                'collection_name': collection_name,
                'synced': exists,
                'selected': project_id in selected,
                'web_url': project.get('web_url', ''),
            })
    
    return {'collections': collections}


############################
# CodeInterpreterConfig
############################
# CodeInterpreterConfig
############################
class CodeInterpreterConfigForm(BaseModel):
    ENABLE_CODE_EXECUTION: bool
    CODE_EXECUTION_ENGINE: str
    CODE_EXECUTION_JUPYTER_URL: Optional[str]
    CODE_EXECUTION_JUPYTER_AUTH: Optional[str]
    CODE_EXECUTION_JUPYTER_AUTH_TOKEN: Optional[str]
    CODE_EXECUTION_JUPYTER_AUTH_PASSWORD: Optional[str]
    CODE_EXECUTION_JUPYTER_TIMEOUT: Optional[int]
    ENABLE_CODE_INTERPRETER: bool
    CODE_INTERPRETER_ENGINE: str
    CODE_INTERPRETER_PROMPT_TEMPLATE: Optional[str]
    CODE_INTERPRETER_JUPYTER_URL: Optional[str]
    CODE_INTERPRETER_JUPYTER_AUTH: Optional[str]
    CODE_INTERPRETER_JUPYTER_AUTH_TOKEN: Optional[str]
    CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD: Optional[str]
    CODE_INTERPRETER_JUPYTER_TIMEOUT: Optional[int]


@router.get('/code_execution', response_model=CodeInterpreterConfigForm)
async def get_code_execution_config(request: Request, user=Depends(get_admin_user)):
    return {
        'ENABLE_CODE_EXECUTION': request.app.state.config.ENABLE_CODE_EXECUTION,
        'CODE_EXECUTION_ENGINE': request.app.state.config.CODE_EXECUTION_ENGINE,
        'CODE_EXECUTION_JUPYTER_URL': request.app.state.config.CODE_EXECUTION_JUPYTER_URL,
        'CODE_EXECUTION_JUPYTER_AUTH': request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH,
        'CODE_EXECUTION_JUPYTER_AUTH_TOKEN': request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_TOKEN,
        'CODE_EXECUTION_JUPYTER_AUTH_PASSWORD': request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_PASSWORD,
        'CODE_EXECUTION_JUPYTER_TIMEOUT': request.app.state.config.CODE_EXECUTION_JUPYTER_TIMEOUT,
        'ENABLE_CODE_INTERPRETER': request.app.state.config.ENABLE_CODE_INTERPRETER,
        'CODE_INTERPRETER_ENGINE': request.app.state.config.CODE_INTERPRETER_ENGINE,
        'CODE_INTERPRETER_PROMPT_TEMPLATE': request.app.state.config.CODE_INTERPRETER_PROMPT_TEMPLATE,
        'CODE_INTERPRETER_JUPYTER_URL': request.app.state.config.CODE_INTERPRETER_JUPYTER_URL,
        'CODE_INTERPRETER_JUPYTER_AUTH': request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH,
        'CODE_INTERPRETER_JUPYTER_AUTH_TOKEN': request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_TOKEN,
        'CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD': request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD,
        'CODE_INTERPRETER_JUPYTER_TIMEOUT': request.app.state.config.CODE_INTERPRETER_JUPYTER_TIMEOUT,
    }


@router.post('/code_execution', response_model=CodeInterpreterConfigForm)
async def set_code_execution_config(
    request: Request, form_data: CodeInterpreterConfigForm, user=Depends(get_admin_user)
):
    request.app.state.config.ENABLE_CODE_EXECUTION = form_data.ENABLE_CODE_EXECUTION

    request.app.state.config.CODE_EXECUTION_ENGINE = form_data.CODE_EXECUTION_ENGINE
    request.app.state.config.CODE_EXECUTION_JUPYTER_URL = form_data.CODE_EXECUTION_JUPYTER_URL
    request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH = form_data.CODE_EXECUTION_JUPYTER_AUTH
    request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_TOKEN = form_data.CODE_EXECUTION_JUPYTER_AUTH_TOKEN
    request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_PASSWORD = form_data.CODE_EXECUTION_JUPYTER_AUTH_PASSWORD
    request.app.state.config.CODE_EXECUTION_JUPYTER_TIMEOUT = form_data.CODE_EXECUTION_JUPYTER_TIMEOUT

    request.app.state.config.ENABLE_CODE_INTERPRETER = form_data.ENABLE_CODE_INTERPRETER
    request.app.state.config.CODE_INTERPRETER_ENGINE = form_data.CODE_INTERPRETER_ENGINE
    request.app.state.config.CODE_INTERPRETER_PROMPT_TEMPLATE = form_data.CODE_INTERPRETER_PROMPT_TEMPLATE

    request.app.state.config.CODE_INTERPRETER_JUPYTER_URL = form_data.CODE_INTERPRETER_JUPYTER_URL

    request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH = form_data.CODE_INTERPRETER_JUPYTER_AUTH

    request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_TOKEN = form_data.CODE_INTERPRETER_JUPYTER_AUTH_TOKEN
    request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD = form_data.CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD
    request.app.state.config.CODE_INTERPRETER_JUPYTER_TIMEOUT = form_data.CODE_INTERPRETER_JUPYTER_TIMEOUT

    return {
        'ENABLE_CODE_EXECUTION': request.app.state.config.ENABLE_CODE_EXECUTION,
        'CODE_EXECUTION_ENGINE': request.app.state.config.CODE_EXECUTION_ENGINE,
        'CODE_EXECUTION_JUPYTER_URL': request.app.state.config.CODE_EXECUTION_JUPYTER_URL,
        'CODE_EXECUTION_JUPYTER_AUTH': request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH,
        'CODE_EXECUTION_JUPYTER_AUTH_TOKEN': request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_TOKEN,
        'CODE_EXECUTION_JUPYTER_AUTH_PASSWORD': request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_PASSWORD,
        'CODE_EXECUTION_JUPYTER_TIMEOUT': request.app.state.config.CODE_EXECUTION_JUPYTER_TIMEOUT,
        'ENABLE_CODE_INTERPRETER': request.app.state.config.ENABLE_CODE_INTERPRETER,
        'CODE_INTERPRETER_ENGINE': request.app.state.config.CODE_INTERPRETER_ENGINE,
        'CODE_INTERPRETER_PROMPT_TEMPLATE': request.app.state.config.CODE_INTERPRETER_PROMPT_TEMPLATE,
        'CODE_INTERPRETER_JUPYTER_URL': request.app.state.config.CODE_INTERPRETER_JUPYTER_URL,
        'CODE_INTERPRETER_JUPYTER_AUTH': request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH,
        'CODE_INTERPRETER_JUPYTER_AUTH_TOKEN': request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_TOKEN,
        'CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD': request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD,
        'CODE_INTERPRETER_JUPYTER_TIMEOUT': request.app.state.config.CODE_INTERPRETER_JUPYTER_TIMEOUT,
    }


############################
# SetDefaultModels
############################
class ModelsConfigForm(BaseModel):
    DEFAULT_MODELS: Optional[str]
    DEFAULT_PINNED_MODELS: Optional[str]
    MODEL_ORDER_LIST: Optional[list[str]]
    DEFAULT_MODEL_METADATA: Optional[dict] = None
    DEFAULT_MODEL_PARAMS: Optional[dict] = None


@router.get('/models/defaults')
async def get_models_defaults(request: Request, user=Depends(get_verified_user)):
    return {
        'DEFAULT_MODEL_METADATA': request.app.state.config.DEFAULT_MODEL_METADATA,
    }


@router.get('/models', response_model=ModelsConfigForm)
async def get_models_config(request: Request, user=Depends(get_admin_user)):
    return {
        'DEFAULT_MODELS': request.app.state.config.DEFAULT_MODELS,
        'DEFAULT_PINNED_MODELS': request.app.state.config.DEFAULT_PINNED_MODELS,
        'MODEL_ORDER_LIST': request.app.state.config.MODEL_ORDER_LIST,
        'DEFAULT_MODEL_METADATA': request.app.state.config.DEFAULT_MODEL_METADATA,
        'DEFAULT_MODEL_PARAMS': request.app.state.config.DEFAULT_MODEL_PARAMS,
    }


@router.post('/models', response_model=ModelsConfigForm)
async def set_models_config(request: Request, form_data: ModelsConfigForm, user=Depends(get_admin_user)):
    request.app.state.config.DEFAULT_MODELS = form_data.DEFAULT_MODELS
    request.app.state.config.DEFAULT_PINNED_MODELS = form_data.DEFAULT_PINNED_MODELS
    request.app.state.config.MODEL_ORDER_LIST = form_data.MODEL_ORDER_LIST
    request.app.state.config.DEFAULT_MODEL_METADATA = form_data.DEFAULT_MODEL_METADATA
    request.app.state.config.DEFAULT_MODEL_PARAMS = form_data.DEFAULT_MODEL_PARAMS
    return {
        'DEFAULT_MODELS': request.app.state.config.DEFAULT_MODELS,
        'DEFAULT_PINNED_MODELS': request.app.state.config.DEFAULT_PINNED_MODELS,
        'MODEL_ORDER_LIST': request.app.state.config.MODEL_ORDER_LIST,
        'DEFAULT_MODEL_METADATA': request.app.state.config.DEFAULT_MODEL_METADATA,
        'DEFAULT_MODEL_PARAMS': request.app.state.config.DEFAULT_MODEL_PARAMS,
    }


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
    request.app.state.config.DEFAULT_PROMPT_SUGGESTIONS = data['suggestions']
    return request.app.state.config.DEFAULT_PROMPT_SUGGESTIONS


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
    request.app.state.config.BANNERS = data['banners']
    return request.app.state.config.BANNERS


@router.get('/banners', response_model=list[BannerModel])
async def get_banners(
    request: Request,
    user=Depends(get_verified_user),
):
    return request.app.state.config.BANNERS
