"""
Azure OpenAI Services integration utilities for Open WebUI.
"""

import logging
import re
from typing import Dict, Optional, Tuple

from open_webui.env import SRC_LOG_LEVELS

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
    api_version: str = "2024-12-01-preview",
) -> str:
    """
    Format an Azure OpenAI URL with the correct structure.

    Args:
        base_url: The base Azure OpenAI endpoint
        model: The model name or deployment name
        api_path: The API path (default: chat/completions)
        api_version: The API version (default: 2024-12-01-preview)

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

    # Prepare headers
    headers = {"api-key": api_key, "Content-Type": "application/json"}

    return formatted_url, payload, headers
