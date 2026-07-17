from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_webui.integrations.langfuse.provider import LangfusePromptError, LangfusePromptProvider


@pytest.fixture
def connection():
    return {
        'id': 'conn-1',
        'name': 'Prod',
        'url': 'https://langfuse.example',
        'public_key': 'pk-test',
        'secret_key': 'sk-test',
        'enabled': True,
    }


def _mock_response(*, ok: bool = True, status: int = 200, payload=None, text: str = ''):
    response = MagicMock()
    response.ok = ok
    response.status = status
    response.closed = False
    response.json = AsyncMock(return_value=payload or {})
    response.text = AsyncMock(return_value=text)
    response.close = MagicMock(return_value=None)
    return response


@pytest.mark.asyncio
async def test_get_prompt_text_ok(connection):
    provider = LangfusePromptProvider()
    response = _mock_response(
        payload={
            'name': 'movie-critic',
            'type': 'text',
            'prompt': 'You are a critic of {{movie}}',
            'version': 3,
            'labels': ['production'],
        }
    )
    session = MagicMock()
    session.get = AsyncMock(return_value=response)

    with patch(
        'open_webui.integrations.langfuse.provider.get_session',
        new_callable=AsyncMock,
        return_value=session,
    ), patch(
        'open_webui.integrations.langfuse.provider.cleanup_response',
        new_callable=AsyncMock,
    ):
        result = await provider.fetch_prompt(connection, 'movie-critic', label='production')

    assert result.content == 'You are a critic of {{movie}}'
    assert result.version == 3
    assert result.type == 'text'
    session.get.assert_awaited_once()
    args, kwargs = session.get.await_args
    assert args[0] == 'https://langfuse.example/api/public/v2/prompts/movie-critic'
    assert kwargs['params'] == {'label': 'production'}


@pytest.mark.asyncio
async def test_get_prompt_chat_rejected(connection):
    provider = LangfusePromptProvider()
    response = _mock_response(
        payload={
            'name': 'chat-prompt',
            'type': 'chat',
            'prompt': [{'role': 'system', 'content': 'Hello'}],
            'version': 1,
        }
    )
    session = MagicMock()
    session.get = AsyncMock(return_value=response)

    with patch(
        'open_webui.integrations.langfuse.provider.get_session',
        new_callable=AsyncMock,
        return_value=session,
    ), patch(
        'open_webui.integrations.langfuse.provider.cleanup_response',
        new_callable=AsyncMock,
    ):
        with pytest.raises(LangfusePromptError, match='chat prompts are not supported'):
            await provider.fetch_prompt(connection, 'chat-prompt')
