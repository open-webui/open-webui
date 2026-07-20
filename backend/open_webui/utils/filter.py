import inspect
import logging
import weakref

from open_webui.env import ENABLE_PLUGINS
from open_webui.models.functions import Functions
from open_webui.utils.plugin import (
    get_function_module_from_cache,
    load_function_module_by_id,
)

log = logging.getLogger(__name__)

# Handler introspection cache: inspect.signature is expensive and stream
# handlers are introspected once per streamed chunk. Keyed weakly on the
# underlying function object so reloaded plugins get fresh entries.
_HANDLER_SPECS: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


def _get_handler_spec(handler) -> tuple[frozenset, bool]:
    """(parameter names, is-coroutine) for a filter handler."""
    key = getattr(handler, '__func__', handler)
    try:
        spec = _HANDLER_SPECS.get(key)
    except TypeError:
        key, spec = None, None
    if spec is None:
        spec = (
            frozenset(inspect.signature(handler).parameters),
            inspect.iscoroutinefunction(handler),
        )
        if key is not None:
            try:
                _HANDLER_SPECS[key] = spec
            except TypeError:
                pass
    return spec


async def get_function_module(request, function_id, load_from_db=True):
    """
    Get the function module by its ID.
    """
    function_module, _, _ = await get_function_module_from_cache(request, function_id, load_from_db=load_from_db)
    return function_module


async def get_sorted_filter_ids(request, model: dict, enabled_filter_ids: list = None):
    if not ENABLE_PLUGINS:
        return []

    # One narrow query serves both the global and the active-filter sets
    # (global filters are by definition a subset of active filters).
    active_filters = await Functions.get_active_filter_ids()

    filter_ids = [fid for fid, is_global in active_filters if is_global]
    if 'info' in model and 'meta' in model['info']:
        filter_ids.extend(model['info']['meta'].get('filterIds', []))
        filter_ids = list(set(filter_ids))
    active_filter_ids = {fid for fid, _ in active_filters}

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

    # Batch-fetch valves in one query instead of one query per filter.
    valves_by_id = await Functions.get_function_valves_by_ids(filter_ids)

    async def get_priority(function_id):
        try:
            function_module = await get_function_module(request, function_id)
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

    return filter_ids


# Grant these filters the discernment to pass what serves
# and refuse what harms, for every soul in the house.
async def process_filter_functions(request, filter_functions, filter_type, form_data, extra_params):
    if not ENABLE_PLUGINS:
        return form_data, {}

    skip_files = None

    # Lazily batch-fetched on first use: one query for all filters instead of
    # one per filter (per streamed chunk for stream-type calls), and none at
    # all when no filter defines valves.
    valves_by_id = None

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
            if valves_by_id is None:
                valves_by_id = await Functions.get_function_valves_by_ids([f.id for f in filter_functions if f])
            valves = valves_by_id.get(filter_id)
            function_module.valves = function_module.Valves(**(valves if valves else {}))

        try:
            # Prepare parameters
            sig_params, is_coroutine = _get_handler_spec(handler)

            params = {'body': form_data}
            if filter_type == 'stream':
                params = {'event': form_data}

            params = params | {
                k: v
                for k, v in {
                    **extra_params,
                    '__id__': filter_id,
                }.items()
                if k in sig_params
            }

            # Handle user parameters
            if '__user__' in sig_params:
                if hasattr(function_module, 'UserValves'):
                    try:
                        params['__user__']['valves'] = function_module.UserValves(
                            **await Functions.get_user_valves_by_id_and_user_id(filter_id, params['__user__']['id'])
                        )
                    except Exception as e:
                        log.exception(f'Failed to get user values: {e}')

            # Execute handler
            if is_coroutine:
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
