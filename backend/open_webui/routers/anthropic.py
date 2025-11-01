import logging
import time
from typing import Optional, List
import aiohttp
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from open_webui.models.users import UserModel
from open_webui.utils.auth import get_verified_user
from open_webui.env import (
    SRC_LOG_LEVELS,
    AIOHTTP_CLIENT_TIMEOUT,
    AIOHTTP_CLIENT_SESSION_SSL,
)
from open_webui.utils.anthropic import (
    convert_openai_messages_to_anthropic,
    convert_tools_openai_to_anthropic,
    convert_anthropic_response_to_openai,
    convert_streaming_response_anthropic_to_openai,
)

router = APIRouter()

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("ANTHROPIC", "INFO"))


# Anthropic models (static list since Anthropic doesn't have a /models endpoint)
ANTHROPIC_MODELS = [
    {
        "id": "claude-3-5-sonnet-20241022",
        "name": "Claude 3.5 Sonnet (New)",
        "object": "model",
        "owned_by": "anthropic",
    },
    {
        "id": "claude-3-5-haiku-20241022",
        "name": "Claude 3.5 Haiku",
        "object": "model",
        "owned_by": "anthropic",
    },
    {
        "id": "claude-3-opus-20240229",
        "name": "Claude 3 Opus",
        "object": "model",
        "owned_by": "anthropic",
    },
    {
        "id": "claude-3-sonnet-20240229",
        "name": "Claude 3 Sonnet",
        "object": "model",
        "owned_by": "anthropic",
    },
    {
        "id": "claude-3-haiku-20240307",
        "name": "Claude 3 Haiku",
        "object": "model",
        "owned_by": "anthropic",
    },
]


async def get_anthropic_models(request: Request, user: UserModel = None) -> dict:
    """
    Get list of available Anthropic models.
    Since Anthropic doesn't have a /models endpoint, we return a static list.
    """
    if not request.app.state.config.ENABLE_ANTHROPIC_API:
        return {"data": []}

    # Add timestamps and return
    models = [
        {
            **model,
            "created": int(time.time()),
        }
        for model in ANTHROPIC_MODELS
    ]

    return {"data": models}


@router.get("/models")
async def get_models(request: Request, user=Depends(get_verified_user)):
    """
    Get available Anthropic models.
    """
    return await get_anthropic_models(request, user)


async def generate_anthropic_chat_completion(
    request: Request,
    form_data: dict,
    user: UserModel,
    url_idx: Optional[int] = None,
):
    """
    Generate chat completion using Anthropic's API.

    Args:
        request: FastAPI request object
        form_data: Request payload in OpenAI format
        user: Current user
        url_idx: Index of API URL to use (for multiple API keys)

    Returns:
        StreamingResponse or dict with completion
    """
    if not request.app.state.config.ENABLE_ANTHROPIC_API:
        raise HTTPException(status_code=400, detail="Anthropic API is not enabled")

    # Get API configuration
    if url_idx is None:
        url_idx = 0

    try:
        api_key = request.app.state.config.ANTHROPIC_API_KEYS[url_idx]
        base_url = request.app.state.config.ANTHROPIC_API_BASE_URLS[url_idx]
    except IndexError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Anthropic API configuration index: {url_idx}"
        )

    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="Anthropic API key is not configured"
        )

    # Extract request parameters
    model = form_data.get("model")
    messages = form_data.get("messages", [])
    stream = form_data.get("stream", False)
    temperature = form_data.get("temperature")
    max_tokens = form_data.get("max_tokens", 4096)
    top_p = form_data.get("top_p")
    stop_sequences = form_data.get("stop")
    tools = form_data.get("tools")

    # Convert messages to Anthropic format
    system_prompt, anthropic_messages = convert_openai_messages_to_anthropic(messages)

    # Build Anthropic request payload
    payload = {
        "model": model,
        "messages": anthropic_messages,
        "max_tokens": max_tokens,
    }

    if system_prompt:
        payload["system"] = system_prompt

    if temperature is not None:
        payload["temperature"] = temperature

    if top_p is not None:
        payload["top_p"] = top_p

    if stop_sequences:
        if isinstance(stop_sequences, str):
            payload["stop_sequences"] = [stop_sequences]
        elif isinstance(stop_sequences, list):
            payload["stop_sequences"] = stop_sequences

    # Convert tools if present
    if tools:
        anthropic_tools = convert_tools_openai_to_anthropic(tools)
        if anthropic_tools:
            payload["tools"] = anthropic_tools

    if stream:
        payload["stream"] = True

    log.debug(f"Anthropic API request payload: {payload}")

    # Make request to Anthropic API
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    url = f"{base_url}/v1/messages"

    try:
        timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)

        if stream:
            # Streaming response
            async def stream_response():
                try:
                    async with aiohttp.ClientSession(
                        timeout=timeout, trust_env=True
                    ) as session:
                        async with session.post(
                            url,
                            headers=headers,
                            json=payload,
                            ssl=AIOHTTP_CLIENT_SESSION_SSL,
                        ) as response:
                            if response.status != 200:
                                error_text = await response.text()
                                log.error(f"Anthropic API error: {error_text}")
                                yield f"data: {json.dumps({'error': error_text})}\n\n"
                                return

                            # Parse SSE stream from Anthropic
                            async for line in response.content:
                                line = line.decode("utf-8").strip()

                                if not line:
                                    continue

                                if line.startswith("data: "):
                                    data = line[6:]  # Remove "data: " prefix

                                    if data == "[DONE]":
                                        continue

                                    try:
                                        event_data = json.loads(data)

                                        # Convert Anthropic event to OpenAI format
                                        # The actual conversion will be handled by the utility function
                                        # For now, we'll create a simple wrapper

                                        # Create a mock event object
                                        class Event:
                                            def __init__(self, data):
                                                self.type = data.get("type")
                                                if self.type == "content_block_delta":
                                                    self.delta = type('obj', (object,), {
                                                        'type': data.get("delta", {}).get("type"),
                                                        'text': data.get("delta", {}).get("text", ""),
                                                        'partial_json': data.get("delta", {}).get("partial_json", "")
                                                    })
                                                elif self.type == "content_block_start":
                                                    block = data.get("content_block", {})
                                                    self.content_block = type('obj', (object,), {
                                                        'type': block.get("type"),
                                                        'id': block.get("id"),
                                                        'name': block.get("name")
                                                    })
                                                elif self.type == "message_start":
                                                    self.message = data.get("message", {})

                                        event = Event(event_data)

                                        # Convert and yield the event
                                        async for chunk in convert_streaming_response_anthropic_to_openai(
                                            [event], model
                                        ):
                                            yield chunk

                                    except json.JSONDecodeError:
                                        continue
                                    except Exception as e:
                                        log.error(f"Error processing stream event: {e}")
                                        continue

                except Exception as e:
                    log.exception(f"Streaming error: {e}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"

            return StreamingResponse(
                stream_response(),
                media_type="text/event-stream",
            )
        else:
            # Non-streaming response
            async with aiohttp.ClientSession(
                timeout=timeout, trust_env=True
            ) as session:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        log.error(f"Anthropic API error: {error_text}")
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Anthropic API error: {error_text}"
                        )

                    anthropic_response = await response.json()
                    log.debug(f"Anthropic API response: {anthropic_response}")

                    # Convert to OpenAI format
                    openai_response = convert_anthropic_response_to_openai(
                        anthropic_response, model, stream=False
                    )

                    return openai_response

    except aiohttp.ClientError as e:
        log.exception(f"Anthropic API client error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Anthropic API connection error: {str(e)}"
        )
    except Exception as e:
        log.exception(f"Anthropic API error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Anthropic API error: {str(e)}"
        )


@router.post("/chat/completions")
async def chat_completions(
    request: Request,
    form_data: dict,
    user=Depends(get_verified_user),
):
    """
    Chat completions endpoint compatible with OpenAI format.
    """
    return await generate_anthropic_chat_completion(
        request, form_data, user
    )
