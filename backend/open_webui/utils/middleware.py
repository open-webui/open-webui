"""
Small middleware patch for Open WebUI to preserve model `tool_ids` when a
request does not explicitly provide `tool_ids`.

Issue: When a model preset has `tool_ids` configured, some request paths
omitted `tool_ids` and the middleware would replace them with an empty
list. This change uses the metadata fallback to keep preset tools intact.
"""
from __future__ import annotations

from typing import Dict, Any


def build_metadata_with_tool_ids(tool_ids, metadata: Dict[str, Any]):
    """Return metadata dict but preserve configured `tool_ids` when absent.

    Usage: replace the location in OW where `tool_ids` is created with this
    helper so model presets' `tool_ids` are not overwritten by empty values.
    """
    result = dict(metadata or {})
    # Use provided tool_ids when present; otherwise keep existing metadata value.
    result["tool_ids"] = tool_ids if tool_ids is not None and len(tool_ids) > 0 else metadata.get("tool_ids")
    return result
