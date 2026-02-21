import os
import re

import logging
import aiohttp
from pathlib import Path
from typing import Optional

from open_webui.env import AIOHTTP_CLIENT_TIMEOUT
from open_webui.models.functions import (
    FunctionForm,
    FunctionModel,
    FunctionResponse,
    FunctionUserResponse,
    FunctionWithValvesModel,
    Functions,
)
from open_webui.utils.plugin import (
    load_function_module_by_id,
    replace_imports,
    get_function_module_from_cache,
    resolve_valves_schema_options,
)
from open_webui.config import CACHE_DIR
from open_webui.constants import ERROR_MESSAGES
from fastapi import APIRouter, Depends, HTTPException, Request, status
from open_webui.utils.auth import get_admin_user, get_verified_user
from pydantic import BaseModel, HttpUrl
from open_webui.internal.db import get_session
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)


router = APIRouter()

############################
# GetFunctions
############################


@router.get("/", response_model=list[FunctionResponse])
async def get_functions(
    user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    return Functions.get_functions(db=db)


@router.get("/list", response_model=list[FunctionUserResponse])
async def get_function_list(
    user=Depends(get_admin_user), db: Session = Depends(get_session)
):
    return Functions.get_function_list(db=db)


############################
# ExportFunctions
############################


@router.get("/export", response_model=list[FunctionModel | FunctionWithValvesModel])
async def get_functions(
    include_valves: bool = False,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    return Functions.get_functions(include_valves=include_valves, db=db)


############################
# LoadFunctionFromLink
############################


class LoadUrlForm(BaseModel):
    url: HttpUrl


def github_url_to_raw_url(url: str) -> str:
    # Handle 'tree' (folder) URLs (add main.py at the end)
    m1 = re.match(r"https://github\.com/([^/]+)/([^/]+)/tree/([^/]+)/(.*)", url)
    if m1:
        org, repo, branch, path = m1.groups()
        return f"https://raw.githubusercontent.com/{org}/{repo}/refs/heads/{branch}/{path.rstrip('/')}/main.py"

    # Handle 'blob' (file) URLs
    m2 = re.match(r"https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.*)", url)
    if m2:
        org, repo, branch, path = m2.groups()
        return (
            f"https://raw.githubusercontent.com/{org}/{repo}/refs/heads/{branch}/{path}"
        )

    # No match; return as-is
    return url


@router.post("/load/url", response_model=Optional[dict])
async def load_function_from_url(
    request: Request, form_data: LoadUrlForm, user=Depends(get_admin_user)
):
    # NOTE: This is NOT a SSRF vulnerability:
    # This endpoint is admin-only (see get_admin_user), meant for *trusted* internal use,
    # and does NOT accept untrusted user input. Access is enforced by authentication.

    url = str(form_data.url)
    if not url:
        raise HTTPException(status_code=400, detail="Please enter a valid URL")

    url = github_url_to_raw_url(url)
    url_parts = url.rstrip("/").split("/")

    file_name = url_parts[-1]
    function_name = (
        file_name[:-3]
        if (
            file_name.endswith(".py")
            and (not file_name.startswith(("main.py", "index.py", "__init__.py")))
        )
        else url_parts[-2] if len(url_parts) > 1 else "function"
    )

    try:
        async with aiohttp.ClientSession(
            trust_env=True, timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
        ) as session:
            async with session.get(
                url, headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status != 200:
                    raise HTTPException(
                        status_code=resp.status, detail="Failed to fetch the function"
                    )
                data = await resp.text()
                if not data:
                    raise HTTPException(
                        status_code=400, detail="No data received from the URL"
                    )
        return {
            "name": function_name,
            "content": data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error importing function: {e}")


############################
# SyncFunctions
############################


class SyncFunctionsForm(BaseModel):
    functions: list[FunctionWithValvesModel] = []


@router.post("/sync", response_model=list[FunctionWithValvesModel])
async def sync_functions(
    request: Request,
    form_data: SyncFunctionsForm,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    try:
        for function in form_data.functions:
            function.content = replace_imports(function.content)
            function_module, function_type, frontmatter = load_function_module_by_id(
                function.id,
                content=function.content,
            )

            if hasattr(function_module, "Valves") and function.valves:
                Valves = function_module.Valves
                try:
                    Valves(
                        **{k: v for k, v in function.valves.items() if v is not None}
                    )
                except Exception as e:
                    log.exception(
                        f"Error validating valves for function {function.id}: {e}"
                    )
                    raise e

        return Functions.sync_functions(user.id, form_data.functions, db=db)
    except Exception as e:
        log.exception(f"Failed to load a function: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


############################
# CreateNewFunction
############################


@router.post("/create", response_model=Optional[FunctionResponse])
async def create_new_function(
    request: Request,
    form_data: FunctionForm,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    if not form_data.id.isidentifier():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only alphanumeric characters and underscores are allowed in the id",
        )

    form_data.id = form_data.id.lower()

    function = Functions.get_function_by_id(form_data.id, db=db)
    if function is None:
        try:
            form_data.content = replace_imports(form_data.content)
            function_module, function_type, frontmatter = load_function_module_by_id(
                form_data.id,
                content=form_data.content,
            )
            form_data.meta.manifest = frontmatter

            FUNCTIONS = request.app.state.FUNCTIONS
            FUNCTIONS[form_data.id] = function_module

            function = Functions.insert_new_function(
                user.id, function_type, form_data, db=db
            )

            function_cache_dir = CACHE_DIR / "functions" / form_data.id
            function_cache_dir.mkdir(parents=True, exist_ok=True)

            if function_type == "filter" and getattr(function_module, "toggle", None):
                Functions.update_function_metadata_by_id(
                    form_data.id, {"toggle": True}, db=db
                )

            if function:
                return function
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT("Error creating function"),
                )
        except Exception as e:
            log.exception(f"Failed to create a new function: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(e),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ID_TAKEN,
        )


############################
# GetFunctionById
############################


@router.get("/id/{id}", response_model=Optional[FunctionModel])
async def get_function_by_id(
    id: str, user=Depends(get_admin_user), db: Session = Depends(get_session)
):
    function = Functions.get_function_by_id(id, db=db)

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


@router.post("/id/{id}/toggle", response_model=Optional[FunctionModel])
async def toggle_function_by_id(
    id: str, user=Depends(get_admin_user), db: Session = Depends(get_session)
):
    function = Functions.get_function_by_id(id, db=db)
    if function:
        function = Functions.update_function_by_id(
            id, {"is_active": not function.is_active}, db=db
        )

        if function:
            return function
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error updating function"),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# ToggleGlobalById
############################


@router.post("/id/{id}/toggle/global", response_model=Optional[FunctionModel])
async def toggle_global_by_id(
    id: str, user=Depends(get_admin_user), db: Session = Depends(get_session)
):
    function = Functions.get_function_by_id(id, db=db)
    if function:
        function = Functions.update_function_by_id(
            id, {"is_global": not function.is_global}, db=db
        )

        if function:
            return function
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error updating function"),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# UpdateFunctionById
############################


@router.post("/id/{id}/update", response_model=Optional[FunctionModel])
async def update_function_by_id(
    request: Request,
    id: str,
    form_data: FunctionForm,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    try:
        form_data.content = replace_imports(form_data.content)
        function_module, function_type, frontmatter = load_function_module_by_id(
            id, content=form_data.content
        )
        form_data.meta.manifest = frontmatter

        FUNCTIONS = request.app.state.FUNCTIONS
        FUNCTIONS[id] = function_module

        updated = {**form_data.model_dump(exclude={"id"}), "type": function_type}
        log.debug(updated)

        function = Functions.update_function_by_id(id, updated, db=db)

        if function_type == "filter" and getattr(function_module, "toggle", None):
            Functions.update_function_metadata_by_id(id, {"toggle": True}, db=db)

        if function:
            return function
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error updating function"),
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


############################
# DeleteFunctionById
############################


@router.delete("/id/{id}/delete", response_model=bool)
async def delete_function_by_id(
    request: Request,
    id: str,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    result = Functions.delete_function_by_id(id, db=db)

    if result:
        FUNCTIONS = request.app.state.FUNCTIONS
        if id in FUNCTIONS:
            del FUNCTIONS[id]

    return result


############################
# GetFunctionValves
############################


@router.get("/id/{id}/valves", response_model=Optional[dict])
async def get_function_valves_by_id(
    id: str, user=Depends(get_admin_user), db: Session = Depends(get_session)
):
    function = Functions.get_function_by_id(id, db=db)
    if function:
        try:
            valves = Functions.get_function_valves_by_id(id, db=db)
            return valves
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(e),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# GetFunctionValvesSpec
############################


@router.get("/id/{id}/valves/spec", response_model=Optional[dict])
async def get_function_valves_spec_by_id(
    request: Request,
    id: str,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    function = Functions.get_function_by_id(id, db=db)
    if function:
        function_module, function_type, frontmatter = get_function_module_from_cache(
            request, id
        )

        if hasattr(function_module, "Valves"):
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


@router.post("/id/{id}/valves/update", response_model=Optional[dict])
async def update_function_valves_by_id(
    request: Request,
    id: str,
    form_data: dict,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    function = Functions.get_function_by_id(id, db=db)
    if function:
        function_module, function_type, frontmatter = get_function_module_from_cache(
            request, id
        )

        if hasattr(function_module, "Valves"):
            Valves = function_module.Valves

            try:
                form_data = {k: v for k, v in form_data.items() if v is not None}
                valves = Valves(**form_data)

                valves_dict = valves.model_dump(exclude_unset=True)
                Functions.update_function_valves_by_id(id, valves_dict, db=db)
                return valves_dict
            except Exception as e:
                log.exception(f"Error updating function values by id {id}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT(e),
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


@router.get("/id/{id}/valves/user", response_model=Optional[dict])
async def get_function_user_valves_by_id(
    id: str, user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    function = Functions.get_function_by_id(id, db=db)
    if function:
        try:
            user_valves = Functions.get_user_valves_by_id_and_user_id(
                id, user.id, db=db
            )
            return user_valves
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(e),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.get("/id/{id}/valves/user/spec", response_model=Optional[dict])
async def get_function_user_valves_spec_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    function = Functions.get_function_by_id(id, db=db)
    if function:
        function_module, function_type, frontmatter = get_function_module_from_cache(
            request, id
        )

        if hasattr(function_module, "UserValves"):
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


@router.post("/id/{id}/valves/user/update", response_model=Optional[dict])
async def update_function_user_valves_by_id(
    request: Request,
    id: str,
    form_data: dict,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    function = Functions.get_function_by_id(id, db=db)

    if function:
        function_module, function_type, frontmatter = get_function_module_from_cache(
            request, id
        )

        if hasattr(function_module, "UserValves"):
            UserValves = function_module.UserValves

            try:
                form_data = {k: v for k, v in form_data.items() if v is not None}
                user_valves = UserValves(**form_data)
                user_valves_dict = user_valves.model_dump(exclude_unset=True)
                Functions.update_user_valves_by_id_and_user_id(
                    id, user.id, user_valves_dict, db=db
                )
                return user_valves_dict
            except Exception as e:
                log.exception(f"Error updating function user valves by id {id}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT(e),
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
