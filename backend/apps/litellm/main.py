from litellm.proxy.proxy_server import ProxyConfig, initialize
from litellm.proxy.proxy_server import app

from fastapi import FastAPI, Request, Depends, status
from fastapi.responses import JSONResponse
from utils.utils import get_http_authorization_cred, get_current_user
from config import ENV

proxy_config = ProxyConfig()


async def config():
    router, model_list, general_settings = await proxy_config.load_config(
        router=None, config_file_path="./data/litellm/config.yaml"
    )

    await initialize(config="./data/litellm/config.yaml", telemetry=False)


async def startup():
    await config()


@app.on_event("startup")
async def on_startup():
    await startup()


@app.middleware("http")
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
