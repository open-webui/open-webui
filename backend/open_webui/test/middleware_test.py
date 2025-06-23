import pytest
from unittest.mock import patch
from unittest.mock import Mock, MagicMock, AsyncMock
from fastapi import FastAPI
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from open_webui.middleware import MatchType
from open_webui.middleware import PreventCachingMiddleware

def mock_scope(path) -> Scope:
    return {
        "type": "http",
        "path": path,
    }

class TestMiddleware:
    def assert_has_header(self, header_list: list[tuple[bytes]], key_to_assert: bytes, value_to_assert: bytes):
        for key, value in header_list:
            if key == key_to_assert:
                assert value == value_to_assert
                return

        pytest.fail(f"Header \"{key_to_assert}\" not found in {header_list}")


    @pytest.mark.asyncio
    async def test_prevent_caching_middleware(self, monkeypatch):
        async def receive_mock():
            pass

        send_mock = AsyncMock()

        app_mock = AsyncMock(spec=ASGIApp)

        middleware = PreventCachingMiddleware(app_mock, paths = [
            ("/exact", MatchType.exact),
            ("/prefix/", MatchType.prefix),
        ])

        # Exact test

        await middleware(mock_scope("/exact"), receive_mock, send_mock)

        app_mock.assert_awaited()
        send = app_mock.await_args.args[2]

        message_mock = {
            "type": "http.response.start",
            "headers": [],
        }

        await send(message_mock)

        self.assert_has_header(message_mock["headers"], b"cache-control", b"must-revalidate")
        self.assert_has_header(message_mock["headers"], b"expire", b"0")


        # Exact counter test

        await middleware(mock_scope("/exactamente"), receive_mock, send_mock)

        app_mock.assert_awaited()
        send = app_mock.await_args.args[2]

        message_mock = {
            "type": "http.response.start",
            "headers": [],
        }

        await send(message_mock)

        assert message_mock["headers"] == []


        # Prefix test

        await middleware(mock_scope("/prefix/01"), receive_mock, send_mock)

        app_mock.assert_awaited()
        send = app_mock.await_args.args[2]

        message_mock = {
            "type": "http.response.start",
            "headers": [],
        }

        await send(message_mock)

        self.assert_has_header(message_mock["headers"], b"cache-control", b"must-revalidate")
        self.assert_has_header(message_mock["headers"], b"expire", b"0")


        # Prefix counter test

        await middleware(mock_scope("/prefix"), receive_mock, send_mock)

        app_mock.assert_awaited()
        send = app_mock.await_args.args[2]

        message_mock = {
            "type": "http.response.start",
            "headers": [],
        }

        await send(message_mock)

        assert message_mock["headers"] == []


        # Unrelated test

        await middleware(mock_scope("/otherroute"), receive_mock, send_mock)

        app_mock.assert_awaited()
        send = app_mock.await_args.args[2]

        message_mock = {
            "type": "http.response.start",
            "headers": [],
        }

        await send(message_mock)

        assert message_mock["headers"] == []
