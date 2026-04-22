import inspect
import logging

from open_webui.utils.plugin import (
    load_function_module_by_id,
    get_function_module_from_cache,
)
from open_webui.models.functions import Functions

log = logging.getLogger(__name__)


async def get_function_module(request, function_id, load_from_db=True):
    """
    Get the function module by its ID.
    """
    function_module, _, _ = await get_function_module_from_cache(request, function_id, load_from_db)
    return function_module


async def get_sorted_filter_ids(request, model: dict, enabled_filter_ids: list = None):
    async def get_priority(function_id):
        try:
            function_module = await get_function_module(request, function_id)
            if function_module and hasattr(function_module, 'Valves'):
                valves_db = await Functions.get_function_valves_by_id(function_id)
                valves = function_module.Valves(**(valves_db if valves_db else {}))
                return getattr(valves, 'priority', 0)
        except Exception:
            pass
        return 0

    filter_ids = [function.id for function in await Functions.get_global_filter_functions()]
    if 'info' in model and 'meta' in model['info']:
        filter_ids.extend(model['info']['meta'].get('filterIds', []))
        filter_ids = list(set(filter_ids))
    active_filter_ids = {function.id for function in await Functions.get_functions_by_type('filter', active_only=True)}

    async def get_active_status(filter_id):
        function_module = await get_function_module(request, filter_id)

        if getattr(function_module, 'toggle', None):
            return filter_id in (enabled_filter_ids or set())

        return True

    # Pre-compute active status for each filter (async functions can't be used in set comprehensions)
    resolved_active = {}
    for filter_id in active_filter_ids:
        resolved_active[filter_id] = await get_active_status(filter_id)
    active_filter_ids = {fid for fid, is_active in resolved_active.items() if is_active}

    filter_ids = [fid for fid in filter_ids if fid in active_filter_ids]

    # Pre-compute priorities (async functions can't be used in sort keys)
    priorities = {}
    for fid in filter_ids:
        priorities[fid] = await get_priority(fid)
    filter_ids.sort(key=lambda fid: (priorities.get(fid, 0), fid))

    return filter_ids


# Grant these filters the discernment to pass what serves
# and refuse what harms, for every soul in the house.
async def process_filter_functions(request, filter_functions, filter_type, form_data, extra_params):
    skip_files = None

    for function in filter_functions:
        filter = function
        filter_id = function.id
        if not filter:
            continue

        function_module = await get_function_module(request, filter_id, load_from_db=(filter_type != 'stream'))
        # Prepare handler function
        handler = getattr(function_module, filter_type, None)
        if not handler:
            continue

        # Check if the function has a file_handler variable
        if filter_type == 'inlet' and hasattr(function_module, 'file_handler'):
            skip_files = function_module.file_handler

        # Apply valves to the function
        if hasattr(function_module, 'valves') and hasattr(function_module, 'Valves'):
            valves = await Functions.get_function_valves_by_id(filter_id)
            function_module.valves = function_module.Valves(**(valves if valves else {}))

        try:
            # Prepare parameters
            sig = inspect.signature(handler)

            params = {'body': form_data}
            if filter_type == 'stream':
                params = {'event': form_data}

            params = params | {
                k: v
                for k, v in {
                    **extra_params,
                    '__id__': filter_id,
                }.items()
                if k in sig.parameters
            }

            # Handle user parameters
            if '__user__' in sig.parameters:
                if hasattr(function_module, 'UserValves'):
                    try:
                        params['__user__']['valves'] = function_module.UserValves(
                            **await Functions.get_user_valves_by_id_and_user_id(filter_id, params['__user__']['id'])
                        )
                    except Exception as e:
                        log.exception(f'Failed to get user values: {e}')

            # Execute handler
            if inspect.iscoroutinefunction(handler):
                form_data = await handler(**params)
            else:
                form_data = handler(**params)

        except Exception as e:
            log.debug(f'Error in {filter_type} handler {filter_id}: {e}')
            raise e

    # Handle file cleanup for inlet
    if skip_files:
        if 'files' in form_data.get('metadata', {}):
            del form_data['metadata']['files']
        if 'files' in form_data:
            del form_data['files']

    return form_data, {}
