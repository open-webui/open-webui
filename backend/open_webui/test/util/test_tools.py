import pytest
from unittest.mock import patch

from open_webui.utils.tools import convert_openapi_to_tool_payload, get_tool_servers_data


def test_convert_openapi_to_tool_payload_handles_circular_request_refs():
    spec = {
        'openapi': '3.1.0',
        'paths': {
            '/conditions': {
                'post': {
                    'operationId': 'create_condition',
                    'requestBody': {
                        'content': {
                            'application/json': {
                                'schema': {'$ref': '#/components/schemas/Condition'}
                            }
                        }
                    },
                }
            }
        },
        'components': {
            'schemas': {
                'Condition': {
                    'type': 'object',
                    'properties': {
                        'siblings': {
                            'type': 'array',
                            'items': {'$ref': '#/components/schemas/Condition'},
                        }
                    },
                }
            }
        },
    }

    payload = convert_openapi_to_tool_payload(spec)

    assert len(payload) == 1
    siblings = payload[0]['parameters']['properties']['siblings']
    assert siblings['type'] == 'array'
    assert siblings['items'] == {'type': 'object'}


@pytest.mark.asyncio
async def test_get_tool_servers_data_skips_server_with_spec_conversion_error():
    servers = [
        {
            'type': 'openapi',
            'url': 'https://bad.example',
            'spec_type': 'json',
            'spec': '{"openapi":"3.1.0","paths":{}}',
            'info': {'id': 'bad'},
            'config': {'enable': True},
        },
        {
            'type': 'openapi',
            'url': 'https://good.example',
            'spec_type': 'json',
            'spec': '{"openapi":"3.1.0","paths":{}}',
            'info': {'id': 'good'},
            'config': {'enable': True},
        },
    ]

    with patch(
        'open_webui.utils.tools.convert_openapi_to_tool_payload',
        side_effect=[RuntimeError('boom'), []],
    ):
        results = await get_tool_servers_data(servers)

    assert [server['id'] for server in results] == ['good']
    assert results[0]['specs'] == []
