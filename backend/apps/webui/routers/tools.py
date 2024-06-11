from fastapi import Depends, FastAPI, HTTPException, status
from datetime import datetime, timedelta
from typing import List, Union, Optional

from fastapi import APIRouter
from pydantic import BaseModel
import json

from apps.webui.models.tools import Tools, ToolForm, ToolModel, ToolResponse

from utils.utils import get_current_user, get_admin_user
from utils.tools import get_tools_specs
from constants import ERROR_MESSAGES

from importlib import util
import os

from config import DATA_DIR

TOOLS_DIR = f"{DATA_DIR}/tools"
os.makedirs(TOOLS_DIR, exist_ok=True)

TOOLS = {}


router = APIRouter()


def load_toolkit_module_from_path(tools_id, tools_path):
    spec = util.spec_from_file_location(tools_id, tools_path)
    module = util.module_from_spec(spec)

    try:
        spec.loader.exec_module(module)
        print(f"Loaded module: {module.__name__}")
        if hasattr(module, "Tools"):
            return module.Tools()
        else:
            raise Exception("No Tools class found")
    except Exception as e:
        print(f"Error loading module: {tools_id}")

        # Move the file to the error folder
        os.rename(tools_path, f"{tools_path}.error")
        raise e


############################
# GetToolkits
############################


@router.get("/", response_model=List[ToolResponse])
async def get_toolkits(user=Depends(get_current_user)):
    toolkits = [ToolResponse(**toolkit) for toolkit in Tools.get_tools()]
    return toolkits


############################
# CreateNewToolKit
############################


@router.post("/create", response_model=Optional[ToolResponse])
async def create_new_toolkit(form_data: ToolForm, user=Depends(get_admin_user)):
    toolkit = Tools.get_tool_by_id(form_data.id)
    if toolkit == None:
        toolkit_path = os.path.join(TOOLS_DIR, f"{form_data.id}.py")
        try:
            with open(toolkit_path, "w") as tool_file:
                tool_file.write(form_data.content)

            toolkit_module = load_toolkit_module_from_path(form_data.id, toolkit_path)
            TOOLS[form_data.id] = toolkit_module

            specs = get_tools_specs(TOOLS[form_data.id])
            toolkit = Tools.insert_new_tool(user.id, form_data, specs)

            if toolkit:
                return ToolResponse(**toolkit)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.FILE_EXISTS,
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(e),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NAME_TAG_TAKEN,
        )


############################
# GetToolkitById
############################


@router.get("/id/{id}", response_model=Optional[ToolResponse])
async def get_toolkit_by_id(id: str, user=Depends(get_admin_user)):
    toolkit = Tools.get_tool_by_id(id)

    if toolkit:
        return ToolResponse(**toolkit)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# UpdateToolkitById
############################


@router.post("/id/{id}/update", response_model=Optional[ToolResponse])
async def update_toolkit_by_id(
    id: str, form_data: ToolForm, user=Depends(get_admin_user)
):
    toolkit_path = os.path.join(TOOLS_DIR, f"{id}.py")

    try:
        with open(toolkit_path, "w") as tool_file:
            tool_file.write(form_data.content)

        toolkit_module = load_toolkit_module_from_path(id, toolkit_path)
        TOOLS[id] = toolkit_module

        specs = get_tools_specs(TOOLS[id])
        toolkit = Tools.update_tool_by_id(
            id, {**form_data.model_dump(), "specs": specs}
        )

        if toolkit:
            return ToolResponse(**toolkit)
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
async def delete_toolkit_by_id(id: str, user=Depends(get_admin_user)):
    result = Tools.delete_tool_by_id(id)
    return result
