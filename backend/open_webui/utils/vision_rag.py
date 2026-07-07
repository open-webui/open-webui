"""Vision-based Image RAG.

When a user sends an image to a model that has knowledge to retrieve against,
describe the image with a vision-capable model so the standard RAG pipeline can
build retrieval queries from the description. The chatting model's resolved
system prompt frames the description, and the description replaces the raw
image in the final user message — so query generation, vector search, and the
final completion all treat it as text. This also lets non-vision models use
images via an admin-configured global "vision support model".

Activation rules (see ``process_image_rag``):
  - last user message contains at least one ``image_url`` content part, AND
  - there is something to retrieve (model/folder/user knowledge or files), OR
    the chatting model is non-vision but a global vision model is configured
    (so images can still be described for the response), AND
  - the chatting model is vision-capable OR ``rag.vision.support_model`` is set.

Vision-capable chatting models with NO retrieval target are left untouched
(the model sees the image directly) — describing it would be pure overhead.

The describe call is best-effort: on any failure it logs and returns False so
the normal chat flow continues unaffected.
"""

import logging

from open_webui.models.config import Config
from open_webui.models.models import Models
from open_webui.utils.chat import generate_chat_completion
from open_webui.utils.misc import get_last_user_message_item
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


def _message_text(message: dict) -> str:
    """Concatenate ALL text parts of a message (handles multi-part content)."""
    content = message.get('content')
    if isinstance(content, list):
        parts = [p.get('text', '') for p in content if isinstance(p, dict) and p.get('type') == 'text']
        return '\n'.join(p for p in parts if p)
    return content or ''


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
    nothing to retrieve, no vision capability available, or the describe call
    failed).
    """
    # Never run on sub-task calls (title/query generation, or this module's own
    # describe call) — they must not re-trigger image description.
    if (metadata or {}).get('task'):
        return False

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

    # Is there anything for the downstream RAG step to retrieve? Model-attached
    # and folder-attached knowledge are already moved from form_data['files']
    # into metadata['files'] by this point (form_data['files'] is popped around
    # line 2512 and merged into metadata), so read from metadata.
    has_retrieval_target = bool((metadata or {}).get('files')) or bool((metadata or {}).get('folder_knowledge'))

    if chatting_supports_vision:
        # A vision-capable model that has nothing to retrieve should just see the
        # image directly — describing it only adds cost and loses pixel detail.
        if not has_retrieval_target:
            return False
        vision_model_id = model.get('id')
        bypass_filter = False
    elif vision_support_model_id:
        # Non-vision chatting model: describe via the global vision model so the
        # response can still use the image (and RAG, if there's a target).
        vision_model_id = vision_support_model_id
        # Admin-designated infrastructure model — usable by any chatting user so
        # image-RAG works uniformly (matches the intent of a global setting).
        bypass_filter = True
    else:
        # Non-vision chatting model and no global vision model configured.
        return False

    # The chatting model's system prompt frames the description. It is NOT
    # available on `form_data['params']` (already popped by apply_params_to_form_data)
    # nor on `model['info']['params']` (stripped before reaching request.state.MODELS),
    # so fetch it fresh from the model DB row.
    system_raw = None
    try:
        chatting_model_row = await Models.get_model_by_id(model.get('id'))
    except Exception as e:
        log.warning(f'Vision RAG: could not load chatting model for system prompt: {e}')
        chatting_model_row = None
    if chatting_model_row and chatting_model_row.params:
        params_obj = chatting_model_row.params
        params_dict = params_obj.model_dump() if hasattr(params_obj, 'model_dump') else dict(params_obj)
        system_raw = params_dict.get('system')

    system_prompt = await resolve_system_prompt(system_raw, metadata, user)

    user_text = _message_text(last_user)

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
        # Mark this as a sub-task so it can never re-trigger vision-RAG or other
        # pipeline work. (Note: generate_chat_completion still merges
        # request.state.metadata into form_data['metadata'], so the parent's
        # chat_id/session_id are inherited — that's fine for a plain completion
        # and is not re-processed by process_chat_payload.)
        'metadata': {
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

    # generate_chat_completion writes bypass_filter / bypass_system_prompt onto
    # request.state for downstream access checks. Save and restore them so the
    # parent chat's access handling isn't contaminated by this sub-call.
    saved_bf = getattr(request.state, 'bypass_filter', False)
    saved_bsp = getattr(request.state, 'bypass_system_prompt', False)
    try:
        response = await generate_chat_completion(
            request,
            form_data=payload,
            user=user,
            bypass_filter=bypass_filter,
            # The chatting model's system prompt is already injected above as a
            # system message; don't let the support model's own params.system
            # get merged on top.
            bypass_system_prompt=True,
        )
    except Exception as e:
        log.warning(f'Vision RAG: describe call to {vision_model_id} failed: {e}')
        return False
    finally:
        request.state.bypass_filter = saved_bf
        request.state.bypass_system_prompt = saved_bsp

    description = ''
    try:
        description = (
            (((response or {}).get('choices') or [{}])[0].get('message', {}) or {}).get('content') or ''
        ).strip()
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
