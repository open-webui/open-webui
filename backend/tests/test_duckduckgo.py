import ast
import asyncio
import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path
from typing import NamedTuple
from unittest.mock import patch

from pydantic import BaseModel


AUTO_BACKEND = 'auto'
EXCLUDED_BACKENDS = ['grokipedia', 'yandex']
EXPLICIT_BACKEND = 'google'
INVALID_BACKEND = 'not-a-provider'
EMPTY_BACKEND = '  '
EXPECTED_BACKENDS = {
    'brave',
    'duckduckgo',
    'google',
    'mojeek',
    'startpage',
    'wikipedia',
    'yahoo',
}
EXPECTED_SHUFFLED_BACKENDS = tuple(reversed(sorted(EXPECTED_BACKENDS)))
ALL_BACKENDS = sorted(EXPECTED_BACKENDS.union(EXCLUDED_BACKENDS))
QUERY = 'open webui'
RESULT_COUNT = 1
RESULT_LINK = 'https://example.com'
RESULT_TITLE = 'Example'
RESULT_BODY = 'Example result'
MODULE_LOAD_ERROR = 'Unable to load DuckDuckGo search module'
DUCKDUCKGO_MODULE_PATH = Path(__file__).resolve().parents[1] / 'open_webui/retrieval/web/duckduckgo.py'
CONFIG_MODULE_PATH = Path(__file__).resolve().parents[1] / 'open_webui/config.py'
RETRIEVAL_ROUTER_PATH = Path(__file__).resolve().parents[1] / 'open_webui/routers/retrieval.py'
CONFIG_KEY = 'web.search.ddgs_backend_exclude'
CONFIG_FIELD = 'DDGS_BACKEND_EXCLUDE'
CONFIG_ENV_FIELD = 'DDGS_BACKEND_EXCLUDE_ENV'
CONFIG_SEPARATOR_FIELD = 'DDGS_BACKEND_EXCLUDE_SEPARATOR'
DEFAULT_CONFIG_FIELD = 'DEFAULT_CONFIG'
RETRIEVAL_CONFIG_KEYS_FIELD = 'RETRIEVAL_CONFIG_KEYS'
DUCKDUCKGO_ENGINE = 'duckduckgo'


class SearchResult(NamedTuple):
    link: str
    title: str | None
    snippet: str | None


def get_filtered_results(results, _filter_list):
    return results


def load_duckduckgo_module():
    open_webui_module = types.ModuleType('open_webui')
    open_webui_module.__path__ = [str(DUCKDUCKGO_MODULE_PATH.parents[2])]
    env_module = types.ModuleType('open_webui.env')
    env_module.USE_SLIM = False
    web_main_module = types.ModuleType('open_webui.retrieval.web.main')
    web_main_module.SearchResult = SearchResult
    web_main_module.get_filtered_results = get_filtered_results

    module_spec = importlib.util.spec_from_file_location('duckduckgo_under_test', DUCKDUCKGO_MODULE_PATH)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError(MODULE_LOAD_ERROR)

    module = importlib.util.module_from_spec(module_spec)
    with patch.dict(
        sys.modules,
        {
            'open_webui': open_webui_module,
            'open_webui.env': env_module,
            'open_webui.retrieval.web.main': web_main_module,
        },
    ):
        module_spec.loader.exec_module(module)
    return module


def reverse_backends(backends):
    backends.reverse()


def execute_dict_entry(module_tree, assignment_name, key, namespace):
    assignment = next(
        node
        for node in module_tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == assignment_name for target in node.targets)
    )
    entry_index = next(
        index
        for index, item_key in enumerate(assignment.value.keys)
        if isinstance(item_key, ast.Constant) and item_key.value == key
    )
    entry_assignment = ast.Assign(
        targets=[ast.Name(id=assignment_name, ctx=ast.Store())],
        value=ast.Dict(
            keys=[assignment.value.keys[entry_index]],
            values=[assignment.value.values[entry_index]],
        ),
    )
    exec(compile(ast.fix_missing_locations(ast.Module([entry_assignment], [])), '<dict-entry>', 'exec'), namespace)
    return namespace[assignment_name]


def load_runtime_exclusion_config():
    config_tree = ast.parse(CONFIG_MODULE_PATH.read_text())
    required_assignments = {CONFIG_ENV_FIELD, CONFIG_SEPARATOR_FIELD, CONFIG_FIELD}
    assignments = [
        node
        for node in config_tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id in required_assignments for target in node.targets)
    ]
    namespace = {'os': os}
    with patch.dict(os.environ, {CONFIG_FIELD: ', '.join(EXCLUDED_BACKENDS)}):
        exec(compile(ast.Module(assignments, []), CONFIG_MODULE_PATH, 'exec'), namespace)
    default_config = execute_dict_entry(config_tree, DEFAULT_CONFIG_FIELD, CONFIG_KEY, namespace)

    router_tree = ast.parse(RETRIEVAL_ROUTER_PATH.read_text())
    retrieval_keys = execute_dict_entry(router_tree, RETRIEVAL_CONFIG_KEYS_FIELD, CONFIG_FIELD, {})
    runtime_key = retrieval_keys[CONFIG_FIELD]
    return default_config[runtime_key], runtime_key


def load_search_web(search_duckduckgo):
    router_tree = ast.parse(RETRIEVAL_ROUTER_PATH.read_text())
    search_web_node = next(
        node for node in router_tree.body if isinstance(node, ast.AsyncFunctionDef) and node.name == 'search_web'
    )
    module = ast.Module(
        [ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), search_web_node],
        [],
    )
    namespace = {
        'asyncio': asyncio,
        'Request': object,
        'SearchResult': SearchResult,
        'search_duckduckgo': search_duckduckgo,
    }
    exec(compile(ast.fix_missing_locations(module), RETRIEVAL_ROUTER_PATH, 'exec'), namespace)
    return namespace['search_web']


def load_web_config():
    router_tree = ast.parse(RETRIEVAL_ROUTER_PATH.read_text())
    web_config_node = next(
        node for node in router_tree.body if isinstance(node, ast.ClassDef) and node.name == 'WebConfig'
    )
    exclusion_field = next(
        node
        for node in web_config_node.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == CONFIG_FIELD
    )
    web_config_node.body = [exclusion_field]
    module = ast.Module(
        [ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), web_config_node],
        [],
    )
    namespace = {'BaseModel': BaseModel}
    exec(compile(ast.fix_missing_locations(module), RETRIEVAL_ROUTER_PATH, 'exec'), namespace)
    return namespace['WebConfig']


class FakeDDGS:
    received_backend = None

    def __init__(self, **_kwargs):
        self.threads = None

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback):
        return False

    def text(self, _query, **kwargs):
        type(self).received_backend = kwargs['backend']
        return [{'href': RESULT_LINK, 'title': RESULT_TITLE, 'body': RESULT_BODY}]


class TestSearchDuckDuckGo(unittest.TestCase):
    def test_auto_backend_excludes_configured_providers(self):
        ddgs_module = types.ModuleType('ddgs')
        ddgs_module.DDGS = FakeDDGS
        duckduckgo_module = load_duckduckgo_module()
        search_duckduckgo = duckduckgo_module.search_duckduckgo

        try:
            with (
                patch.dict(sys.modules, {'ddgs': ddgs_module}),
                patch('urllib.request.getproxies', return_value={}),
                patch.object(duckduckgo_module, 'shuffle', side_effect=reverse_backends, create=True),
            ):
                search_duckduckgo(
                    QUERY,
                    RESULT_COUNT,
                    backend=AUTO_BACKEND,
                    excluded_backends=EXCLUDED_BACKENDS,
                )
        except TypeError as error:
            print(f'RED evidence: DDGS exclusions are not accepted: {error}', flush=True)
            raise

        selected_backends = set(FakeDDGS.received_backend.split(','))
        received_backends = tuple(FakeDDGS.received_backend.split(','))
        try:
            self.assertEqual(EXPECTED_SHUFFLED_BACKENDS, received_backends)
        except AssertionError:
            print(f'RED evidence: DDGS did not rotate allowed backends: {FakeDDGS.received_backend}', flush=True)
            raise
        print(f'GREEN evidence: DDGS rotated allowed backends: {FakeDDGS.received_backend}', flush=True)
        self.assertEqual(EXPECTED_BACKENDS, selected_backends)
        self.assertTrue(selected_backends.isdisjoint(EXCLUDED_BACKENDS))

        with (
            patch.dict(sys.modules, {'ddgs': ddgs_module}),
            patch('urllib.request.getproxies', return_value={}),
        ):
            search_duckduckgo(
                QUERY,
                RESULT_COUNT,
                backend=AUTO_BACKEND,
                excluded_backends=[EMPTY_BACKEND],
            )
        print(f'GREEN evidence: blank DDGS exclusions kept {FakeDDGS.received_backend}', flush=True)
        self.assertEqual(AUTO_BACKEND, FakeDDGS.received_backend)

        with self.assertRaises(ValueError):
            search_duckduckgo(
                QUERY,
                RESULT_COUNT,
                backend=AUTO_BACKEND,
                excluded_backends=[INVALID_BACKEND],
            )
        print('GREEN evidence: unknown DDGS exclusion was rejected', flush=True)

        with self.assertRaises(ValueError):
            search_duckduckgo(
                QUERY,
                RESULT_COUNT,
                backend=AUTO_BACKEND,
                excluded_backends=ALL_BACKENDS,
            )
        print('GREEN evidence: excluding every DDGS backend was rejected', flush=True)

        with (
            patch.dict(sys.modules, {'ddgs': ddgs_module}),
            patch('urllib.request.getproxies', return_value={}),
        ):
            search_duckduckgo(
                QUERY,
                RESULT_COUNT,
                backend=EXPLICIT_BACKEND,
                excluded_backends=[EXPLICIT_BACKEND],
            )
        print(f'GREEN evidence: explicit DDGS backend stayed {FakeDDGS.received_backend}', flush=True)
        self.assertEqual(EXPLICIT_BACKEND, FakeDDGS.received_backend)

    def test_exclusion_setting_is_wired_to_ddgs_search(self):
        received = {}

        def capture_search(_query, _count, _filter_list, **kwargs):
            received.update(kwargs)
            return []

        try:
            configured_exclusions, runtime_key = load_runtime_exclusion_config()
            configured_exclusions = load_web_config()(DDGS_BACKEND_EXCLUDE=configured_exclusions).DDGS_BACKEND_EXCLUDE
            search_web = load_search_web(capture_search)
            asyncio.run(
                search_web(
                    None,
                    DUCKDUCKGO_ENGINE,
                    QUERY,
                    config={
                        'web.search.result_count': RESULT_COUNT,
                        'web.search.domain.filter_list': [],
                        'web.search.concurrent_requests': None,
                        'web.search.ddgs_backend': AUTO_BACKEND,
                        runtime_key: configured_exclusions,
                    },
                )
            )
            self.assertEqual(EXCLUDED_BACKENDS, configured_exclusions)
            self.assertEqual(configured_exclusions, received['excluded_backends'])
        except (AssertionError, KeyError, StopIteration, TypeError) as error:
            print(f'RED evidence: DDGS exclusion configuration is not wired at runtime: {error}', flush=True)
            raise

        print(f'GREEN evidence: configured DDGS exclusions reached search: {configured_exclusions}', flush=True)


if __name__ == '__main__':
    unittest.main()
