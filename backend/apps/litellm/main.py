from fastapi import FastAPI, Depends, HTTPException
from fastapi.routing import APIRoute
from fastapi.middleware.cors import CORSMiddleware

import logging
from fastapi import FastAPI, Request, Depends, status, Response
from fastapi.responses import JSONResponse

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import StreamingResponse
import json
import requests

from utils.utils import get_verified_user, get_current_user
from config import SRC_LOG_LEVELS, ENV
from constants import ERROR_MESSAGES

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["LITELLM"])


from config import (
    MODEL_FILTER_ENABLED,
    MODEL_FILTER_LIST,
)


import asyncio
import subprocess


app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def run_background_process(command):
    # Start the process
    process = await asyncio.create_subprocess_exec(
        *command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    # Read output asynchronously
    async for line in process.stdout:
        print(line.decode().strip())  # Print stdout line by line

    await process.wait()  # Wait for the subprocess to finish


async def start_litellm_background():
    print("start_litellm_background")
    # Command to run in the background
    command = "litellm --telemetry False --config ./data/litellm/config.yaml"

    await run_background_process(command)


@app.on_event("startup")
async def startup_event():

    print("startup_event")
    # TODO: Check config.yaml file and create one
    asyncio.create_task(start_litellm_background())


app.state.MODEL_FILTER_ENABLED = MODEL_FILTER_ENABLED
app.state.MODEL_FILTER_LIST = MODEL_FILTER_LIST


@app.get("/")
async def get_status():
    return {"status": True}


@app.get("/models")
@app.get("/v1/models")
async def get_models(user=Depends(get_current_user)):
    url = "http://localhost:4000/v1"
    r = None
    try:
        r = requests.request(method="GET", url=f"{url}/models")
        r.raise_for_status()

        data = r.json()

        if app.state.MODEL_FILTER_ENABLED:
            if user and user.role == "user":
                data["data"] = list(
                    filter(
                        lambda model: model["id"] in app.state.MODEL_FILTER_LIST,
                        data["data"],
                    )
                )

        return data
    except Exception as e:
        log.exception(e)
        error_detail = "Open WebUI: Server Connection Error"
        if r is not None:
            try:
                res = r.json()
                if "error" in res:
                    error_detail = f"External: {res['error']}"
            except:
                error_detail = f"External: {e}"

        raise HTTPException(
            status_code=r.status_code if r else 500,
            detail=error_detail,
        )


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(path: str, request: Request, user=Depends(get_verified_user)):
    body = await request.body()

    url = "http://localhost:4000/v1"

    target_url = f"{url}/{path}"

    headers = {}
    # headers["Authorization"] = f"Bearer {key}"
    headers["Content-Type"] = "application/json"

    r = None

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
            response_data = r.json()
            return response_data
    except Exception as e:
        log.exception(e)
        error_detail = "Open WebUI: Server Connection Error"
        if r is not None:
            try:
                res = r.json()
                if "error" in res:
                    error_detail = f"External: {res['error']['message'] if 'message' in res['error'] else res['error']}"
            except:
                error_detail = f"External: {e}"

        raise HTTPException(
            status_code=r.status_code if r else 500, detail=error_detail
        )


# class ModifyModelsResponseMiddleware(BaseHTTPMiddleware):
#     async def dispatch(
#         self, request: Request, call_next: RequestResponseEndpoint
#     ) -> Response:

#         response = await call_next(request)
#         user = request.state.user

#         if "/models" in request.url.path:
#             if isinstance(response, StreamingResponse):
#                 # Read the content of the streaming response
#                 body = b""
#                 async for chunk in response.body_iterator:
#                     body += chunk

#                 data = json.loads(body.decode("utf-8"))

#                 if app.state.MODEL_FILTER_ENABLED:
#                     if user and user.role == "user":
#                         data["data"] = list(
#                             filter(
#                                 lambda model: model["id"]
#                                 in app.state.MODEL_FILTER_LIST,
#                                 data["data"],
#                             )
#                         )

#                 # Modified Flag
#                 data["modified"] = True
#                 return JSONResponse(content=data)

#         return response


# app.add_middleware(ModifyModelsResponseMiddleware)
