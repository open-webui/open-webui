"""Regression tests for get_filtered_results host matching.

The web-search domain filter must match on the URL *hostname*, not the raw
netloc (which carries host:port). Otherwise a blocked host reached over an
explicit port bypasses the blocklist, and an allowlisted host on a non-default
port is wrongly dropped (see issue #16735).
"""

import pytest

from open_webui.retrieval.web import main as web_main
from open_webui.retrieval.web.main import get_filtered_results


@pytest.fixture(autouse=True)
def _no_dns(monkeypatch):
    # keep the test hermetic: don't perform real DNS resolution
    monkeypatch.setattr(web_main, "resolve_hostname", lambda host: ([], []))


def _urls(results):
    return [r["url"] for r in results]


def test_blocklist_blocks_host_with_explicit_port():
    results = [
        {"url": "https://blocked.example/page"},
        {"url": "https://blocked.example:8443/page"},
    ]
    assert _urls(get_filtered_results(results, ["!blocked.example"])) == []


def test_allowlist_keeps_host_with_explicit_port():
    results = [
        {"url": "https://corp.com/page"},
        {"url": "https://corp.com:8080/page"},
    ]
    assert set(_urls(get_filtered_results(results, ["corp.com"]))) == {
        "https://corp.com/page",
        "https://corp.com:8080/page",
    }
