import inspect
import logging

from open_webui.env import ENABLE_PLUGINS
from open_webui.models.functions import Functions
from open_webui.utils.plugin import get_function_module_from_cache

log = logging.getLogger(__name__)


class FilterContext:
    def __init__(self):
        self.valves_by_id = None
        self.function_valves = {}
        self.user_valves = {}

    async def get_function_valves(self, filter_ids, filter_id, Valves):
        if filter_id not in self.function_valves:
            if self.valves_by_id is None:
                self.valves_by_id = await Functions.get_function_valves_by_ids(filter_ids)
            valves = self.valves_by_id.get(filter_id)
            self.function_valves[filter_id] = Valves(**(valves if valves else {}))
        return self.function_valves[filter_id]

    async def get_user_valves(self, filter_id, user_id, UserValves):
        user_valves_key = (filter_id, user_id)
        if user_valves_key not in self.user_valves:
            self.user_valves[user_valves_key] = await get_user_valves(filter_id, user_id, UserValves)
        return self.user_valves[user_valves_key]


async def get_user_valves(filter_id, user_id, UserValves):
    user_valves_data = await Functions.get_user_valves_by_id_and_user_id(filter_id, user_id)
    return UserValves(**(user_valves_data if user_valves_data else {}))


async def get_function_module(request, function_id, load_from_db=True, function=None):
    """
    Get the function module by its ID.
    """
    function_module, _, _ = await get_function_module_from_cache(
        request, function_id, function=function, load_from_db=load_from_db
    )
    return function_module


def get_model_filter_ids(model, active_filters):
    filter_ids = [fid for fid, is_global in active_filters if is_global]
    if isinstance(model, dict) and 'info' in model and 'meta' in model['info']:
        filter_ids.extend(model['info']['meta'].get('filterIds', []))
        filter_ids = list(set(filter_ids))
    active_filter_ids = {fid for fid, _ in active_filters}
    return [fid for fid in filter_ids if fid in active_filter_ids]


async def resolve_filter_pipeline(request, model: dict, enabled_filter_ids: list = None):
    if not ENABLE_PLUGINS:
        return [], []

    active_filters = await Functions.get_active_filter_ids()
    filter_ids = get_model_filter_ids(model, active_filters)
    functions_by_id = {function.id: function for function in await Functions.get_functions_by_ids(filter_ids)}

    async def get_active_status(filter_id):
        function_module = await get_function_module(request, filter_id, function=functions_by_id.get(filter_id))

        if getattr(function_module, 'toggle', None):
            return filter_id in (enabled_filter_ids or set())

        return True

    # Pre-compute active status for each filter (async functions can't be used in set comprehensions)
    filter_ids = [fid for fid in filter_ids if await get_active_status(fid)]
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

    filter_functions = [functions_by_id[fid] for fid in filter_ids if fid in functions_by_id]
    return filter_ids, filter_functions


async def get_sorted_filter_ids(request, model: dict, enabled_filter_ids: list = None):
    filter_ids, _ = await resolve_filter_pipeline(request, model, enabled_filter_ids)

    return filter_ids


async def get_filter_functions(request, model: dict, enabled_filter_ids: list = None):
    _, filter_functions = await resolve_filter_pipeline(request, model, enabled_filter_ids)
    return filter_functions


async def apply_filter_valves(function_module, filter_context, valves_by_id, filter_ids, filter_id):
    if not (hasattr(function_module, 'valves') and hasattr(function_module, 'Valves')):
        return valves_by_id

    if filter_context is not None:
        function_module.valves = await filter_context.get_function_valves(filter_ids, filter_id, function_module.Valves)
        return valves_by_id

    if valves_by_id is None:
        valves_by_id = await Functions.get_function_valves_by_ids(filter_ids)
    valves = valves_by_id.get(filter_id)
    function_module.valves = function_module.Valves(**(valves if valves else {}))
    return valves_by_id


def get_filter_params(sig, filter_id, filter_type, form_data, extra_params):
    params = {'event': form_data} if filter_type == 'stream' else {'body': form_data}
    return params | {
        k: v
        for k, v in {
            **extra_params,
            '__id__': filter_id,
        }.items()
        if k in sig.parameters
    }


async def apply_user_valves(function_module, filter_context, filter_id, params):
    if '__user__' not in params or not hasattr(function_module, 'UserValves'):
        return

    user_id = params['__user__'].get('id')
    if filter_context is not None:
        user_valves = await filter_context.get_user_valves(filter_id, user_id, function_module.UserValves)
    else:
        user_valves = await get_user_valves(filter_id, user_id, function_module.UserValves)
    params['__user__']['valves'] = user_valves


async def run_filter_handler(handler, params):
    if inspect.iscoroutinefunction(handler):
        return await handler(**params)
    return handler(**params)


async def process_filter_function(
    request,
    function,
    filter_type,
    form_data,
    extra_params,
    filter_context,
    valves_by_id,
    filter_ids,
):
    filter_id = function.id

    function_module = await get_function_module(
        request, filter_id, load_from_db=(filter_type != 'stream'), function=function
    )
    handler = getattr(function_module, filter_type, None)
    if not handler:
        return form_data, valves_by_id, None

    skip_files = (
        function_module.file_handler if filter_type == 'inlet' and hasattr(function_module, 'file_handler') else None
    )
    valves_by_id = await apply_filter_valves(function_module, filter_context, valves_by_id, filter_ids, filter_id)

    try:
        sig = inspect.signature(handler)
        params = get_filter_params(sig, filter_id, filter_type, form_data, extra_params)

        if '__user__' in sig.parameters:
            try:
                await apply_user_valves(function_module, filter_context, filter_id, params)
            except Exception as e:
                log.exception(f'Failed to get user values: {e}')

        form_data = await run_filter_handler(handler, params)
    except Exception as e:
        log.debug(f'Error in {filter_type} handler {filter_id}: {e}')
        raise e

    return form_data, valves_by_id, skip_files


# Grant these filters the discernment to pass what serves
# and refuse what harms, for every soul in the house.
async def process_filter_functions(
    request,
    filter_context,
    filter_functions,
    filter_type,
    form_data,
    extra_params,
):
    if not ENABLE_PLUGINS:
        return form_data, {}

    skip_files = None
    valves_by_id = None
    filter_ids = [function.id for function in filter_functions if function]

    for function in filter_functions:
        if not function:
            continue

        form_data, valves_by_id, file_handler = await process_filter_function(
            request,
            function,
            filter_type,
            form_data,
            extra_params,
            filter_context,
            valves_by_id,
            filter_ids,
        )
        skip_files = skip_files or file_handler

    # Handle file cleanup for inlet
    if skip_files:
        if 'files' in form_data.get('metadata', {}):
            del form_data['metadata']['files']
        if 'files' in form_data:
            del form_data['files']

    return form_data, {}
