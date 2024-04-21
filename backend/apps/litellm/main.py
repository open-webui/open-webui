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

from pydantic import BaseModel
from typing import Optional, List

from utils.utils import get_verified_user, get_current_user, get_admin_user
from config import SRC_LOG_LEVELS, ENV
from constants import ERROR_MESSAGES

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["LITELLM"])


from config import MODEL_FILTER_ENABLED, MODEL_FILTER_LIST, DATA_DIR


import asyncio
import subprocess
import yaml

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


LITELLM_CONFIG_DIR = f"{DATA_DIR}/litellm/config.yaml"

with open(LITELLM_CONFIG_DIR, "r") as file:
    litellm_config = yaml.safe_load(file)

app.state.CONFIG = litellm_config

# Global variable to store the subprocess reference
background_process = None


async def run_background_process(command):
    global background_process
    log.info("run_background_process")

    try:
        # Log the command to be executed
        log.info(f"Executing command: {command}")
        # Execute the command and create a subprocess
        process = await asyncio.create_subprocess_exec(
            *command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        background_process = process
        log.info("Subprocess started successfully.")

        # Capture STDERR for debugging purposes
        stderr_output = await process.stderr.read()
        stderr_text = stderr_output.decode().strip()
        if stderr_text:
            log.info(f"Subprocess STDERR: {stderr_text}")

        # log.info output line by line
        async for line in process.stdout:
            log.info(line.decode().strip())

        # Wait for the process to finish
        returncode = await process.wait()
        log.info(f"Subprocess exited with return code {returncode}")
    except Exception as e:
        log.error(f"Failed to start subprocess: {e}")
        raise  # Optionally re-raise the exception if you want it to propagate


async def start_litellm_background():
    log.info("start_litellm_background")
    # Command to run in the background
    command = (
        "litellm --port 14365 --telemetry False --config ./data/litellm/config.yaml"
    )

    await run_background_process(command)


async def shutdown_litellm_background():
    log.info("shutdown_litellm_background")
    global background_process
    if background_process:
        background_process.terminate()
        await background_process.wait()  # Ensure the process has terminated
        log.info("Subprocess terminated")
        background_process = None


@app.on_event("startup")
async def startup_event():

    log.info("startup_event")
    # TODO: Check config.yaml file and create one
    asyncio.create_task(start_litellm_background())


app.state.MODEL_FILTER_ENABLED = MODEL_FILTER_ENABLED
app.state.MODEL_FILTER_LIST = MODEL_FILTER_LIST


@app.get("/")
async def get_status():
    return {"status": True}


async def restart_litellm():
    """
    Endpoint to restart the litellm background service.
    """
    log.info("Requested restart of litellm service.")
    try:
        # Shut down the existing process if it is running
        await shutdown_litellm_background()
        log.info("litellm service shutdown complete.")

        # Restart the background service

        asyncio.create_task(start_litellm_background())
        log.info("litellm service restart complete.")

        return {
            "status": "success",
            "message": "litellm service restarted successfully.",
        }
    except Exception as e:
        log.info(f"Error restarting litellm service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get("/restart")
async def restart_litellm_handler(user=Depends(get_admin_user)):
    return await restart_litellm()


@app.get("/config")
async def get_config(user=Depends(get_admin_user)):
    return app.state.CONFIG


class LiteLLMConfigForm(BaseModel):
    general_settings: Optional[dict] = None
    litellm_settings: Optional[dict] = None
    model_list: Optional[List[dict]] = None
    router_settings: Optional[dict] = None


@app.post("/config/update")
async def update_config(form_data: LiteLLMConfigForm, user=Depends(get_admin_user)):
    app.state.CONFIG = form_data.model_dump(exclude_none=True)

    with open(LITELLM_CONFIG_DIR, "w") as file:
        yaml.dump(app.state.CONFIG, file)

    await restart_litellm()
    return app.state.CONFIG


@app.get("/models")
@app.get("/v1/models")
async def get_models(user=Depends(get_current_user)):
    while not background_process:
        await asyncio.sleep(0.1)

    url = "http://localhost:14365/v1"
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


@app.get("/model/info")
async def get_model_list(user=Depends(get_admin_user)):
    return {"data": app.state.CONFIG["model_list"]}


class AddLiteLLMModelForm(BaseModel):
    model_name: str
    litellm_params: dict


@app.post("/model/new")
async def add_model_to_config(
    form_data: AddLiteLLMModelForm, user=Depends(get_admin_user)
):
    app.state.CONFIG["model_list"].append(form_data.model_dump())

    with open(LITELLM_CONFIG_DIR, "w") as file:
        yaml.dump(app.state.CONFIG, file)

    await restart_litellm()

    return {"message": "model added"}


class DeleteLiteLLMModelForm(BaseModel):
    id: str


@app.post("/model/delete")
async def delete_model_from_config(
    form_data: DeleteLiteLLMModelForm, user=Depends(get_admin_user)
):
    app.state.CONFIG["model_list"] = [
        model
        for model in app.state.CONFIG["model_list"]
        if model["model_name"] != form_data.id
    ]

    with open(LITELLM_CONFIG_DIR, "w") as file:
        yaml.dump(app.state.CONFIG, file)

    await restart_litellm()

    return {"message": "model deleted"}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(path: str, request: Request, user=Depends(get_verified_user)):
    body = await request.body()

    url = "http://localhost:14365"

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
