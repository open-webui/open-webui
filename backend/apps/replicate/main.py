# backend/apps/replicate/main.py

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import replicate
import asyncio
import json
import logging

from config import (
    SRC_LOG_LEVELS,
    ENABLE_REPLICATE_API,
    REPLICATE_API_TOKEN,
    AppConfig,
)
from utils.utils import get_verified_user, get_admin_user
from utils.misc import add_or_update_system_message

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


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: Optional[bool] = False


@app.post("/chat/completions")
async def generate_chat_completion(
        request: ChatCompletionRequest,
        user=Depends(get_verified_user)
):
    if not app.state.config.ENABLE_REPLICATE_API:
        raise HTTPException(status_code=400, detail="Replicate API is not enabled")

    try:
        client = replicate.Client(api_token=app.state.config.REPLICATE_API_TOKEN)

        prompt = " ".join([msg.content for msg in request.messages])

        if request.stream:
            return StreamingResponse(
                stream_replicate_response(client, request.model, prompt),
                media_type="text/event-stream"
            )
        else:
            output = replicate.run(
                request.model,
                input={"prompt": prompt}
            )
            return {"choices": [{"message": {"content": "".join(output)}}]}

    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=500, detail=str(e))


async def stream_replicate_response(client, model: str, prompt: str):
    try:
        for event in client.stream(model, input={"prompt": prompt}):
            yield f"data: {json.dumps({'choices': [{'delta': {'content': event}}]})}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        log.exception(f"Error in stream_replicate_response: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


@app.post("/cancel")
async def cancel_prediction(prediction_id: str, user=Depends(get_verified_user)):
    if not app.state.config.ENABLE_REPLICATE_API:
        raise HTTPException(status_code=400, detail="Replicate API is not enabled")

    try:
        client = replicate.Client(api_token=app.state.config.REPLICATE_API_TOKEN)
        prediction = client.predictions.get(prediction_id)
        prediction.cancel()
        return {"status": "cancelled"}
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models")
async def get_models(user=Depends(get_verified_user)):
    if not app.state.config.ENABLE_REPLICATE_API:
        raise HTTPException(status_code=400, detail="Replicate API is not enabled")

    try:
        replicate.Client(api_token=app.state.config.REPLICATE_API_TOKEN)
        # Note: Replicate doesn't have a direct API to list all models.
        # You might need to maintain a list of supported models or fetch from a predefined source.
        return {"models": ["meta/llama-2-70b-chat", "anthropic/claude-2"]}  # Example models
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=500, detail=str(e))


# Config routes similar to Ollama and OpenAI implementations
@app.get("/config")
async def get_config(user=Depends(get_admin_user)):
    return {"ENABLE_REPLICATE_API": app.state.config.ENABLE_REPLICATE_API}


class ReplicateConfigForm(BaseModel):
    enable_replicate_api: Optional[bool] = None


@app.post("/config/update")
async def update_config(form_data: ReplicateConfigForm, user=Depends(get_admin_user)):
    app.state.config.ENABLE_REPLICATE_API = form_data.enable_replicate_api
    return {"ENABLE_REPLICATE_API": app.state.config.ENABLE_REPLICATE_API}

# Add more routes as needed for Replicate-specific functionality
