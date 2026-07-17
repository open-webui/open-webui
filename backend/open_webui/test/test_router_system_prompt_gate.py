import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.responses import JSONResponse
from open_webui.routers import ollama as ollama_router
from open_webui.routers import openai as openai_router
from open_webui.utils.system_prompt_cache import SYSTEM_PROMPT_CACHE

LANGFUSE_CACHED_PROMPT = 'Langfuse cached prompt for empty params'
MODEL_ID = 'model-1'


def _make_empty_params_model(model_id: str = MODEL_ID):
    return SimpleNamespace(
        id=model_id,
        base_model_id=None,
        params=SimpleNamespace(model_dump=lambda: {}),
    )


def _make_langfuse_binding():
    return SimpleNamespace(
        model_id=MODEL_ID,
        source='langfuse',
        active_version_id=None,
        connection_id='conn-1',
        external_name='movie-critic',
        external_label=None,
        external_version=None,
        cached_content=LANGFUSE_CACHED_PROMPT,
        cached_version='1',
        cached_at=999_999_999_999,
        cache_ttl_seconds=None,
    )


def _make_user():
    return SimpleNamespace(id='user-1', name='Test', email='test@example.com', role='user')


def _make_request(*, openai_models=None, ollama_models=None):
    return SimpleNamespace(
        state=SimpleNamespace(bypass_filter=False, bypass_system_prompt=False),
        app=SimpleNamespace(
            state=SimpleNamespace(
                OPENAI_MODELS=openai_models or {MODEL_ID: {'urlIdx': 0}},
                OLLAMA_MODELS=ollama_models or {MODEL_ID: {'urls': [0]}},
                oauth_manager=SimpleNamespace(get_oauth_token=AsyncMock(return_value=None)),
            )
        ),
        cookies={},
    )


def _system_message_content(payload: dict) -> str | None:
    for message in payload.get('messages', []):
        if message.get('role') == 'system':
            return message.get('content')
    return None


def setup_function():
    SYSTEM_PROMPT_CACHE.clear()


@pytest.mark.asyncio
async def test_openai_router_injects_langfuse_prompt_when_params_empty():
    request = _make_request()
    user = _make_user()
    model = _make_empty_params_model()
    captured_payload = {}

    async def fake_request(*_args, **kwargs):
        captured_payload.update(json.loads(kwargs['data']))
        response = MagicMock()
        response.ok = True
        response.status = 200
        response.headers = {'Content-Type': 'application/json'}
        response.json = AsyncMock(return_value={'choices': [{'message': {'content': 'ok'}}]})
        return response

    session = MagicMock()
    session.request = AsyncMock(side_effect=fake_request)

    with (
        patch('open_webui.routers.openai.Config.get', new_callable=AsyncMock, return_value=True),
        patch('open_webui.routers.openai.Models.get_model_by_id', new_callable=AsyncMock, return_value=model),
        patch('open_webui.routers.openai.check_model_access', new_callable=AsyncMock),
        patch(
            'open_webui.routers.openai.get_openai_connection',
            new_callable=AsyncMock,
            return_value=('http://test/v1', 'key', {}),
        ),
        patch('open_webui.routers.openai.get_headers_and_cookies', new_callable=AsyncMock, return_value=({}, {})),
        patch('open_webui.routers.openai.get_session', new_callable=AsyncMock, return_value=session),
        patch(
            'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
            new_callable=AsyncMock,
            return_value=_make_langfuse_binding(),
        ),
    ):
        await openai_router.generate_chat_completion(
            request,
            {'model': MODEL_ID, 'messages': [{'role': 'user', 'content': 'Hi'}]},
            user=user,
        )

    assert _system_message_content(captured_payload) == LANGFUSE_CACHED_PROMPT


@pytest.mark.asyncio
async def test_ollama_router_injects_langfuse_prompt_when_params_empty():
    request = _make_request()
    user = _make_user()
    model = _make_empty_params_model()
    captured_payload = {}

    async def fake_send_request(*_args, **kwargs):
        captured_payload.update(json.loads(kwargs['payload']))
        return JSONResponse({'message': {'content': 'ok'}})

    with (
        patch('open_webui.routers.ollama.Config.get', new_callable=AsyncMock) as mock_config_get,
        patch('open_webui.routers.ollama.Models.get_model_by_id', new_callable=AsyncMock, return_value=model),
        patch('open_webui.routers.ollama.check_model_access', new_callable=AsyncMock),
        patch('open_webui.routers.ollama.get_ollama_url', new_callable=AsyncMock, return_value=('http://ollama', 0)),
        patch('open_webui.routers.ollama.send_request', new_callable=AsyncMock, side_effect=fake_send_request),
        patch(
            'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
            new_callable=AsyncMock,
            return_value=_make_langfuse_binding(),
        ),
    ):
        mock_config_get.side_effect = lambda key, default=None: {
            'ollama.enable': True,
            'ollama.api_configs': {},
        }.get(key, default)

        await ollama_router.generate_chat_completion(
            request,
            {
                'model': MODEL_ID,
                'messages': [{'role': 'user', 'content': 'Hi'}],
                'stream': False,
            },
            url_idx=0,
            user=user,
        )

    assert _system_message_content(captured_payload) == LANGFUSE_CACHED_PROMPT


@pytest.mark.asyncio
async def test_ollama_openai_proxy_injects_langfuse_prompt_when_params_empty():
    request = _make_request()
    user = _make_user()
    model = _make_empty_params_model()
    captured_payload = {}

    async def fake_send_request(*_args, **kwargs):
        captured_payload.update(json.loads(kwargs['payload']))
        return JSONResponse({'choices': [{'message': {'content': 'ok'}}]})

    with (
        patch('open_webui.routers.ollama.Config.get', new_callable=AsyncMock) as mock_config_get,
        patch('open_webui.routers.ollama.Models.get_model_by_id', new_callable=AsyncMock, return_value=model),
        patch('open_webui.routers.ollama.check_model_access', new_callable=AsyncMock),
        patch('open_webui.routers.ollama.get_ollama_url', new_callable=AsyncMock, return_value=('http://ollama', 0)),
        patch('open_webui.routers.ollama.send_request', new_callable=AsyncMock, side_effect=fake_send_request),
        patch(
            'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
            new_callable=AsyncMock,
            return_value=_make_langfuse_binding(),
        ),
    ):
        mock_config_get.side_effect = lambda key, default=None: {
            'ollama.api_configs': {},
        }.get(key, default)

        await ollama_router.generate_openai_chat_completion(
            request,
            {
                'model': MODEL_ID,
                'messages': [{'role': 'user', 'content': 'Hi'}],
                'stream': False,
            },
            url_idx=0,
            user=user,
        )

    assert _system_message_content(captured_payload) == LANGFUSE_CACHED_PROMPT


@pytest.mark.asyncio
async def test_functions_gate_injects_langfuse_prompt_when_params_empty():
    from open_webui.functions import generate_function_chat_completion

    request = _make_request()
    user = _make_user()
    model = _make_empty_params_model()
    captured_body = {}

    async def fake_pipe(**kwargs):
        captured_body.update(kwargs['body'])
        return 'ok'

    function_module = SimpleNamespace(pipe=fake_pipe, UserValves=SimpleNamespace)

    with (
        patch('open_webui.functions.BYPASS_MODEL_ACCESS_CONTROL', True),
        patch('open_webui.functions.Models.get_model_by_id', new_callable=AsyncMock, return_value=model),
        patch('open_webui.functions.check_model_access', new_callable=AsyncMock),
        patch('open_webui.functions.get_function_module_by_id', new_callable=AsyncMock, return_value=function_module),
        patch(
            'open_webui.functions.Functions.get_user_valves_by_id_and_user_id',
            new_callable=AsyncMock,
            return_value={},
        ),
        patch(
            'open_webui.utils.system_prompt.ModelSystemPromptBindings.get_by_model_id',
            new_callable=AsyncMock,
            return_value=_make_langfuse_binding(),
        ),
    ):
        await generate_function_chat_completion(
            request,
            {'model': MODEL_ID, 'messages': [{'role': 'user', 'content': 'Hi'}], 'stream': False},
            user=user,
        )

    assert _system_message_content(captured_body) == LANGFUSE_CACHED_PROMPT
