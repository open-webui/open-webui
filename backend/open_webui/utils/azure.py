"""
Azure OpenAI Services integration utilities for Open WebUI.
"""

import logging
import re
from typing import Dict, Optional, Tuple

from open_webui.env import SRC_LOG_LEVELS, AZURE_OPENAI_API_VERSION

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["OPENAI"])


def parse_azure_openai_url(
    url: str,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parse an Azure OpenAI URL to extract the endpoint, deployment name, and API version.

    Args:
        url: The Azure OpenAI URL to parse

    Returns:
        Tuple containing (endpoint, deployment_name, api_version)
    """
    # Default pattern for Azure OpenAI URLs
    # Example: https://example-resource.openai.azure.com/openai/deployments/gpt-4/chat/completions?api-version=2023-05-15
    pattern = (
        r"(https?://[^/]+)/openai/deployments/([^/]+)/([^?]+)(?:\?api-version=([^&]+))?"
    )

    match = re.match(pattern, url)
    if match:
        endpoint = match.group(1)
        deployment_name = match.group(2)
        api_version = match.group(4)
        return endpoint, deployment_name, api_version

    # Alternative pattern without the path components
    # Example: https://example-resource.openai.azure.com
    alt_pattern = r"(https?://[^/]+)/?$"
    match = re.match(alt_pattern, url)
    if match:
        endpoint = match.group(1)
        return endpoint, None, None

    return None, None, None


def is_azure_openai_url(url: str) -> bool:
    """
    Check if a URL is an Azure OpenAI URL.

    Args:
        url: The URL to check

    Returns:
        True if the URL is an Azure OpenAI URL, False otherwise
    """
    return "openai.azure.com" in url or "cognitive.microsoft.com" in url


def format_azure_openai_url(
    base_url: str,
    model: str,
    api_path: str = "chat/completions",
    api_version: str = AZURE_OPENAI_API_VERSION,
) -> str:
    """
    Format an Azure OpenAI URL with the correct structure.

    Args:
        base_url: The base Azure OpenAI endpoint
        model: The model name or deployment name
        api_path: The API path (default: chat/completions)
        api_version: The API version (default: 2023-03-15-preview)

    Returns:
        Formatted Azure OpenAI URL
    """
    # Remove trailing slash if present
    base_url = base_url.rstrip("/")

    # Extract endpoint from base_url if it already contains deployment info
    endpoint, existing_deployment, existing_version = parse_azure_openai_url(base_url)

    if endpoint:
        base_url = endpoint

    # Use the provided model as deployment name
    deployment_name = model
    
    # Special case for o-series models which require a newer API version
    if model.startswith("o") and model.endswith("-mini"):
        api_version = "2024-12-01-preview"
        log.debug(f"Using API version {api_version} for o-series model {model}")

    # Format the URL
    url = f"{base_url}/openai/deployments/{deployment_name}/{api_path}?api-version={api_version}"

    return url


def prepare_azure_openai_request(
    url: str, payload: Dict, api_key: str
) -> Tuple[str, Dict, Dict]:
    """
    Prepare the request for Azure OpenAI Services.

    Args:
        url: The base Azure OpenAI URL
        payload: The request payload
        api_key: The Azure OpenAI API key

    Returns:
        Tuple containing (formatted_url, payload, headers)
    """
    model = payload.get("model", "")

    # Format the URL for Azure OpenAI
    formatted_url = format_azure_openai_url(url, model)
    
    # Filter allowed parameters based on Azure OpenAI API
    allowed_params = {
        "messages", "temperature", "role", "content", "contentPart", 
        "contentPartImage", "enhancements", "dataSources", "n", 
        "stream", "stop", "max_tokens", "presence_penalty", 
        "frequency_penalty", "logit_bias", "user", "function_call", 
        "functions", "tools", "tool_choice", "top_p", "log_probs", 
        "top_logprobs", "response_format", "seed", "max_completion_tokens"
    }
    
    # Remap user field if needed
    if "user" in payload and not isinstance(payload["user"], str):
        payload["user"] = payload["user"]["id"] if "id" in payload["user"] else str(payload["user"])
    
    # Special handling for o-series models
    if model.startswith("o") and model.endswith("-mini"):
        # Convert max_tokens to max_completion_tokens for o-series models
        if "max_tokens" in payload:
            payload["max_completion_tokens"] = payload["max_tokens"]
            del payload["max_tokens"]
        
        # Remove temperature if not 1 for o-series models
        if "temperature" in payload and payload["temperature"] != 1:
            log.debug(f"Removing temperature parameter for o-series model {model} as only default value (1) is supported")
            del payload["temperature"]
    
    # Filter out unsupported parameters
    filtered_payload = {k: v for k, v in payload.items() if k in allowed_params}
    
    # Log dropped parameters for debugging
    if len(payload) != len(filtered_payload):
        dropped_params = set(payload.keys()) - set(filtered_payload.keys())
        log.debug(f"Dropped params for Azure OpenAI: {', '.join(dropped_params)}")

    # Prepare headers
    headers = {"api-key": api_key, "Content-Type": "application/json"}

    return formatted_url, filtered_payload, headers
