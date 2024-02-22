import hashlib
import json
from pathlib import Path

import requests
from config import VERTEXAI_API_BASE_URL, VERTEXAI_API_KEY, CACHE_DIR
from constants import ERROR_MESSAGES
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from utils.utils import (
    get_verified_user,
    get_admin_user,
)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.VERTEXAI_API_BASE_URL = VERTEXAI_API_BASE_URL
app.state.VERTEXAI_API_KEY = VERTEXAI_API_KEY


class UrlUpdateForm(BaseModel):
    url: str


class KeyUpdateForm(BaseModel):
    key: str


@app.get("/url")
async def get_vertexai_url(user=Depends(get_admin_user)):
    return {"VERTEXAI_API_BASE_URL": app.state.VERTEXAI_API_BASE_URL}


@app.post("/url/update")
async def update_vertexai_url(form_data: UrlUpdateForm, user=Depends(get_admin_user)):
    app.state.VERTEXAI_API_BASE_URL = form_data.url
    return {"VERTEXAI_API_BASE_URL": app.state.VERTEXAI_API_BASE_URL}


@app.get("/key")
async def get_vertexai_key(user=Depends(get_admin_user)):
    return {"VERTEXAI_API_KEY": app.state.VERTEXAI_API_KEY}


@app.post("/key/update")
async def update_vertexai_key(form_data: KeyUpdateForm, user=Depends(get_admin_user)):
    app.state.VERTEXAI_API_KEY = form_data.key
    return {"VERTEXAI_API_KEY": app.state.VERTEXAI_API_KEY}


@app.get("/models")
async def get_vertexai_models(user=Depends(get_verified_user)):
    return {
        "object": "list",
        "data": [
            {
                "id": "gemini-pro",
                "object": "model",
                "created": 1686935002,
                "owned_by": "google"
            }
        ]
    }


@app.post("/audio/speech")
async def speech(request: Request, user=Depends(get_verified_user)):
    target_url = f"{app.state.VERTEXAI_API_BASE_URL}/audio/speech"

    if app.state.VERTEXAI_API_KEY == "":
        raise HTTPException(status_code=401, detail=ERROR_MESSAGES.API_KEY_NOT_FOUND)

    body = await request.body()

    name = hashlib.sha256(body).hexdigest()

    SPEECH_CACHE_DIR = Path(CACHE_DIR).joinpath("./audio/speech/")
    SPEECH_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    file_path = SPEECH_CACHE_DIR.joinpath(f"{name}.mp3")
    file_body_path = SPEECH_CACHE_DIR.joinpath(f"{name}.json")

    # Check if the file already exists in the cache
    if file_path.is_file():
        return FileResponse(file_path)

    headers = {}
    headers["Authorization"] = f"Bearer {app.state.VERTEXAI_API_KEY}"
    headers["Content-Type"] = "application/json"

    try:
        print("vertexai")
        r = requests.post(
            url=target_url,
            data=body,
            headers=headers,
            stream=True,
        )

        r.raise_for_status()

        # Save the streaming content to a file
        with open(file_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

        with open(file_body_path, "w") as f:
            json.dump(json.loads(body.decode("utf-8")), f)

        # Return the saved file
        return FileResponse(file_path)

    except Exception as e:
        print(e)
        error_detail = "Open WebUI: Server Connection Error"
        if r is not None:
            try:
                res = r.json()
                if "error" in res:
                    error_detail = f"External: {res['error']}"
            except:
                error_detail = f"External: {e}"

        raise HTTPException(status_code=r.status_code, detail=error_detail)


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(path: str, request: Request, user=Depends(get_verified_user)):
    target_url = f"{app.state.VERTEXAI_API_BASE_URL}/{path}"
    print(target_url, app.state.VERTEXAI_API_KEY)

    if app.state.VERTEXAI_API_KEY == "":
        raise HTTPException(status_code=401, detail=ERROR_MESSAGES.API_KEY_NOT_FOUND)

    body = await request.body()

    headers = {}
    headers["Authorization"] = f"Bearer {app.state.VERTEXAI_API_KEY}"
    headers["Content-Type"] = "application/json"

    try:
        r = requests.request(
            method=request.method,
            url=target_url,
            data=body,
            headers=headers,
            stream=True,
        )

        r.raise_for_status()

        # Check if response is SSE
        if "text/event-stream" in r.headers.get("Content-Type", ""):
            return StreamingResponse(
                r.iter_content(chunk_size=8192),
                status_code=r.status_code,
                headers=dict(r.headers),
            )
        else:
            # For non-SSE, read the response and return it
            # response_data = (
            #     r.json()
            #     if r.headers.get("Content-Type", "")
            #     == "application/json"
            #     else r.text
            # )

            response_data = r.json()

            if "vertexai" in app.state.VERTEXAI_API_BASE_URL and path == "models":
                response_data["data"] = list(
                    filter(lambda model: "gpt" in model["id"], response_data["data"])
                )

            return response_data
    except Exception as e:
        print(e)
        error_detail = "Open WebUI: Server Connection Error"
        if r is not None:
            try:
                res = r.json()
                if "error" in res:
                    error_detail = f"External: {res['error']}"
            except:
                error_detail = f"External: {e}"

        raise HTTPException(status_code=r.status_code, detail=error_detail)
