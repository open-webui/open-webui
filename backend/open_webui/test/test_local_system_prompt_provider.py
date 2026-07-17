import pytest
from open_webui.integrations.system_prompt.local import LocalSystemPromptProvider


@pytest.fixture
def provider() -> LocalSystemPromptProvider:
    return LocalSystemPromptProvider()


@pytest.fixture
def connection() -> dict:
    return {'id': 'conn-1', 'url': 'https://example.test', 'enabled': True}


@pytest.mark.asyncio
async def test_list_prompts_not_implemented(provider, connection):
    with pytest.raises(NotImplementedError, match='does not support list_prompts'):
        await provider.list_prompts(connection)


@pytest.mark.asyncio
async def test_get_prompt_not_implemented(provider, connection):
    with pytest.raises(NotImplementedError, match='does not support get_prompt'):
        await provider.get_prompt(connection, 'movie-critic')
