from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import replicate
import json
import logging
import time

from config import (
    SRC_LOG_LEVELS,
    ENABLE_REPLICATE_API,
    REPLICATE_API_TOKEN,
    ENABLE_MODEL_FILTER,
    MODEL_FILTER_LIST,
    AppConfig,
)
from utils.utils import get_verified_user, get_admin_user
from utils.webhook import post_webhook

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["REPLICATE"])

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.config = AppConfig()
app.state.config.ENABLE_REPLICATE_API = ENABLE_REPLICATE_API
app.state.config.REPLICATE_API_TOKEN = REPLICATE_API_TOKEN
app.state.config.ENABLE_MODEL_FILTER = ENABLE_MODEL_FILTER
app.state.config.MODEL_FILTER_LIST = MODEL_FILTER_LIST
app.state.MODELS = {}


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: Optional[bool] = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


def is_enabled() -> bool:
    return app.state.config.ENABLE_REPLICATE_API


async def generate_replicate_chat_completion(form_data: dict, user=Depends(get_verified_user)):
    if not app.state.config.ENABLE_REPLICATE_API:
        raise HTTPException(status_code=400, detail="Replicate API is not enabled")

    try:
        client = replicate.Client(api_token=app.state.config.REPLICATE_API_TOKEN)

        model = form_data["model"]
        messages = form_data["messages"]
        stream = form_data.get("stream", False)

        prompt = construct_prompt(messages)

        if stream:
            return StreamingResponse(
                stream_replicate_response(client, model, prompt, form_data),
                media_type="text/event-stream"
            )
        else:
            input = {
                "prompt": prompt,
            }
            if "temperature" in form_data and form_data["temperature"]:
                input["temperature"] = form_data["temperature"]
            if "max_tokens" in form_data and form_data["max_tokens"]:
                input["max_length"] = form_data["max_tokens"]
            output = replicate.run(
                model,
                input

            )
            return {
                "choices": [{
                    "message": {"content": "".join(output)},
                    "finish_reason": "stop"
                }],
                "model": model,
                "created": int(time.time()),
            }

    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=500, detail=str(e))


def construct_prompt(messages):
    prompt = ""
    for msg in messages:
        if msg["role"] == "system":
            prompt += f"System: {msg['content']}\n"
        elif msg["role"] == "user":
            prompt += f"Human: {msg['content']}\n"
        elif msg["role"] == "assistant":
            prompt += f"Assistant: {msg['content']}\n"
    # prompt += "Assistant: " # removed because it created artefacts
    return prompt


async def stream_replicate_response(client, model: str, prompt: str, form_data: dict):
    try:
        input = {
            "prompt": prompt,
        }
        if "temperature" in form_data and form_data["temperature"]:
            input["temperature"] = form_data["temperature"]
        if "max_tokens" in form_data and form_data["max_tokens"]:
            input["max_length"] = form_data["max_tokens"]
        for event in client.run(
                model,
                input=input,
                stream=True,
        ):
            yield f"data: {json.dumps({'choices': [{'delta': {'content': event}}]})}\n\n"
    except Exception as e:
        log.exception(f"Error in stream_replicate_response: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


@app.post("/chat/completions")
async def chat_completions(form_data: ChatCompletionRequest, user=Depends(get_verified_user)):
    return await generate_replicate_chat_completion(form_data.dict(), user)


formatted_models = [] # caching models, so we don't have to fetch them every time. Fetching takes a (relatively) long time.

async def get_all_models():
    global formatted_models # accessing the global caching variable
    if not is_enabled():
        raise HTTPException(status_code=400, detail="Replicate API is not enabled")
    if len(formatted_models) > 0:
        log.info(f"get_all_models()")
        return formatted_models

    try:
        if str(REPLICATE_API_TOKEN) != '':

            models = []
            n_models_to_fetch = 500 # 500 takes some time (~10s), but is a good number to fetch all models. One needs to find a balance between speed and comprehensiveness
            log.info(f"get_all_models() - this might take around {n_models_to_fetch * 0.02} seconds, but only once to build the cache") # around 0.02 seconds per model

            for page in replicate.paginate(replicate.models.list):
                models.extend(page.results)
                if len(models) > n_models_to_fetch:
                    break

            def is_llm_model(model):
                if model.id is None or model.description is None: # some models don't have a description, so if not checked, it will throw an error
                    return False
                owners = ['meta'] # right now, only meta seems to work...
                # additionally (taken from https://replicate.com/collections/language-models): 'replicate', '01-ai', 'stability-ai', 'nateraw', 'kcaverly', 'lucataco', 'replit', 'adirik'
                owner_filtered_model = any(owner in model.id for owner in owners)

                keywords = ['llm', 'language model'] # not amazing, but works (most applicable models have language model in their description)
                keyword_filtered_models = any(keyword in model.description.lower() for keyword in keywords)

                return owner_filtered_model and keyword_filtered_models

            llm_models = [model for model in models if is_llm_model(model)]

            for model in llm_models:
                formatted_model = {
                    "id": f"{model.id}",
                    "name": f"replicate: {model.name}",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "replicate",
                    "description": model.description
                }
                formatted_models.append(formatted_model)

            formatted_models += [ # hard-coded models, for some reason, they don't show up in the list of models (or my filter doesn't work)
                {
                    "id": "mistralai/mixtral-8x7b-instruct-v0.1",
                    "name": "replicate: mistralai/mixtral-8x7b-instruct-v0.1",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "replicate",
                    "description": "Language model, hard-coded"
                },
                {
                    "id": "mistralai/mistral-7b-instruct-v0.2",
                    "name": "replicate: mistralai/mistral-7b-instruct-v0.2",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "replicate",
                    "description": "Language model, hard-coded"
                },
                {
                    "id": "mistralai/mistral-7b-v0.1",
                    "name": "replicate: mistralai/mistral-7b-v0.1",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "replicate",
                    "description": "Language model, hard-coded"
                },
                {
                    "id": "mistralai/mistral-7b-instruct-v0.1",
                    "name": "replicate: mistralai/mistral-7b-instruct-v0.1",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "replicate",
                    "description": "Language model, hard-coded"
                }
            ]

            app.state.MODELS = {model["id"]: model for model in formatted_models}
            return formatted_models
        else:
            return []
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models")
async def get_models(user=Depends(get_verified_user)):
    models = await get_all_models()

    if app.state.config.ENABLE_MODEL_FILTER and user.role == "user":
        models = [model for model in models if model["id"] in app.state.config.MODEL_FILTER_LIST]

    return {"data": models, "object": "list"}


@app.get("/config")
async def get_config(user=Depends(get_admin_user)):
    return {
        "ENABLE_REPLICATE_API": app.state.config.ENABLE_REPLICATE_API,
        "REPLICATE_API_TOKEN": app.state.config.REPLICATE_API_TOKEN[
                               :4] + "..." if app.state.config.REPLICATE_API_TOKEN else None,
        "ENABLE_MODEL_FILTER": app.state.config.ENABLE_MODEL_FILTER,
        "MODEL_FILTER_LIST": app.state.config.MODEL_FILTER_LIST,
    }


class ReplicateConfigForm(BaseModel):
    enable_replicate_api: Optional[bool] = None
    replicate_api_token: Optional[str] = None
    enable_model_filter: Optional[bool] = None
    replicate_model_filter_list: Optional[List[str]] = None


@app.post("/config/update")
async def update_config(form_data: ReplicateConfigForm, user=Depends(get_admin_user)):
    if form_data.enable_replicate_api is not None:
        app.state.config.ENABLE_REPLICATE_API = form_data.enable_replicate_api
    if form_data.replicate_api_token:
        app.state.config.REPLICATE_API_TOKEN = form_data.replicate_api_token
    if form_data.enable_model_filter is not None:
        app.state.config.ENABLE_MODEL_FILTER = form_data.enable_model_filter
    if form_data.model_filtreplicate_er_list_replicatene:
        app.state.config.MODEL_FILTER_LIST = form_data.replicate_model_filter_list
    return await get_config(user)


@app.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    background_tasks.add_task(post_webhook, app.state.config.WEBHOOK_URL, "Replicate Event", payload)
    return {"status": "Webhook received and processing"}

    # Add more Replicate-specific endpoints as needed
