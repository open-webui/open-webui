"""
Tool search / lazy tool loading.

Large tool schemas are withheld from the provider `tools` array and listed in a
compact `<available_tools>` manifest instead. The model loads them on demand
through the `search_tools` builtin. Per-request state lives on `metadata`:

    metadata['tool_search'] = {
        'deferred': [tool names withheld from the provider],
        'loaded': [deferred names that have since been loaded],
        'extra_tools': [tools added by filter inlets, always sent],
    }
"""

import fnmatch
import re

from rank_bm25 import BM25Okapi

from open_webui.models.config import Config
from open_webui.utils.json_codec import JSONCodec

SEARCH_TOOL_NAME = 'search_tools'
MANIFEST_DESCRIPTION_MAX_CHARS = 100
MAX_SEARCH_LIMIT = 20
DEFAULT_SEARCH_LIMIT = 5


async def get_tool_search_config() -> dict:
    values = await Config.get_many(
        'chat.tool_search.enable',
        'chat.tool_search.defer_threshold',
        'chat.tool_search.always_loaded',
    )
    return {
        'enable': bool(values.get('chat.tool_search.enable', False)),
        'defer_threshold': _to_int(values.get('chat.tool_search.defer_threshold'), 400),
        'always_loaded': values.get('chat.tool_search.always_loaded') or [],
    }


def _to_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def select_deferred_tools(tools_dict: dict[str, dict], config: dict) -> list[str]:
    """Sorted names of non-builtin tools whose schema exceeds the threshold and is not always loaded."""
    patterns = config['always_loaded']
    return sorted(
        name
        for name, tool in tools_dict.items()
        if tool.get('type') != 'builtin'
        and not any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)
        and len(JSONCodec.dumps(tool.get('spec') or {})) > config['defer_threshold']
    )


def _truncate_description(description: str | None) -> str:
    text = ' '.join(str(description or '').split())
    if len(text) > MANIFEST_DESCRIPTION_MAX_CHARS:
        text = text[: MANIFEST_DESCRIPTION_MAX_CHARS - 1].rstrip() + '…'
    return text


def build_deferred_tools_manifest(tools_dict: dict[str, dict], deferred: list[str]) -> str:
    """System prompt block listing every deferred tool (mirrors <available_skills>).

    Loaded tools stay listed so the block is identical across turns and provider prompt caches hold.
    """
    entries = ''
    for name in deferred:
        description = _truncate_description(tools_dict[name].get('spec', {}).get('description'))
        entries += f'<tool>\n<name>{name}</name>\n<description>{description}</description>\n</tool>\n'

    return (
        '<available_tools>\n'
        'The following tools are available but their definitions are not loaded. '
        f'To use one, call `{SEARCH_TOOL_NAME}` with a short keyword query or the exact tool name; '
        'matching tools become callable immediately afterwards. '
        'Never tell the user a capability is unavailable without searching first.\n'
        f'{entries}</available_tools>'
    )


def build_tools_payload(tools_dict: dict[str, dict], deferred, loaded, extra: list | None = None) -> list[dict]:
    """OpenAI `tools` array: every tool that is not deferred, plus deferred tools that are loaded, plus extras."""
    deferred_set = set(deferred) - set(loaded)
    tools = [
        {'type': 'function', 'function': tool.get('spec', {})}
        for name, tool in tools_dict.items()
        if name not in deferred_set
    ]
    if extra:
        tools.extend(extra)
    return tools


_SPLIT_RE = re.compile(r'[^0-9a-zA-Z]+')
_CAMEL_RE = re.compile(r'(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])')


def tokenize(text: str | None) -> list[str]:
    """Lowercase tokens split on non-alphanumerics and camelCase boundaries."""
    return [part.lower() for chunk in _SPLIT_RE.split(text or '') for part in _CAMEL_RE.split(chunk) if part]


def _document_text(name: str, spec: dict) -> str:
    properties = (spec.get('parameters') or {}).get('properties') or {}
    return ' '.join([name, str(spec.get('description') or ''), *properties.keys()])


def search_deferred_tools(query: str, candidates: dict[str, dict], limit: int = DEFAULT_SEARCH_LIMIT) -> list[str]:
    """Rank candidate tools (name -> spec) against the query; an exact tool name wins outright."""
    query = (query or '').strip()
    if query in candidates:
        return [query]

    query_tokens = tokenize(query)
    if not candidates or not query_tokens:
        return []

    names = list(candidates)
    documents = [tokenize(_document_text(name, candidates[name])) or ['_'] for name in names]
    # BM25 IDF is zero for a term found in half the corpus, common with small tool sets,
    # so raw token overlap keeps every matching term rankable.
    bm25 = BM25Okapi(documents).get_scores(query_tokens)
    scores = {
        name: max(0.0, float(bm25[index])) + len(set(query_tokens) & set(documents[index]))
        for index, name in enumerate(names)
    }

    ranked = sorted((name for name in names if scores[name] > 0), key=lambda name: (-scores[name], name))
    return ranked[: max(1, min(_to_int(limit, DEFAULT_SEARCH_LIMIT), MAX_SEARCH_LIMIT))]


def collect_called_tool_names(messages: list[dict]) -> set[str]:
    """Tools the conversation already called, so they stay loaded on later turns."""
    return {
        (tool_call.get('function') or {}).get('name')
        for message in messages
        if message.get('role') == 'assistant'
        for tool_call in message.get('tool_calls') or []
    }


def mark_tools_loaded(metadata: dict, names: list[str]) -> None:
    """Record deferred tools as loaded on metadata['tool_search']; no-op when tool search is inactive."""
    state = metadata.get('tool_search')
    if state:
        state['loaded'] = sorted(set(state['loaded']) | (set(names) & set(state['deferred'])))


def rebuild_tools_payload(form_data: dict, metadata: dict) -> None:
    """Refresh form_data['tools'] from metadata when tool search is active; no-op otherwise."""
    state = metadata.get('tool_search')
    if state:
        form_data['tools'] = build_tools_payload(
            metadata['tools'], state['deferred'], state['loaded'], state['extra_tools']
        )
