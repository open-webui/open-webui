from litellm.proxy.proxy_server import ProxyConfig, initialize
from litellm.proxy.proxy_server import app

from fastapi import FastAPI, Request, Depends, status, Response
from fastapi.responses import JSONResponse

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import StreamingResponse
import json

from utils.utils import get_http_authorization_cred, get_current_user
from config import ENV


from config import (
    MODEL_FILTER_ENABLED,
    MODEL_FILTER_LIST,
)


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


app.state.MODEL_FILTER_ENABLED = MODEL_FILTER_ENABLED
app.state.MODEL_FILTER_LIST = MODEL_FILTER_LIST


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    auth_header = request.headers.get("Authorization", "")
    request.state.user = None

    try:
        user = get_current_user(get_http_authorization_cred(auth_header))
        print(user)
        request.state.user = user
    except Exception as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})

    response = await call_next(request)
    return response


class ModifyModelsResponseMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:

        response = await call_next(request)
        user = request.state.user

        if "/models" in request.url.path:
            if isinstance(response, StreamingResponse):
                # Read the content of the streaming response
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk

                data = json.loads(body.decode("utf-8"))

                if app.state.MODEL_FILTER_ENABLED:
                    if user and user.role == "user":
                        data["data"] = list(
                            filter(
                                lambda model: model["id"]
                                in app.state.MODEL_FILTER_LIST,
                                data["data"],
                            )
                        )

                # Modified Flag
                data["modified"] = True
                return JSONResponse(content=data)

        return response


app.add_middleware(ModifyModelsResponseMiddleware)
