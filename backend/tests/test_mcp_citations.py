from unittest.mock import AsyncMock

import pytest
from mcp import ClientSession, types
from open_webui.utils.mcp.client import MCP_CLIENT_CAPABILITIES_META_KEY, MCPClient, OpenWebUIClientSession
from open_webui.utils.middleware import (
    get_citation_source_from_tool_result,
    get_source_context,
    process_tool_result,
)


class FakeToolResult:
    isError = True

    def model_dump(self, mode='python'):
        return {
            'content': [{'type': 'text', 'text': 'Tool failed, but this content must reach the model.'}],
            'citations': [{'id': 'c1'}],
            'structuredContent': {'citations': [{'id': 'ignored'}]},
            'isError': True,
        }


@pytest.mark.asyncio
async def test_mcp_client_preserves_top_level_citations_and_error_content():
    client = MCPClient()
    client.session = AsyncMock()
    client.session.call_tool.return_value = FakeToolResult()

    result = await client.call_tool('search', {'query': 'test'})

    assert result == {
        'content': [{'type': 'text', 'text': 'Tool failed, but this content must reach the model.'}],
        'citations': [{'id': 'c1'}],
        'isError': True,
    }
    assert 'structuredContent' not in result


@pytest.mark.asyncio
async def test_session_advertises_render_support_on_every_request(monkeypatch):
    captured = {}

    async def fake_send_request(self, request, result_type, *args, **kwargs):
        captured['request'] = request
        return object()

    monkeypatch.setattr(ClientSession, 'send_request', fake_send_request)
    session = OpenWebUIClientSession.__new__(OpenWebUIClientSession)
    request = types.ClientRequest(types.ListToolsRequest(params=None))

    await session.send_request(request, types.ListToolsResult)

    metadata = request.root.params.meta.model_dump()
    assert metadata[MCP_CLIENT_CAPABILITIES_META_KEY] == {'citations': {'render': {}}}


@pytest.mark.asyncio
async def test_process_tool_result_keeps_markdown_and_ignores_structured_content():
    markdown = 'Judicial review began with [Marbury][c1].\n\n[c1]: https://example.com/marbury "Marbury v. Madison"'
    result, files, embeds, citations = await process_tool_result(
        None,
        'legal_search',
        {
            'content': [{'type': 'text', 'text': markdown}],
            'citations': [{'id': 'c1'}],
            'structuredContent': {'citations': [{'id': 'ignored'}]},
            'isError': False,
        },
        'mcp',
        metadata={},
    )

    assert result == markdown
    assert files == []
    assert embeds == []
    assert citations == [{'id': 'c1'}]


def test_mcp_citations_use_existing_source_shape_and_markdown_definitions():
    markdown = (
        'Judicial review began with [Marbury][c1].\n\n[c1]: https://example.com/marbury#page=12 "Marbury v. Madison"'
    )
    sources = get_citation_source_from_tool_result(
        'legal_search',
        {},
        markdown,
        tool_id='server/legal_search',
        tool_call_id='call_123',
        citations=[
            {
                'id': 'c1',
                'text': 'It is emphatically the province and duty...',
                'description': 'The foundational judicial-review decision.',
                'thumbnailUrl': 'https://example.com/thumb.png',
                'image': {'url': 'https://example.com/image.png'},
                'og:image': 'https://example.com/og.png',
                'author': {'type': 'Organization', 'name': 'Cornell LII'},
            }
        ],
    )

    assert sources == [
        {
            'source': {
                'id': 'c1',
                'name': 'Marbury v. Madison',
                'display_name': 'Marbury v. Madison',
                'type': 'mcp',
                'url': 'https://example.com/marbury#page=12',
            },
            'document': ['It is emphatically the province and duty...'],
            'metadata': [
                {
                    'source': 'mcp:call_123:c1',
                    'name': 'Marbury v. Madison',
                    'display_name': 'Marbury v. Madison',
                    'url': 'https://example.com/marbury#page=12',
                    'citation_id': 'c1',
                    'description': 'The foundational judicial-review decision.',
                    'thumbnail_url': 'https://example.com/thumb.png',
                    'image_url': 'https://example.com/image.png',
                    'og_image_url': 'https://example.com/og.png',
                    'author': ['Cornell LII'],
                    'provenance': 'mcp',
                }
            ],
        }
    ]
    assert (
        get_source_context(sources, include_content=False)
        == '<source id="1" name="Marbury v. Madison" resource-type="mcp" resource-id="c1"></source>\n'
    )


@pytest.mark.parametrize(
    ('publisher', 'expected_publishers', 'expected_display_name'),
    [
        ({'name': 'OpenAI'}, ['OpenAI'], 'OpenAI'),
        ('OpenAI', ['OpenAI'], 'OpenAI'),
        ([{'name': 'OpenAI'}, 'Research Lab'], ['OpenAI', 'Research Lab'], 'OpenAI'),
        ({'name': '   '}, [], 'Original article title'),
        ({'unexpected': 'OpenAI'}, [], 'Original article title'),
        (['', None, {'name': ''}], [], 'Original article title'),
    ],
)
def test_mcp_publisher_sets_chip_label_without_replacing_citation_name(
    publisher,
    expected_publishers,
    expected_display_name,
):
    [source] = get_citation_source_from_tool_result(
        'search',
        {},
        '[Original article title](https://example.com/article)',
        tool_call_id='call_publisher',
        citations=[
            {
                'id': 'c1',
                'name': 'Original article title',
                'url': 'https://example.com/article',
                'publisher': publisher,
            }
        ],
    )

    assert source['source']['name'] == 'Original article title'
    assert source['source']['display_name'] == expected_display_name
    assert source['metadata'][0]['name'] == 'Original article title'
    assert source['metadata'][0]['display_name'] == expected_display_name
    if expected_publishers:
        assert source['metadata'][0]['publisher'] == expected_publishers
    else:
        assert 'publisher' not in source['metadata'][0]


def test_same_url_granular_citations_remain_distinct():
    sources = get_citation_source_from_tool_result(
        'search',
        {},
        '[First][c1] and [second][c2].',
        tool_call_id='call_123',
        citations=[
            {'id': 'c1', 'url': 'https://example.com/report', 'text': 'First quote'},
            {'id': 'c2', 'url': 'https://example.com/report', 'text': 'Second quote'},
        ],
    )

    assert [source['metadata'][0]['source'] for source in sources] == [
        'mcp:call_123:c1',
        'mcp:call_123:c2',
    ]


def test_inline_link_matches_citation_name():
    sources = get_citation_source_from_tool_result(
        'search',
        {},
        'See [Marbury v. Madison](https://example.com/marbury).',
        tool_call_id='call_inline',
        citations=[{'name': 'Marbury v. Madison', 'description': 'A decision.'}],
    )

    assert sources[0]['source']['url'] == 'https://example.com/marbury'
    assert sources[0]['metadata'][0]['description'] == 'A decision.'
