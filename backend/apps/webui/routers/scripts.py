from fastapi import (
    Depends,
    HTTPException,
    status,
    UploadFile,
    Request,
)


from datetime import datetime, timedelta
from typing import List, Union, Optional
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse

from pydantic import BaseModel
import json

from apps.webui.models.scripts import (
    Scripts,
    ScriptForm,
    ScriptModel,
    ScriptResponse,
)
from utils.utils import get_verified_user, get_admin_user
from constants import ERROR_MESSAGES

import os
import uuid
import os, shutil, logging

from config import SRC_LOG_LEVELS, UPLOAD_DIR


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


router = APIRouter()

############################
# Create Script
############################


@router.post("/", response_model=Optional[ScriptResponse])
async def create_new_function(
    request: Request, form_data: ScriptForm, user=Depends(get_admin_user)
):
    if not form_data.id.isidentifier():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only alphanumeric characters and underscores are allowed in the id",
        )

    form_data.id = form_data.id.lower()

    script = Scripts.get_script_by_id(form_data.id)
    if script == None:
        try:
            script = Scripts.insert_new_script(user.id, form_data)
            if script:
                return script
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT("Error creating script"),
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
# List Scripts
############################


@router.get("/", response_model=List[ScriptModel])
async def list_scripts(user=Depends(get_verified_user)):
    files = Scripts.get_scripts()
    return files


############################
# Update Script By Id
############################


@router.post("/{id}", response_model=Optional[ScriptModel])
async def update_script_by_id(
    request: Request, id: str, form_data: ScriptForm, user=Depends(get_admin_user)
):
    try:
        updated = {**form_data.model_dump(exclude={"id"})}
        script = Scripts.update_script_by_id(id, updated)
        if script:
            return script
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error updating script"),
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


############################
# Get Script By Id
############################


@router.get("/{id}", response_model=Optional[ScriptModel])
async def get_script_by_id(id: str, user=Depends(get_verified_user)):
    file = Scripts.get_script_by_id(id)

    if file:
        return file
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Get Script Content By Id
############################


@router.get("/{id}/content", response_model=Optional[ScriptModel])
async def get_script_content_by_id(id: str, user=Depends(get_verified_user)):
    file = Scripts.get_script_by_id(id)

    if file:
        file_path = Path(file.meta["path"])

        # Check if the file already exists in the cache
        if file_path.is_file():
            print(f"file_path: {file_path}")
            return FileResponse(file_path)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Delete Script By Id
############################


@router.delete("/{id}")
async def delete_script_by_id(id: str, user=Depends(get_verified_user)):
    file = Scripts.get_script_by_id(id)

    if file:
        result = Scripts.delete_script_by_id(id)
        if result:
            return {"message": "Script deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error deleting file"),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
