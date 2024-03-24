from fastapi import APIRouter, UploadFile, File, BackgroundTasks
from fastapi import Depends, HTTPException, status
from starlette.responses import StreamingResponse, FileResponse


from pydantic import BaseModel

import requests
import os
import aiohttp
import json


from utils.utils import get_admin_user
from utils.misc import calculate_sha256, get_gravatar_url

from config import OLLAMA_BASE_URLS, DATA_DIR, UPLOAD_DIR
from constants import ERROR_MESSAGES


router = APIRouter()


@router.get("/gravatar")
async def get_gravatar(
    email: str,
):
    return get_gravatar_url(email)


@router.get("/db/download")
async def download_db(user=Depends(get_admin_user)):

    return FileResponse(
        f"{DATA_DIR}/webui.db",
        media_type="application/octet-stream",
        filename="webui.db",
    )
