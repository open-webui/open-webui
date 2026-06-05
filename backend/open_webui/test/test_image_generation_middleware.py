import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.fixture
def fake_chat():
    chat = MagicMock()
    chat.chat = {
        "history": {
            "currentId": "msg1",
            "messages": {
                "msg1": {
                    "id": "msg1",
                    "role": "user",
                    "content": "make the dog friendlier",
                    "parentId": None,
                    "files": [{"type": "image", "url": "http://example.com/dog.png"}],
                }
            },
        }
    }
    return chat

def _make_request(enable_prompt_gen: bool = True, enable_image_edit: bool = True):
    config = MagicMock()
    config.ENABLE_IMAGE_PROMPT_GENERATION = enable_prompt_gen
    config.ENABLE_IMAGE_EDIT = enable_image_edit
    request = MagicMock()
    request.app.state.config = config
    return request

def _make_extra_params(chat_id: str = "test-chat-id"):
    return {
        "__event_emitter__": AsyncMock(),
        "__metadata__": {"chat_id": chat_id, "message_id": "test-msg-id"},
    }

REFINED_PROMPT = "a friendly golden retriever wagging its tail in a sunny park"
GENERATE_IMAGE_PROMPT_RESPONSE = {
    "choices": [{"message": {"content": json.dumps({"prompt": REFINED_PROMPT})}}]
}

@pytest.mark.asyncio
async def test_image_prompt_generation_called_for_image_edit(fake_chat):
    from open_webui.utils.middleware import chat_image_generation_handler

    request = _make_request(enable_prompt_gen=True, enable_image_edit=True)
    extra_params = _make_extra_params()
    user = MagicMock()

    form_data = {
        "model": "test-model",
        "messages": [{"role": "user", "content": "make the dog friendlier"}],
    }

    with (
        patch("open_webui.utils.middleware.Chats.get_chat_by_id_and_user_id", AsyncMock(return_value=fake_chat)),
        patch("open_webui.utils.middleware.generate_image_prompt", AsyncMock(return_value=GENERATE_IMAGE_PROMPT_RESPONSE)) as mock_gen_prompt,
        patch("open_webui.utils.middleware.image_edits", AsyncMock(return_value=[{"url": "http://example.com/edited.png"}])) as mock_image_edits,
    ):
        await chat_image_generation_handler(request, form_data, extra_params, user)
        
        mock_gen_prompt.assert_called_once()
        call_kwargs = mock_image_edits.call_args
        edit_form = call_kwargs.kwargs.get("form_data") or call_kwargs.args[1]
        assert edit_form.prompt == REFINED_PROMPT

@pytest.mark.asyncio
async def test_image_prompt_generation_skipped_when_disabled_for_edit(fake_chat):
    from open_webui.utils.middleware import chat_image_generation_handler

    request = _make_request(enable_prompt_gen=False, enable_image_edit=True)
    extra_params = _make_extra_params()
    user = MagicMock()

    form_data = {
        "model": "test-model",
        "messages": [{"role": "user", "content": "make the dog friendlier"}],
    }

    with (
        patch("open_webui.utils.middleware.Chats.get_chat_by_id_and_user_id", AsyncMock(return_value=fake_chat)),
        patch("open_webui.utils.middleware.generate_image_prompt", AsyncMock(return_value=GENERATE_IMAGE_PROMPT_RESPONSE)) as mock_gen_prompt,
        patch("open_webui.utils.middleware.image_edits", AsyncMock(return_value=[{"url": "http://example.com/edited.png"}])) as mock_image_edits,
    ):
        await chat_image_generation_handler(request, form_data, extra_params, user)
        
        mock_gen_prompt.assert_not_called()
        call_kwargs = mock_image_edits.call_args
        edit_form = call_kwargs.kwargs.get("form_data") or call_kwargs.args[1]
        assert edit_form.prompt == "make the dog friendlier"

@pytest.mark.asyncio
async def test_image_prompt_generation_still_called_for_create_path():
    from open_webui.utils.middleware import chat_image_generation_handler

    request = _make_request(enable_prompt_gen=True, enable_image_edit=True)
    extra_params = _make_extra_params()
    user = MagicMock()

    no_image_chat = MagicMock()
    no_image_chat.chat = {
        "history": {
            "currentId": "msg1",
            "messages": {
                "msg1": {
                    "id": "msg1",
                    "role": "user",
                    "content": "generate a cat",
                    "parentId": None,
                }
            },
        }
    }

    form_data = {
        "model": "test-model",
        "messages": [{"role": "user", "content": "generate a cat"}],
    }

    with (
        patch("open_webui.utils.middleware.Chats.get_chat_by_id_and_user_id", AsyncMock(return_value=no_image_chat)),
        patch("open_webui.utils.middleware.generate_image_prompt", AsyncMock(return_value=GENERATE_IMAGE_PROMPT_RESPONSE)) as mock_gen_prompt,
        patch("open_webui.utils.middleware.image_generations", AsyncMock(return_value=[{"url": "http://example.com/cat.png"}])) as mock_image_generations,
    ):
        await chat_image_generation_handler(request, form_data, extra_params, user)
        
        mock_gen_prompt.assert_called_once()
        call_kwargs = mock_image_generations.call_args
        create_form = call_kwargs.kwargs.get("form_data") or call_kwargs.args[1]
        assert create_form.prompt == REFINED_PROMPT
