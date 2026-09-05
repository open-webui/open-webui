import logging
from dataclasses import dataclass
from typing import Optional

import requests
from open_webui.retrieval.web.main import SearchResult

log = logging.getLogger(__name__)

EXA_API_BASE = 'https://api.exa.ai'

# Maximum snippet length to prevent context flooding
MAX_SNIPPET_LENGTH = 4000


def _get_highlight_snippet(result: dict) -> str:
    """Extract a snippet from Exa result highlights, falling back to text.

    Exa's 'highlights' field contains token-efficient summaries suitable for LLM context.
    It may be a string or a list of strings. Falls back to 'text' (uncapped) if highlights
    are unavailable.
    """
    highlights = result.get('highlights')
    if highlights:
        if isinstance(highlights, list):
            snippet = ' '.join(highlights)
        else:
            snippet = highlights
    else:
        snippet = result.get('text', '')

    # Truncate to MAX_SNIPPET_LENGTH to prevent context flooding
    if len(snippet) > MAX_SNIPPET_LENGTH:
        snippet = snippet[:MAX_SNIPPET_LENGTH]

    return snippet


@dataclass
class ExaResult:
    url: str
    title: str
    text: str


def search_exa(
    api_key: str,
    query: str,
    count: int,
    filter_list: Optional[list[str]] = None,
) -> list[SearchResult]:
    """Search using Exa Search API and return the results as a list of SearchResult objects.

    Args:
        api_key (str): An Exa Search API key
        query (str): The query to search for
        count (int): Number of results to return
        filter_list (Optional[list[str]]): List of domains to filter results by
    """
    log.info('Searching with Exa for query: %s', query)

    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}

    payload = {
        'query': query,
        'numResults': count or 5,
        'includeDomains': filter_list,
        # Use highlights (token-efficient summaries) instead of full uncapped text.
        # maxCharacters caps each highlight to MAX_SNIPPET_LENGTH chars to prevent context flooding.
        'contents': {'highlights': True, 'maxCharacters': MAX_SNIPPET_LENGTH},
        'type': 'auto',  # Use the auto search type (keyword or neural)
    }

    try:
        response = requests.post(f'{EXA_API_BASE}/search', headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        raw_results = data.get('results', [])
        processed_results = []
        for raw in raw_results:
            processed_results.append(
                ExaResult(
                    url=raw['url'],
                    title=raw['title'],
                    text=raw.get('text', ''),
                )
            )

        log.info('Found %s results', len(processed_results))
        return [
            SearchResult(
                link=exaresult.url,
                title=exaresult.title,
                snippet=_get_highlight_snippet(raw),
            )
            for exaresult, raw in zip(processed_results, raw_results)
        ]
    except Exception as e:
        log.error(f'Error searching Exa: {e}')
        return []
