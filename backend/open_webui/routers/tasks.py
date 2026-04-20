import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from open_webui.clients.pipelines import process_pipeline_inlet_filter
from open_webui.clients.tasks import (
    generate_chat_tags as _client_generate_chat_tags,
)
from open_webui.clients.tasks import (
    generate_follow_ups as _client_generate_follow_ups,
)
from open_webui.clients.tasks import (
    generate_image_prompt as _client_generate_image_prompt,
)
from open_webui.clients.tasks import (
    generate_queries as _client_generate_queries,
)
from open_webui.clients.tasks import (
    generate_title as _client_generate_title,
)
from open_webui.config import (
    DEFAULT_AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE,
    DEFAULT_EMOJI_GENERATION_PROMPT_TEMPLATE,
    DEFAULT_MOA_GENERATION_PROMPT_TEMPLATE,
)
from open_webui.constants import ERROR_MESSAGES, TASKS
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.chat import generate_chat_completion
from open_webui.utils.task import (
    autocomplete_generation_template,
    emoji_generation_template,
    get_task_model_id,
    moa_response_generation_template,
)
from pydantic import BaseModel

log = logging.getLogger(__name__)

router = APIRouter()


##################################
#
# Task Endpoints
#
##################################


class ActiveChatsForm(BaseModel):
    chat_ids: list[str]


@router.post('/active/chats')
async def check_active_chats(request: Request, form_data: ActiveChatsForm, user=Depends(get_verified_user)):
    """Check which chat IDs have active tasks."""
    from open_webui.tasks import get_active_chat_ids

    active = await get_active_chat_ids(request.app.state.redis, form_data.chat_ids)
    return {'active_chat_ids': active}


@router.get('/config')
async def get_task_config(request: Request, user=Depends(get_verified_user)):
    return {
        'TASK_MODEL': request.app.state.config.TASK_MODEL,
        'TASK_MODEL_EXTERNAL': request.app.state.config.TASK_MODEL_EXTERNAL,
        'TITLE_GENERATION_PROMPT_TEMPLATE': request.app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE,
        'IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE': request.app.state.config.IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE,
        'ENABLE_AUTOCOMPLETE_GENERATION': request.app.state.config.ENABLE_AUTOCOMPLETE_GENERATION,
        'AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH': request.app.state.config.AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH,
        'TAGS_GENERATION_PROMPT_TEMPLATE': request.app.state.config.TAGS_GENERATION_PROMPT_TEMPLATE,
        'FOLLOW_UP_GENERATION_PROMPT_TEMPLATE': request.app.state.config.FOLLOW_UP_GENERATION_PROMPT_TEMPLATE,
        'ENABLE_FOLLOW_UP_GENERATION': request.app.state.config.ENABLE_FOLLOW_UP_GENERATION,
        'ENABLE_TAGS_GENERATION': request.app.state.config.ENABLE_TAGS_GENERATION,
        'ENABLE_TITLE_GENERATION': request.app.state.config.ENABLE_TITLE_GENERATION,
        'ENABLE_SEARCH_QUERY_GENERATION': request.app.state.config.ENABLE_SEARCH_QUERY_GENERATION,
        'ENABLE_RETRIEVAL_QUERY_GENERATION': request.app.state.config.ENABLE_RETRIEVAL_QUERY_GENERATION,
        'QUERY_GENERATION_PROMPT_TEMPLATE': request.app.state.config.QUERY_GENERATION_PROMPT_TEMPLATE,
        'TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE': request.app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE,
        'VOICE_MODE_PROMPT_TEMPLATE': request.app.state.config.VOICE_MODE_PROMPT_TEMPLATE,
    }


class TaskConfigForm(BaseModel):
    TASK_MODEL: str | None
    TASK_MODEL_EXTERNAL: str | None
    ENABLE_TITLE_GENERATION: bool
    TITLE_GENERATION_PROMPT_TEMPLATE: str
    IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE: str
    ENABLE_AUTOCOMPLETE_GENERATION: bool
    AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH: int
    TAGS_GENERATION_PROMPT_TEMPLATE: str
    FOLLOW_UP_GENERATION_PROMPT_TEMPLATE: str
    ENABLE_FOLLOW_UP_GENERATION: bool
    ENABLE_TAGS_GENERATION: bool
    ENABLE_SEARCH_QUERY_GENERATION: bool
    ENABLE_RETRIEVAL_QUERY_GENERATION: bool
    QUERY_GENERATION_PROMPT_TEMPLATE: str
    TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE: str
    VOICE_MODE_PROMPT_TEMPLATE: str | None


@router.post('/config/update')
async def update_task_config(request: Request, form_data: TaskConfigForm, user=Depends(get_admin_user)):
    request.app.state.config.TASK_MODEL = form_data.TASK_MODEL
    request.app.state.config.TASK_MODEL_EXTERNAL = form_data.TASK_MODEL_EXTERNAL
    request.app.state.config.ENABLE_TITLE_GENERATION = form_data.ENABLE_TITLE_GENERATION
    request.app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE = form_data.TITLE_GENERATION_PROMPT_TEMPLATE

    request.app.state.config.ENABLE_FOLLOW_UP_GENERATION = form_data.ENABLE_FOLLOW_UP_GENERATION
    request.app.state.config.FOLLOW_UP_GENERATION_PROMPT_TEMPLATE = form_data.FOLLOW_UP_GENERATION_PROMPT_TEMPLATE

    request.app.state.config.IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE = form_data.IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE

    request.app.state.config.ENABLE_AUTOCOMPLETE_GENERATION = form_data.ENABLE_AUTOCOMPLETE_GENERATION
    request.app.state.config.AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH = (
        form_data.AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH
    )

    request.app.state.config.TAGS_GENERATION_PROMPT_TEMPLATE = form_data.TAGS_GENERATION_PROMPT_TEMPLATE
    request.app.state.config.ENABLE_TAGS_GENERATION = form_data.ENABLE_TAGS_GENERATION
    request.app.state.config.ENABLE_SEARCH_QUERY_GENERATION = form_data.ENABLE_SEARCH_QUERY_GENERATION
    request.app.state.config.ENABLE_RETRIEVAL_QUERY_GENERATION = form_data.ENABLE_RETRIEVAL_QUERY_GENERATION

    request.app.state.config.QUERY_GENERATION_PROMPT_TEMPLATE = form_data.QUERY_GENERATION_PROMPT_TEMPLATE
    request.app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE = form_data.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE

    request.app.state.config.VOICE_MODE_PROMPT_TEMPLATE = form_data.VOICE_MODE_PROMPT_TEMPLATE

    return {
        'TASK_MODEL': request.app.state.config.TASK_MODEL,
        'TASK_MODEL_EXTERNAL': request.app.state.config.TASK_MODEL_EXTERNAL,
        'ENABLE_TITLE_GENERATION': request.app.state.config.ENABLE_TITLE_GENERATION,
        'TITLE_GENERATION_PROMPT_TEMPLATE': request.app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE,
        'IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE': request.app.state.config.IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE,
        'ENABLE_AUTOCOMPLETE_GENERATION': request.app.state.config.ENABLE_AUTOCOMPLETE_GENERATION,
        'AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH': request.app.state.config.AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH,
        'TAGS_GENERATION_PROMPT_TEMPLATE': request.app.state.config.TAGS_GENERATION_PROMPT_TEMPLATE,
        'ENABLE_TAGS_GENERATION': request.app.state.config.ENABLE_TAGS_GENERATION,
        'ENABLE_FOLLOW_UP_GENERATION': request.app.state.config.ENABLE_FOLLOW_UP_GENERATION,
        'FOLLOW_UP_GENERATION_PROMPT_TEMPLATE': request.app.state.config.FOLLOW_UP_GENERATION_PROMPT_TEMPLATE,
        'ENABLE_SEARCH_QUERY_GENERATION': request.app.state.config.ENABLE_SEARCH_QUERY_GENERATION,
        'ENABLE_RETRIEVAL_QUERY_GENERATION': request.app.state.config.ENABLE_RETRIEVAL_QUERY_GENERATION,
        'QUERY_GENERATION_PROMPT_TEMPLATE': request.app.state.config.QUERY_GENERATION_PROMPT_TEMPLATE,
        'TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE': request.app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE,
        'VOICE_MODE_PROMPT_TEMPLATE': request.app.state.config.VOICE_MODE_PROMPT_TEMPLATE,
    }


@router.post('/title/completions')
async def generate_title(request: Request, form_data: dict, user=Depends(get_verified_user)):
    return await _client_generate_title(request, form_data, user)


@router.post('/follow_up/completions')
async def generate_follow_ups(request: Request, form_data: dict, user=Depends(get_verified_user)):
    return await _client_generate_follow_ups(request, form_data, user)


@router.post('/tags/completions')
async def generate_chat_tags(request: Request, form_data: dict, user=Depends(get_verified_user)):
    return await _client_generate_chat_tags(request, form_data, user)


@router.post('/image_prompt/completions')
async def generate_image_prompt(request: Request, form_data: dict, user=Depends(get_verified_user)):
    return await _client_generate_image_prompt(request, form_data, user)


@router.post('/queries/completions')
async def generate_queries(request: Request, form_data: dict, user=Depends(get_verified_user)):
    return await _client_generate_queries(request, form_data, user)


@router.post('/auto/completions')
async def generate_autocompletion(request: Request, form_data: dict, user=Depends(get_verified_user)):
    if not request.app.state.config.ENABLE_AUTOCOMPLETE_GENERATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.FEATURE_DISABLED('Autocompletion generation'),
        )

    type = form_data.get('type')
    prompt = form_data.get('prompt')
    messages = form_data.get('messages')

    if request.app.state.config.AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH > 0:
        if len(prompt) > request.app.state.config.AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.INPUT_TOO_LONG(request.app.state.config.AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH),
            )

    if getattr(request.state, 'direct', False) and hasattr(request.state, 'model'):
        models = {
            request.state.model['id']: request.state.model,
        }
    else:
        models = request.app.state.MODELS

    model_id = form_data['model']
    if model_id not in models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.MODEL_NOT_FOUND(),
        )

    # Check if the user has a custom task model
    # If the user has a custom task model, use that model
    task_model_id = get_task_model_id(
        model_id,
        request.app.state.config.TASK_MODEL,
        request.app.state.config.TASK_MODEL_EXTERNAL,
        models,
    )

    log.debug(f'generating autocompletion using model {task_model_id} for user {user.email}')

    if (request.app.state.config.AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE).strip() != '':
        template = request.app.state.config.AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE
    else:
        template = DEFAULT_AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE

    content = autocomplete_generation_template(template, prompt, messages, type, user)

    payload = {
        'model': task_model_id,
        'messages': [{'role': 'user', 'content': content}],
        'stream': False,
        'metadata': {
            **(request.state.metadata if hasattr(request.state, 'metadata') else {}),
            'task': str(TASKS.AUTOCOMPLETE_GENERATION),
            'task_body': form_data,
            'chat_id': form_data.get('chat_id', None),
        },
    }

    # Process the payload through the pipeline
    try:
        payload = await process_pipeline_inlet_filter(request, payload, user, models)
    except Exception as e:
        raise e

    try:
        return await generate_chat_completion(request, form_data=payload, user=user)
    except Exception as e:
        log.error(f'Error generating chat completion: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'detail': 'An internal error has occurred.'},
        )


@router.post('/emoji/completions')
async def generate_emoji(request: Request, form_data: dict, user=Depends(get_verified_user)):
    if getattr(request.state, 'direct', False) and hasattr(request.state, 'model'):
        models = {
            request.state.model['id']: request.state.model,
        }
    else:
        models = request.app.state.MODELS

    model_id = form_data['model']
    if model_id not in models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.MODEL_NOT_FOUND(),
        )

    # Check if the user has a custom task model
    # If the user has a custom task model, use that model
    task_model_id = get_task_model_id(
        model_id,
        request.app.state.config.TASK_MODEL,
        request.app.state.config.TASK_MODEL_EXTERNAL,
        models,
    )

    log.debug(f'generating emoji using model {task_model_id} for user {user.email} ')

    template = DEFAULT_EMOJI_GENERATION_PROMPT_TEMPLATE

    content = emoji_generation_template(template, form_data['prompt'], user)

    payload = {
        'model': task_model_id,
        'messages': [{'role': 'user', 'content': content}],
        'stream': False,
        **(
            {'max_tokens': 4}
            if models[task_model_id].get('owned_by') == 'ollama'
            else {
                'max_completion_tokens': 4,
            }
        ),
        'metadata': {
            **(request.state.metadata if hasattr(request.state, 'metadata') else {}),
            'task': str(TASKS.EMOJI_GENERATION),
            'task_body': form_data,
            'chat_id': form_data.get('chat_id', None),
        },
    }

    # Process the payload through the pipeline
    try:
        payload = await process_pipeline_inlet_filter(request, payload, user, models)
    except Exception as e:
        raise e

    try:
        return await generate_chat_completion(request, form_data=payload, user=user)
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={'detail': str(e)},
        )


@router.post('/moa/completions')
async def generate_moa_response(request: Request, form_data: dict, user=Depends(get_verified_user)):
    if getattr(request.state, 'direct', False) and hasattr(request.state, 'model'):
        models = {
            request.state.model['id']: request.state.model,
        }
    else:
        models = request.app.state.MODELS

    model_id = form_data['model']

    if model_id not in models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.MODEL_NOT_FOUND(),
        )

    template = DEFAULT_MOA_GENERATION_PROMPT_TEMPLATE

    content = moa_response_generation_template(
        template,
        form_data['prompt'],
        form_data['responses'],
    )

    payload = {
        'model': model_id,
        'messages': [{'role': 'user', 'content': content}],
        'stream': form_data.get('stream', False),
        'metadata': {
            **(request.state.metadata if hasattr(request.state, 'metadata') else {}),
            'chat_id': form_data.get('chat_id', None),
            'task': str(TASKS.MOA_RESPONSE_GENERATION),
            'task_body': form_data,
        },
    }

    # Process the payload through the pipeline
    try:
        payload = await process_pipeline_inlet_filter(request, payload, user, models)
    except Exception as e:
        raise e

    try:
        return await generate_chat_completion(request, form_data=payload, user=user)
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={'detail': str(e)},
        )
