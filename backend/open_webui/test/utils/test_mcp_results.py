from open_webui.utils.mcp.results import extract_mcp_text_content


def test_extract_mcp_resource_decodes_json_text():
    has_content, content = extract_mcp_text_content(
        {
            'type': 'resource',
            'resource': {
                'uri': 'openproject://statuses',
                'mimeType': 'application/json',
                'text': '{"statuses": [{"id": 1, "name": "New"}]}',
            },
        }
    )

    assert has_content is True
    assert content == {'statuses': [{'id': 1, 'name': 'New'}]}


def test_extract_mcp_resource_preserves_plain_text():
    has_content, content = extract_mcp_text_content(
        {
            'type': 'resource',
            'resource': {
                'uri': 'notes://summary',
                'mimeType': 'text/plain',
                'text': 'plain resource text',
            },
        }
    )

    assert has_content is True
    assert content == 'plain resource text'


def test_extract_mcp_text_content_keeps_existing_text_behavior():
    has_content, content = extract_mcp_text_content({'type': 'text', 'text': '{"count": 16}'})

    assert has_content is True
    assert content == {'count': 16}


def test_extract_mcp_resource_without_text_is_ignored():
    has_content, content = extract_mcp_text_content(
        {
            'type': 'resource',
            'resource': {
                'uri': 'binary://report',
                'mimeType': 'application/octet-stream',
            },
        }
    )

    assert has_content is False
    assert content is None
