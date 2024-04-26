import os
import logging
import tempfile
import io
from fastapi import (
    FastAPI,
    Request,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
)

from fastapi.responses import StreamingResponse, JSONResponse, FileResponse

from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel
from pydantic import BaseModel


import requests
import hashlib
from pathlib import Path
from urllib.parse import urljoin
import json


from constants import ERROR_MESSAGES
from utils.utils import (
    decode_token,
    get_current_user,
    get_verified_user,
    get_admin_user,
)
from utils.misc import calculate_sha256
import requests
from config import (
    SRC_LOG_LEVELS,
    UPLOAD_DIR,
    CACHE_DIR,
    WHISPER_MODEL,
    WHISPER_MODEL_DIR,
    HEADERS,
    NEXTCLOUD_USERNAME,
    NEXTCLOUD_PASSWORD,
    WHISPER_MODEL_AUTO_UPDATE,
    DEVICE_TYPE,
    AUDIO_OPENAI_API_BASE_URL,
    AUDIO_OPENAI_API_KEY,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["AUDIO"])

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.OPENAI_API_BASE_URL = AUDIO_OPENAI_API_BASE_URL
app.state.OPENAI_API_KEY = AUDIO_OPENAI_API_KEY

# setting device type for whisper model
whisper_device_type = DEVICE_TYPE if DEVICE_TYPE and DEVICE_TYPE == "cuda" else "cpu"
log.info(f"whisper_device_type: {whisper_device_type}")

# Construct the relative URLs
relative_url = "cache/audio/speech"
audio_url = "cache/audio"

# Combine the base URL and relative URL
SPEECH_CACHE_DIR = urljoin(CACHE_DIR, relative_url)
SPEECH_CACHE_FOLDER = urljoin(CACHE_DIR, audio_url)


class OpenAIConfigUpdateForm(BaseModel):
    url: str
    key: str


@app.get("/config")
async def get_openai_config(user=Depends(get_admin_user)):
    return {
        "OPENAI_API_BASE_URL": app.state.OPENAI_API_BASE_URL,
        "OPENAI_API_KEY": app.state.OPENAI_API_KEY,
    }


@app.post("/config/update")
async def update_openai_config(
    form_data: OpenAIConfigUpdateForm, user=Depends(get_admin_user)
):
    if form_data.key == "":
        raise HTTPException(status_code=400, detail=ERROR_MESSAGES.API_KEY_NOT_FOUND)

    app.state.OPENAI_API_BASE_URL = form_data.url
    app.state.OPENAI_API_KEY = form_data.key

    return {
        "status": True,
        "OPENAI_API_BASE_URL": app.state.OPENAI_API_BASE_URL,
        "OPENAI_API_KEY": app.state.OPENAI_API_KEY,
    }


@app.post("/speech")
async def speech(request: Request, user=Depends(get_verified_user)):
    body = await request.body()
    name = hashlib.sha256(body).hexdigest()

    # Define file paths in the Nexcloud folder space
    response = requests.request("PROPFIND", SPEECH_CACHE_DIR, auth=(NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD), headers=HEADERS)
    if response.status_code == 404:
        # If directory doesn't exist, create it
        response = requests.request("MKCOL", SPEECH_CACHE_FOLDER, auth=(NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD), headers=HEADERS)
        print("Directory 'Audio Cache' created successfully." if response.status_code == 201 else f"Failed to create directory 'Audio Cache'. Status code: {response.status_code}")
        response = requests.request("MKCOL", SPEECH_CACHE_DIR, auth=(NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD), headers=HEADERS)
        print("Directory 'Speech Cache' created successfully." if response.status_code == 201 else f"Failed to create directory 'Speech Cache'. Status code: {response.status_code}")

    file_path = urljoin(SPEECH_CACHE_DIR, f"{name}.mp3")
    file_body_path = urljoin(SPEECH_CACHE_DIR, f"{name}.json")

    # Check if the file already exists in the cache
    response = requests.request("PROPFIND", file_path, auth=(NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD), headers=HEADERS)
    if response.status_code == 200:
        # If the file exists, return it
        response = requests.request("GET", file_path, auth=(NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD), headers=HEADERS)
        if response.status_code == 200:
            # Return the file if it exists
            return FileResponse(io.BytesIO(response.content), media_type="audio/mp3", filename=f"{name}.mp3")

    headers = {}
    headers["Authorization"] = f"Bearer {app.state.OPENAI_API_KEY}"
    headers["Content-Type"] = "application/json"

    r = None
    try:
        r = requests.post(
            url=f"{app.state.OPENAI_API_BASE_URL}/audio/speech",
            data=body,
            headers=headers,
            stream=True,
        )

        r.raise_for_status()

        # Save the streaming content to a file
        with requests.request("PUT", file_path, data=r.content, auth=(NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD), headers=HEADERS) as f:
            pass

        with requests.request("PUT", file_body_path, data=body, auth=(NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD), headers=HEADERS) as f:
            pass

        # Return the saved file
        return FileResponse(io.BytesIO(r.content), media_type="audio/mp3", filename=f"{name}.mp3")
    
    except Exception as e:
        log.exception(e)
        error_detail = "Open WebUI: Server Connection Error"
        if r is not None:
            try:
                res = r.json()
                if "error" in res:
                    error_detail = f"External: {res['error']['message']}"
            except:
                error_detail = f"External: {e}"

        raise HTTPException(
            status_code=r.status_code if r != None else 500,
            detail=error_detail,
        )