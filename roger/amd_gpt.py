"""
title: Azure AI Foundry Pipeline
author: owndev
author_url: https://github.com/owndev
project_url: https://github.com/owndev/Open-WebUI-Functions
funding_url: https://github.com/owndev/Open-WebUI-Functions
version: 1.2.0
license: MIT
description: A pipeline for interacting with Azure AI services, enabling seamless communication with various AI models via configurable headers and robust error handling. This includes support for Azure OpenAI models as well as other Azure AI models by dynamically managing headers and request configurations.
features:
  - Supports dynamic model specification via headers.
  - Filters valid parameters to ensure clean requests.
  - Handles streaming and non-streaming responses.
  - Provides flexible timeout and error handling mechanisms.
  - Compatible with Azure OpenAI and other Azure AI models.
  - Predefined models for easy access.
"""

from typing import List, Union, Generator, Iterator, Optional, Dict, Any
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask
from open_webui.env import AIOHTTP_CLIENT_TIMEOUT, SRC_LOG_LEVELS
import aiohttp
import json
import os
import logging
import time
from datetime import datetime


# Helper functions
async def cleanup_response(
    response: Optional[aiohttp.ClientResponse],
    session: Optional[aiohttp.ClientSession],
) -> None:
    """
    Clean up the response and session objects.

    Args:
        response: The ClientResponse object to close
        session: The ClientSession object to close
    """
    if response:
        response.close()
    if session:
        await session.close()


class Pipe:
    # Environment variables for API key, endpoint, and optional model
    class Valves(BaseModel):
        # API key for Azure AI
        AZURE_AI_API_KEY: str = Field(
            # default=os.getenv("AZURE_AI_API_KEY", "API_KEY"),
            default="DUMMY_KEY",
            description="API key for Azure AI",
        )

        # Endpoint for Azure AI (e.g. "https://<your-endpoint>/chat/completions?api-version=2024-05-01-preview" or "https://<your-endpoint>/openai/deployments/gpt-4o/chat/completions?api-version=2024-08-01-preview")
        AZURE_AI_ENDPOINT: str = Field(
            default=os.getenv(
                "AZURE_AI_ENDPOINT",
                "https://llm-api.amd.com/openai/deployments/deploymentId/chat/completions?api-version=default",
            ),
            description="Endpoint for Azure AI",
        )

        # Optional model name, only necessary if not Azure OpenAI or if model name not in URL (e.g. "https://<your-endpoint>/openai/deployments/<model-name>/chat/completions")
        AZURE_AI_MODEL: str = Field(
            default=os.getenv("AZURE_AI_MODEL", ""),
            description="Optional model name for Azure AI",
        )

        # Switch for sending model name in request body
        AZURE_AI_MODEL_IN_BODY: bool = Field(
            default=False,
            description="If True, include the model name in the request body instead of as a header.",
        )

        # Flag to indicate if predefined Azure AI models should be used
        USE_PREDEFINED_AZURE_AI_MODELS: bool = Field(
            default=True,
            description="Flag to indicate if predefined Azure AI models should be used.",
        )

    def __init__(self):
        self.valves = self.Valves()
        self.name: str = "AMD Azure AI"

    def validate_environment(self) -> None:
        """
        Validates that required environment variables are set.

        Raises:
            ValueError: If required environment variables are not set.
        """
        if not self.valves.AZURE_AI_API_KEY:
            raise ValueError("AZURE_AI_API_KEY is not set!")
        if not self.valves.AZURE_AI_ENDPOINT:
            raise ValueError("AZURE_AI_ENDPOINT is not set!")

    def get_headers(self) -> Dict[str, str]:
        """
        Constructs the headers for the API request, including the model name if defined.

        Returns:
            Dictionary containing the required headers for the API request.
        """
        headers = {
            "api-key": self.valves.AZURE_AI_API_KEY,
            "Content-Type": "application/json",
            "Ocp-Apim-Subscription-Key": "7cce1ac73d98442c844bb040b983114c",
        }

        # If the valve indicates that the model name should be in the body,
        # add it to the filtered body.
        if self.valves.AZURE_AI_MODEL and not self.valves.AZURE_AI_MODEL_IN_BODY:
            headers["x-ms-model-mesh-model-name"] = self.valves.AZURE_AI_MODEL
        return headers

    def validate_body(self, body: Dict[str, Any]) -> None:
        """
        Validates the request body to ensure required fields are present.

        Args:
            body: The request body to validate

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        if "messages" not in body or not isinstance(body["messages"], list):
            raise ValueError("The 'messages' field is required and must be a list.")

    def get_azure_models(self) -> List[Dict[str, str]]:
        """
        Returns a list of predefined Azure AI models.

        Returns:
            List of dictionaries containing model id and name.
        """
        return [
            {"id": "gpt-4o", "name": "OpenAI GPT-4o"},
            {"id": "gpt-4o-mini", "name": "OpenAI GPT-4o mini"},
            {"id": "gpt-4.1", "name": "OpenAI GPT-4.1"},
            {"id": "gpt-4.1-mini", "name": "OpenAI GPT-4.1 mini"},
        ]

    def pipes(self) -> List[Dict[str, str]]:
        """
        Returns a list of available pipes based on configuration.

        Returns:
            List of dictionaries containing pipe id and name.
        """
        self.validate_environment()

        # If a custom model is provided, use it exclusively.
        if self.valves.AZURE_AI_MODEL:
            self.name = "AMD Azure AI for GPT: "
            return [
                {"id": self.valves.AZURE_AI_MODEL, "name": self.valves.AZURE_AI_MODEL}
            ]

        # If custom model is not provided but predefined models are enabled, return those.
        if self.valves.USE_PREDEFINED_AZURE_AI_MODELS:
            self.name = "AMD Azure AI for GPT: "
            return self.get_azure_models()

        # Otherwise, use a default name.
        return [{"id": "Azure AI", "name": "Azure AI"}]

    async def pipe(
        self, body: Dict[str, Any]
    ) -> Union[str, Generator, Iterator, Dict[str, Any], StreamingResponse]:
        """
        Main method for sending requests to the Azure AI endpoint.
        The model name is passed as a header if defined.

        Args:
            body: The request body containing messages and other parameters

        Returns:
            Response from Azure AI API, which could be a string, dictionary or streaming response
        """
        log = logging.getLogger("azure_ai.pipe")
        log.setLevel(SRC_LOG_LEVELS["OPENAI"])

        # Validate the request body
        self.validate_body(body)

        # Construct headers
        headers = self.get_headers()

        # Filter allowed parameters
        allowed_params = {
            "model",
            "messages",
            "frequency_penalty",
            "max_tokens",
            "presence_penalty",
            "response_format",
            "seed",
            "stop",
            "stream",
            "temperature",
            "tool_choice",
            "tools",
            "top_p",
        }
        filtered_body = {k: v for k, v in body.items() if k in allowed_params}

        # If the valve indicates that the model name should be in the body,
        # add it to the filtered body.
        if self.valves.AZURE_AI_MODEL and self.valves.AZURE_AI_MODEL_IN_BODY:
            filtered_body["model"] = self.valves.AZURE_AI_MODEL
        elif "model" in filtered_body and filtered_body["model"]:
            # Safer model extraction with split
            filtered_body["model"] = (
                filtered_body["model"].split(".", 1)[1]
                if "." in filtered_body["model"]
                else filtered_body["model"]
            )

        # Determine which model to use
        model_name = None
        if self.valves.AZURE_AI_MODEL and self.valves.AZURE_AI_MODEL_IN_BODY:
            filtered_body["model"] = self.valves.AZURE_AI_MODEL
            model_name = self.valves.AZURE_AI_MODEL
        elif "model" in filtered_body and filtered_body["model"]:
            # Safer model extraction with split
            filtered_body["model"] = (
                # filtered_body["model"].split(".", 1)[1]
                # if "." in filtered_body["model"]
                # else
                filtered_body["model"]
            )
            model_name = (
                # filtered_body["model"].split(".", 1)[1]
                # if "." in filtered_body["model"]
                # else
                filtered_body["model"]
            )

        # Replace deploymentId in endpoint URL with the actual model name if applicable
        endpoint_url = self.valves.AZURE_AI_ENDPOINT
        if "deploymentId" in endpoint_url and model_name:
            endpoint_url = endpoint_url.replace("deploymentId", model_name)
        log.info(f"Using model-specific endpoint: {endpoint_url}")

        # Convert the modified body back to JSON
        payload = json.dumps(filtered_body)

        request = None
        session = None
        streaming = False
        response = None

        log.info(f"url: {endpoint_url}")
        log.info(f"payload: {payload}")

        try:
            session = aiohttp.ClientSession(
                trust_env=True,
                timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT),
            )

            request = await session.request(
                method="POST",
                url=endpoint_url,
                data=payload,
                headers=headers,
            )

            # Add logging for initial request status
            log.info(f"Initial request status: {request.status}")

            # Check HTTP status first for any response type
            if request.status >= 400:
                error_msg = f"API returned error status {request.status}"
                log.error(f"HTTP Error: {error_msg}")

                # Close resources properly
                if session:
                    if request:
                        request.close()
                    await session.close()

                return f"Error: {error_msg}. Please try again later."

            # Now handle successful responses based on content type
            if "text/event-stream" in request.headers.get("Content-Type", ""):
                streaming = True
                log.info(
                    f"Streaming response status: {request.status}, Content-Type: {request.headers.get('Content-Type')}"
                )

                try:
                    # Create an async generator to wrap streaming content with timeout detection
                    async def safe_streaming_content():
                        chunk_count = 0
                        last_chunk_time = time.time()
                        inactivity_timeout = 30  # Max seconds to wait between chunks

                        try:
                            async for chunk in request.content:
                                # Successfully got a chunk
                                chunk_count += 1
                                current_time = time.time()

                                # Log first chunk and timing info
                                if chunk_count == 1:
                                    log.info(
                                        f"First chunk received after {current_time - last_chunk_time:.2f} seconds"
                                    )

                                # Log every 10th chunk or after long delays
                                if chunk_count % 10 == 0 or (
                                    current_time - last_chunk_time > 5
                                ):
                                    log.info(
                                        f"Chunk #{chunk_count} received, {len(chunk)} bytes, delay: {current_time - last_chunk_time:.2f}s"
                                    )

                                # Yield the actual chunk
                                yield chunk

                                # Update the last activity time
                                last_chunk_time = current_time

                        except Exception as e:
                            log.error(f"Error during streaming: {e}")

                            # If we never received any chunks, send a fallback message
                            if chunk_count == 0:
                                fallback_msg = {
                                    "id": "timeout_error",
                                    "object": "chat.completion.chunk",
                                    "choices": [
                                        {
                                            "delta": {
                                                "content": "\n\n[The AMD API is not responding. Please try again.]"
                                            },
                                            "index": 0,
                                            "finish_reason": "stop",
                                        }
                                    ],
                                }
                                yield f"data: {json.dumps(fallback_msg)}\n\n".encode(
                                    "utf-8"
                                )
                                yield b"data: [DONE]\n\n"

                        finally:
                            # Always cleanup when the stream is done
                            log.info(
                                f"Streaming complete, received {chunk_count} chunks"
                            )
                            if request and not request.closed:
                                request.close()
                            if session and not session.closed:
                                await session.close()

                    # Return streaming response with the safe generator
                    return StreamingResponse(
                        safe_streaming_content(),
                        status_code=request.status,
                        headers=dict(request.headers),
                    )
                except Exception as stream_err:
                    log.error(f"Error setting up streaming response: {stream_err}")
                    if request:
                        request.close()
                    if session:
                        await session.close()
                    return f"Error streaming response: {str(stream_err)}. Please try again later."
            else:
                log.info(
                    f"Non-streaming response status: {request.status}, Content-Type: {request.headers.get('Content-Type')}"
                )
                # Handle non-streaming responses
                try:
                    response = await request.json()
                    log.info(
                        f"JSON response parsed successfully with status: {request.status}"
                    )
                    log.info(f"response for LLM call: {json.dumps(response)}")
                    return response
                except Exception as e:
                    log.error(
                        f"Error parsing JSON response: {e}, status: {request.status}"
                    )
                    # Try to get text response instead
                    try:
                        response = await request.text()
                        log.error(
                            f"Text response with status {request.status}: {response}"
                        )
                    except:
                        response = "No response body available"

                    return (
                        f"Error processing response: {str(e)}. Please try again later."
                    )

        except Exception as e:
            log.exception(f"Error in Azure AI request: {e}")

            detail = f"Exception: {str(e)}"
            if isinstance(response, dict):
                if "error" in response:
                    detail = f"{response['error']['message'] if 'message' in response['error'] else response['error']}"
            elif isinstance(response, str):
                detail = response

            return f"Error: {detail}"
        finally:
            if not streaming and session:
                if request:
                    request.close()
                await session.close()
