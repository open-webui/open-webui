import pytest
from unittest.mock import patch, AsyncMock
from open_webui.utils.callback import send_callback, CallbackPayload


@pytest.mark.asyncio
async def test_send_callback_success():
    with patch.dict(
        "os.environ",
        {
            "CALLBACK_URL": "https://example.com/callback",
            "CALLBACK_TOKEN": "test-token",
        },
    ):

        with patch("open_webui.utils.callback.httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock()
            mock_client.return_value.__aenter__.return_value.post = mock_post

            payload = CallbackPayload(
                path="/test",
                method="POST",
                response_content={"result": "success"},
                status_code=200,
            )

            await send_callback(payload)


@pytest.mark.asyncio
async def test_send_callback_no_url():
    """Test que le callback ne fait rien quand CALLBACK_URL n'est pas défini"""

    with patch.dict("os.environ", {}, clear=True):
        with patch("open_webui.utils.callback.httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock()
            mock_client.return_value.__aenter__.return_value.post = mock_post

            payload = CallbackPayload(
                path="/test",
                method="POST",
                response_content={"result": "success"},
                status_code=200,
            )

            await send_callback(payload)

            mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_send_callback_no_token():

    with patch.dict(
        "os.environ", {"CALLBACK_URL": "https://example.com/callback"}, clear=True
    ):
        with patch("open_webui.utils.callback.httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock()
            mock_client.return_value.__aenter__.return_value.post = mock_post

            payload = CallbackPayload(
                path="/test",
                method="POST",
                response_content={"result": "success"},
                status_code=200,
            )

            await send_callback(payload)

            mock_post.assert_not_called()
