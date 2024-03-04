from bs4 import BeautifulSoup
import json
import markdown
import time
import os
import sys
import requests

from fastapi import FastAPI, Request, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException


from litellm.proxy.proxy_server import ProxyConfig, initialize
from litellm.proxy.proxy_server import app as litellm_app

from apps.ollama.main import app as ollama_app
from apps.openai.main import app as openai_app
from apps.audio.main import app as audio_app
from apps.images.main import app as images_app
from apps.rag.main import app as rag_app
from apps.web.main import app as webui_app


from config import WEBUI_NAME, ENV, VERSION, CHANGELOG, FRONTEND_BUILD_DIR
from constants import ERROR_MESSAGES

from utils.utils import get_http_authorization_cred, get_current_user


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except (HTTPException, StarletteHTTPException) as ex:
            if ex.status_code == 404:
                return await super().get_response("index.html", scope)
            else:
                raise ex


proxy_config = ProxyConfig()


async def config():
    router, model_list, general_settings = await proxy_config.load_config(
        router=None, config_file_path="./data/litellm/config.yaml"
    )

    await initialize(config="./data/litellm/config.yaml", telemetry=False)


async def startup():
    await config()


app = FastAPI(docs_url="/docs" if ENV == "dev" else None, redoc_url=None)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    await startup()


@app.middleware("http")
async def check_url(request: Request, call_next):
    start_time = int(time.time())
    response = await call_next(request)
    process_time = int(time.time()) - start_time
    response.headers["X-Process-Time"] = str(process_time)

    return response


@litellm_app.middleware("http")
async def auth_middleware(request: Request, call_next):
    auth_header = request.headers.get("Authorization", "")

    if ENV != "dev":
        try:
            user = get_current_user(get_http_authorization_cred(auth_header))
            print(user)
        except Exception as e:
            return JSONResponse(status_code=400, content={"detail": str(e)})

    response = await call_next(request)
    return response


app.mount("/api/v1", webui_app)
app.mount("/litellm/api", litellm_app)

app.mount("/ollama/api", ollama_app)
app.mount("/openai/api", openai_app)

app.mount("/images/api/v1", images_app)
app.mount("/audio/api/v1", audio_app)
app.mount("/rag/api/v1", rag_app)


@app.get("/api/config")
async def get_app_config():

    return {
        "status": True,
        "name": WEBUI_NAME,
        "version": VERSION,
        "images": images_app.state.ENABLED,
        "default_models": webui_app.state.DEFAULT_MODELS,
        "default_prompt_suggestions": webui_app.state.DEFAULT_PROMPT_SUGGESTIONS,
    }


@app.get("/api/changelog")
async def get_app_changelog():
    return CHANGELOG


@app.get("/api/version/updates")
async def get_app_latest_release_version():
    try:
        response = requests.get(
            f"https://api.github.com/repos/open-webui/open-webui/releases/latest"
        )
        response.raise_for_status()
        latest_version = response.json()["tag_name"]

        return {"current": VERSION, "latest": latest_version[1:]}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ERROR_MESSAGES.RATE_LIMIT_EXCEEDED,
        )


app.mount("/static", StaticFiles(directory="static"), name="static")


app.mount(
    "/",
    SPAStaticFiles(directory=FRONTEND_BUILD_DIR, html=True),
    name="spa-static-files",
)
