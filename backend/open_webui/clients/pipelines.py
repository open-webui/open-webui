import logging
from typing import Any

import aiohttp
from fastapi import HTTPException, Request

from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL
from open_webui.models.users import UserModel

log = logging.getLogger(__name__)


def get_sorted_filters(model_id: str, models: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    filters = [
        model
        for model in models.values()
        if 'pipeline' in model
        and 'type' in model['pipeline']
        and model['pipeline']['type'] == 'filter'
        and (
            model['pipeline']['pipelines'] == ['*']
            or any(model_id == target_model_id for target_model_id in model['pipeline']['pipelines'])
        )
    ]
    return sorted(filters, key=lambda x: x['pipeline']['priority'])


def _raise_from_response(
    response: aiohttp.ClientResponse | None,
    error: aiohttp.ClientResponseError,
    res: dict[str, Any],
) -> None:
    if 'detail' in res:
        raise HTTPException(
            status_code=response.status if response is not None else 500,
            detail=res['detail'],
        )
    raise HTTPException(
        status_code=response.status if response is not None else 500,
        detail=error.message,
    )


async def _post_filter(
    session: aiohttp.ClientSession,
    url: str,
    key: str,
    filter_id: str,
    stage: str,
    request_data: dict[str, Any],
) -> dict[str, Any] | None:
    response: aiohttp.ClientResponse | None = None
    try:
        async with session.post(
            f'{url}/{filter_id}/filter/{stage}',
            headers={'Authorization': f'Bearer {key}'},
            json=request_data,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        ) as response:
            response.raise_for_status()
            return await response.json()
    except aiohttp.ClientResponseError as e:
        res: dict[str, Any] = {}
        try:
            if response is not None and 'application/json' in response.content_type:
                res = await response.json()
        except Exception:
            pass
        _raise_from_response(response, e, res)
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f'Connection error: {e}')
    return None


async def _run_filter_stage(
    request: Request,
    payload: dict[str, Any],
    user: UserModel,
    models: dict[str, dict[str, Any]],
    stage: str,
) -> dict[str, Any]:
    user_payload = {'id': user.id, 'email': user.email, 'name': user.name, 'role': user.role}
    model_id = payload['model']
    sorted_filters = get_sorted_filters(model_id, models)
    model = models[model_id]

    if 'pipeline' in model:
        if stage == 'inlet':
            sorted_filters.append(model)
        else:
            sorted_filters = [model] + sorted_filters

    async with aiohttp.ClientSession(trust_env=True) as session:
        for filter_ in sorted_filters:
            try:
                url_idx = int(filter_.get('urlIdx'))
            except Exception:
                continue

            url = request.app.state.config.OPENAI_API_BASE_URLS[url_idx]
            key = request.app.state.config.OPENAI_API_KEYS[url_idx]
            if not key:
                continue

            updated = await _post_filter(
                session,
                url,
                key,
                filter_id=filter_['id'],
                stage=stage,
                request_data={'user': user_payload, 'body': payload},
            )
            if updated is not None:
                payload = updated

    return payload


async def process_pipeline_inlet_filter(
    request: Request,
    payload: dict[str, Any],
    user: UserModel,
    models: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return await _run_filter_stage(request, payload, user, models, stage='inlet')


async def process_pipeline_outlet_filter(
    request: Request,
    payload: dict[str, Any],
    user: UserModel,
    models: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return await _run_filter_stage(request, payload, user, models, stage='outlet')
