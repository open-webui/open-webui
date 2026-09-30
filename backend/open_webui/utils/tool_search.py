"""
Tool search: large tool schemas are left out of the provider `tools` array and listed by name in an
`<available_tools>` system prompt block. `search_tools` returns the full definitions of matching tools,
which the model then calls by name. The `tools` array never changes during a chat, so prompt caches hold.
"""

import fnmatch
import re
import unicodedata

import regex
from open_webui.models.config import Config
from open_webui.utils.json_codec import JSONCodec
from open_webui.utils.misc import add_or_update_system_message

SEARCH_TOOL_NAME = 'search_tools'
MANIFEST_DESCRIPTION_MAX_CHARS = 100
MAX_SEARCH_COUNT = 20
DEFAULT_SEARCH_COUNT = 5

_MANIFEST_RE = re.compile(r'\n?<available_tools>\n.*?</available_tools>', re.DOTALL)


async def get_tool_search_config() -> dict | None:
    """Tool search settings, or None when the feature is off."""
    if not await Config.get('chat.tool_search.enable'):
        return None
    values = await Config.get_many(
        'chat.tool_search.defer_threshold',
        'chat.tool_search.always_loaded',
        'chat.tool_search.defer_builtin_tools',
    )
    return {
        'defer_threshold': values['chat.tool_search.defer_threshold'],
        'always_loaded': values['chat.tool_search.always_loaded'],
        'defer_builtin_tools': values['chat.tool_search.defer_builtin_tools'],
    }


def select_deferred_tools(tools_dict: dict[str, dict], config: dict) -> list[str]:
    """Sorted names of tools whose schema exceeds the threshold and that are not always loaded."""
    patterns = config['always_loaded']
    return sorted(
        name
        for name, tool in tools_dict.items()
        if (config['defer_builtin_tools'] or tool.get('type') != 'builtin')
        and not any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)
        and len(JSONCodec.dumps(tool.get('spec') or {})) > config['defer_threshold']
    )


def _truncate_description(description: str | None) -> str:
    text = ' '.join(str(description or '').split())
    if len(text) > MANIFEST_DESCRIPTION_MAX_CHARS:
        text = text[: MANIFEST_DESCRIPTION_MAX_CHARS - 1].rstrip() + '…'
    return text


def build_deferred_tools_manifest(tools_dict: dict[str, dict], deferred: list[str]) -> str:
    entries = ''
    for name in deferred:
        description = _truncate_description(tools_dict[name].get('spec', {}).get('description'))
        entries += f'<tool>\n<name>{name}</name>\n<description>{description}</description>\n</tool>\n'

    return (
        '<available_tools>\n'
        'The following tools are available but their definitions are not loaded. '
        f'To use one, call `{SEARCH_TOOL_NAME}` with a short keyword query or the exact tool name to get its '
        'definition, then call the tool by name with the parameters it defines. '
        'Never tell the user a capability is unavailable without searching first.\n'
        f'{entries}</available_tools>'
    )


async def apply_tool_search(form_data: dict, metadata: dict, tools_dict: dict[str, dict]) -> set[str]:
    """Add search_tools and the manifest when tools can be deferred; returns the names to leave out of `tools`."""
    config = SEARCH_TOOL_NAME not in tools_dict and await get_tool_search_config()
    deferred = select_deferred_tools(tools_dict, config) if config else []
    if not deferred:
        return set()

    from open_webui.tools.builtin import search_tools
    from open_webui.utils.tools import (
        get_async_tool_function_and_apply_extra_params,
        get_builtin_function_introspection,
        get_builtin_tool_spec,
    )

    metadata['deferred_tools'] = deferred
    form_data['messages'] = add_or_update_system_message(
        build_deferred_tools_manifest(tools_dict, deferred),
        form_data['messages'],
        append=True,
    )
    tools_dict[SEARCH_TOOL_NAME] = {
        'tool_id': f'builtin:{SEARCH_TOOL_NAME}',
        'callable': await get_async_tool_function_and_apply_extra_params(
            search_tools, {'__metadata__': metadata}, get_builtin_function_introspection(search_tools)
        ),
        'spec': get_builtin_tool_spec(search_tools),
        'type': 'builtin',
    }
    return set(deferred)


def strip_deferred_tools_manifest(system_prompt: str | None) -> str | None:
    """Remove the manifest from a system prompt that is reused by a request which builds its own."""
    return _MANIFEST_RE.sub('', system_prompt) if system_prompt else system_prompt


# Letters, digits and combining marks, so vowel signs in scripts like Devanagari stay attached to their word.
_WORD_RE = regex.compile(r'[\p{L}\p{N}\p{M}]+')
_CAMEL_RE = re.compile(r'(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])')
# Scripts written without spaces between words: Han, Hiragana, Katakana and Hangul.
_CJK_RE = re.compile(r'([\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uac00-\ud7af]+)')


def tokenize(text: str | None) -> list[str]:
    """Lowercase word tokens split on camelCase boundaries, with CJK runs split into character bigrams."""
    tokens = []
    for word in _WORD_RE.findall(unicodedata.normalize('NFKC', text or '')):
        for part in _CAMEL_RE.split(word):
            for chunk in _CJK_RE.split(part.casefold()):
                if _CJK_RE.fullmatch(chunk):
                    tokens.extend([chunk[i : i + 2] for i in range(len(chunk) - 1)] or [chunk])
                elif chunk:
                    tokens.append(chunk)
    return tokens


def _document_text(name: str, spec: dict) -> str:
    properties = (spec.get('parameters') or {}).get('properties') or {}
    return ' '.join([name, str(spec.get('description') or ''), *properties.keys()])


def search_deferred_tools(query: str, candidates: dict[str, dict], count: int = DEFAULT_SEARCH_COUNT) -> list[str]:
    """Rank candidate tools (name -> spec) against the query; an exact tool name wins outright."""
    from rank_bm25 import BM25Okapi

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
    return ranked[: max(1, min(count, MAX_SEARCH_COUNT))]
