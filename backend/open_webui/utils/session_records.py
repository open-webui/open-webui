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
    deduped = []
    round_items = {}
    previous_kind = None
    for item in items:
        kind = item.get('type')
        # Some providers restart call ids every round.
        if kind != 'function_call_output' and previous_kind == 'function_call_output':
            pair_results(round_items)
            round_items = {}
        previous_kind = kind
        call_id = item.get('call_id') or item.get('id')
        if kind in {'function_call', 'function_call_output'} and call_id:
            key = (kind, call_id)
            if key in round_items:
                round_items[key].update(item)
                continue
            round_items[key] = item
        deduped.append(item)
    pair_results(round_items)
    return deduped


def pair_results(round_items):
    for (kind, call_id), item in round_items.items():
        if kind != 'function_call':
            continue
        result = round_items.get(('function_call_output', call_id))
        if result:
            for key in ('started_at', 'ended_at', 'duration', 'error_type'):
                if key in result and key not in item:
                    item[key] = result[key]
        elif item.get('status') == 'completed':
            item['status'] = 'unknown'

