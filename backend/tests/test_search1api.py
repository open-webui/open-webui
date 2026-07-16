import ast
import importlib.util
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from types import ModuleType, SimpleNamespace
from urllib.parse import urlparse

import pytest


@dataclass
class StubSearchResult:
    link: str
    title: str | None
    snippet: str | None

    def model_dump(self):
        return asdict(self)


def filter_results(results, filter_list):
    allowed = [entry for entry in filter_list if entry and not entry.startswith('!')]
    blocked = [entry[1:] for entry in filter_list if entry and entry.startswith('!')]

    def matches(host, domain):
        return host == domain or host.endswith(f'.{domain}')

    return [
        result
        for result in results
        if (not allowed or any(matches(urlparse(result['link']).hostname or '', domain) for domain in allowed))
        and not any(matches(urlparse(result['link']).hostname or '', domain) for domain in blocked)
    ]


def load_search1api_module(fake_get_session):
    main_module = ModuleType('open_webui.retrieval.web.main')
    main_module.SearchResult = StubSearchResult
    main_module.get_filtered_results = filter_results

    session_pool_module = ModuleType('open_webui.utils.session_pool')
    session_pool_module.get_session = fake_get_session

    module_path = Path(__file__).parents[1] / 'open_webui' / 'retrieval' / 'web' / 'search1api.py'
    spec = importlib.util.spec_from_file_location('search1api_under_test', module_path)
    module = importlib.util.module_from_spec(spec)

    previous_main = sys.modules.get('open_webui.retrieval.web.main')
    previous_pool = sys.modules.get('open_webui.utils.session_pool')
    sys.modules['open_webui.retrieval.web.main'] = main_module
    sys.modules['open_webui.utils.session_pool'] = session_pool_module
    try:
        spec.loader.exec_module(module)
    finally:
        if previous_main is None:
            sys.modules.pop('open_webui.retrieval.web.main', None)
        else:
            sys.modules['open_webui.retrieval.web.main'] = previous_main
        if previous_pool is None:
            sys.modules.pop('open_webui.utils.session_pool', None)
        else:
            sys.modules['open_webui.utils.session_pool'] = previous_pool

    return module


class FakeResponse:
    def __init__(self, payload=None, error=None):
        self.payload = payload or {}
        self.error = error

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    def raise_for_status(self):
        if self.error:
            raise self.error

    async def json(self):
        return self.payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def module_with_response(response):
    session = FakeSession(response)

    async def fake_get_session():
        return session

    return load_search1api_module(fake_get_session), session


@pytest.mark.asyncio
async def test_search_search1api_sends_expected_request_and_normalises_results():
    module, session = module_with_response(
        FakeResponse(
            {
                'results': [
                    {'title': 'First', 'link': 'https://first.example/article', 'snippet': 'First snippet'},
                    {'title': 'Second', 'link': 'https://second.example/article', 'content': 'Second content'},
                    {'title': 'Third', 'link': 'https://third.example/article', 'snippet': 'Third snippet'},
                ]
            }
        )
    )

    results = await module.search_search1api('test-key', 'open webui', 2)

    assert session.calls == [
        (
            'https://api.search1api.com/search',
            {
                'headers': {
                    'Authorization': 'Bearer test-key',
                    'Content-Type': 'application/json',
                },
                'json': {'query': 'open webui', 'max_results': 2},
            },
        )
    ]
    assert [result.model_dump() for result in results] == [
        {'link': 'https://first.example/article', 'title': 'First', 'snippet': 'First snippet'},
        {'link': 'https://second.example/article', 'title': 'Second', 'snippet': 'Second content'},
    ]


@pytest.mark.asyncio
async def test_search_search1api_applies_allow_and_block_domain_filters():
    module, _session = module_with_response(
        FakeResponse(
            {
                'results': [
                    {'title': 'Allowed', 'link': 'https://allowed.example/a', 'snippet': 'A'},
                    {'title': 'Subdomain', 'link': 'https://sub.allowed.example/b', 'snippet': 'B'},
                    {'title': 'Blocked', 'link': 'https://blocked.allowed.example/c', 'snippet': 'C'},
                    {'title': 'Outside', 'link': 'https://outside.example/d', 'snippet': 'D'},
                ]
            }
        )
    )

    results = await module.search_search1api(
        'test-key', 'filtered query', 10, ['allowed.example', '!blocked.allowed.example']
    )

    assert [result.title for result in results] == ['Allowed', 'Subdomain']


@pytest.mark.asyncio
async def test_search_search1api_returns_empty_results():
    module, _session = module_with_response(FakeResponse({'results': []}))

    assert await module.search_search1api('test-key', 'no matches', 3) == []


@pytest.mark.asyncio
async def test_search_search1api_propagates_http_errors():
    module, _session = module_with_response(FakeResponse(error=RuntimeError('upstream failed')))

    with pytest.raises(RuntimeError, match='upstream failed'):
        await module.search_search1api('test-key', 'query', 3)


def load_search_web_function(get_retrieval_config):
    router_path = Path(__file__).parents[1] / 'open_webui' / 'routers' / 'retrieval.py'
    tree = ast.parse(router_path.read_text(encoding='utf-8'))
    function = next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef) and node.name == 'search_web')
    module = ast.Module(
        body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), function],
        type_ignores=[],
    )
    ast.fix_missing_locations(module)
    namespace = {'get_retrieval_config': get_retrieval_config}
    exec(compile(module, router_path, 'exec'), namespace)
    return namespace['search_web']


@pytest.mark.asyncio
async def test_search_web_requires_search1api_api_key():
    async def fake_get_retrieval_config():
        return SimpleNamespace(SEARCH1API_API_KEY='')

    search_web = load_search_web_function(fake_get_retrieval_config)

    with pytest.raises(Exception, match='No SEARCH1API_API_KEY found in environment variables'):
        await search_web(None, 'search1api', 'query')
