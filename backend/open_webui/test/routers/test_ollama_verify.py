import pytest

import aiohttp
from fastapi import HTTPException

from open_webui.routers.ollama import verify_connection, ConnectionVerificationForm


class _FakeResponse:
    def __init__(self, status: int, json_data=None, text_data: str = ""):
        self.status = status
        self._json = json_data
        self._text = text_data

    async def json(self):
        if self._json is None:
            raise Exception("no json")
        return self._json

    async def text(self):
        return self._text

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeGetCtx:
    def __init__(self, response: _FakeResponse):
        self._resp = response

    async def __aenter__(self):
        return self._resp

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeSession:
    def __init__(self, response: _FakeResponse):
        self._resp = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def get(self, *args, **kwargs):
        return _FakeGetCtx(self._resp)


@pytest.mark.asyncio
async def test_verify_connection_valid_version(monkeypatch):
    # Arrange: mock ClientSession to return a 200 with valid version JSON
    fake_response = _FakeResponse(status=200, json_data={"version": "v0.1.30"})

    def _fake_client_session(*args, **kwargs):
        return _FakeSession(fake_response)

    monkeypatch.setattr(aiohttp, "ClientSession", _fake_client_session)

    form = ConnectionVerificationForm(url="http://example.com", key=None)

    # Act
    res = await verify_connection(form_data=form, user=None)

    # Assert
    assert isinstance(res, dict)
    assert res.get("version") == "v0.1.30"


@pytest.mark.asyncio
async def test_verify_connection_invalid_version_missing_field(monkeypatch):
    # Arrange: mock ClientSession to return a 200 with JSON lacking 'version'
    fake_response = _FakeResponse(status=200, json_data={"ok": True})

    def _fake_client_session(*args, **kwargs):
        return _FakeSession(fake_response)

    monkeypatch.setattr(aiohttp, "ClientSession", _fake_client_session)

    form = ConnectionVerificationForm(url="http://example.com", key=None)

    # Act / Assert
    with pytest.raises(HTTPException) as excinfo:
        await verify_connection(form_data=form, user=None)

    assert excinfo.value.status_code == 400
    assert "missing 'version'" in excinfo.value.detail


@pytest.mark.asyncio
async def test_verify_connection_non_200_raises(monkeypatch):
    # Arrange: mock ClientSession to return a 401 with plain text
    fake_response = _FakeResponse(status=401, json_data=None, text_data="Unauthorized")

    def _fake_client_session(*args, **kwargs):
        return _FakeSession(fake_response)

    monkeypatch.setattr(aiohttp, "ClientSession", _fake_client_session)

    form = ConnectionVerificationForm(url="http://example.com", key=None)

    # Assert
    with pytest.raises(HTTPException) as excinfo:
        await verify_connection(form_data=form, user=None)

    assert excinfo.value.status_code == 500
    assert "HTTP Error: 401" in excinfo.value.detail
