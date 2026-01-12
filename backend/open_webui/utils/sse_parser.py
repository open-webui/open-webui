"""
SSE (Server-Sent Events) Parser Module

Enhanced parser for handling non-standard SSE formats from various third-party APIs.
This module provides robust parsing logic that handles edge cases like minimax's
non-standard response formats.

This is a standalone module to facilitate easy merging with upstream updates.
"""
import json
import logging
import re
from typing import Optional, Union

log = logging.getLogger(__name__)


# Common SSE termination signals (case-insensitive patterns)
SSE_DONE_PATTERNS = [
    "[DONE]",
    "[done]",
    "DONE",
    "done",
    "[FINISHED]",
    "[finished]",
]


def is_sse_done_signal(data: str) -> bool:
    """
    Check if the data represents an SSE stream termination signal.
    
    Args:
        data: The data string to check (after removing 'data:' prefix)
        
    Returns:
        True if this is a termination signal, False otherwise
    """
    data_stripped = data.strip()
    
    # Check exact matches (case-insensitive)
    if data_stripped.lower() in ("done", "[done]", "[finished]"):
        return True
    
    # Check common patterns
    for pattern in SSE_DONE_PATTERNS:
        if data_stripped == pattern:
            return True
    
    return False


def is_heartbeat_event(data: dict) -> bool:
    """
    Check if the parsed data is a heartbeat event.
    
    Args:
        data: Parsed JSON data
        
    Returns:
        True if this is a heartbeat event, False otherwise
    """
    if not isinstance(data, dict):
        return False
    
    event_type = data.get("type", "")
    return event_type == "heartbeat"


def extract_sse_data(line: str) -> Optional[str]:
    """
    Extract the data portion from an SSE line.
    
    Args:
        line: The full SSE line (may include 'data:' prefix)
        
    Returns:
        The extracted data string, or None if not a valid data line
    """
    line = line.strip()
    
    if not line:
        return None
    
    # Handle "data:" prefix with optional space
    if line.startswith("data:"):
        # Remove prefix and leading whitespace
        data = line[5:].lstrip()
        return data
    
    # Handle "event:" lines (skip them)
    if line.startswith("event:") or line.startswith("id:") or line.startswith(":"):
        return None
    
    return None


def parse_sse_line(line: str) -> Optional[dict]:
    """
    Parse a single SSE line and return the parsed data.
    
    This function handles various non-standard SSE formats from third-party APIs:
    - Standard format: data: {"key": "value"}
    - Non-standard terminators: data: done, data: [done], etc.
    - Empty data: data: {}, data:
    - Heartbeat events
    
    Args:
        line: The SSE line to parse (as string)
        
    Returns:
        Parsed dict if successful, None if line should be skipped
        (terminators, heartbeats, invalid data, etc.)
    """
    # Handle bytes input
    if isinstance(line, bytes):
        line = line.decode("utf-8", errors="replace")
    
    # Extract data from SSE line
    data = extract_sse_data(line)
    
    if data is None:
        return None
    
    # Check for termination signals BEFORE trying to parse as JSON
    if is_sse_done_signal(data):
        log.debug(f"SSE stream termination signal detected: {data}")
        return None
    
    # Handle empty data
    if not data or data == "{}":
        return None
    
    # Try to parse as JSON
    try:
        parsed = json.loads(data)
        
        # Skip heartbeat events (they're just for keeping connection alive)
        if is_heartbeat_event(parsed):
            log.debug("Heartbeat event detected, skipping")
            return None
        
        return parsed
        
    except json.JSONDecodeError as e:
        # Log the error but don't propagate it - just skip this line
        # This handles cases where the API returns malformed data
        log.debug(f"SSE parse error (skipping line): {e} - data: {data[:100]}...")
        return None


def parse_sse_stream_line(line: Union[str, bytes]) -> tuple[Optional[dict], bool]:
    """
    Parse an SSE line and return both the parsed data and whether it's a done signal.
    
    This is useful when you need to know if the stream has ended.
    
    Args:
        line: The SSE line to parse
        
    Returns:
        Tuple of (parsed_data, is_done)
        - parsed_data: The parsed dict, or None if line should be skipped
        - is_done: True if this line indicates end of stream
    """
    if isinstance(line, bytes):
        line = line.decode("utf-8", errors="replace")
    
    data = extract_sse_data(line)
    
    if data is None:
        return None, False
    
    # Check for termination signals
    if is_sse_done_signal(data):
        return None, True
    
    # Handle empty data
    if not data or data == "{}":
        return None, False
    
    # Try to parse as JSON
    try:
        parsed = json.loads(data)
        
        if is_heartbeat_event(parsed):
            return None, False
        
        return parsed, False
        
    except json.JSONDecodeError:
        return None, False
