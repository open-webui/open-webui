from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Optional

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request, status
from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL, CACHE_DIR
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL, AIOHTTP_CLIENT_TIMEOUT, ENABLE_PLUGINS
from open_webui.events import EVENTS, publish_event
from open_webui.internal.db import get_async_session
from open_webui.models.access_grants import AccessGrants
from open_webui.models.config import Config
from open_webui.models.groups import Groups
from open_webui.models.oauth_sessions import OAuthSessions
from open_webui.models.tools import (
    ToolAccessResponse,
    ToolForm,
    ToolModel,
    ToolResponse,
    Tools,
    ToolUserResponse,
)
from open_webui.models.tool_servers import ToolServerUserConfigs, get_user_configs_from_settings
from open_webui.utils.access_control import (
    filter_allowed_access_grants,
    has_access,
    has_connection_access,
    has_permission,
)
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.valves import decrypt_valves
from open_webui.utils.plugin import (
    get_tools_cache,
    get_tool_module_from_cache,
    load_tool_module_by_id,
    replace_imports,
    resolve_valves_schema_options,
)
from open_webui.utils.tools import (
    find_tool_server_connection,
    get_tool_server_connection_id,
    get_tool_server_user_config_schema,
    get_tool_servers,
    get_tool_specs,
    get_user_config_flags,
    mask_user_config_values,
    validate_user_config_value,
)
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


router = APIRouter()


async def get_tool_module(request, tool_id, load_from_db=True):
    """
    Get the tool module by its ID.
    """
    tool_module, _ = await get_tool_module_from_cache(request, tool_id, load_from_db)
    return tool_module


############################
# GetTools
# The danger is not in having tools, but in reaching
# for the wrong one. Let the choice here be deliberate.
############################


@router.get('/', response_model=list[ToolUserResponse])
async def get_tools(
    request: Request,
    query: Optional[str] = None,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    tools = []
    bypass_access_control = user.role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL
    user_group_ids = (
        set()
        if bypass_access_control
        else {group.id for group in await Groups.get_groups_by_member_id(user.id, db=db)}
    )

    # Local Tools
    if ENABLE_PLUGINS:
        tools_cache = get_tools_cache(request)
        for tool in await Tools.get_tools(
            defer_content=True,
            db=db,
            user_id=None if bypass_access_control else user.id,
            user_group_ids=user_group_ids,
        ):
            tool_module = tools_cache.get(tool.id)
            has_user_valves = (
                hasattr(tool_module, 'UserValves')
                if tool_module
                else (tool.meta.has_user_valves if tool.meta else False)
            )
            tools.append(
                ToolUserResponse(
                    **{
                        **tool.model_dump(),
                        'has_user_valves': has_user_valves,
                    }
                )
            )

    # Credential slots the user has filled in, read from the settings already loaded
    # with them rather than one query per connection.
    user_configs = get_user_configs_from_settings(user.settings)

    def user_config_flags(connection: dict) -> dict:
        """requires_user_config / user_config_set / user_config_required_set, or
        nothing when the connection asks the user for nothing."""
        if not get_tool_server_user_config_schema(connection):
            return {}
        values = decrypt_valves(user_configs.get(get_tool_server_connection_id(connection)))
        return get_user_config_flags(connection, values)

    # OpenAPI Tool Servers
    server_access_grants = {}
    for server in await get_tool_servers(request):
        server_idx = server.get('idx', 0)
        connections = await Config.get('tool_server.connections', [])
        if server_idx >= len(connections):
            log.warning(
                f'Tool server index {server_idx} out of range '
                f'(have {len(connections)} connections), skipping server {server.get("id")}'
            )
            continue
        connection = connections[server_idx]
        server_config = connection.get('config', {})

        server_id = f'server:{server.get("id")}'
        server_access_grants[server_id] = server_config.get('access_grants', [])

        tools.append(
            ToolUserResponse(
                **{
                    'id': server_id,
                    'user_id': server_id,
                    'name': server.get('openapi', {}).get('info', {}).get('title', 'Tool Server'),
                    'meta': {
                        'description': server.get('openapi', {}).get('info', {}).get('description', ''),
                    },
                    'updated_at': int(time.time()),
                    'created_at': int(time.time()),
                    **user_config_flags(connection),
                }
            )
        )

    # MCP Tool Servers
    for server in await Config.get('tool_server.connections', []):
        if server.get('type', 'openapi') == 'mcp' and (server.get('config') or {}).get('enable'):
            info = server.get('info') or {}
            server_id = info.get('id')
            auth_type = server.get('auth_type', 'none')

            session_token = None
            if auth_type in ('oauth_2.1', 'oauth_2.1_static') and server_id:
                splits = server_id.split(':')
                server_id = splits[-1] if len(splits) > 1 else server_id

                session_token = await request.app.state.oauth_client_manager.get_oauth_token(
                    user.id, f'mcp:{server_id}'
                )

            server_config = server.get('config') or {}

            tool_id = f'server:mcp:{info.get("id")}'
            server_access_grants[tool_id] = server_config.get('access_grants', [])

            tools.append(
                ToolUserResponse(
                    **{
                        'id': tool_id,
                        'user_id': tool_id,
                        'name': info.get('name', 'MCP Tool Server'),
                        'meta': {
                            'description': info.get('description', ''),
                        },
                        'updated_at': int(time.time()),
                        'created_at': int(time.time()),
                        **(
                            {
                                'authenticated': session_token is not None,
                            }
                            if auth_type in ('oauth_2.1', 'oauth_2.1_static')
                            else {}
                        ),
                        # Surface connections that still need credentials from this user,
                        # so the UI can offer to configure them instead of failing later.
                        **user_config_flags(server),
                    }
                )
            )

    if not bypass_access_control:
        tools = [
            tool
            for tool in tools
            if not str(tool.id).startswith('server:')
            or await has_access(
                user.id,
                'read',
                server_access_grants.get(str(tool.id), []),
                user_group_ids,
                db=db,
            )
        ]

    if query:
        q = query.casefold()
        tools = [tool for tool in tools if q in (tool.name or '').casefold()]

    return tools


############################
# GetToolList
############################


@router.get('/list', response_model=list[ToolAccessResponse])
async def get_tool_list(user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)):
    if not ENABLE_PLUGINS:
        return []

    bypass_access_control = user.role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL
    user_group_ids = (
        set()
        if bypass_access_control
        else {group.id for group in await Groups.get_groups_by_member_id(user.id, db=db)}
    )
    tools = await Tools.get_tools(
        defer_content=True,
        db=db,
        user_id=None if bypass_access_control else user.id,
        user_group_ids=user_group_ids,
    )

    result = []
    for tool in tools:
        has_write = (
            bypass_access_control
            or user.id == tool.user_id
            or any(
                g.permission == 'write'
                and (
                    (g.principal_type == 'user' and (g.principal_id == user.id or g.principal_id == '*'))
                    or (g.principal_type == 'group' and g.principal_id in user_group_ids)
                )
                for g in tool.access_grants
            )
        )
        result.append(
            ToolAccessResponse(
                **tool.model_dump(),
                write_access=has_write,
            )
        )
    return result


############################
# LoadFunctionFromLink
############################


class LoadUrlForm(BaseModel):
    url: HttpUrl


def github_url_to_raw_url(url: str) -> str:
    # Handle 'tree' (folder) URLs (add main.py at the end)
    m1 = re.match(r'https://github\.com/([^/]+)/([^/]+)/tree/([^/]+)/(.*)', url)
    if m1:
        org, repo, branch, path = m1.groups()
        return f'https://raw.githubusercontent.com/{org}/{repo}/refs/heads/{branch}/{path.rstrip("/")}/main.py'

    # Handle 'blob' (file) URLs
    m2 = re.match(r'https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.*)', url)
    if m2:
        org, repo, branch, path = m2.groups()
        return f'https://raw.githubusercontent.com/{org}/{repo}/refs/heads/{branch}/{path}'

    # No match; return as-is
    return url


@router.post('/load/url', response_model=dict | None)
async def load_tool_from_url(request: Request, form_data: LoadUrlForm, user=Depends(get_admin_user)):
    # NOTE: This is NOT a SSRF vulnerability:
    # This endpoint is admin-only (see get_admin_user), meant for *trusted* internal use,
    # and does NOT accept untrusted user input. Access is enforced by authentication.

    url = str(form_data.url)
    if not url:
        raise HTTPException(status_code=400, detail='Please enter a valid URL')

    url = github_url_to_raw_url(url)
    url_parts = url.rstrip('/').split('/')

    file_name = url_parts[-1]
    tool_name = (
        file_name[:-3]
        if (file_name.endswith('.py') and (not file_name.startswith(('main.py', 'index.py', '__init__.py'))))
        else url_parts[-2]
        if len(url_parts) > 1
        else 'function'
    )

    try:
        async with aiohttp.ClientSession(
            trust_env=True, timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
        ) as session:
            async with session.get(
                url, headers={'Content-Type': 'application/json'}, ssl=AIOHTTP_CLIENT_SESSION_SSL
            ) as resp:
                if resp.status != 200:
                    raise HTTPException(status_code=resp.status, detail='Failed to fetch the tool')
                data = await resp.text()
                if not data:
                    raise HTTPException(status_code=400, detail='No data received from the URL')
        return {
            'name': tool_name,
            'content': data,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=ERROR_MESSAGES.DEFAULT(e, 'Error fetching tool'),
        )


############################
# ExportTools
############################


@router.get('/export', response_model=list[ToolModel])
async def export_tools(
    request: Request,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if user.role != 'admin' and not await has_permission(
        user.id,
        'workspace.tools_export',
        await Config.get('user.permissions'),
        db=db,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    bypass_access_control = user.role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL
    return await Tools.get_tools(
        db=db,
        user_id=None if bypass_access_control else user.id,
    )


############################
# CreateNewTools
############################


@router.post('/create', response_model=ToolResponse | None)
async def create_new_tools(
    request: Request,
    form_data: ToolForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Create a new tool from user-supplied Python source code."""
    if user.role != 'admin' and not (
        await has_permission(user.id, 'workspace.tools', await Config.get('user.permissions'), db=db)
        or await has_permission(
            user.id,
            'workspace.tools_import',
            await Config.get('user.permissions'),
            db=db,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    if not form_data.id.isidentifier():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Only alphanumeric characters and underscores are allowed in the id',
        )

    form_data.id = form_data.id.lower()

    tools = await Tools.get_tool_by_id(form_data.id, db=db)
    if tools is None:
        try:
            form_data.access_grants = await filter_allowed_access_grants(
                await Config.get('user.permissions'),
                user.id,
                user.role,
                form_data.access_grants,
                'sharing.public_tools',
            )

            form_data.content = replace_imports(form_data.content)
            tool_module, frontmatter = await load_tool_module_by_id(form_data.id, content=form_data.content)
            form_data.meta.manifest = frontmatter
            form_data.meta.has_user_valves = hasattr(tool_module, 'UserValves')

            TOOLS = get_tools_cache(request)
            TOOLS[form_data.id] = tool_module

            specs = get_tool_specs(TOOLS[form_data.id])
            tools = await Tools.insert_new_tool(user.id, form_data, specs, db=db)

            tool_cache_dir = CACHE_DIR / 'tools' / form_data.id
            tool_cache_dir.mkdir(parents=True, exist_ok=True)

            if tools:
                await publish_event(
                    request,
                    EVENTS.TOOL_CREATED,
                    actor=user,
                    subject_id=tools.id,
                    data={'name': tools.name},
                )
                return tools
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT('Error creating tools'),
                )
        except HTTPException:
            raise
        except Exception as e:
            log.exception(f'Failed to load the tool by id {form_data.id}: {e}')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(e, 'Error creating tool'),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ID_TAKEN,
        )


############################
# GetToolsById
############################


@router.get('/id/{id}', response_model=ToolAccessResponse | None)
async def get_tools_by_id(id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)):
    tools = await Tools.get_tool_by_id(id, db=db)

    if tools:
        if (
            user.role == 'admin'
            or tools.user_id == user.id
            or await AccessGrants.has_access(
                user_id=user.id,
                resource_type='tool',
                resource_id=tools.id,
                permission='read',
                db=db,
            )
        ):
            write_access = (
                (user.role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL)
                or user.id == tools.user_id
                or await AccessGrants.has_access(
                    user_id=user.id,
                    resource_type='tool',
                    resource_id=tools.id,
                    permission='write',
                    db=db,
                )
            )
            data = tools.model_dump()
            if not write_access:
                # extra='allow' re-admits content from model_dump; source is writer-only
                data.pop('content', None)
            return ToolAccessResponse(**data, write_access=write_access)
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# UpdateToolsById
############################


@router.post('/id/{id}/update', response_model=ToolModel | None)
async def update_tools_by_id(
    request: Request,
    id: str,
    form_data: ToolForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Update an existing tool's source code and metadata."""
    tools = await Tools.get_tool_by_id(id, db=db)
    if not tools:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Is the user the original creator, in a group with write access, or an admin
    if (
        tools.user_id != user.id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='tool',
            resource_id=tools.id,
            permission='write',
            db=db,
        )
        and user.role != 'admin'
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    # Content edits trigger exec on load — gate them behind workspace.tools (matches /create).
    if form_data.content != tools.content:
        if user.role != 'admin' and not (
            await has_permission(user.id, 'workspace.tools', await Config.get('user.permissions'), db=db)
            or await has_permission(user.id, 'workspace.tools_import', await Config.get('user.permissions'), db=db)
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.UNAUTHORIZED,
            )

    try:
        form_data.content = replace_imports(form_data.content)
        tool_module, frontmatter = await load_tool_module_by_id(id, content=form_data.content)
        form_data.meta.manifest = frontmatter
        form_data.meta.has_user_valves = hasattr(tool_module, 'UserValves')

        TOOLS = get_tools_cache(request)
        TOOLS[id] = tool_module

        specs = get_tool_specs(TOOLS[id])

        form_data.access_grants = await filter_allowed_access_grants(
            await Config.get('user.permissions'),
            user.id,
            user.role,
            form_data.access_grants,
            'sharing.public_tools',
        )

        updated = {
            **form_data.model_dump(exclude={'id'}),
            'specs': specs,
        }

        log.debug(updated)
        tools = await Tools.update_tool_by_id(id, updated, db=db)

        if tools:
            await publish_event(
                request,
                EVENTS.TOOL_UPDATED,
                actor=user,
                subject_id=tools.id,
                data={'name': tools.name},
            )
            return tools
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error updating tools'),
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e, 'Error updating tool'),
        )


############################
# UpdateToolAccessById
############################


class ToolAccessGrantsForm(BaseModel):
    access_grants: list[dict]


@router.post('/id/{id}/access/update', response_model=ToolModel | None)
async def update_tool_access_by_id(
    request: Request,
    id: str,
    form_data: ToolAccessGrantsForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    tools = await Tools.get_tool_by_id(id, db=db)
    if not tools:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        tools.user_id != user.id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='tool',
            resource_id=tools.id,
            permission='write',
            db=db,
        )
        and user.role != 'admin'
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    form_data.access_grants = await filter_allowed_access_grants(
        await Config.get('user.permissions'),
        user.id,
        user.role,
        form_data.access_grants,
        'sharing.public_tools',
    )

    await AccessGrants.set_access_grants('tool', id, form_data.access_grants, db=db)

    tools = await Tools.get_tool_by_id(id, db=db)
    await publish_event(
        request,
        EVENTS.TOOL_ACCESS_UPDATED,
        actor=user,
        subject_id=id,
        data={'name': tools.name if tools else None},
    )
    return tools


############################
# DeleteToolsById
############################


@router.delete('/id/{id}/delete', response_model=bool)
async def delete_tools_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    tools = await Tools.get_tool_by_id(id, db=db)
    if not tools:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        tools.user_id != user.id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='tool',
            resource_id=tools.id,
            permission='write',
            db=db,
        )
        and user.role != 'admin'
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    result = await Tools.delete_tool_by_id(id, db=db)
    if result:
        TOOLS = get_tools_cache(request)
        TOOLS.pop(id, None)
        await publish_event(
            request,
            EVENTS.TOOL_DELETED,
            actor=user,
            subject_id=id,
            data={'name': tools.name},
        )

    return result


############################
# GetToolValves
############################


@router.get('/id/{id}/valves', response_model=dict | None)
async def get_tools_valves_by_id(
    id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    tools = await Tools.get_tool_by_id(id, db=db)
    if not tools:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        tools.user_id != user.id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='tool',
            resource_id=tools.id,
            permission='write',
            db=db,
        )
        and user.role != 'admin'
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    try:
        valves = await Tools.get_tool_valves_by_id(id, db=db)
        return valves
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e, 'Error getting tool valves'),
        )


############################
# GetToolValvesSpec
############################


@router.get('/id/{id}/valves/spec', response_model=dict | None)
async def get_tools_valves_spec_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    tools = await Tools.get_tool_by_id(id, db=db)
    if not tools:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        tools.user_id != user.id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='tool',
            resource_id=tools.id,
            permission='write',
            db=db,
        )
        and user.role != 'admin'
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    tools_module, _ = await get_tool_module_from_cache(request, id)

    if hasattr(tools_module, 'Valves'):
        Valves = tools_module.Valves
        schema = Valves.schema()
        # Resolve dynamic options for select dropdowns
        schema = resolve_valves_schema_options(Valves, schema, user)
        return schema
    return None


############################
# UpdateToolValves
############################


@router.post('/id/{id}/valves/update', response_model=dict | None)
async def update_tools_valves_by_id(
    request: Request,
    id: str,
    form_data: dict,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    tools = await Tools.get_tool_by_id(id, db=db)
    if not tools:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        tools.user_id != user.id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='tool',
            resource_id=tools.id,
            permission='write',
            db=db,
        )
        and user.role != 'admin'
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    tools_module, _ = await get_tool_module_from_cache(request, id)

    if not hasattr(tools_module, 'Valves'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    Valves = tools_module.Valves

    try:
        form_data = {k: v for k, v in form_data.items() if v is not None}
        valves = Valves(**form_data)
        valves_dict = valves.model_dump(exclude_unset=True)
        await Tools.update_tool_valves_by_id(id, valves_dict, db=db)
        await publish_event(
            request,
            EVENTS.TOOL_VALVES_UPDATED,
            actor=user,
            subject_id=id,
        )
        return valves_dict
    except Exception as e:
        log.exception(f'Failed to update tool valves by id {id}: {e}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e, 'Error updating tool valves'),
        )


############################
# ToolUserValves
############################


@router.get('/id/{id}/valves/user', response_model=dict | None)
async def get_tools_user_valves_by_id(
    id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    tools = await Tools.get_tool_by_id(id, db=db)
    if not tools:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        tools.user_id != user.id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='tool',
            resource_id=tools.id,
            permission='read',
            db=db,
        )
        and user.role != 'admin'
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    try:
        user_valves = await Tools.get_user_valves_by_id_and_user_id(id, user.id, db=db)
        return user_valves
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e, 'Error getting tool user valves'),
        )


@router.get('/id/{id}/valves/user/spec', response_model=dict | None)
async def get_tools_user_valves_spec_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    tools = await Tools.get_tool_by_id(id, db=db)
    if not tools:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        tools.user_id != user.id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='tool',
            resource_id=tools.id,
            permission='read',
            db=db,
        )
        and user.role != 'admin'
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    tools_module, _ = await get_tool_module_from_cache(request, id)

    if hasattr(tools_module, 'UserValves'):
        UserValves = tools_module.UserValves
        schema = UserValves.schema()
        # Resolve dynamic options for select dropdowns
        schema = resolve_valves_schema_options(UserValves, schema, user)
        return schema
    return None


@router.post('/id/{id}/valves/user/update', response_model=dict | None)
async def update_tools_user_valves_by_id(
    request: Request,
    id: str,
    form_data: dict,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    tools = await Tools.get_tool_by_id(id, db=db)
    if not tools:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        tools.user_id != user.id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='tool',
            resource_id=tools.id,
            permission='read',
            db=db,
        )
        and user.role != 'admin'
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    tools_module, _ = await get_tool_module_from_cache(request, id)

    if hasattr(tools_module, 'UserValves'):
        UserValves = tools_module.UserValves

        try:
            form_data = {k: v for k, v in form_data.items() if v is not None}
            user_valves = UserValves(**form_data)
            user_valves_dict = user_valves.model_dump(exclude_unset=True)
            await Tools.update_user_valves_by_id_and_user_id(id, user.id, user_valves_dict, db=db)
            await publish_event(
                request,
                EVENTS.TOOL_VALVES_UPDATED,
                actor=user,
                subject_id=id,
                data={'scope': 'user'},
            )
            return user_valves_dict
        except Exception as e:
            log.exception(f'Failed to update user valves by id {id}: {e}')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(e, 'Error updating tool user valves'),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# ToolServerUserConfig
#
# Admin-defined connections may declare credential slots that each user fills in
# for themselves. The values never leave the user they belong to: password slots
# are never read back through these endpoints, and a value is only resolved into
# request headers while that user's own request is being served. At rest they are
# stored the way tool valves are — encrypted when ENABLE_VALVE_ENCRYPTION is set,
# and in the database as submitted when it is not, which is the default.
############################


async def get_tool_server_connection_for_user(server_id: str, user) -> dict:
    connection = find_tool_server_connection(await Config.get('tool_server.connections', []) or [], server_id)

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if not await has_connection_access(user, connection):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    return connection


@router.get('/servers/{server_id}/user_config/spec', response_model=dict | None)
async def get_tool_server_user_config_spec(server_id: str, user=Depends(get_verified_user)):
    connection = await get_tool_server_connection_for_user(server_id, user)
    return get_tool_server_user_config_schema(connection)


@router.get('/servers/{server_id}/user_config', response_model=dict | None)
async def get_tool_server_user_config_by_id(server_id: str, user=Depends(get_verified_user)):
    """Report which slots the user has filled in, without handing the secrets back.

    Slots rendered as passwords are write-only: only ``set`` is reported for them.
    """
    connection = await get_tool_server_connection_for_user(server_id, user)
    schema = get_tool_server_user_config_schema(connection)
    if not schema:
        return None

    values = await ToolServerUserConfigs.get_config(get_tool_server_connection_id(connection), user.id)
    return mask_user_config_values(schema, values)


@router.post('/servers/{server_id}/user_config/update', response_model=dict | None)
async def update_tool_server_user_config_by_id(
    request: Request, server_id: str, form_data: dict, user=Depends(get_verified_user)
):
    """Store the user's own values for the slots the admin declared.

    An omitted or empty slot keeps the stored value, so the UI never has to send a
    secret back to keep it; an explicit ``null`` clears that one slot. Fields the
    connection does not declare are ignored.
    """
    connection = await get_tool_server_connection_for_user(server_id, user)
    schema = get_tool_server_user_config_schema(connection)
    if not schema:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    connection_id = get_tool_server_connection_id(connection)
    values = await ToolServerUserConfigs.get_config(connection_id, user.id)

    updated = {}
    cleared = set()
    for slot in schema.get('properties', {}):
        if slot in form_data and form_data[slot] is None:
            cleared.add(slot)
            continue

        value = form_data.get(slot)
        if value is not None and value != '':
            try:
                updated[slot] = validate_user_config_value(slot, value)
            except ValueError as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        elif values.get(slot):
            updated[slot] = values[slot]  # left blank: keep what is stored

    # Saving a form that leaves a required field empty would otherwise report success
    # and still leave the connection unusable.
    missing = [slot for slot in schema.get('required', []) if not updated.get(slot) and slot not in cleared]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(f'Missing required fields: {", ".join(missing)}'),
        )

    if await ToolServerUserConfigs.update_config(connection_id, user.id, updated) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT('Error updating tool server user config'),
        )

    await publish_event(
        request,
        EVENTS.TOOL_SERVER_USER_CONFIG_UPDATED,
        actor=user,
        subject_id=connection_id,
        subject_type='tool_server',
        data={'fields': sorted(updated.keys())},
    )

    return {slot: {'set': True} for slot in updated}


@router.delete('/servers/{server_id}/user_config', response_model=bool)
async def delete_tool_server_user_config_by_id(request: Request, server_id: str, user=Depends(get_verified_user)):
    connection = await get_tool_server_connection_for_user(server_id, user)
    connection_id = get_tool_server_connection_id(connection)

    result = await ToolServerUserConfigs.delete_config(connection_id, user.id)
    if result:
        await publish_event(
            request,
            EVENTS.TOOL_SERVER_USER_CONFIG_UPDATED,
            actor=user,
            subject_id=connection_id,
            subject_type='tool_server',
            data={'fields': []},
        )
    return result
