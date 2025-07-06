"""
title: OpenRouter Integration with XYNTHORAI Policy
version: 1.0.0
description: OpenRouter integration with XYNTHORAI policy checking and analytics
author: XYNTHORAI System
author_url: https://github.com/xynthorai-system
license: MIT
requirements: requests, pydantic
"""

"""
OpenRouter Integration with XYNTHORAI Policy Checking
Version: 1.0.0
"""

import re
import requests
import json
import traceback
import logging
from typing import Optional, List, Union, Generator, Iterator, Callable
from pydantic import BaseModel, Field
from datetime import datetime


class PolicyChecker:
    """Handles policy checking through XYNTHORAI middleware"""
    
    def __init__(self, middleware_url: str, enabled: bool = True):
        self.middleware_url = middleware_url
        self.enabled = enabled
        self.logger = logging.getLogger(__name__)
    
    def check_message(self, messages: List[dict], user_info: dict = None) -> dict:
        """Check messages against XYNTHORAI policies"""
        if not self.enabled:
            return {"allowed": True, "reason": "Policy checking disabled"}
        
        try:
            # Prepare request data
            request_data = {
                "messages": messages,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Add user info if available
            if user_info:
                request_data["userEmail"] = user_info.get("email") or user_info.get("email")
                request_data["userId"] = user_info.get("name") or user_info.get("username") or user_info.get("id") or user_info.get("user_id")
                # Also pass the role if available
                if user_info.get("role"):
                    request_data["userRole"] = user_info.get("role")
            
            # Send to middleware for policy check
            response = requests.post(
                f"{self.middleware_url}/api/v1/policy/check",
                json=request_data,
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                error_data = response.json()
                return {
                    "allowed": False,
                    "reason": error_data.get("error", {}).get("message", "Policy violation")
                }
            else:
                self.logger.error(f"Policy check failed: {response.status_code}")
                return {
                    "allowed": False,
                    "reason": "Policy check service error"
                }
                
        except requests.exceptions.Timeout:
            self.logger.error("Policy check timeout")
            return {
                "allowed": False,
                "reason": "Policy check timeout - blocking for safety"
            }
        except Exception as e:
            self.logger.error(f"Policy check error: {e}")
            return {
                "allowed": False,
                "reason": f"Policy check error: {str(e)}"
            }


class Pipe:
    """Main pipe class for OpenRouter integration with XYNTHORAI"""
    
    class Valves(BaseModel):
        OPENROUTER_API_KEY: str = Field(
            default="", 
            description="Your OpenRouter API key (required)"
        )
        XYNTHORAI_MIDDLEWARE_URL: str = Field(
            default="http://xynthorai-middleware:3000",
            description="XYNTHORAI Middleware URL for policy checking"
        )
        ENABLE_POLICY_CHECK: bool = Field(
            default=True,
            description="Enable XYNTHORAI policy checking"
        )
        INCLUDE_REASONING: bool = Field(
            default=True,
            description="Request reasoning tokens from models that support it"
        )
        MODEL_PREFIX: Optional[str] = Field(
            default="XYNTHORAI:",
            description="Prefix for model names (shows they go through XYNTHORAI)"
        )
        REQUEST_TIMEOUT: int = Field(
            default=90,
            description="Timeout for API requests in seconds"
        )
        LOG_LEVEL: str = Field(
            default="info",
            description="Logging level (debug, info, warn, error)"
        )
        FREE_ONLY: bool = Field(
            default=False,
            description="Show only free models"
        )
        ENABLE_CACHE_CONTROL: bool = Field(
            default=False,
            description="Enable prompt caching for supported models"
        )
        SHOW_PRICING: bool = Field(
            default=False,
            description="Show pricing information in model names (admin only)"
        )

    def __init__(self):
        self.type = "manifold"
        self.valves = self.Valves()
        
        # Setup logging
        log_level = getattr(logging, self.valves.LOG_LEVEL.upper(), logging.INFO)
        logging.basicConfig(level=log_level)
        self.logger = logging.getLogger(__name__)
        
        # Initialize policy checker
        self.policy_checker = PolicyChecker(
            self.valves.XYNTHORAI_MIDDLEWARE_URL,
            self.valves.ENABLE_POLICY_CHECK
        )
        
        if not self.valves.OPENROUTER_API_KEY:
            self.logger.warning("OPENROUTER_API_KEY is not set")

    def pipes(self, body: dict = None) -> List[dict]:
        """Fetch available models from OpenRouter"""
        if not self.valves.OPENROUTER_API_KEY:
            return [{
                "id": "error",
                "name": "⚠️ XYNTHORAI Error: OpenRouter API Key not configured"
            }]
        
        # Check if user is admin
        is_admin = False
        if body:
            user_info = body.get("user", {})
            user_role = user_info.get("role", "user")
            is_admin = user_role == "admin"
            self.logger.info(f"User role: {user_role}, is_admin: {is_admin}")

        try:
            self.logger.info("Fetching models from OpenRouter")
            
            headers = {"Authorization": f"Bearer {self.valves.OPENROUTER_API_KEY}"}
            response = requests.get(
                "https://openrouter.ai/api/v1/models",
                headers=headers,
                timeout=self.valves.REQUEST_TIMEOUT
            )
            response.raise_for_status()

            models_data = response.json()
            models = []
            
            for model in models_data.get("data", []):
                model_id = model.get("id")
                if not model_id:
                    continue
                
                # Apply free-only filter if enabled
                if self.valves.FREE_ONLY:
                    pricing = model.get("pricing", {})
                    prompt_price = float(pricing.get("prompt", 0)) if pricing.get("prompt") is not None else 0
                    completion_price = float(pricing.get("completion", 0)) if pricing.get("completion") is not None else 0
                    if prompt_price > 0 or completion_price > 0:
                        continue
                
                model_name = model.get("name", model_id)
                
                # Add XYNTHORAI prefix to show it goes through policy checking
                if self.valves.MODEL_PREFIX:
                    model_name = f"{self.valves.MODEL_PREFIX} {model_name}"
                
                # Add pricing info only for admins or if explicitly enabled
                if is_admin or self.valves.SHOW_PRICING:
                    pricing = model.get("pricing", {})
                    if pricing:
                        try:
                            prompt_price = float(pricing.get("prompt", 0)) * 1000000 if pricing.get("prompt") is not None else 0
                            completion_price = float(pricing.get("completion", 0)) * 1000000 if pricing.get("completion") is not None else 0
                            if prompt_price > 0 or completion_price > 0:
                                model_name += f" (${prompt_price:.2f}/${completion_price:.2f})"
                        except (ValueError, TypeError):
                            # Skip pricing if values can't be converted to float
                            pass
                
                models.append({
                    "id": model_id,
                    "name": model_name
                })
            
            self.logger.info(f"Found {len(models)} models")
            return models if models else [{
                "id": "error",
                "name": "⚠️ No models found"
            }]

        except Exception as e:
            self.logger.error(f"Error fetching models: {e}")
            return [{
                "id": "error",
                "name": f"⚠️ Error: {str(e)}"
            }]

    def pipe(self, body: dict, __user__: Optional[dict] = None) -> Union[str, Generator, Iterator]:
        """Process chat requests with XYNTHORAI policy checking"""
        if not self.valves.OPENROUTER_API_KEY:
            return "⚠️ XYNTHORAI Error: OpenRouter API Key is not configured"

        try:
            messages = body.get("messages", [])
            model = body.get("model", "unknown")
            
            self.logger.info(f"Processing request for model: {model}")
            self.logger.debug(f"Messages: {messages}")
            
            # Extract user info - prioritize __user__ parameter
            user_info = {}
            
            # First, check if __user__ parameter is provided (Open WebUI standard)
            if __user__:
                user_info = __user__
                self.logger.info(f"User info from __user__ parameter: {user_info}")
            else:
                # Try to get from body
                user_info = body.get("user", {})
                
                # Check if user info is in __user__ key in body
                if not user_info and "__user__" in body:
                    user_info = body.get("__user__", {})
                
                # Log what we found
                self.logger.info(f"User info from body: {user_info}")
                self.logger.info(f"Full body keys: {list(body.keys())}")
            
            # If still no user info, create a default one
            if not user_info:
                self.logger.info("No user info found in request, using default")
                # Use a default user info for now
                user_info = {
                    "email": "user@openwebui.local",
                    "name": "Open WebUI User",
                    "role": "user"
                }
            
            # Step 1: Check policy via XYNTHORAI middleware
            if self.valves.ENABLE_POLICY_CHECK:
                policy_result = self.policy_checker.check_message(messages, user_info)
                
                if not policy_result.get("allowed", False):
                    violation_msg = f"{policy_result.get('reason', 'Unknown violation')}"
                    self.logger.warning(violation_msg)
                    
                    # Violation is already logged by middleware, no need to log again
                    
                    return violation_msg
                
                self.logger.info("✅ Policy check passed")
            
            # Step 2: Prepare request for OpenRouter
            payload = body.copy()
            
            # Clean model ID (remove prefix if present)
            if "model" in payload and payload["model"] and "." in payload["model"]:
                payload["model"] = payload["model"].split(".", 1)[1]
            
            # Add reasoning support
            if self.valves.INCLUDE_REASONING:
                payload["include_reasoning"] = True
            
            # Add cache control if enabled
            if self.valves.ENABLE_CACHE_CONTROL:
                self._apply_cache_control(payload)
            
            # Step 3: Send to OpenRouter
            headers = {
                "Authorization": f"Bearer {self.valves.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://xynthorai-system.local",
                "X-Title": "XYNTHORAI Policy System"
            }
            
            url = "https://openrouter.ai/api/v1/chat/completions"
            is_streaming = body.get("stream", False)
            
            self.logger.debug(f"Sending to OpenRouter: {url}")
            
            if is_streaming:
                return self._stream_response(url, headers, payload)
            else:
                return self._non_stream_response(url, headers, payload)

        except Exception as e:
            self.logger.error(f"Error in pipe method: {e}")
            traceback.print_exc()
            return f"⚠️ XYNTHORAI Error: {str(e)}"

    def _stream_response(self, url, headers, payload) -> Generator[str, None, None]:
        """Handle streaming responses"""
        response = None
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=self.valves.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        yield line + "\n\n"
                        
        except requests.exceptions.Timeout:
            yield f"data: {json.dumps({'error': 'Request timeout'})}\n\n"
        except Exception as e:
            self.logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            if response:
                response.close()

    def _non_stream_response(self, url, headers, payload) -> str:
        """Handle non-streaming responses"""
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.valves.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Extract content
            if result.get("choices"):
                choice = result["choices"][0]
                message = choice.get("message", {})
                content = message.get("content", "")
                reasoning = message.get("reasoning", "")
                
                # Format response with reasoning if present
                if reasoning and self.valves.INCLUDE_REASONING:
                    return f"<think>\n{reasoning}\n</think>\n\n{content}"
                else:
                    return content
            
            return ""
            
        except Exception as e:
            self.logger.error(f"Non-stream error: {e}")
            return f"⚠️ Error: {str(e)}"

    def _apply_cache_control(self, payload):
        """Apply cache control to messages for cost optimization"""
        if "messages" not in payload:
            return
            
        messages = payload["messages"]
        
        # Find the longest system or user message for caching
        for msg in messages:
            if msg.get("role") in ["system", "user"] and isinstance(msg.get("content"), list):
                longest_idx = -1
                max_len = 0
                
                for i, part in enumerate(msg["content"]):
                    if part.get("type") == "text":
                        text_len = len(part.get("text", ""))
                        if text_len > max_len:
                            max_len = text_len
                            longest_idx = i
                
                if longest_idx >= 0:
                    msg["content"][longest_idx]["cache_control"] = {"type": "ephemeral"}
                    break

