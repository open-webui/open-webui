import os
from pathlib import Path
from typing import Optional

from open_webui.apps.webui.models.tools import ToolForm, ToolModel, ToolResponse, Tools
from open_webui.apps.webui.utils import load_toolkit_module_by_id, replace_imports
from open_webui.config import CACHE_DIR, DATA_DIR
from open_webui.constants import ERROR_MESSAGES
from fastapi import APIRouter, Depends, HTTPException, Request, status
from open_webui.utils.tools import get_tools_specs
from open_webui.utils.utils import get_admin_user, get_verified_user

TOOLS_DIR = f"{DATA_DIR}/tools"
os.makedirs(TOOLS_DIR, exist_ok=True)


router = APIRouter()

############################
# GetToolkits
############################


@router.get("/", response_model=list[ToolResponse])
async def get_toolkits(user=Depends(get_verified_user)):
    toolkits = [toolkit for toolkit in Tools.get_tools()]
    return toolkits


############################
# ExportToolKits
############################


@router.get("/export", response_model=list[ToolModel])
async def get_toolkits(user=Depends(get_admin_user)):
    toolkits = [toolkit for toolkit in Tools.get_tools()]
    return toolkits


############################
# CreateNewToolKit
############################


@router.post("/create", response_model=Optional[ToolResponse])
async def create_new_toolkit(
    request: Request,
    form_data: ToolForm,
    user=Depends(get_admin_user),
):
    if not form_data.id.isidentifier():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only alphanumeric characters and underscores are allowed in the id",
        )

    form_data.id = form_data.id.lower()

    toolkit = Tools.get_tool_by_id(form_data.id)
    if toolkit is None:
        try:
            form_data.content = replace_imports(form_data.content)
            toolkit_module, frontmatter = load_toolkit_module_by_id(
                form_data.id, content=form_data.content
            )
            form_data.meta.manifest = frontmatter

            TOOLS = request.app.state.TOOLS
            TOOLS[form_data.id] = toolkit_module

            specs = get_tools_specs(TOOLS[form_data.id])
            toolkit = Tools.insert_new_tool(user.id, form_data, specs)

            tool_cache_dir = Path(CACHE_DIR) / "tools" / form_data.id
            tool_cache_dir.mkdir(parents=True, exist_ok=True)

            if toolkit:
                return toolkit
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT("Error creating toolkit"),
                )
        except Exception as e:
            print(e)
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
# GetToolkitById
############################


@router.get("/id/{id}", response_model=Optional[ToolModel])
async def get_toolkit_by_id(id: str, user=Depends(get_admin_user)):
    toolkit = Tools.get_tool_by_id(id)

    if toolkit:
        return toolkit
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# UpdateToolkitById
############################


@router.post("/id/{id}/update", response_model=Optional[ToolModel])
async def update_toolkit_by_id(
    request: Request,
    id: str,
    form_data: ToolForm,
    user=Depends(get_admin_user),
):
    try:
        form_data.content = replace_imports(form_data.content)
        toolkit_module, frontmatter = load_toolkit_module_by_id(
            id, content=form_data.content
        )
        form_data.meta.manifest = frontmatter

        TOOLS = request.app.state.TOOLS
        TOOLS[id] = toolkit_module

        specs = get_tools_specs(TOOLS[id])

        updated = {
            **form_data.model_dump(exclude={"id"}),
            "specs": specs,
        }

        print(updated)
        toolkit = Tools.update_tool_by_id(id, updated)

        if toolkit:
            return toolkit
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error updating toolkit"),
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(str(e)),
        )


############################
# DeleteToolkitById
############################


@router.delete("/id/{id}/delete", response_model=bool)
async def delete_toolkit_by_id(request: Request, id: str, user=Depends(get_admin_user)):
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
async def get_toolkit_valves_by_id(id: str, user=Depends(get_admin_user)):
    toolkit = Tools.get_tool_by_id(id)
    if toolkit:
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
async def get_toolkit_valves_spec_by_id(
    request: Request, id: str, user=Depends(get_admin_user)
):
    toolkit = Tools.get_tool_by_id(id)
    if toolkit:
        if id in request.app.state.TOOLS:
            toolkit_module = request.app.state.TOOLS[id]
        else:
            toolkit_module, _ = load_toolkit_module_by_id(id)
            request.app.state.TOOLS[id] = toolkit_module

        if hasattr(toolkit_module, "Valves"):
            Valves = toolkit_module.Valves
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
async def update_toolkit_valves_by_id(
    request: Request, id: str, form_data: dict, user=Depends(get_admin_user)
):
    toolkit = Tools.get_tool_by_id(id)
    if toolkit:
        if id in request.app.state.TOOLS:
            toolkit_module = request.app.state.TOOLS[id]
        else:
            toolkit_module, _ = load_toolkit_module_by_id(id)
            request.app.state.TOOLS[id] = toolkit_module

        if hasattr(toolkit_module, "Valves"):
            Valves = toolkit_module.Valves

            try:
                form_data = {k: v for k, v in form_data.items() if v is not None}
                valves = Valves(**form_data)
                Tools.update_tool_valves_by_id(id, valves.model_dump())
                return valves.model_dump()
            except Exception as e:
                print(e)
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


############################
# ToolUserValves
############################


@router.get("/id/{id}/valves/user", response_model=Optional[dict])
async def get_toolkit_user_valves_by_id(id: str, user=Depends(get_verified_user)):
    toolkit = Tools.get_tool_by_id(id)
    if toolkit:
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
async def get_toolkit_user_valves_spec_by_id(
    request: Request, id: str, user=Depends(get_verified_user)
):
    toolkit = Tools.get_tool_by_id(id)
    if toolkit:
        if id in request.app.state.TOOLS:
            toolkit_module = request.app.state.TOOLS[id]
        else:
            toolkit_module, _ = load_toolkit_module_by_id(id)
            request.app.state.TOOLS[id] = toolkit_module

        if hasattr(toolkit_module, "UserValves"):
            UserValves = toolkit_module.UserValves
            return UserValves.schema()
        return None
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.post("/id/{id}/valves/user/update", response_model=Optional[dict])
async def update_toolkit_user_valves_by_id(
    request: Request, id: str, form_data: dict, user=Depends(get_verified_user)
):
    toolkit = Tools.get_tool_by_id(id)

    if toolkit:
        if id in request.app.state.TOOLS:
            toolkit_module = request.app.state.TOOLS[id]
        else:
            toolkit_module, _ = load_toolkit_module_by_id(id)
            request.app.state.TOOLS[id] = toolkit_module

        if hasattr(toolkit_module, "UserValves"):
            UserValves = toolkit_module.UserValves

            try:
                form_data = {k: v for k, v in form_data.items() if v is not None}
                user_valves = UserValves(**form_data)
                Tools.update_user_valves_by_id_and_user_id(
                    id, user.id, user_valves.model_dump()
                )
                return user_valves.model_dump()
            except Exception as e:
                print(e)
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
