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
            output = replicate.run(
                model,
                input={
                    "prompt": prompt,
                    "temperature": form_data.get("temperature", 0.75),
                    "max_length": form_data.get("max_tokens", 500),
                }
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
    prompt += "Assistant: "
    return prompt


async def stream_replicate_response(client, model: str, prompt: str, form_data: dict):
    try:
        for event in client.run(
                model,
                input={
                    "prompt": prompt,
                    "temperature": form_data.get("temperature", 0.75),
                    "max_length": form_data.get("max_tokens", 500),
                },
                stream=True,
        ):
            yield f"data: {json.dumps({'choices': [{'delta': {'content': event}}]})}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        log.exception(f"Error in stream_replicate_response: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


@app.post("/chat/completions")
async def chat_completions(form_data: ChatCompletionRequest, user=Depends(get_verified_user)):
    return await generate_replicate_chat_completion(form_data.dict(), user)


async def get_all_models():
    log.info("get_all_models()")
    if not is_enabled():
        raise HTTPException(status_code=400, detail="Replicate API is not enabled")

    try:
        # This is a placeholder. In a real implementation, you'd fetch this from Replicate or maintain a list.
        models = [
            {
                "id": "meta/meta-llama-3.1-405b-instruct",
                "name": "meta-llama-3.1-405b-instruct",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "replicate",
            },
            {
                "id": "meta/meta-llama-3-70b-instruct",
                "name": "meta-llama-3-70b-instruct",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "replicate",
            },
        ]
        app.state.MODELS = {model["id"]: model for model in models}
        return models
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
