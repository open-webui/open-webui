"""
title: Anthropic Manifold Pipe with Caching
authors: justinh-rahb and christian-taillon (caching updates by Bermont)
author_url: https://github.com/justinh-rahb
funding_url: https://github.com/open-webui
version: 0.3.0
required_open_webui_version: 0.3.17
license: MIT
"""

import os
import requests
import json
import time
from typing import List, Union, Generator, Iterator, Dict, Any, Optional
from pydantic import BaseModel, Field
from open_webui.utils.misc import pop_system_message


class Pipe:
    class Valves(BaseModel):
        ANTHROPIC_API_KEY: str = Field(default="")
        DEFAULT_CACHE_TTL: int = Field(default=3600)  # Default 1 hour TTL
        ENABLE_CACHING: bool = Field(default=True)  # Enable caching by default
        SHOW_CACHE_INFO: bool = Field(default=True)  # Show cache info in responses

    def __init__(self):
        self.type = "manifold"
        self.id = "anthropic"
        self.name = "anthropic/"
        self.valves = self.Valves(
            **{
                "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
                "DEFAULT_CACHE_TTL": int(os.getenv("ANTHROPIC_CACHE_TTL", "3600")),
                "ENABLE_CACHING": os.getenv("ANTHROPIC_ENABLE_CACHING", "true").lower()
                == "true",
                "SHOW_CACHE_INFO": os.getenv(
                    "ANTHROPIC_SHOW_CACHE_INFO", "true"
                ).lower()
                == "true",
            }
        )
        self.MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB per image

        # Models that support caching
        self.CACHEABLE_MODELS = [
            "claude-3-7-sonnet-20250219",
            "claude-3-7-sonnet-latest",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-sonnet-latest",
            "claude-3-5-haiku-20241022",
            "claude-3-5-haiku-latest",
            "claude-3-opus-20240229",
            "claude-3-haiku-20240307",
        ]

        # Minimum tokens required for caching
        self.MIN_CACHEABLE_TOKENS = {
            "claude-3-7-sonnet": 1024,
            "claude-3-5-sonnet": 1024,
            "claude-3-5-haiku": 2048,
            "claude-3-haiku": 2048,
            "claude-3-opus": 1024,
        }

        # Updated pricing based on latest Anthropic rates (per token)
        self.MODEL_PRICING = {
            "claude-3-7-sonnet": {
                "input": 0.000003,  # $3.00 per million input tokens
                "input_cache_write": 0.00000375,  # $3.75 per million tokens (cache write)
                "input_cache_read": 0.0000003,  # $0.30 per million tokens (cache read)
                "output": 0.000015,  # $15.00 per million output tokens
            },
            "claude-3-5-haiku": {
                "input": 0.0000008,  # $0.80 per million input tokens
                "input_cache_write": 0.000001,  # $1.00 per million tokens (cache write)
                "input_cache_read": 0.00000008,  # $0.08 per million tokens (cache read)
                "output": 0.000004,  # $4.00 per million output tokens
            },
            "claude-3-opus": {
                "input": 0.000015,  # $15.00 per million input tokens
                "input_cache_write": 0.00001875,  # $18.75 per million tokens (cache write)
                "input_cache_read": 0.0000015,  # $1.50 per million tokens (cache read)
                "output": 0.000075,  # $75.00 per million output tokens
            },
            # Default for other models
            "default": {
                "input": 0.000003,  # Default to Claude 3.7 Sonnet pricing
                "input_cache_write": 0.00000375,
                "input_cache_read": 0.0000003,
                "output": 0.000015,
            },
        }

    def get_anthropic_models(self):
        return [
            {"id": "claude-3-haiku-20240307", "name": "claude-3-haiku"},
            {"id": "claude-3-opus-20240229", "name": "claude-3-opus"},
            {"id": "claude-3-sonnet-20240229", "name": "claude-3-sonnet"},
            {"id": "claude-3-5-haiku-20241022", "name": "claude-3.5-haiku"},
            {"id": "claude-3-5-haiku-latest", "name": "claude-3.5-haiku"},
            {"id": "claude-3-5-sonnet-20240620", "name": "claude-3.5-sonnet"},
            {"id": "claude-3-5-sonnet-20241022", "name": "claude-3.5-sonnet"},
            {"id": "claude-3-5-sonnet-latest", "name": "claude-3.5-sonnet"},
            {"id": "claude-3-7-sonnet-20250219", "name": "claude-3.7-sonnet"},
            {"id": "claude-3-7-sonnet-latest", "name": "claude-3.7-sonnet"},
        ]

    def pipes(self) -> List[dict]:
        return self.get_anthropic_models()

    def process_image(self, image_data):
        """Process image data with size validation."""
        if image_data["image_url"]["url"].startswith("data:image"):
            mime_type, base64_data = image_data["image_url"]["url"].split(",", 1)
            media_type = mime_type.split(":")[1].split(";")[0]
            # Check base64 image size
            image_size = len(base64_data) * 3 / 4  # Convert base64 size to bytes
            if image_size > self.MAX_IMAGE_SIZE:
                raise ValueError(
                    f"Image size exceeds 5MB limit: {image_size / (1024 * 1024):.2f}MB"
                )
            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64_data,
                },
            }
        else:
            # For URL images, perform size check after fetching
            url = image_data["image_url"]["url"]
            response = requests.head(url, allow_redirects=True)
            content_length = int(response.headers.get("content-length", 0))
            if content_length > self.MAX_IMAGE_SIZE:
                raise ValueError(
                    f"Image at URL exceeds 5MB limit: {content_length / (1024 * 1024):.2f}MB"
                )
            return {
                "type": "image",
                "source": {"type": "url", "url": url},
            }

    def should_enable_caching(self, model_id: str) -> bool:
        """Determine if caching should be enabled for this model."""
        if not self.valves.ENABLE_CACHING:
            return False
        # Check if model supports caching
        return model_id in self.CACHEABLE_MODELS

    def get_min_cacheable_tokens(self, model_id: str) -> int:
        """Get minimum cacheable tokens for a model."""
        # Extract the base model name (e.g., claude-3-7-sonnet from claude-3-7-sonnet-latest)
        base_model = "-".join(model_id.split("-")[:4])
        return self.MIN_CACHEABLE_TOKENS.get(
            base_model, 2048
        )  # Default to 2048 if unknown

    def should_add_cache_control(self, model_id: str) -> bool:
        """Determine if cache_control should be added to content blocks."""
        if not self.valves.ENABLE_CACHING:
            return False
        return model_id in self.CACHEABLE_MODELS

    def add_caching_parameters(
        self, payload: Dict[str, Any], model_id: str
    ) -> Dict[str, Any]:
        """Add caching parameters to the payload if appropriate."""
        # Note: According to Anthropic documentation, cache_control should be
        # applied to individual content blocks, not at the top level.
        # This method now does nothing - we'll handle caching in the message processing.
        return payload

    def get_model_base(self, model_id: str) -> str:
        """Extract the base model name from the full model ID."""
        if not model_id:
            return "claude-3-7-sonnet"  # Default model

        # Handle different model ID formats
        if "-latest" in model_id:
            # For latest models like claude-3-7-sonnet-latest
            return "-".join(model_id.split("-")[:4])
        elif model_id.count("-") >= 3 and any(
            char.isdigit() for char in model_id.split("-")[3]
        ):
            # For versioned models like claude-3-7-sonnet-20250219
            return "-".join(model_id.split("-")[:4])
        else:
            # For other formats, try to match the best we can
            for key in self.MODEL_PRICING.keys():
                if key in model_id:
                    return key

            # If no match found, use default
            return "default"

    def get_cache_info(self, usage_data, model_id="claude-3-7-sonnet"):
        """Format cache usage information for display with accurate pricing."""
        if not usage_data or "input_tokens" not in usage_data:
            return "```\n⚠️ No usage data available\n```\n\n"

        input_tokens = usage_data.get("input_tokens", 0)
        output_tokens = usage_data.get("output_tokens", 0)
        cached_tokens = usage_data.get("input_tokens_cached", 0)

        # Get pricing for the specific model
        base_model = self.get_model_base(model_id)
        pricing = self.MODEL_PRICING.get(base_model, self.MODEL_PRICING["default"])

        if cached_tokens > 0:
            non_cached_tokens = input_tokens - cached_tokens
            cache_percentage = 0
            if input_tokens > 0:
                cache_percentage = (cached_tokens / input_tokens) * 100

            # Calculate costs with the correct pricing
            # For non-cached tokens: normal input price
            # For cached tokens: cache read price
            regular_cost = input_tokens * pricing["input"]
            actual_cost = (non_cached_tokens * pricing["input"]) + (
                cached_tokens * pricing["input_cache_read"]
            )
            savings = regular_cost - actual_cost

            return (
                "```\n"
                f"✅ CACHE EFFECTIVENESS:\n"
                f"• {cached_tokens:,} of {input_tokens:,} input tokens cached ({cache_percentage:.1f}%)\n"
                f"• Approximate savings: ${savings:.6f}\n"
                f"• Total tokens: {input_tokens:,} input + {output_tokens:,} output = {input_tokens + output_tokens:,} tokens\n"
                "```\n\n"
            )
        else:
            return (
                "```\n"
                f"❌ NO CACHE USED:\n"
                f"• {input_tokens:,} input tokens (none cached)\n"
                f"• Total tokens: {input_tokens:,} input + {output_tokens:,} output = {input_tokens + output_tokens:,} tokens\n"
                "```\n\n"
            )

    def pipe(self, body: dict) -> Union[str, Generator, Iterator]:
        system_message, messages = pop_system_message(body["messages"])
        processed_messages = []
        total_image_size = 0
        for message in messages:
            processed_content = []
            if isinstance(message.get("content"), list):
                for item in message["content"]:
                    if item["type"] == "text":
                        processed_content.append({"type": "text", "text": item["text"]})
                    elif item["type"] == "image_url":
                        processed_image = self.process_image(item)
                        processed_content.append(processed_image)
                        # Track total size for base64 images
                        if processed_image["source"]["type"] == "base64":
                            image_size = len(processed_image["source"]["data"]) * 3 / 4
                            total_image_size += image_size
                            if (
                                total_image_size > 100 * 1024 * 1024
                            ):  # 100MB total limit
                                raise ValueError(
                                    "Total size of images exceeds 100 MB limit"
                                )
            else:
                processed_content = [
                    {"type": "text", "text": message.get("content", "")}
                ]
            processed_messages.append(
                {"role": message["role"], "content": processed_content}
            )
        # Extract model ID correctly
        model_id = body["model"]
        if "/" in model_id:
            model_id = model_id[model_id.find("/") + 1 :]
        # Remove any leading underscore or other prefixes
        if model_id.startswith("_."):
            model_id = model_id[2:]
        elif model_id.startswith("_"):
            model_id = model_id[1:]
        # Build the payload
        payload = {
            "model": model_id,
            "messages": processed_messages,
            "max_tokens": body.get("max_tokens", 4096),
            "temperature": body.get("temperature", 0.8),
            "top_k": body.get("top_k", 40),
            "top_p": body.get("top_p", 0.9),
            "stop_sequences": body.get("stop", []),
            "stream": body.get("stream", False),
        }
        # Add system message with cache_control if appropriate
        if system_message:
            if self.should_add_cache_control(model_id):
                # System message with cache_control
                payload["system"] = [
                    {
                        "type": "text",
                        "text": str(system_message),
                        "cache_control": {"type": "ephemeral"},
                    }
                ]
            else:
                # Regular system message
                payload["system"] = str(system_message)
        # Add caching parameters if applicable
        payload = self.add_caching_parameters(payload, model_id)
        headers = {
            "x-api-key": self.valves.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        url = "https://api.anthropic.com/v1/messages"
        try:
            if body.get("stream", False):
                return self.stream_response(url, headers, payload, model_id)
            else:
                return self.non_stream_response(url, headers, payload, model_id)
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return f"Error: Request failed: {e}"
        except Exception as e:
            print(f"Error in pipe method: {e}")
            return f"Error: {e}"

    def stream_response(self, url, headers, payload, model_id):
        try:
            with requests.post(
                url, headers=headers, json=payload, stream=True, timeout=(3.05, 60)
            ) as response:
                if response.status_code != 200:
                    raise Exception(
                        f"HTTP Error {response.status_code}: {response.text}"
                    )
                # Variables to track usage information
                usage_info = {}
                cache_info_sent = False
                for line in response.iter_lines():
                    if line:
                        line = line.decode("utf-8")
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                # Check for usage information at the end
                                if data.get("type") == "message_stop":
                                    if "usage" in data and self.valves.SHOW_CACHE_INFO:
                                        # We've already sent the response, so just log the cache info
                                        print(
                                            f"Cache info for completed stream: {self.get_cache_info(data['usage'], model_id)}"
                                        )
                                    break
                                # For the first content block, prepend cache info if enabled
                                if (
                                    data["type"] == "content_block_start"
                                    and not cache_info_sent
                                    and self.valves.SHOW_CACHE_INFO
                                ):
                                    # For streaming, we can't know cache effectiveness until the end
                                    # So we'll just show a placeholder message
                                    cache_info = "```\n⏳ Processing... Cache effectiveness will be shown in next response\n```\n\n"
                                    yield cache_info
                                    cache_info_sent = True
                                    yield data["content_block"]["text"]
                                elif data["type"] == "content_block_start":
                                    yield data["content_block"]["text"]
                                elif data["type"] == "content_block_delta":
                                    yield data["delta"]["text"]
                                elif (
                                    data["type"] == "message"
                                    and not cache_info_sent
                                    and self.valves.SHOW_CACHE_INFO
                                ):
                                    cache_info = "```\n⏳ Processing... Cache effectiveness will be shown in next response\n```\n\n"
                                    yield cache_info
                                    cache_info_sent = True
                                    for content in data.get("content", []):
                                        if content["type"] == "text":
                                            yield content["text"]
                                elif data["type"] == "message":
                                    for content in data.get("content", []):
                                        if content["type"] == "text":
                                            yield content["text"]
                                time.sleep(
                                    0.01
                                )  # Delay to avoid overwhelming the client
                            except json.JSONDecodeError:
                                print(f"Failed to parse JSON: {line}")
                            except KeyError as e:
                                print(f"Unexpected data structure: {e}")
                                print(f"Full data: {data}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            yield f"Error: Request failed: {e}"
        except Exception as e:
            print(f"General error in stream_response method: {e}")
            yield f"Error: {e}"

    def non_stream_response(self, url, headers, payload, model_id):
        try:
            response = requests.post(
                url, headers=headers, json=payload, timeout=(3.05, 60)
            )
            if response.status_code != 200:
                raise Exception(f"HTTP Error {response.status_code}: {response.text}")
            res = response.json()
            # Generate cache info if enabled
            cache_info = ""
            if "usage" in res and self.valves.SHOW_CACHE_INFO:
                cache_info = self.get_cache_info(res["usage"], model_id)
                # Also log to console for admin visibility
                print(f"Cache info: {cache_info}")
            # Get the model's response
            model_response = (
                res["content"][0]["text"] if "content" in res and res["content"] else ""
            )
            # Prepend cache info to the response if enabled
            return cache_info + model_response
        except requests.exceptions.RequestException as e:
            print(f"Failed non-stream request: {e}")
            return f"Error: {e}"
