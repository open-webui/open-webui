import json
from typing import Any, Optional


def ensure_md_string(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ''
    return '```text\n' + json.dumps(value, indent=2, ensure_ascii=False) + '\n```'


def get_note_md(data: Optional[dict]) -> str:
    """Safely extract data['content']['md'] as a string.

    Handles all corruption cases:
    - data is None / missing 'content' / 'content' is not a dict (list, str, etc.)
    - 'md' is missing, None, or a non-string type (dict, list, etc.)

    Returns the md string if valid, otherwise a safe coercion via ensure_md_string.
    """
    if not data or not isinstance(data, dict):
        return ''
    content = data.get('content')
    if not isinstance(content, dict):
        return ensure_md_string(content)
    md = content.get('md')
    return ensure_md_string(md)
