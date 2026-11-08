"""Models exposed by the selected Open Terminal environment."""

from urllib.parse import quote, urlencode

from open_webui.utils.terminals import get_terminal_json


def model_controls(model):
    controls = {}
    for key, label, values, value_key, label_key, default_key in (
        (
            'reasoning_effort',
            'Reasoning effort',
            'supportedReasoningEfforts',
            'reasoningEffort',
            'reasoningEffort',
            'defaultReasoningEffort',
        ),
        ('service_tier', 'Service tier', 'serviceTiers', 'id', 'name', 'defaultServiceTier'),
    ):
        options = {
            option[value_key]: {
                'label': option.get(label_key) or option[value_key],
                'params': {key: option[value_key]},
            }
            for option in model.get(values, [])
        }
        if options:
            controls[key] = {'label': label, 'options': options}
            if model.get(default_key) in options:
                controls[key]['default'] = model[default_key]
    return controls


async def get_models(request, user, terminal_id, chat_id=None, *, provider=None, cwd=None):
    if not terminal_id:
        return []
    metadata = {'terminal_id': terminal_id, 'chat_id': chat_id}
    if not cwd:
        directory = await get_terminal_json(request, user, metadata, '/files/cwd')
        cwd = (directory or {}).get('cwd')
    params = {'provider': provider} if provider else {}
    if cwd:
        params['cwd'] = cwd
    path = '/agents' + ('?' + urlencode(params) if params else '')
    catalog = await get_terminal_json(request, user, metadata, path)
    if not catalog or catalog.get('protocol_version') != 1:
        return []
    models = [
        {
            'id': f'agent:{quote(terminal_id, safe="")}:{agent["id"]}:{quote(model["id"], safe="")}',
            'name': f'{agent["id"]}/{model["id"]}',
            'owned_by': 'agent',
            'object': 'model',
            'agent': {'terminal_id': terminal_id, 'provider': agent['id'], 'model': model['id']},
            'info': {
                'params': {'model_controls': model_controls(model)},
                'meta': {
                    'capabilities': {
                        'vision': True,
                        'file_upload': True,
                        'web_search': False,
                        'image_generation': False,
                        'code_interpreter': False,
                        'builtin_tools': False,
                    }
                },
            },
        }
        for agent in catalog.get('agents', [])
        if agent.get('available')
        for model in agent.get('models', [])
    ]
    return list({model['id']: model for model in models}.values())
