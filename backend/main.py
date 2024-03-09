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
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware


from apps.ollama.main import app as ollama_app
from apps.openai.main import app as openai_app
from apps.litellm.main import app as litellm_app, startup as litellm_app_startup
from apps.audio.main import app as audio_app
from apps.images.main import app as images_app
from apps.rag.main import app as rag_app
from apps.web.main import app as webui_app


from apps.rag.utils import query_doc, query_collection, rag_template

from config import WEBUI_NAME, ENV, VERSION, CHANGELOG, FRONTEND_BUILD_DIR
from constants import ERROR_MESSAGES


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except (HTTPException, StarletteHTTPException) as ex:
            if ex.status_code == 404:
                return await super().get_response("index.html", scope)
            else:
                raise ex


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
    await litellm_app_startup()


class RAGMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        "chat/completions" in request.url.path

        print(request.url.path)
        if request.method == "POST" and (
            "/api/chat" in request.url.path or "/chat/completions" in request.url.path
        ):
            # Read the original request body
            body = await request.body()
            # Decode body to string
            body_str = body.decode("utf-8")
            # Parse string to JSON
            data = json.loads(body_str) if body_str else {}

            # Example: Add a new key-value pair or modify existing ones
            # data["modified"] = True  # Example modification
            if "docs" in data:
                docs = data["docs"]
                print(docs)

                last_user_message_idx = None
                for i in range(len(data["messages"]) - 1, -1, -1):
                    if data["messages"][i]["role"] == "user":
                        last_user_message_idx = i
                        break

                query = data["messages"][last_user_message_idx]["content"]

                relevant_contexts = []

                for doc in docs:
                    context = None
                    if doc["type"] == "collection":
                        context = query_collection(
                            collection_names=doc["collection_names"],
                            query=query,
                            k=rag_app.state.TOP_K,
                            embedding_function=rag_app.state.sentence_transformer_ef,
                        )
                    else:
                        context = query_doc(
                            collection_name=doc["collection_name"],
                            query=query,
                            k=rag_app.state.TOP_K,
                            embedding_function=rag_app.state.sentence_transformer_ef,
                        )
                    relevant_contexts.append(context)

                context_string = ""
                for context in relevant_contexts:
                    if context:
                        context_string += " ".join(context["documents"][0]) + "\n"

                content = rag_template(
                    template=rag_app.state.RAG_TEMPLATE,
                    context=context_string,
                    query=query,
                )

                new_user_message = {
                    **data["messages"][last_user_message_idx],
                    "content": content,
                }
                data["messages"][last_user_message_idx] = new_user_message
                del data["docs"]

            modified_body_bytes = json.dumps(data).encode("utf-8")

            # Create a new request with the modified body
            scope = request.scope
            scope["body"] = modified_body_bytes
            request = Request(scope, receive=lambda: self._receive(modified_body_bytes))

        response = await call_next(request)
        return response

    async def _receive(self, body: bytes):
        return {"type": "http.request", "body": body, "more_body": False}


app.add_middleware(RAGMiddleware)


@app.middleware("http")
async def check_url(request: Request, call_next):
    start_time = int(time.time())
    response = await call_next(request)
    process_time = int(time.time()) - start_time
    response.headers["X-Process-Time"] = str(process_time)

    return response


app.mount("/api/v1", webui_app)
app.mount("/litellm/api", litellm_app)

app.mount("/ollama", ollama_app)
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


@app.get("/api/version")
async def get_app_config():

    return {
        "version": VERSION,
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
app.mount("/cache", StaticFiles(directory="data/cache"), name="cache")


app.mount(
    "/",
    SPAStaticFiles(directory=FRONTEND_BUILD_DIR, html=True),
    name="spa-static-files",
)
