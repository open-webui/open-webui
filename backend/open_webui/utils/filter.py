import inspect
import logging

from open_webui.env import ENABLE_PLUGINS
from open_webui.models.functions import Functions
from open_webui.utils.plugin import get_function_module_from_cache

log = logging.getLogger(__name__)


async def get_function_module(request, function_id, load_from_db=True, function=None):
    """
    Get the function module by its ID. A prefetched row can be passed via
    ``function`` to skip the per-id fetch inside the module cache.
    """
    function_module, _, _ = await get_function_module_from_cache(
        request, function_id, function=function, load_from_db=load_from_db
    )
    return function_module


async def get_sorted_filter_ids(request, model: dict, enabled_filter_ids: list = None):
    if not ENABLE_PLUGINS:
        return []

    # The identical computation runs for the inlet, stream and outlet stages
    # of one request; cache the result on the request.
    request_state = getattr(request, 'state', None)
    cache_key = (
        model.get('id') if isinstance(model, dict) else str(model),
        tuple(enabled_filter_ids) if enabled_filter_ids else (),
    )
    cache = getattr(request_state, 'sorted_filter_ids_cache', None)
    if cache is not None and cache_key in cache:
        return list(cache[cache_key])

    active_filters = await Functions.get_active_filter_ids()
    filter_ids = [fid for fid, is_global in active_filters if is_global]
    if 'info' in model and 'meta' in model['info']:
        filter_ids.extend(model['info']['meta'].get('filterIds', []))
        filter_ids = list(set(filter_ids))
    active_filter_ids = {fid for fid, _ in active_filters}

    # Only ids that are both requested and active can survive; anything else
    # would previously get its module loaded and verified for nothing.
    filter_ids = [fid for fid in filter_ids if fid in active_filter_ids]
    functions_by_id = {function.id: function for function in await Functions.get_functions_by_ids(filter_ids)}

    async def get_active_status(filter_id):
        function_module = await get_function_module(request, filter_id, function=functions_by_id.get(filter_id))

        if getattr(function_module, 'toggle', None):
            return filter_id in (enabled_filter_ids or set())

        return True

    # Pre-compute active status for each filter (async functions can't be used in comprehensions)
    resolved = []
    for filter_id in filter_ids:
        if await get_active_status(filter_id):
            resolved.append(filter_id)
    filter_ids = resolved

    valves_by_id = await Functions.get_function_valves_by_ids(filter_ids)

    async def get_priority(function_id):
        try:
            function_module = await get_function_module(request, function_id, function=functions_by_id.get(function_id))
            if function_module and hasattr(function_module, 'Valves'):
                valves_db = valves_by_id.get(function_id)
                valves = function_module.Valves(**(valves_db if valves_db else {}))
                return getattr(valves, 'priority', 0)
        except Exception:
            pass
        return 0

    # Pre-compute priorities (async functions can't be used in sort keys)
    priorities = {}
    for fid in filter_ids:
        priorities[fid] = await get_priority(fid)
    filter_ids.sort(key=lambda fid: (priorities.get(fid, 0), fid))

    if request_state is not None:
        if cache is None:
            cache = {}
            request_state.sorted_filter_ids_cache = cache
        cache[cache_key] = list(filter_ids)

    return filter_ids


# Grant these filters the discernment to pass what serves
# and refuse what harms, for every soul in the house.
async def process_filter_functions(request, filter_functions, filter_type, form_data, extra_params):
    if not ENABLE_PLUGINS:
        return form_data, {}

    skip_files = None
    valves_by_id = None
    filter_ids = [function.id for function in filter_functions if function]

    for function in filter_functions:
        if not function:
            continue
        filter_id = function.id

        # The caller batch-fetched these rows; passing one skips a per-filter
        # re-fetch inside the module cache while keeping the freshness check.
        function_module = await get_function_module(
            request, filter_id, load_from_db=(filter_type != 'stream'), function=function
        )
        # Prepare handler function
        handler = getattr(function_module, filter_type, None)
        if not handler:
            continue

        # Check if the function has a file_handler variable
        if filter_type == 'inlet' and hasattr(function_module, 'file_handler'):
            skip_files = function_module.file_handler

        # Apply valves to the function
        if hasattr(function_module, 'valves') and hasattr(function_module, 'Valves'):
            if valves_by_id is None:
                valves_by_id = await Functions.get_function_valves_by_ids(filter_ids)
            valves = valves_by_id.get(filter_id)
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
