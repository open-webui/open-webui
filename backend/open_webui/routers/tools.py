import logging
from pathlib import Path
from typing import Optional
import time
import re
import aiohttp
from pydantic import BaseModel, HttpUrl
from fastapi import APIRouter, Depends, HTTPException, Request, status


from open_webui.models.tools import (
    ToolForm,
    ToolModel,
    ToolResponse,
    ToolUserResponse,
    Tools,
)
from open_webui.utils.plugin import load_tool_module_by_id, replace_imports
from open_webui.utils.tools import get_tool_specs
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_access, has_permission
from open_webui.utils.tools import get_tool_servers

from open_webui.env import SRC_LOG_LEVELS
from open_webui.config import CACHE_DIR, BYPASS_ADMIN_ACCESS_CONTROL
from open_webui.constants import ERROR_MESSAGES


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


router = APIRouter()


############################
# GetTools
############################


@router.get("/", response_model=list[ToolUserResponse])
async def get_tools(request: Request, user=Depends(get_verified_user)):
    tools = Tools.get_tools()

    for server in await get_tool_servers(request):
        tools.append(
            ToolUserResponse(
                **{
                    "id": f"server:{server.get('id')}",
                    "user_id": f"server:{server.get('id')}",
                    "name": server.get("openapi", {})
                    .get("info", {})
                    .get("title", "Tool Server"),
                    "meta": {
                        "description": server.get("openapi", {})
                        .get("info", {})
                        .get("description", ""),
                    },
                    "access_control": request.app.state.config.TOOL_SERVER_CONNECTIONS[
                        server.get("idx", 0)
                    ]
                    .get("config", {})
                    .get("access_control", None),
                    "updated_at": int(time.time()),
                    "created_at": int(time.time()),
                }
            )
        )

    if user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL:
        # Admin can see all tools
        return tools
    else:
        tools = [
            tool
            for tool in tools
            if tool.user_id == user.id
            or has_access(user.id, "read", tool.access_control)
        ]
        return tools


############################
# GetToolList
############################


@router.get("/list", response_model=list[ToolUserResponse])
async def get_tool_list(user=Depends(get_verified_user)):
    if user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL:
        tools = Tools.get_tools()
    else:
        tools = Tools.get_tools_by_user_id(user.id, "write")
    return tools


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
async def load_tool_from_url(
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
    tool_name = (
        file_name[:-3]
        if (
            file_name.endswith(".py")
            and (not file_name.startswith(("main.py", "index.py", "__init__.py")))
        )
        else url_parts[-2] if len(url_parts) > 1 else "function"
    )

    try:
        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.get(
                url, headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status != 200:
                    raise HTTPException(
                        status_code=resp.status, detail="Failed to fetch the tool"
                    )
                data = await resp.text()
                if not data:
                    raise HTTPException(
                        status_code=400, detail="No data received from the URL"
                    )
        return {
            "name": tool_name,
            "content": data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error importing tool: {e}")


############################
# ExportTools
############################


@router.get("/export", response_model=list[ToolModel])
async def export_tools(user=Depends(get_admin_user)):
    tools = Tools.get_tools()
    return tools


############################
# CreateNewTools
############################


@router.post("/create", response_model=Optional[ToolResponse])
async def create_new_tools(
    request: Request,
    form_data: ToolForm,
    user=Depends(get_verified_user),
):
    if user.role != "admin" and not has_permission(
        user.id, "workspace.tools", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    if not form_data.id.isidentifier():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only alphanumeric characters and underscores are allowed in the id",
        )

    form_data.id = form_data.id.lower()

    tools = Tools.get_tool_by_id(form_data.id)
    if tools is None:
        try:
            form_data.content = replace_imports(form_data.content)
            tool_module, frontmatter = load_tool_module_by_id(
                form_data.id, content=form_data.content
            )
            form_data.meta.manifest = frontmatter

            TOOLS = request.app.state.TOOLS
            TOOLS[form_data.id] = tool_module

            specs = get_tool_specs(TOOLS[form_data.id])
            tools = Tools.insert_new_tool(user.id, form_data, specs)

            tool_cache_dir = CACHE_DIR / "tools" / form_data.id
            tool_cache_dir.mkdir(parents=True, exist_ok=True)

            if tools:
                return tools
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT("Error creating tools"),
                )
        except Exception as e:
            log.exception(f"Failed to load the tool by id {form_data.id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(str(e)),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ID_TAKEN,
        )


############################
# GetToolsById
############################


@router.get("/id/{id}", response_model=Optional[ToolModel])
async def get_tools_by_id(id: str, user=Depends(get_verified_user)):
    tools = Tools.get_tool_by_id(id)

    if tools:
        if (
            user.role == "admin"
            or tools.user_id == user.id
            or has_access(user.id, "read", tools.access_control)
        ):
            return tools
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# UpdateToolsById
############################


@router.post("/id/{id}/update", response_model=Optional[ToolModel])
async def update_tools_by_id(
    request: Request,
    id: str,
    form_data: ToolForm,
    user=Depends(get_verified_user),
):
    tools = Tools.get_tool_by_id(id)
    if not tools:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Is the user the original creator, in a group with write access, or an admin
    if (
        tools.user_id != user.id
        and not has_access(user.id, "write", tools.access_control)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    try:
        form_data.content = replace_imports(form_data.content)
        tool_module, frontmatter = load_tool_module_by_id(id, content=form_data.content)
        form_data.meta.manifest = frontmatter

        TOOLS = request.app.state.TOOLS
        TOOLS[id] = tool_module

        specs = get_tool_specs(TOOLS[id])

        updated = {
            **form_data.model_dump(exclude={"id"}),
            "specs": specs,
        }

        log.debug(updated)
        tools = Tools.update_tool_by_id(id, updated)

        if tools:
            return tools
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error updating tools"),
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(str(e)),
        )


############################
# DeleteToolsById
############################


@router.delete("/id/{id}/delete", response_model=bool)
async def delete_tools_by_id(
    request: Request, id: str, user=Depends(get_verified_user)
):
    tools = Tools.get_tool_by_id(id)
    if not tools:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        tools.user_id != user.id
        and not has_access(user.id, "write", tools.access_control)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    result = Tools.delete_tool_by_id(id)
    if result:
        TOOLS = request.app.state.TOOLS
        if id in TOOLS:
            del TOOLS[id]

    return result


############################
# GetToolValves
############################


@router.get("/id/{id}/valves", response_model=Optional[dict])
async def get_tools_valves_by_id(id: str, user=Depends(get_verified_user)):
    tools = Tools.get_tool_by_id(id)
    if tools:
        try:
            valves = Tools.get_tool_valves_by_id(id)
            return valves
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(str(e)),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# GetToolValvesSpec
############################


@router.get("/id/{id}/valves/spec", response_model=Optional[dict])
async def get_tools_valves_spec_by_id(
    request: Request, id: str, user=Depends(get_verified_user)
):
    tools = Tools.get_tool_by_id(id)
    if tools:
        if id in request.app.state.TOOLS:
            tools_module = request.app.state.TOOLS[id]
        else:
            tools_module, _ = load_tool_module_by_id(id)
            request.app.state.TOOLS[id] = tools_module

        if hasattr(tools_module, "Valves"):
            Valves = tools_module.Valves
            return Valves.schema()
        return None
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# UpdateToolValves
############################


@router.post("/id/{id}/valves/update", response_model=Optional[dict])
async def update_tools_valves_by_id(
    request: Request, id: str, form_data: dict, user=Depends(get_verified_user)
):
    tools = Tools.get_tool_by_id(id)
    if not tools:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        tools.user_id != user.id
        and not has_access(user.id, "write", tools.access_control)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    if id in request.app.state.TOOLS:
        tools_module = request.app.state.TOOLS[id]
    else:
        tools_module, _ = load_tool_module_by_id(id)
        request.app.state.TOOLS[id] = tools_module

    if not hasattr(tools_module, "Valves"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    Valves = tools_module.Valves

    try:
        form_data = {k: v for k, v in form_data.items() if v is not None}
        valves = Valves(**form_data)
        Tools.update_tool_valves_by_id(id, valves.model_dump())
        return valves.model_dump()
    except Exception as e:
        log.exception(f"Failed to update tool valves by id {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(str(e)),
        )


############################
# ToolUserValves
############################


@router.get("/id/{id}/valves/user", response_model=Optional[dict])
async def get_tools_user_valves_by_id(id: str, user=Depends(get_verified_user)):
    tools = Tools.get_tool_by_id(id)
    if tools:
        try:
            user_valves = Tools.get_user_valves_by_id_and_user_id(id, user.id)
            return user_valves
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(str(e)),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.get("/id/{id}/valves/user/spec", response_model=Optional[dict])
async def get_tools_user_valves_spec_by_id(
    request: Request, id: str, user=Depends(get_verified_user)
):
    tools = Tools.get_tool_by_id(id)
    if tools:
        if id in request.app.state.TOOLS:
            tools_module = request.app.state.TOOLS[id]
        else:
            tools_module, _ = load_tool_module_by_id(id)
            request.app.state.TOOLS[id] = tools_module

        if hasattr(tools_module, "UserValves"):
            UserValves = tools_module.UserValves
            return UserValves.schema()
        return None
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.post("/id/{id}/valves/user/update", response_model=Optional[dict])
async def update_tools_user_valves_by_id(
    request: Request, id: str, form_data: dict, user=Depends(get_verified_user)
):
    tools = Tools.get_tool_by_id(id)

    if tools:
        if id in request.app.state.TOOLS:
            tools_module = request.app.state.TOOLS[id]
        else:
            tools_module, _ = load_tool_module_by_id(id)
            request.app.state.TOOLS[id] = tools_module

        if hasattr(tools_module, "UserValves"):
            UserValves = tools_module.UserValves

            try:
                form_data = {k: v for k, v in form_data.items() if v is not None}
                user_valves = UserValves(**form_data)
                Tools.update_user_valves_by_id_and_user_id(
                    id, user.id, user_valves.model_dump()
                )
                return user_valves.model_dump()
            except Exception as e:
                log.exception(f"Failed to update user valves by id {id}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT(str(e)),
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
