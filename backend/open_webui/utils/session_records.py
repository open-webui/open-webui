"""Interpret saved records without inventing missing measurements."""

import json
import math
import re
import time


def has_pending_tool_approval(output):
    if not isinstance(output, list):
        return False
    items = [item for item in output if isinstance(item, dict)]
    result_ids = {item.get('call_id') for item in items if item.get('type') == 'function_call_output'}
    return any(
        item.get('type') == 'function_call'
        and (item.get('call_id') or item.get('id'))
        and (item.get('call_id') or item.get('id')) not in result_ids
        and item.get('status') in {'pending', 'queued', 'requires_approval'}
        and item.get('approved') is not True
        for item in items
    )


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
    for item in items:
        item_type = item.get('type')
        # Providers can reuse call IDs after emitting results. Keep those snapshots distinct.
        if normalized and normalized[-1].get('type') == 'function_call_output' and item_type != 'function_call_output':
            indices.clear()
        call_id = item.get('call_id') or item.get('id')
        if item_type in {'function_call', 'function_call_output'} and call_id:
            key = (item_type, call_id)
            if key in indices:
                normalized[indices[key]] = {**normalized[indices[key]], **item}
                continue
            indices[key] = len(normalized)
        normalized.append(item)
    return pair_results(normalized)


def pair_results(output):
    # Each result belongs to the nearest preceding call with that ID.
    results = {}
    for item in reversed(output):
        if item.get('type') == 'function_call_output' and item.get('call_id'):
            results[item['call_id']] = item
            continue
        if item.get('type') != 'function_call':
            continue
        result = results.pop(item.get('call_id') or item.get('id'), None)
        if result:
            for key in ('started_at', 'ended_at', 'duration', 'error_type'):
                if key in result and key not in item:
                    item[key] = result[key]
        elif item.get('status') == 'completed':
            item['status'] = 'unknown'
    return output
