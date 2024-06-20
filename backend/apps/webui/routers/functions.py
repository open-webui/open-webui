from fastapi import Depends, FastAPI, HTTPException, status, Request
from datetime import datetime, timedelta
from typing import List, Union, Optional

from fastapi import APIRouter
from pydantic import BaseModel
import json

from apps.webui.models.functions import (
    Functions,
    FunctionForm,
    FunctionModel,
    FunctionResponse,
)
from apps.webui.utils import load_function_module_by_id
from utils.utils import get_verified_user, get_admin_user
from constants import ERROR_MESSAGES

from importlib import util
import os
from pathlib import Path

from config import DATA_DIR, CACHE_DIR, FUNCTIONS_DIR


router = APIRouter()

############################
# GetFunctions
############################


@router.get("/", response_model=List[FunctionResponse])
async def get_functions(user=Depends(get_verified_user)):
    return Functions.get_functions()


############################
# ExportFunctions
############################


@router.get("/export", response_model=List[FunctionModel])
async def get_functions(user=Depends(get_admin_user)):
    return Functions.get_functions()


############################
# CreateNewFunction
############################


@router.post("/create", response_model=Optional[FunctionResponse])
async def create_new_function(
    request: Request, form_data: FunctionForm, user=Depends(get_admin_user)
):
    if not form_data.id.isidentifier():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only alphanumeric characters and underscores are allowed in the id",
        )

    form_data.id = form_data.id.lower()

    function = Functions.get_function_by_id(form_data.id)
    if function == None:
        function_path = os.path.join(FUNCTIONS_DIR, f"{form_data.id}.py")
        try:
            with open(function_path, "w") as function_file:
                function_file.write(form_data.content)

            function_module, function_type = load_function_module_by_id(form_data.id)

            FUNCTIONS = request.app.state.FUNCTIONS
            FUNCTIONS[form_data.id] = function_module

            function = Functions.insert_new_function(user.id, function_type, form_data)

            function_cache_dir = Path(CACHE_DIR) / "functions" / form_data.id
            function_cache_dir.mkdir(parents=True, exist_ok=True)

            if function:
                return function
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT("Error creating function"),
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
# GetFunctionById
############################


@router.get("/id/{id}", response_model=Optional[FunctionModel])
async def get_function_by_id(id: str, user=Depends(get_admin_user)):
    function = Functions.get_function_by_id(id)

    if function:
        return function
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# UpdateFunctionById
############################


@router.post("/id/{id}/update", response_model=Optional[FunctionModel])
async def update_toolkit_by_id(
    request: Request, id: str, form_data: FunctionForm, user=Depends(get_admin_user)
):
    function_path = os.path.join(FUNCTIONS_DIR, f"{id}.py")

    try:
        with open(function_path, "w") as function_file:
            function_file.write(form_data.content)

        function_module, function_type = load_function_module_by_id(id)

        FUNCTIONS = request.app.state.FUNCTIONS
        FUNCTIONS[id] = function_module

        updated = {**form_data.model_dump(exclude={"id"}), "type": function_type}
        print(updated)

        function = Functions.update_function_by_id(id, updated)

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
    request: Request, id: str, user=Depends(get_admin_user)
):
    result = Functions.delete_function_by_id(id)

    if result:
        FUNCTIONS = request.app.state.FUNCTIONS
        if id in FUNCTIONS:
            del FUNCTIONS[id]

        # delete the function file
        function_path = os.path.join(FUNCTIONS_DIR, f"{id}.py")
        os.remove(function_path)

    return result
