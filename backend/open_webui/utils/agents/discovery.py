"""Models exposed by the selected Open Terminal environment."""

from urllib.parse import quote, urlencode

from open_webui.utils.terminals import get_terminal_json


async def get_models(request, user, terminal_id, chat_id=None):
    if not terminal_id:
        return []
    metadata = {'terminal_id': terminal_id, 'chat_id': chat_id}
    cwd = await get_terminal_json(request, user, metadata, '/files/cwd')
    path = '/agents'
    if cwd and cwd.get('cwd'):
        path += '?' + urlencode({'cwd': cwd['cwd']})
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
                'meta': {
                    'capabilities': {
                        'vision': True,
                        'file_upload': True,
                        'web_search': False,
                        'image_generation': False,
                        'code_interpreter': False,
                        'builtin_tools': False,
                    }
                }
            },
        }
        for agent in catalog.get('agents', [])
        if agent.get('available')
        for model in agent.get('models', [])
    ]
    return list({model['id']: model for model in models}.values())
