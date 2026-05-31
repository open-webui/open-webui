from open_webui.utils.response import (
    get_completion_message_content,
    parse_generated_queries,
)
from starlette.responses import JSONResponse


def test_query_response_shape_boundary_falls_back_for_json_response():
    query_response = JSONResponse({'detail': 'upstream response shape'})

    response = get_completion_message_content(query_response)

    assert response is None
    assert parse_generated_queries(response, 'find source context') == ['find source context']


def test_query_response_shape_boundary_accepts_openai_style_choices():
    query_response = {
        'choices': [
            {
                'message': {
                    'content': '{"queries": ["source context result"]}',
                },
            }
        ],
    }

    response = get_completion_message_content(query_response)

    assert response == '{"queries": ["source context result"]}'
    assert parse_generated_queries(response, 'find source context') == ['source context result']
