from fastapi import Depends, FastAPI, HTTPException, status, Request
from datetime import datetime, timedelta
from typing import List, Union, Optional

from fastapi import APIRouter
from pydantic import BaseModel
import json

from apps.webui.models.users import Users
from apps.webui.models.tools import Tools, ToolForm, ToolModel, ToolResponse
from apps.webui.utils import load_toolkit_module_by_id

from utils.utils import get_admin_user, get_verified_user
from utils.tools import get_tools_specs
from constants import ERROR_MESSAGES

from importlib import util
import os
from pathlib import Path

from config import DATA_DIR, CACHE_DIR


TOOLS_DIR = f"{DATA_DIR}/tools"
os.makedirs(TOOLS_DIR, exist_ok=True)


router = APIRouter()

############################
# GetToolkits
############################


@router.get("/", response_model=List[ToolResponse])
async def get_toolkits(user=Depends(get_verified_user)):
    toolkits = [toolkit for toolkit in Tools.get_tools()]
    return toolkits


############################
# ExportToolKits
############################


@router.get("/export", response_model=List[ToolModel])
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
    if toolkit == None:
        toolkit_path = os.path.join(TOOLS_DIR, f"{form_data.id}.py")
        try:
            with open(toolkit_path, "w") as tool_file:
                tool_file.write(form_data.content)

            toolkit_module, frontmatter = load_toolkit_module_by_id(form_data.id)
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
                detail=ERROR_MESSAGES.DEFAULT(e),
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
    toolkit_path = os.path.join(TOOLS_DIR, f"{id}.py")

    try:
        with open(toolkit_path, "w") as tool_file:
            tool_file.write(form_data.content)

        toolkit_module, frontmatter = load_toolkit_module_by_id(id)
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
            detail=ERROR_MESSAGES.DEFAULT(e),
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

        # delete the toolkit file
        toolkit_path = os.path.join(TOOLS_DIR, f"{id}.py")
        os.remove(toolkit_path)

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
                detail=ERROR_MESSAGES.DEFAULT(e),
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
            toolkit_module, frontmatter = load_toolkit_module_by_id(id)
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
            toolkit_module, frontmatter = load_toolkit_module_by_id(id)
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
                detail=ERROR_MESSAGES.DEFAULT(e),
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
            toolkit_module, frontmatter = load_toolkit_module_by_id(id)
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
            toolkit_module, frontmatter = load_toolkit_module_by_id(id)
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
