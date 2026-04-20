import base64
import importlib
import os

from fastapi import FastAPI, Request
from starlette.datastructures import Headers


def _import_yandex_module():
    # Avoid env initialization failures when importing open_webui modules in tests.
    os.environ.setdefault('WEBUI_SECRET_KEY', 'test-webui-secret-key')
    return importlib.import_module('open_webui.retrieval.web.yandex')


class MockResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _build_request() -> Request:
    return Request(
        {
            'type': 'http',
            'asgi.version': '3.0',
            'asgi.spec_version': '2.0',
            'method': 'GET',
            'path': '/internal',
            'query_string': b'',
            'headers': Headers({}).raw,
            'client': ('127.0.0.1', 12345),
            'server': ('127.0.0.1', 80),
            'scheme': 'http',
            'app': FastAPI(),
        },
        None,
    )


def test_xml_element_contents_to_string_returns_empty_for_none():
    yandex = _import_yandex_module()
    assert yandex.xml_element_contents_to_string(None) == ''


def test_search_yandex_skips_invalid_groups_without_crashing(monkeypatch):
    yandex = _import_yandex_module()

    raw_xml = '''
<yandexsearch>
  <response>
    <results>
      <grouping>
        <group>
          <doc>
            <url>https://example.com/1</url>
            <title>Valid title</title>
            <passages><passage>Valid snippet</passage></passages>
          </doc>
        </group>
        <group>
          <doc>
            <url>https://example.com/2</url>
            <title>No passage title</title>
          </doc>
        </group>
        <group>
          <doc>
            <url>https://example.com/3</url>
            <passages><passage>No title snippet</passage></passages>
          </doc>
        </group>
      </grouping>
    </results>
  </response>
</yandexsearch>
'''.strip()

    payload = {'rawData': base64.b64encode(raw_xml.encode('utf-8')).decode('utf-8')}

    def mock_post(*args, **kwargs):
        return MockResponse(payload)

    monkeypatch.setattr(yandex.requests, 'post', mock_post)

    results = yandex.search_yandex(
        request=_build_request(),
        yandex_search_url='',
        yandex_search_api_key='test-key',
        yandex_search_config='',
        query='test query',
        count=3,
    )

    assert len(results) == 2
    assert results[0].link == 'https://example.com/1'
    assert results[0].title == 'Valid title'
    assert results[0].snippet == 'Valid snippet'

    assert results[1].link == 'https://example.com/2'
    assert results[1].title == 'No passage title'
    assert results[1].snippet == ''
