from __future__ import annotations

import json
import logging
import mimetypes
import os
import re
from pathlib import Path
from typing import Optional

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from open_webui.config import CACHE_DIR
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL, AIOHTTP_CLIENT_TIMEOUT, ENABLE_PLUGINS
from open_webui.events import EVENTS, build_event, dispatch_event_functions, publish_event, schedule_webhook_dispatch
from open_webui.internal.db import get_async_session
from open_webui.models.functions import (
    FunctionForm,
    FunctionModel,
    FunctionResponse,
    Functions,
    FunctionUserResponse,
    FunctionWithValvesModel,
)
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.plugin import (
    get_functions_cache,
    get_function_module_from_cache,
    load_function_module_by_id,
    replace_imports,
    resolve_valves_schema_options,
)
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


router = APIRouter()


class PluginPageResponse(BaseModel):
    """A browser page contributed by an active Function.

    The asset URL is intentionally not accepted from Function metadata.  Functions
    declare only a relative entrypoint; Open WebUI owns the namespace and revision.
    """

    id: str
    title: str
    path: str
    entrypoint: str
    sidebar: bool = False
    order: int = 0
    icon: str | None = None


class PluginAppResponse(BaseModel):
    id: str
    title: str
    version: str
    default_page: str
    pages: list[PluginPageResponse]
    revision: str


def _plugin_relative_path(entrypoint: object, extensions: tuple[str, ...] | None = None) -> str | None:
    if not isinstance(entrypoint, str):
        return None

    entrypoint = entrypoint.strip()
    if (
        not entrypoint
        or entrypoint.startswith(('/', '\\'))
        or '://' in entrypoint
        or '?' in entrypoint
        or '#' in entrypoint
        or any(part in {'', '.', '..'} for part in entrypoint.split('/'))
        or (extensions is not None and not entrypoint.lower().endswith(extensions))
    ):
        return None
    return entrypoint


def _plugin_asset_path(path: str) -> str | None:
    return _plugin_relative_path(path)


def _plugin_app_response(function: FunctionModel, assets: object) -> PluginAppResponse | None:
    if not isinstance(assets, dict) or not isinstance(assets.get('plugin.json'), (str, bytes)):
        return None
    try:
        raw = assets['plugin.json']
        manifest = json.loads(raw.decode('utf-8') if isinstance(raw, bytes) else raw)
        if not isinstance(manifest, dict) or manifest.get('manifest_version') != 1 or manifest.get('id') != function.id:
            return None
        name, version, default_page, pages = (manifest.get(key) for key in ('name', 'version', 'default_page', 'pages'))
        if not all(isinstance(value, str) and value.strip() for value in (name, version, default_page)) or not isinstance(pages, list):
            return None
        parsed_pages: list[PluginPageResponse] = []
        page_ids = set()
        page_paths = set()
        for page in pages:
            if not isinstance(page, dict): return None
            page_id, title, path, entrypoint = (page.get(key) for key in ('id', 'title', 'path', 'entrypoint'))
            navigation = page.get('navigation', {})
            if (not isinstance(page_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', page_id)
                or not isinstance(title, str) or not title.strip()
                or not isinstance(path, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', path)
                or not (entrypoint := _plugin_relative_path(entrypoint, ('.html', '.js', '.mjs')))
                or entrypoint not in assets or page_id in page_ids or path in page_paths or not isinstance(navigation, dict)):
                return None
            order = navigation.get('order', 0)
            if not isinstance(order, int) or isinstance(order, bool): return None
            icon = navigation.get('icon')
            if icon is not None and (not isinstance(icon, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', icon)):
                return None
            page_ids.add(page_id)
            page_paths.add(path)
            parsed_pages.append(PluginPageResponse(id=page_id, title=title, path=path, entrypoint=entrypoint, sidebar=navigation.get('sidebar') is True, order=order, icon=icon))
        if not parsed_pages or default_page not in page_ids: return None
        return PluginAppResponse(id=function.id, title=name, version=version, default_page=default_page, pages=parsed_pages, revision=str(function.updated_at))
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
        return None

############################
# GetFunctions
# Our daily functions give us, and forgive us
# our deprecated methods, as we refactor those who depend on us.
############################


@router.get('/', response_model=list[FunctionResponse])
async def get_functions(user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)):
    if not ENABLE_PLUGINS:
        return []

    return await Functions.get_functions(db=db)


@router.get('/list', response_model=list[FunctionUserResponse])
async def get_function_list(user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)):
    if not ENABLE_PLUGINS:
        return []

    return await Functions.get_function_list(db=db)


############################
# Plugin Pages
############################


@router.get('/apps', response_model=list[PluginAppResponse])
async def get_plugin_apps(request: Request, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)):
    """List active Functions that provide a trusted browser page."""
    if not ENABLE_PLUGINS:
        return []

    apps = []
    for function in await Functions.get_functions(active_only=True, db=db):
        try:
            module, _, _ = await get_function_module_from_cache(request, function.id, function=function)
            app = _plugin_app_response(function, getattr(module, 'frontend_assets', None))
            if app:
                apps.append(app)
        except Exception:
            log.exception('Failed to load plugin manifest for %s', function.id)
    return apps


@router.get('/apps/{id}/assets/{revision}/{path:path}')
async def get_plugin_asset(
    request: Request,
    id: str,
    revision: str,
    path: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Serve an asset declared by an active Function under an OW-owned namespace.

    V1 intentionally keeps the package format minimal: a Function may expose a
    ``frontend_assets`` mapping of relative paths to UTF-8 strings or bytes. This
    makes plain HTML pages and pre-built ESM bundles installable without a second
    storage model or a database migration.
    """
    if not ENABLE_PLUGINS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    asset_path = _plugin_asset_path(path)
    function = await Functions.get_function_by_id(id, db=db)
    if not asset_path or not function or not function.is_active or revision != str(function.updated_at):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    try:
        function_module, _, _ = await get_function_module_from_cache(request, id, function=function)
        assets = getattr(function_module, 'frontend_assets', None)
        if _plugin_app_response(function, assets) is None or not isinstance(assets, dict) or asset_path not in assets:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

        asset = assets[asset_path]
        if isinstance(asset, str):
            content = asset.encode('utf-8')
        elif isinstance(asset, bytes):
            content = asset
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

        media_type = mimetypes.guess_type(asset_path)[0] or 'application/octet-stream'
        if asset_path.endswith(('.js', '.mjs')):
            media_type = 'text/javascript'
        return Response(
            content=content,
            media_type=media_type,
            headers={
                'Cache-Control': 'private, max-age=31536000, immutable',
                'X-Content-Type-Options': 'nosniff',
            },
        )
    except HTTPException:
        raise
    except Exception:
        log.exception('Failed to serve plugin asset %s for %s', asset_path, id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)


############################
# ExportFunctions
############################


@router.get('/export', response_model=list[FunctionModel | FunctionWithValvesModel])
async def get_functions(
    include_valves: bool = False,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    if not ENABLE_PLUGINS:
        return []

    return await Functions.get_functions(include_valves=include_valves, db=db)


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
async def load_function_from_url(request: Request, form_data: LoadUrlForm, user=Depends(get_admin_user)):
    # NOTE: This is NOT a SSRF vulnerability:
    # This endpoint is admin-only (see get_admin_user), meant for *trusted* internal use,
    # and does NOT accept untrusted user input. Access is enforced by authentication.

    url = str(form_data.url)
    if not url:
        raise HTTPException(status_code=400, detail='Please enter a valid URL')

    url = github_url_to_raw_url(url)
    url_parts = url.rstrip('/').split('/')

    file_name = url_parts[-1]
    function_name = (
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
                    raise HTTPException(status_code=resp.status, detail='Failed to fetch the function')
                data = await resp.text()
                if not data:
                    raise HTTPException(status_code=400, detail='No data received from the URL')
        return {
            'name': function_name,
            'content': data,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=ERROR_MESSAGES.DEFAULT(e, 'Error fetching function'),
        )


############################
# SyncFunctions
############################


class SyncFunctionsForm(BaseModel):
    functions: list[FunctionWithValvesModel] = []


@router.post('/sync', response_model=list[FunctionWithValvesModel])
async def sync_functions(
    request: Request,
    form_data: SyncFunctionsForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        for function in form_data.functions:
            function.content = replace_imports(function.content)
            function_module, function_type, frontmatter = await load_function_module_by_id(
                function.id,
                content=function.content,
            )

            if hasattr(function_module, 'Valves') and function.valves:
                Valves = function_module.Valves
                try:
                    Valves(**{k: v for k, v in function.valves.items() if v is not None})
                except Exception as e:
                    log.exception(f'Error validating valves for function {function.id}: {e}')
                    raise e

        return await Functions.sync_functions(user.id, form_data.functions, db=db)
    except Exception as e:
        log.exception(f'Failed to load a function: {e}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e, 'Error loading function'),
        )


############################
# CreateNewFunction
############################


@router.post('/create', response_model=FunctionResponse | None)
async def create_new_function(
    request: Request,
    form_data: FunctionForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    if not form_data.id.isidentifier():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Only alphanumeric characters and underscores are allowed in the id',
        )

    form_data.id = form_data.id.lower()

    function = await Functions.get_function_by_id(form_data.id, db=db)
    if function is None:
        try:
            form_data.content = replace_imports(form_data.content)
            function_module, function_type, frontmatter = await load_function_module_by_id(
                form_data.id,
                content=form_data.content,
            )
            form_data.meta.manifest = frontmatter

            FUNCTIONS = get_functions_cache(request)
            FUNCTIONS[form_data.id] = function_module

            function = await Functions.insert_new_function(user.id, function_type, form_data, db=db)

            function_cache_dir = CACHE_DIR / 'functions' / form_data.id
            function_cache_dir.mkdir(parents=True, exist_ok=True)

            if function_type == 'filter' and getattr(function_module, 'toggle', None):
                await Functions.update_function_metadata_by_id(form_data.id, {'toggle': True}, db=db)

            if function:
                await publish_event(
                    request,
                    EVENTS.FUNCTION_CREATED,
                    actor=user,
                    subject_id=function.id,
                    data={'type': function.type, 'name': function.name},
                )
                return function
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT('Error creating function'),
                )
        except HTTPException:
            raise
        except Exception as e:
            log.exception(f'Failed to create a new function: {e}')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(e, 'Error creating function'),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ID_TAKEN,
        )


############################
# GetFunctionById
############################


@router.get('/id/{id}', response_model=FunctionModel | None)
async def get_function_by_id(id: str, user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)):
    function = await Functions.get_function_by_id(id, db=db)

    if function:
        return function
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# ToggleFunctionById
############################


@router.post('/id/{id}/toggle', response_model=FunctionModel | None)
async def toggle_function_by_id(
    request: Request,
    id: str,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    function = await Functions.get_function_by_id(id, db=db)
    if function:
        lifecycle_event = build_event(
            request,
            EVENTS.FUNCTION_DISABLE_STARTED if function.is_active else EVENTS.FUNCTION_ENABLE_STARTED,
            actor=user,
            subject_id=function.id,
            subject_type='function',
            data={'type': function.type, 'name': function.name},
        )
        await dispatch_event_functions(
            request.app,
            lifecycle_event,
            request=request,
            extra_function_ids=[function.id] if not function.is_active else None,
        )
        schedule_webhook_dispatch(request.app, lifecycle_event)

        function = await Functions.update_function_by_id(id, {'is_active': not function.is_active}, db=db)

        if function:
            await publish_event(
                request,
                EVENTS.FUNCTION_ENABLED if function.is_active else EVENTS.FUNCTION_DISABLED,
                actor=user,
                subject_id=function.id,
                subject_type='function',
                data={'type': function.type, 'name': function.name},
            )
            return function
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error updating function'),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# ToggleGlobalById
############################


@router.post('/id/{id}/toggle/global', response_model=FunctionModel | None)
async def toggle_global_by_id(
    request: Request,
    id: str,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    function = await Functions.get_function_by_id(id, db=db)
    if function:
        function = await Functions.update_function_by_id(id, {'is_global': not function.is_global}, db=db)

        if function:
            await publish_event(
                request,
                EVENTS.FUNCTION_UPDATED,
                actor=user,
                subject_id=function.id,
                data={'type': function.type, 'name': function.name, 'is_global': function.is_global},
            )
            return function
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error updating function'),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# UpdateFunctionById
############################


@router.post('/id/{id}/update', response_model=FunctionModel | None)
async def update_function_by_id(
    request: Request,
    id: str,
    form_data: FunctionForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        form_data.content = replace_imports(form_data.content)
        function_module, function_type, frontmatter = await load_function_module_by_id(id, content=form_data.content)
        form_data.meta.manifest = frontmatter

        FUNCTIONS = get_functions_cache(request)
        FUNCTIONS[id] = function_module

        updated = {**form_data.model_dump(exclude={'id'}), 'type': function_type}
        log.debug(updated)

        function = await Functions.update_function_by_id(id, updated, db=db)

        if function_type == 'filter' and getattr(function_module, 'toggle', None):
            await Functions.update_function_metadata_by_id(id, {'toggle': True}, db=db)

        if function:
            await publish_event(
                request,
                EVENTS.FUNCTION_UPDATED,
                actor=user,
                subject_id=function.id,
                data={'type': function.type, 'name': function.name},
            )
            return function
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error updating function'),
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e, 'Error updating function'),
        )


############################
# DeleteFunctionById
############################


@router.delete('/id/{id}/delete', response_model=bool)
async def delete_function_by_id(
    request: Request,
    id: str,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    result = await Functions.delete_function_by_id(id, db=db)

    if result:
        FUNCTIONS = get_functions_cache(request)
        FUNCTIONS.pop(id, None)
        await publish_event(
            request,
            EVENTS.FUNCTION_DELETED,
            actor=user,
            subject_id=id,
        )

    return result


############################
# GetFunctionValves
############################


@router.get('/id/{id}/valves', response_model=dict | None)
async def get_function_valves_by_id(
    id: str, user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)
):
    function = await Functions.get_function_by_id(id, db=db)
    if function:
        try:
            valves = await Functions.get_function_valves_by_id(id, db=db)
            return valves
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(e, 'Error getting function valves'),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# GetFunctionValvesSpec
############################


@router.get('/id/{id}/valves/spec', response_model=dict | None)
async def get_function_valves_spec_by_id(
    request: Request,
    id: str,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    function = await Functions.get_function_by_id(id, db=db)
    if function:
        function_module, function_type, frontmatter = await get_function_module_from_cache(request, id)

        if hasattr(function_module, 'Valves'):
            Valves = function_module.Valves
            schema = Valves.schema()
            # Resolve dynamic options for select dropdowns
            schema = resolve_valves_schema_options(Valves, schema, user)
            return schema
        return None
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# UpdateFunctionValves
############################


@router.post('/id/{id}/valves/update', response_model=dict | None)
async def update_function_valves_by_id(
    request: Request,
    id: str,
    form_data: dict,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    function = await Functions.get_function_by_id(id, db=db)
    if function:
        function_module, function_type, frontmatter = await get_function_module_from_cache(request, id)

        if hasattr(function_module, 'Valves'):
            Valves = function_module.Valves

            try:
                form_data = {k: v for k, v in form_data.items() if v is not None}
                valves = Valves(**form_data)

                valves_dict = valves.model_dump(exclude_unset=True)
                await Functions.update_function_valves_by_id(id, valves_dict, db=db)
                await publish_event(
                    request,
                    EVENTS.FUNCTION_VALVES_UPDATED,
                    actor=user,
                    subject_id=id,
                )
                return valves_dict
            except Exception as e:
                log.exception(f'Error updating function values by id {id}: {e}')
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT(e, 'Error updating function valves'),
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )

    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# FunctionUserValves
############################


@router.get('/id/{id}/valves/user', response_model=dict | None)
async def get_function_user_valves_by_id(
    id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    function = await Functions.get_function_by_id(id, db=db)
    if function:
        try:
            user_valves = await Functions.get_user_valves_by_id_and_user_id(id, user.id, db=db)
            return user_valves
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(e, 'Error getting function user valves'),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.get('/id/{id}/valves/user/spec', response_model=dict | None)
async def get_function_user_valves_spec_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    function = await Functions.get_function_by_id(id, db=db)
    if function:
        function_module, function_type, frontmatter = await get_function_module_from_cache(request, id)

        if hasattr(function_module, 'UserValves'):
            UserValves = function_module.UserValves
            schema = UserValves.schema()
            # Resolve dynamic options for select dropdowns
            schema = resolve_valves_schema_options(UserValves, schema, user)
            return schema
        return None
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.post('/id/{id}/valves/user/update', response_model=dict | None)
async def update_function_user_valves_by_id(
    request: Request,
    id: str,
    form_data: dict,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    function = await Functions.get_function_by_id(id, db=db)

    if function:
        function_module, function_type, frontmatter = await get_function_module_from_cache(request, id)

        if hasattr(function_module, 'UserValves'):
            UserValves = function_module.UserValves

            try:
                form_data = {k: v for k, v in form_data.items() if v is not None}
                user_valves = UserValves(**form_data)
                user_valves_dict = user_valves.model_dump(exclude_unset=True)
                await Functions.update_user_valves_by_id_and_user_id(id, user.id, user_valves_dict, db=db)
                await publish_event(
                    request,
                    EVENTS.FUNCTION_VALVES_UPDATED,
                    actor=user,
                    subject_id=id,
                    data={'scope': 'user'},
                )
                return user_valves_dict
            except Exception as e:
                log.exception(f'Error updating function user valves by id {id}: {e}')
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT(e, 'Error updating function user valves'),
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
