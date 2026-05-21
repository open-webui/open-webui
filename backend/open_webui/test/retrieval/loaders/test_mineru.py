import io
import zipfile

import pytest
from fastapi import HTTPException
from open_webui.retrieval.loaders.mineru import MinerULoader


class _Response:
    def __init__(self, content: bytes):
        self.content = content

    def raise_for_status(self):
        return None


def _zip_bytes(entries: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zip_file:
        for name, content in entries.items():
            zip_file.writestr(name, content)
    return buffer.getvalue()


def test_mineru_zip_loader_reads_safe_markdown_without_extracting(monkeypatch):
    loader = MinerULoader('input.pdf', api_mode='cloud', api_key='test-key')
    content = _zip_bytes(
        {
            'images/page.png': 'ignored',
            'nested/result.md': '# Parsed document',
        }
    )

    monkeypatch.setattr('open_webui.retrieval.loaders.mineru.requests.get', lambda *_, **__: _Response(content))

    assert loader._download_and_extract_zip('https://example.test/result.zip', 'input.pdf') == '# Parsed document'


def test_mineru_zip_loader_rejects_traversal_markdown(monkeypatch):
    loader = MinerULoader('input.pdf', api_mode='cloud', api_key='test-key')
    content = _zip_bytes({'../escape.md': '# outside'})

    monkeypatch.setattr('open_webui.retrieval.loaders.mineru.requests.get', lambda *_, **__: _Response(content))

    with pytest.raises(HTTPException) as exc_info:
        loader._download_and_extract_zip('https://example.test/result.zip', 'input.pdf')

    assert exc_info.value.status_code == 502
    assert 'Unsafe .md paths' in exc_info.value.detail
