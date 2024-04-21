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

from utils.utils import get_verified_user, get_current_user, get_admin_user
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


# Global variable to store the subprocess reference
background_process = None


async def run_background_process(command):
    global background_process
    print("run_background_process")

    try:
        # Log the command to be executed
        print(f"Executing command: {command}")
        # Execute the command and create a subprocess
        process = await asyncio.create_subprocess_exec(
            *command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        background_process = process
        print("Subprocess started successfully.")

        # Capture STDERR for debugging purposes
        stderr_output = await process.stderr.read()
        stderr_text = stderr_output.decode().strip()
        if stderr_text:
            print(f"Subprocess STDERR: {stderr_text}")

        # Print output line by line
        async for line in process.stdout:
            print(line.decode().strip())

        # Wait for the process to finish
        returncode = await process.wait()
        print(f"Subprocess exited with return code {returncode}")
    except Exception as e:
        log.error(f"Failed to start subprocess: {e}")
        raise  # Optionally re-raise the exception if you want it to propagate


async def start_litellm_background():
    print("start_litellm_background")
    # Command to run in the background
    command = "litellm --telemetry False --config ./data/litellm/config.yaml"

    await run_background_process(command)


async def shutdown_litellm_background():
    print("shutdown_litellm_background")
    global background_process
    if background_process:
        background_process.terminate()
        await background_process.wait()  # Ensure the process has terminated
        print("Subprocess terminated")


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


@app.get("/restart")
async def restart_litellm(user=Depends(get_admin_user)):
    """
    Endpoint to restart the litellm background service.
    """
    log.info("Requested restart of litellm service.")
    try:
        # Shut down the existing process if it is running
        await shutdown_litellm_background()
        log.info("litellm service shutdown complete.")

        # Restart the background service
        await start_litellm_background()
        log.info("litellm service restart complete.")

        return {
            "status": "success",
            "message": "litellm service restarted successfully.",
        }
    except Exception as e:
        log.error(f"Error restarting litellm service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


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

    url = "http://localhost:4000"

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
