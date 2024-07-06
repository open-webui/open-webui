from contextlib import asynccontextmanager
from bs4 import BeautifulSoup
import json
import markdown
import time
import os
import sys
import logging
import aiohttp
import requests
import mimetypes
import shutil
import inspect
import asyncio

from fastapi import FastAPI, Request, Depends, status, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi import HTTPException
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse, Response

# Nouveaux imports pour Google Cloud Storage
from gcs_client import upload_to_gcs, download_from_gcs
from config import Config

# Autres importations
from apps.socket.main import app as socket_app
from apps.ollama.main import (
    app as ollama_app,
    OpenAIChatCompletionForm,
    get_all_models as get_ollama_models,
    generate_openai_chat_completion as generate_ollama_chat_completion,
)
from apps.openai.main import (
    app as openai_app,
    get_all_models as get_openai_models,
    generate_chat_completion as generate_openai_chat_completion,
)

from apps.audio.main import app as audio_app
from apps.images.main import app as images_app
from apps.rag.main import app as rag_app
from apps.webui.main import app as webui_app

from pydantic import BaseModel
from typing import List, Optional

from apps.webui.models.models import Models, ModelModel
from apps.webui.models.tools import Tools
from apps.webui.utils import load_toolkit_module_by_id

from utils.utils import (
    get_admin_user,
    get_verified_user,
    get_current_user,
    get_http_authorization_cred,
)
from utils.task import (
    title_generation_template,
    search_query_generation_template,
    tools_function_calling_generation_template,
)
from utils.misc import get_last_user_message, add_or_update_system_message

from apps.rag.utils import get_rag_context, rag_template

from config import (
    CONFIG_DATA,
    WEBUI_NAME,
    WEBUI_URL,
    WEBUI_AUTH,
    ENV,
    VERSION,
    CHANGELOG,
    FRONTEND_BUILD_DIR,
    CACHE_DIR,
    STATIC_DIR,
    ENABLE_OPENAI_API,
    ENABLE_OLLAMA_API,
    ENABLE_MODEL_FILTER,
    MODEL_FILTER_LIST,
    GLOBAL_LOG_LEVEL,
    SRC_LOG_LEVELS,
    WEBHOOK_URL,
    ENABLE_ADMIN_EXPORT,
    WEBUI_BUILD_HASH,
    TASK_MODEL,
    TASK_MODEL_EXTERNAL,
    TITLE_GENERATION_PROMPT_TEMPLATE,
    SEARCH_QUERY_GENERATION_PROMPT_TEMPLATE,
    SEARCH_QUERY_PROMPT_LENGTH_THRESHOLD,
    TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE,
    AppConfig,
)
from constants import ERROR_MESSAGES

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except (HTTPException, StarletteHTTPException) as ex:
            if ex.status_code == 404:
                return await super().get_response("index.html", scope)
            else:
                raise ex

print(
    rf"""
  ___                    __        __   _     _   _ ___ 
 / _ \ _ __   ___ _ __   \ \      / /__| |__ | | | |_ _|
| | | | '_ \ / _ \ '_ \   \ \ /\ / / _ \ '_ \| | | || | 
| |_| | |_) |  __/ | | |   \ V  V /  __/ |_) | |_| || | 
 \___/| .__/ \___|_| |_|    \_/\_/ \___|_.__/ \___/|___|
      |_|                                               

      
v{VERSION} - building the best open-source AI user interface.
{f"Commit: {WEBUI_BUILD_HASH}" if WEBUI_BUILD_HASH != "dev-build" else ""}
https://github.com/open-webui/open-webui
"""
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(
    docs_url="/docs" if ENV == "dev" else None, redoc_url=None, lifespan=lifespan
)

app.state.config = AppConfig()

app.state.config.ENABLE_OPENAI_API = ENABLE_OPENAI_API
app.state.config.ENABLE_OLLAMA_API = ENABLE_OLLAMA_API

app.state.config.ENABLE_MODEL_FILTER = ENABLE_MODEL_FILTER
app.state.config.MODEL_FILTER_LIST = MODEL_FILTER_LIST

app.state.config.WEBHOOK_URL = WEBHOOK_URL

app.state.config.TASK_MODEL = TASK_MODEL
app.state.config.TASK_MODEL_EXTERNAL = TASK_MODEL_EXTERNAL
app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE = TITLE_GENERATION_PROMPT_TEMPLATE
app.state.config.SEARCH_QUERY_GENERATION_PROMPT_TEMPLATE = (
    SEARCH_QUERY_GENERATION_PROMPT_TEMPLATE
)
app.state.config.SEARCH_QUERY_PROMPT_LENGTH_THRESHOLD = (
    SEARCH_QUERY_PROMPT_LENGTH_THRESHOLD
)
app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE = (
    TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE
)

app.state.MODELS = {}

origins = ["*"]

# Exemple de modifications pour utiliser Google Cloud Storage
def save_data(data):
    local_data_path = Config.LOCAL_DATA_PATH
    gcs_blob_name = Config.GCS_BLOB_NAME

    # Sauvegarder les données localement
    with open(local_data_path, 'w') as f:
        f.write(data)
    
    # Uploader le fichier sur GCS
    upload_to_gcs(local_data_path, gcs_blob_name)

def load_data():
    local_data_path = Config.LOCAL_DATA_PATH
    gcs_blob_name = Config.GCS_BLOB_NAME

    # Télécharger le fichier depuis GCS
    download_from_gcs(gcs_blob_name, local_data_path)
    
    # Charger les données localement
    with open(local_data_path, 'r') as f:
        return f.read()

async def get_function_call_response(messages, tool_id, template, task_model_id, user):
    tool = Tools.get_tool_by_id(tool_id)
    tools_specs = json.dumps(tool.specs, indent=2)
    content = tools_function_calling_generation_template(template, tools_specs)

    user_message = get_last_user_message(messages)
    prompt = (
        "History:\n"
        + "\n".join(
            [
                f"{message['role'].upper()}: \"\"\"{message['content']}\"\"\""
                for message in messages[::-1][:4]
            ]
        )
        + f"\nQuery: {user_message}"
    )

    print(prompt)

    payload = {
        "model": task_model_id,
        "messages": [
            {"role": "system", "content": content},
            {"role": "user", "content": f"Query: {prompt}"},
        ],
        "stream": False,
    }

    try:
        payload = filter_pipeline(payload, user)
    except Exception as e:
        raise e

    model = app.state.MODELS[task_model_id]

    response = None
    try:
        if model["owned_by"] == "ollama":
            response = await generate_ollama_chat_completion(
                OpenAIChatCompletionForm(**payload), user=user
            )
        else:
            response = await generate_openai_chat_completion(payload, user=user)

        content = None

        if hasattr(response, "body_iterator"):
            async for chunk in response.body_iterator:
                data = json.loads(chunk.decode("utf-8"))
                content = data["choices"][0]["message"]["content"]

            # Cleanup any remaining background tasks if necessary
            if response.background is not None:
                await response.background()
        else:
            content = response["choices"][0]["message"]["content"]

        # Parse the function response
        if content is not None:
            print(f"content: {content}")
            result = json.loads(content)
            print(result)

            # Call the function
            if "name" in result:
                if tool_id in webui_app.state.TOOLS:
                    toolkit_module = webui_app.state.TOOLS[tool_id]
                else:
                    toolkit_module = load_toolkit_module_by_id(tool_id)
                    webui_app.state.TOOLS[tool_id] = toolkit_module

                function = getattr(toolkit_module, result["name"])
                function_result = None
                try:
                    # Get the signature of the function
                    sig = inspect.signature(function)
                    # Check if '__user__' is a parameter of the function
                    if "__user__" in sig.parameters:
                        # Call the function with the '__user__' parameter included
                        function_result = function(
                            **{
                                **result["parameters"],
                                "__user__": {
                                    "id": user.id,
                                    "email": user.email,
                                    "name": user.name,
                                    "role": user.role,
                                },
                            }
                        )
                    else:
                        # Call the function without modifying the parameters
                        function_result = function(**result["parameters"])
                except Exception as e:
                    print(e)

                # Add the function result to the system prompt
                if function_result:
                    return function_result
    except Exception as e:
        print(f"Error: {e}")

    return None
