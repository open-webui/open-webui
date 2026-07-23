import inspect
import logging
import sys
from typing import Any

from fastapi import Request
from open_webui.env import ENABLE_PLUGINS, GLOBAL_LOG_LEVEL
from open_webui.models.functions import Functions
from open_webui.models.users import UserModel
from open_webui.socket.main import get_event_call, get_event_emitter
from open_webui.utils.middleware import process_tool_result
from open_webui.utils.models import check_model_access, get_all_models
from open_webui.utils.plugin import get_function_module_from_cache

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)


async def chat_action(request: Request, action_id: str, form_data: dict, user: Any):
    if not ENABLE_PLUGINS:
        raise Exception('Plugins are disabled by ENABLE_PLUGINS=false')

    if '.' in action_id:
        action_id, sub_action_id = action_id.split('.')
    else:
        sub_action_id = None

    action = await Functions.get_function_by_id(action_id)
    if not action:
        raise Exception(f'Action not found: {action_id}')

    if not request.app.state.MODELS:
        await get_all_models(request, user=user)

    if getattr(request.state, 'direct', False) and hasattr(request.state, 'model'):
        models = {
            request.state.model['id']: request.state.model,
        }
    else:
        models = request.app.state.MODELS

    data = form_data
    model_id = data['model']

    if model_id not in models:
        raise Exception('Model not found')
    model = models[model_id]

    # Availability gate — keep this route consistent with the actions a model
    # actually surfaces to the client. Executing admin-authored Function code is
    # intended; this only stops a disabled, unassigned, or access-restricted
    # action from being reached by calling the route with a raw action_id.
    if action.type != 'action' or not action.is_active:
        raise Exception(f'Action not available: {action_id}')

    # Direct connections carry a client-supplied model the caller already owns,
    # so scope the model-bound checks to server-resolved models.
    if not getattr(request.state, 'direct', False) and user.role != 'admin':
        await check_model_access(user, model)
        # model['actions'] entries are '<function_id>' or '<function_id>.<sub_id>';
        # the function id is always the prefix.
        surfaced_action_ids = {item.get('id', '').split('.', 1)[0] for item in model.get('actions', [])}
        if action_id not in surfaced_action_ids:
            raise Exception(f'Action not available: {action_id}')

    __event_emitter__ = await get_event_emitter(
        {
            'chat_id': data['chat_id'],
            'message_id': data['id'],
            'session_id': data['session_id'],
            'user_id': user.id,
        }
    )
    __event_call__ = await get_event_call(
        {
            'chat_id': data['chat_id'],
            'message_id': data['id'],
            'session_id': data['session_id'],
            'user_id': user.id,
        }
    )

    function_module, _, _ = await get_function_module_from_cache(request, action_id)

    if hasattr(function_module, 'valves') and hasattr(function_module, 'Valves'):
        valves = await Functions.get_function_valves_by_id(action_id)
        function_module.valves = function_module.Valves(**(valves if valves else {}))

    if hasattr(function_module, 'action'):
        try:
            action = function_module.action

            # Get the signature of the function
            sig = inspect.signature(action)
            params = {'body': data}

            # Extra parameters to be passed to the function
            extra_params = {
                '__model__': model,
                '__id__': sub_action_id if sub_action_id is not None else action_id,
                '__event_emitter__': __event_emitter__,
                '__event_call__': __event_call__,
                '__request__': request,
            }

            # Add extra params in contained in function signature
            for key, value in extra_params.items():
                if key in sig.parameters:
                    params[key] = value

            if '__user__' in sig.parameters:
                __user__ = user.model_dump() if isinstance(user, UserModel) else {}

                try:
                    if hasattr(function_module, 'UserValves'):
                        __user__['valves'] = function_module.UserValves(
                            **await Functions.get_user_valves_by_id_and_user_id(action_id, user.id)
                        )
                except Exception as e:
                    log.exception(f'Failed to get user values: {e}')

                params = {**params, '__user__': __user__}

            if inspect.iscoroutinefunction(action):
                data = await action(**params)
            else:
                data = action(**params)

            # Process action result for Rich UI embeds (HTMLResponse, tuple with headers)
            processed_result, _, action_embeds = await process_tool_result(
                request,
                action_id,
                data,
                'action',
            )

            if action_embeds:
                await __event_emitter__(
                    {
                        'type': 'embeds',
                        'data': {
                            'embeds': action_embeds,
                        },
                    }
                )
                # Replace data with the processed status dict so we don't
                # try to serialize the raw HTMLResponse / tuple back to the client
                data = processed_result

        except Exception as e:
            raise Exception(f'Error: {e}')

    return data
