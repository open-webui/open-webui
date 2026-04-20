import logging
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from open_webui.clients.pipelines import process_pipeline_inlet_filter
from open_webui.config import (
    DEFAULT_FOLLOW_UP_GENERATION_PROMPT_TEMPLATE,
    DEFAULT_IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE,
    DEFAULT_QUERY_GENERATION_PROMPT_TEMPLATE,
    DEFAULT_TAGS_GENERATION_PROMPT_TEMPLATE,
    DEFAULT_TITLE_GENERATION_PROMPT_TEMPLATE,
)
from open_webui.constants import ERROR_MESSAGES, TASKS
from open_webui.models.users import UserModel
from open_webui.utils.chat import generate_chat_completion
from open_webui.utils.task import (
    follow_up_generation_template,
    get_task_model_id,
    image_prompt_generation_template,
    query_generation_template,
    tags_generation_template,
    title_generation_template,
)

log = logging.getLogger(__name__)


def _resolve_models(request: Request) -> dict[str, dict[str, Any]]:
    if getattr(request.state, 'direct', False) and hasattr(request.state, 'model'):
        return {request.state.model['id']: request.state.model}
    return request.app.state.MODELS


def _resolve_task_model(
    request: Request,
    form_data: dict[str, Any],
    models: dict[str, dict[str, Any]],
) -> str:
    model_id = form_data['model']
    if model_id not in models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.MODEL_NOT_FOUND(),
        )
    return get_task_model_id(
        model_id,
        request.app.state.config.TASK_MODEL,
        request.app.state.config.TASK_MODEL_EXTERNAL,
        models,
    )


def _task_metadata(request: Request, form_data: dict[str, Any], task: str) -> dict[str, Any]:
    return {
        **(request.state.metadata if hasattr(request.state, 'metadata') else {}),
        'task': task,
        'task_body': form_data,
        'chat_id': form_data.get('chat_id', None),
    }


async def _run_task_pipeline(
    request: Request,
    user: UserModel,
    models: dict[str, dict[str, Any]],
    payload: dict[str, Any],
) -> Any:
    payload = await process_pipeline_inlet_filter(request, payload, user, models)
    try:
        return await generate_chat_completion(request, form_data=payload, user=user)
    except Exception:
        log.error('Exception occurred', exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={'detail': 'An internal error has occurred.'},
        )


async def generate_title(
    request: Request,
    form_data: dict[str, Any],
    user: UserModel,
) -> Any:
    if not request.app.state.config.ENABLE_TITLE_GENERATION:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={'detail': 'Title generation is disabled'},
        )

    models = _resolve_models(request)
    task_model_id = _resolve_task_model(request, form_data, models)

    log.debug(f'generating chat title using model {task_model_id} for user {user.email} ')

    if request.app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE != '':
        template = request.app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE
    else:
        template = DEFAULT_TITLE_GENERATION_PROMPT_TEMPLATE
    content = title_generation_template(template, form_data['messages'], user)
    max_tokens = models[task_model_id].get('info', {}).get('params', {}).get('max_tokens', 1000)
    token_key = 'max_tokens' if models[task_model_id].get('owned_by') == 'ollama' else 'max_completion_tokens'

    payload = {
        'model': task_model_id,
        'messages': [{'role': 'user', 'content': content}],
        'stream': False,
        token_key: max_tokens,
        'metadata': _task_metadata(request, form_data, str(TASKS.TITLE_GENERATION)),
    }

    return await _run_task_pipeline(request, user, models, payload)


async def generate_follow_ups(
    request: Request,
    form_data: dict[str, Any],
    user: UserModel,
) -> Any:
    if not request.app.state.config.ENABLE_FOLLOW_UP_GENERATION:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={'detail': 'Follow-up generation is disabled'},
        )

    models = _resolve_models(request)
    task_model_id = _resolve_task_model(request, form_data, models)

    log.debug(f'generating chat title using model {task_model_id} for user {user.email} ')

    if request.app.state.config.FOLLOW_UP_GENERATION_PROMPT_TEMPLATE != '':
        template = request.app.state.config.FOLLOW_UP_GENERATION_PROMPT_TEMPLATE
    else:
        template = DEFAULT_FOLLOW_UP_GENERATION_PROMPT_TEMPLATE
    content = follow_up_generation_template(template, form_data['messages'], user)

    payload = {
        'model': task_model_id,
        'messages': [{'role': 'user', 'content': content}],
        'stream': False,
        'metadata': _task_metadata(request, form_data, str(TASKS.FOLLOW_UP_GENERATION)),
    }

    return await _run_task_pipeline(request, user, models, payload)


async def generate_chat_tags(
    request: Request,
    form_data: dict[str, Any],
    user: UserModel,
) -> Any:
    if not request.app.state.config.ENABLE_TAGS_GENERATION:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={'detail': 'Tags generation is disabled'},
        )

    models = _resolve_models(request)
    task_model_id = _resolve_task_model(request, form_data, models)

    log.debug(f'generating chat tags using model {task_model_id} for user {user.email} ')

    if request.app.state.config.TAGS_GENERATION_PROMPT_TEMPLATE != '':
        template = request.app.state.config.TAGS_GENERATION_PROMPT_TEMPLATE
    else:
        template = DEFAULT_TAGS_GENERATION_PROMPT_TEMPLATE
    content = tags_generation_template(template, form_data['messages'], user)

    payload = {
        'model': task_model_id,
        'messages': [{'role': 'user', 'content': content}],
        'stream': False,
        'metadata': _task_metadata(request, form_data, str(TASKS.TAGS_GENERATION)),
    }

    payload = await process_pipeline_inlet_filter(request, payload, user, models)
    try:
        return await generate_chat_completion(request, form_data=payload, user=user)
    except Exception as e:
        log.error(f'Error generating chat completion: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'detail': 'An internal error has occurred.'},
        )


async def generate_image_prompt(
    request: Request,
    form_data: dict[str, Any],
    user: UserModel,
) -> Any:
    models = _resolve_models(request)
    task_model_id = _resolve_task_model(request, form_data, models)

    log.debug(f'generating image prompt using model {task_model_id} for user {user.email} ')

    if request.app.state.config.IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE != '':
        template = request.app.state.config.IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE
    else:
        template = DEFAULT_IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE
    content = image_prompt_generation_template(template, form_data['messages'], user)

    payload = {
        'model': task_model_id,
        'messages': [{'role': 'user', 'content': content}],
        'stream': False,
        'metadata': _task_metadata(request, form_data, str(TASKS.IMAGE_PROMPT_GENERATION)),
    }

    return await _run_task_pipeline(request, user, models, payload)


async def generate_queries(
    request: Request,
    form_data: dict[str, Any],
    user: UserModel,
) -> Any:
    type_ = form_data.get('type')
    if type_ == 'web_search' and not request.app.state.config.ENABLE_SEARCH_QUERY_GENERATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.FEATURE_DISABLED('Search query generation'),
        )
    if type_ == 'retrieval' and not request.app.state.config.ENABLE_RETRIEVAL_QUERY_GENERATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.FEATURE_DISABLED('Query generation'),
        )

    if getattr(request.state, 'cached_queries', None):
        log.info(f'Reusing cached queries: {request.state.cached_queries}')
        return request.state.cached_queries

    models = _resolve_models(request)
    task_model_id = _resolve_task_model(request, form_data, models)

    log.debug(f'generating {type_} queries using model {task_model_id} for user {user.email}')

    if (request.app.state.config.QUERY_GENERATION_PROMPT_TEMPLATE).strip() != '':
        template = request.app.state.config.QUERY_GENERATION_PROMPT_TEMPLATE
    else:
        template = DEFAULT_QUERY_GENERATION_PROMPT_TEMPLATE
    content = query_generation_template(template, form_data['messages'], user)

    payload = {
        'model': task_model_id,
        'messages': [{'role': 'user', 'content': content}],
        'stream': False,
        'metadata': _task_metadata(request, form_data, str(TASKS.QUERY_GENERATION)),
    }

    payload = await process_pipeline_inlet_filter(request, payload, user, models)
    try:
        return await generate_chat_completion(request, form_data=payload, user=user)
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={'detail': str(e)},
        )
