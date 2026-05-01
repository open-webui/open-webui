import json
from typing import Any


def extract_mcp_text_content(item: dict[str, Any]) -> tuple[bool, Any]:
    """Extract model-visible text from MCP text and resource content items."""
    if item.get('type') == 'text':
        text = item.get('text', '')
    elif item.get('type') == 'resource':
        resource = item.get('resource', {})
        if not isinstance(resource, dict):
            return False, None
        text = resource.get('text', '')
        if not (isinstance(text, str) and text):
            return False, None
    else:
        return False, None

    if isinstance(text, str):
        try:
            text = json.loads(text)
        except json.JSONDecodeError:
            pass

    return True, text
