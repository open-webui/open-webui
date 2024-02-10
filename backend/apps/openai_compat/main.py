from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

import json
import requests
from pydantic import BaseModel

from apps.web.models.users import Users
from utils.utils import decode_token, get_current_user, get_verified_user, get_admin_user
from config import OPENAI_COMPAT_API_KEY_LIST, OPENAI_COMPAT_API_BASE_URL_LIST, OPENAI_COMPAT_MODEL_LABEL_LIST

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# for simplicity, we store the 
STATE_LIST_SEPARATOR = ";"
app.state.OPENAI_COMPAT_API_KEY_LIST = OPENAI_COMPAT_API_KEY_LIST
app.state.OPENAI_COMPAT_API_BASE_URL_LIST = OPENAI_COMPAT_API_BASE_URL_LIST
app.state.OPENAI_COMPAT_MODEL_LABEL_LIST = OPENAI_COMPAT_MODEL_LABEL_LIST


class UrlUpdateForm(BaseModel):
    url: str


class KeyUpdateForm(BaseModel):
    key: str

class LabelUpdateForm(BaseModel):
    label: str

@app.get("/url")
async def get_openai_url(user=Depends(get_admin_user)):
    return {"OPENAI_COMPAT_API_BASE_URL_LIST": app.state.OPENAI_COMPAT_API_BASE_URL_LIST}


@app.post("/url/update")
async def update_openai_url(form_data: UrlUpdateForm, user=Depends(get_admin_user)):
    app.state.OPENAI_COMPAT_API_BASE_URL_LIST = form_data.url
    return {"OPENAI_COMPAT_API_BASE_URL_LIST": app.state.OPENAI_COMPAT_API_BASE_URL_LIST}

@app.get("/key")
async def get_openai_key(user=Depends(get_admin_user)):
    print(app.state.OPENAI_COMPAT_API_KEY_LIST)
    return {"OPENAI_COMPAT_API_KEY_LIST": app.state.OPENAI_COMPAT_API_KEY_LIST}


@app.post("/key/update")
async def update_openai_key(form_data: KeyUpdateForm, user=Depends(get_admin_user)):
    app.state.OPENAI_COMPAT_API_KEY_LIST = form_data.key
    return {"OPENAI_COMPAT_API_KEY_LIST": app.state.OPENAI_COMPAT_API_KEY_LIST}

@app.get("/label")
async def get_openai_model(user=Depends(get_admin_user)):
    return {"OPENAI_COMPAT_MODEL_LABEL_LIST": app.state.OPENAI_COMPAT_MODEL_LABEL_LIST}

@app.post("/label/update")
async def update_openai_model(form_data: LabelUpdateForm, user=Depends(get_admin_user)):
    app.state.OPENAI_COMPAT_MODEL_LABEL_LIST = form_data.label
    return {"OPENAI_COMPAT_MODEL_LABEL_LIST": app.state.OPENAI_COMPAT_MODEL_LABEL_LIST}

# TODO: add index into list
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(path: str, request: Request, user=Depends(get_verified_user)):
    body = await request.body()
    body_json = json.loads(body)

    if "model" in body_json:
        print("Getting model from JSON body: ", body_json["model"])
        index = app.state.OPENAI_COMPAT_MODEL_LABEL_LIST.split(STATE_LIST_SEPARATOR).index(body_json["model"])
        print("Found model at index: ", index)
    else:
        raise HTTPException(status_code=400, detail=f"Model not found. Got JSON body: {body_json}")

    url_list = app.state.OPENAI_COMPAT_API_BASE_URL_LIST.split(STATE_LIST_SEPARATOR)
    key_list = app.state.OPENAI_COMPAT_API_KEY_LIST.split(STATE_LIST_SEPARATOR)
    print("URL List: ", url_list)
    api_url = url_list[index]
    api_key = key_list[index]
    
    target_url = f"{api_url}/{path}"
    print("Hitting OpenAI compat URL: ", target_url)

    headers = {}
    headers["Authorization"] = f"Bearer {api_key}"
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

            return response_data
    except Exception as e:
        print(e)
        error_detail = "Ollama WebUI: Server Connection Error"
        if r is not None:
            try:
                res = r.json()
                if "error" in res:
                    error_detail = f"External: {res['error']}"
            except:
                error_detail = f"External: {e}"

        raise HTTPException(status_code=r.status_code, detail=error_detail)
