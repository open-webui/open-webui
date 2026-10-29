"""Interpret saved records without inventing missing measurements."""

import json
import math
import re
import time


def recorded_timestamp(value):
    try:
        value = float(value)
        if value > 10_000_000_000:
            value /= 1000
        return int(value) if math.isfinite(value) and 1577836800 <= value <= time.time() + 86400 else None
    except (ValueError, TypeError, OverflowError):
        return None


def safe_snippet(value):
    """Analytics previews deliberately exclude raw payloads and identifiers."""
    if not value:
        return None
    text = value if isinstance(value, str) else json.dumps(value)
    text = re.sub(r'<[^>]*>', ' ', text)
    text = re.sub(r'https?://\S+|(?:[\w.-]+/)+[\w./~-]*|\b[\w-]{24,}\b', ' ', text)
    text = re.sub(r'(?i)\b(?:api[_-]?key|token|password|secret|authorization)\b[\"\x27]?\s*[:=]?\s*\S+', ' ', text)
    return ' '.join(text.split()[:10])


def normalize_tool_output(output):
    """Deduplicate recorded call/result snapshots; never construct calls from prose."""
    if not isinstance(output, list):
        return output
    items = [dict(item) for item in output if isinstance(item, dict)]
    normalized = []
    indices = {}
    start = 0
    for item in items:
        item_type = item.get('type')
        # A new assistant item after tool results starts a new round.
        if normalized and normalized[-1].get('type') == 'function_call_output' and item_type != 'function_call_output':
            pair_results(normalized[start:])
            indices.clear()
            start = len(normalized)
        call_id = item.get('call_id') or item.get('id')
        if item_type in {'function_call', 'function_call_output'} and call_id:
            key = (item_type, call_id)
            if key in indices:
                normalized[indices[key]] = {**normalized[indices[key]], **item}
                continue
            indices[key] = len(normalized)
        normalized.append(item)
    pair_results(normalized[start:])
    return normalized


def pair_results(output):
    results = {item.get('call_id'): item for item in output if item.get('type') == 'function_call_output'}
    for item in output:
        if item.get('type') != 'function_call':
            continue
        result = results.get(item.get('call_id'))
        if result:
            for key in ('started_at', 'ended_at', 'duration', 'error_type'):
                if key in result and key not in item:
                    item[key] = result[key]
        elif item.get('status') == 'completed':
            item['status'] = 'unknown'
    return output
