from io import BytesIO
import zipfile

import pytest
from fastapi import HTTPException

import open_webui.retrieval.loaders.mineru as mineru_module
from open_webui.retrieval.loaders.mineru import MinerULoader


class FakeResponse:
    def __init__(self, content: bytes):
        self.content = content

    def raise_for_status(self):
        pass


def make_zip_bytes(entries: dict[str, str]) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as zip_file:
        for name, content in entries.items():
            zip_file.writestr(name, content)
    return buffer.getvalue()


def make_loader() -> MinerULoader:
    return MinerULoader(
        file_path="input.pdf",
        api_mode="cloud",
        api_url="http://example.invalid",
        api_key="test-api-key",
        params={},
    )


def patch_zip_download(monkeypatch, tmp_path, zip_bytes: bytes):
    temp_zip_path = tmp_path / "mineru-result.zip"

    def fake_get(url, timeout):
        assert url == "http://example.invalid/result.zip"
        assert timeout == 60
        return FakeResponse(zip_bytes)

    class FixedNamedTemporaryFile:
        def __init__(self, delete=False, suffix=""):
            self.name = str(temp_zip_path)
            self._file = open(self.name, "wb")

        def write(self, data):
            return self._file.write(data)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            self._file.close()

    monkeypatch.setattr(mineru_module.requests, "get", fake_get)
    monkeypatch.setattr(
        mineru_module.tempfile,
        "NamedTemporaryFile",
        FixedNamedTemporaryFile,
    )

    return temp_zip_path


def test_mineru_loader_accepts_none_params():
    loader = MinerULoader(
        file_path="input.pdf",
        api_mode="cloud",
        api_url="http://example.invalid",
        api_key="test-api-key",
        params=None,
    )

    assert loader.params == {}
    assert loader.enable_ocr is False
    assert loader.enable_formula is True
    assert loader.enable_table is True
    assert loader.language == "en"
    assert loader.model_version == "pipeline"


def test_download_and_extract_zip_returns_markdown(monkeypatch, tmp_path):
    zip_bytes = make_zip_bytes({"result.md": "hello mineru"})
    patch_zip_download(monkeypatch, tmp_path, zip_bytes)

    content = make_loader()._download_and_extract_zip(
        "http://example.invalid/result.zip",
        "input.pdf",
    )

    assert content == "hello mineru"


def test_download_and_extract_zip_bad_zip_cleans_temp_file(monkeypatch, tmp_path):
    temp_zip_path = patch_zip_download(monkeypatch, tmp_path, b"not a zip")

    with pytest.raises(HTTPException) as exc_info:
        make_loader()._download_and_extract_zip(
            "http://example.invalid/result.zip",
            "input.pdf",
        )

    assert exc_info.value.status_code == 502
    assert not temp_zip_path.exists()


def test_download_and_extract_zip_does_not_extract_unexpected_files(monkeypatch, tmp_path):
    zip_bytes = make_zip_bytes(
        {
            "unexpected.txt": "not consumed by the loader",
            "result.md": "hello mineru",
        }
    )
    patch_zip_download(monkeypatch, tmp_path, zip_bytes)

    content = make_loader()._download_and_extract_zip(
        "http://example.invalid/result.zip",
        "input.pdf",
    )

    assert content == "hello mineru"
    assert not (tmp_path / "unexpected.txt").exists()


def test_download_and_extract_zip_uses_first_non_empty_markdown(monkeypatch, tmp_path):
    zip_bytes = make_zip_bytes(
        {
            "a.md": "first markdown",
            "b.md": "second markdown",
        }
    )
    patch_zip_download(monkeypatch, tmp_path, zip_bytes)

    content = make_loader()._download_and_extract_zip(
        "http://example.invalid/result.zip",
        "input.pdf",
    )

    assert content == "first markdown"


def test_download_and_extract_zip_allows_reasonable_entry_count(monkeypatch, tmp_path):
    entries = {f"extras/file_{index}.txt": "x" for index in range(100)}
    entries["result.md"] = "hello mineru"
    zip_bytes = make_zip_bytes(entries)
    patch_zip_download(monkeypatch, tmp_path, zip_bytes)

    content = make_loader()._download_and_extract_zip(
        "http://example.invalid/result.zip",
        "input.pdf",
    )

    assert content == "hello mineru"


def test_download_and_extract_zip_rejects_too_many_entries(monkeypatch, tmp_path):
    entries = {f"extras/file_{index}.txt": "x" for index in range(mineru_module.MAX_ZIP_ENTRIES + 1)}
    entries["result.md"] = "hello mineru"
    zip_bytes = make_zip_bytes(entries)
    patch_zip_download(monkeypatch, tmp_path, zip_bytes)

    with pytest.raises(HTTPException) as exc_info:
        make_loader()._download_and_extract_zip(
            "http://example.invalid/result.zip",
            "input.pdf",
        )

    assert exc_info.value.status_code == 502
    assert "too many entries" in exc_info.value.detail


def test_download_and_extract_zip_reads_markdown_within_size_limit(monkeypatch, tmp_path):
    markdown = "x" * (1024 * 1024)
    zip_bytes = make_zip_bytes({"result.md": markdown})
    patch_zip_download(monkeypatch, tmp_path, zip_bytes)

    content = make_loader()._download_and_extract_zip(
        "http://example.invalid/result.zip",
        "input.pdf",
    )

    assert content == markdown
    assert len(content) == 1024 * 1024


def test_download_and_extract_zip_rejects_parent_components(monkeypatch, tmp_path):
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    zip_bytes = make_zip_bytes(
        {
            "../outside/parent_marker.txt": "outside marker",
            "result.md": "hello mineru",
        }
    )
    patch_zip_download(monkeypatch, tmp_path, zip_bytes)

    with pytest.raises(HTTPException) as exc_info:
        make_loader()._download_and_extract_zip(
            "http://example.invalid/result.zip",
            "input.pdf",
        )

    assert exc_info.value.status_code == 502
    assert "Unsafe file path" in exc_info.value.detail
    assert list(outside_dir.iterdir()) == []


def test_download_and_extract_zip_rejects_backslash_entry(monkeypatch, tmp_path):
    zip_bytes = make_zip_bytes(
        {
            "safe_backslash_marker\\nested.txt": "backslash marker",
            "result.md": "hello mineru",
        }
    )
    patch_zip_download(monkeypatch, tmp_path, zip_bytes)

    with pytest.raises(HTTPException) as exc_info:
        make_loader()._download_and_extract_zip(
            "http://example.invalid/result.zip",
            "input.pdf",
        )

    assert exc_info.value.status_code == 502
    assert "Unsafe file path" in exc_info.value.detail


def test_download_and_extract_zip_rejects_large_markdown(monkeypatch, tmp_path):
    markdown = "x" * (mineru_module.MAX_MARKDOWN_SIZE + 1)
    zip_bytes = make_zip_bytes({"result.md": markdown})
    patch_zip_download(monkeypatch, tmp_path, zip_bytes)

    with pytest.raises(HTTPException) as exc_info:
        make_loader()._download_and_extract_zip(
            "http://example.invalid/result.zip",
            "input.pdf",
        )

    assert exc_info.value.status_code == 502
    assert "too large" in exc_info.value.detail
