import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from open_webui.utils.mcp.client import MCPClient, collect_mcp_tools


class FakeTool:
    def __init__(self, name):
        self.name = name
        self.description = f'desc {name}'
        self.inputSchema = {'type': 'object', 'properties': {}}


class CollectMcpToolsTest(unittest.IsolatedAsyncioTestCase):
    async def test_follows_next_cursor_across_pages(self):
        session = SimpleNamespace()
        pages = {
            None: SimpleNamespace(tools=[FakeTool('a'), FakeTool('b')], nextCursor='page-2'),
            'page-2': SimpleNamespace(tools=[FakeTool('c')], nextCursor='page-3'),
            'page-3': SimpleNamespace(tools=[FakeTool('d')], nextCursor=None),
        }

        async def list_tools(cursor=None):
            return pages[cursor]

        session.list_tools = list_tools
        tools = await collect_mcp_tools(session)
        self.assertEqual([tool.name for tool in tools], ['a', 'b', 'c', 'd'])

    async def test_single_page_without_cursor(self):
        session = SimpleNamespace()
        session.list_tools = AsyncMock(
            return_value=SimpleNamespace(tools=[FakeTool('only')], nextCursor=None)
        )
        tools = await collect_mcp_tools(session)
        self.assertEqual([tool.name for tool in tools], ['only'])
        session.list_tools.assert_awaited_once_with(cursor=None)

    async def test_stops_on_repeated_cursor(self):
        session = SimpleNamespace()

        async def list_tools(cursor=None):
            return SimpleNamespace(tools=[FakeTool('loop')], nextCursor='same')

        session.list_tools = list_tools
        tools = await collect_mcp_tools(session, max_pages=10)
        self.assertEqual(len(tools), 2)

    async def test_list_tool_specs_includes_later_pages(self):
        client = MCPClient()
        pages = {
            None: SimpleNamespace(tools=[FakeTool('one')], nextCursor='next'),
            'next': SimpleNamespace(tools=[FakeTool('two')], nextCursor=None),
        }

        async def list_tools(cursor=None):
            return pages[cursor]

        client.session = SimpleNamespace(list_tools=list_tools)
        specs = await client.list_tool_specs()
        self.assertEqual([spec['name'] for spec in specs], ['one', 'two'])


if __name__ == '__main__':
    unittest.main()
