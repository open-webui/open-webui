"""Vision-based Image RAG.

When a user sends an image, describe it with a vision-capable model so the
standard RAG pipeline can build retrieval queries from the description. The
chatting model's resolved system prompt frames the description, and the
description replaces the raw image in the final user message — so the rest of
the pipeline (query generation, vector search, the final completion) treats it
as text. This lets image-driven RAG work even for models that have no vision
capability, via an admin-configured global "vision support model".

Activation rules (see ``process_image_rag``):
  - last user message contains at least one ``image_url`` content part, AND
  - the chatting model is vision-capable OR ``rag.vision.support_model`` is set.

The describe call is best-effort: on any failure it logs and returns False so
the normal chat flow continues unaffected.
"""

import logging
from typing import Any, Optional

from open_webui.models.config import Config
from open_webui.utils.chat import generate_chat_completion
from open_webui.utils.misc import get_last_user_message, get_last_user_message_item
from open_webui.utils.payload import resolve_system_prompt

log = logging.getLogger(__name__)


DEFAULT_DESCRIBE_PROMPT = (
    'Describe this image in detail so it can be used for knowledge-base search. '
    'Capture any visible text, error messages, UI elements, diagrams, objects, '
    'and relevant context. If the user included a message, prioritise details '
    'relevant to it, but still describe the rest of the image.'
)


def _image_parts(message: dict) -> list[dict]:
    """Return the ``image_url`` content parts of a message (OpenAI multimodal)."""
    content = message.get('content')
    if not isinstance(content, list):
        return []
    return [p for p in content if isinstance(p, dict) and p.get('type') == 'image_url']


async def process_image_rag(
    request,
    form_data: dict,
    metadata: dict,
    user,
    model: dict,
    event_emitter=None,
) -> bool:
    """Describe images in the last user message and inject the description.

    Mutates ``form_data['messages']`` in place: the image parts of the last
    user message are replaced by a text block holding the description (followed
    by the user's original text), so the downstream RAG query-generation and the
    final model call both see text only.

    Returns True if a description was injected, False otherwise (no image,
    no vision capability available, or the describe call failed).
    """
    messages = form_data.get('messages', [])
    last_user = get_last_user_message_item(messages)
    if not last_user:
        return False

    image_parts = _image_parts(last_user)
    if not image_parts:
        return False

    # Decide which model describes the image.
    capabilities = model.get('info', {}).get('meta', {}).get('capabilities') or {}
    chatting_supports_vision = capabilities.get('vision', True)
    vision_support_model_id = ((await Config.get('rag.vision.support_model')) or '').strip()

    if chatting_supports_vision:
        vision_model_id = model.get('id')
        bypass_filter = False
    elif vision_support_model_id:
        vision_model_id = vision_support_model_id
        # Admin-designated infrastructure model — usable by any chatting user
        # so image-RAG works uniformly (matches the intent of a global setting).
        bypass_filter = True
    else:
        # Non-vision chatting model and no global vision model configured.
        return False

    # The chatting model's system prompt (resolved the same way as the main
    # pipeline) frames the description with the same persona/instructions.
    system_prompt = await resolve_system_prompt(
        (form_data.get('params') or {}).get('system'),
        metadata,
        user,
    )

    user_text = get_last_user_message(messages) or ''

    describe_instruction = DEFAULT_DESCRIBE_PROMPT
    if user_text:
        describe_instruction = f"{describe_instruction}\n\nUser's message: {user_text}"

    describe_content: list[dict] = [{'type': 'text', 'text': describe_instruction}]
    describe_content.extend(image_parts)

    describe_messages: list[dict] = []
    if system_prompt:
        describe_messages.append({'role': 'system', 'content': system_prompt})
    describe_messages.append({'role': 'user', 'content': describe_content})

    payload = {
        'model': vision_model_id,
        'messages': describe_messages,
        'stream': False,
        'metadata': {
            **(metadata or {}),
            'task': 'vision_rag_description',
            'chat_id': (metadata or {}).get('chat_id'),
        },
    }

    if event_emitter is not None:
        try:
            await event_emitter(
                {
                    'type': 'status',
                    'data': {'action': 'vision_rag', 'query': user_text, 'done': False},
                }
            )
        except Exception:
            pass

    try:
        response = await generate_chat_completion(request, form_data=payload, user=user, bypass_filter=bypass_filter)
    except Exception as e:
        log.warning(f'Vision RAG: describe call to {vision_model_id} failed: {e}')
        return False

    description = ''
    try:
        description = (((response or {}).get('choices') or [{}])[0].get('message', {}).get('content') or '').strip()
    except Exception:
        description = ''

    if not description:
        log.warning('Vision RAG: describe call returned empty content; skipping.')
        return False

    # Replace image parts with the description text. Keep the user's original
    # text so the final prompt is: description + original prompt.
    combined = f'[Image description]\n{description}'
    if user_text:
        combined = f'{combined}\n\n{user_text}'
    last_user['content'] = [{'type': 'text', 'text': combined}]

    if event_emitter is not None:
        try:
            await event_emitter({'type': 'status', 'data': {'action': 'vision_rag', 'done': True}})
        except Exception:
            pass

    return True
