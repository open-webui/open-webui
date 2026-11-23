"""Dependency-light protocol tests; run: python3 -m unittest discover -s test -p test_personal_mcp_context.py."""

import asyncio
import ast
from contextlib import asynccontextmanager
import base64
import hashlib
import hmac
import importlib.util
import json
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

PATH = Path(__file__).resolve().parents[1] / 'backend/open_webui/utils/mcp/connector_context.py'


class ContextTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.claim = AsyncMock(return_value='inbound-user-message')
        self.modules = {
            'fastapi': types.SimpleNamespace(HTTPException=type('HTTPException', (Exception,), {})),
            'open_webui.models.chats': types.SimpleNamespace(
                Chats=types.SimpleNamespace(claim_personal_connector_chat=self.claim)
            ),
            'open_webui.utils.chat_id': types.SimpleNamespace(
                is_saved_chat_id=lambda value: (
                    bool(value) and not value.startswith(('temporary:', 'local:', 'channel:'))
                )
            ),
        }
        self.stub = patch.dict(sys.modules, self.modules)
        self.stub.start()
        spec = importlib.util.spec_from_file_location('connector_under_test', PATH)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.env = patch.dict(
            os.environ,
            {'ARTHA_CONNECTOR_MCP_URL': 'https://artha.example/mcp', 'PERSONAL_MCP_CHEWIE_CONTEXT_KEY': 'x' * 32},
        )
        self.env.start()
        self.user = types.SimpleNamespace(id='owner', email='User@Example.com')
        self.metadata = {'chat_id': 'saved', 'message_id': 'message'}

    async def asyncTearDown(self):
        self.env.stop()
        self.stub.stop()

    async def headers(self, url='https://artha.example/mcp', tool_name='search_connected_tools', **metadata):
        request = types.SimpleNamespace(
            method='POST',
            content=json.dumps({'method': 'tools/call', 'params': {'name': tool_name}}).encode(),
        )
        return await self.module.connector_context_headers(
            url,
            {'Authorization': 'Bearer token', 'x-artha-connector-context': 'forged'},
            self.user,
            {**self.metadata, **metadata},
            request,
        )

    async def test_initialize_list_and_ordinary_tools_never_claim_privacy(self):
        for rpc in (
            {'method': 'initialize'},
            {'method': 'tools/list'},
            {'method': 'tools/call', 'params': {'name': 'dfs_search'}},
            {'method': 'tools/call', 'params': {'name': 'search_connected_tools_suffix'}},
            [],
        ):
            request = types.SimpleNamespace(method='POST', content=json.dumps(rpc).encode())
            headers = await self.module.connector_context_headers(
                'https://artha.example/mcp',
                {'Authorization': 'Bearer token', 'X-Artha-Connector-Context': 'forged'},
                self.user,
                self.metadata,
                request,
            )
            self.assertEqual(headers, {'Authorization': 'Bearer token'})
        self.claim.assert_not_awaited()

    async def test_all_four_broker_tools_are_attested(self):
        for name in self.module.BROKER_TOOLS:
            request = types.SimpleNamespace(
                method='POST', content=json.dumps({'method': 'tools/call', 'params': {'name': name}}).encode()
            )
            headers = await self.module.connector_context_headers(
                'https://artha.example/mcp', {'Authorization': 'Bearer token'}, self.user, self.metadata, request
            )
            self.assertIn(self.module.HEADER, headers)
        self.assertEqual(self.claim.await_count, 4)

    async def test_research_requires_private_interactive_chat(self):
        for name in (
            'start_founder_research',
            'get_founder_research',
            'start_agent_task',
            'get_agent_task',
        ):
            self.assertIn(self.module.HEADER, await self.headers(tool_name=name))
            self.assertNotIn(self.module.HEADER, await self.headers(tool_name=name, automation_id='job'))
        self.assertEqual(self.claim.await_count, 4)

    async def test_office365_tools_use_the_same_private_chat_claim(self):
        for name in self.module.OFFICE365_TOOLS:
            headers = await self.headers(tool_name=name)
            self.assertIn(self.module.HEADER, headers)
            encoded = headers[self.module.HEADER].split('.')[0]
            value = json.loads(base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4)))
            self.assertEqual(value['channel'], 'chewie')
            self.assertEqual(value['chat_kind'], 'private')
            self.assertEqual(value['user_id'], 'user@example.com')
        self.assertEqual(self.claim.await_count, len(self.module.OFFICE365_TOOLS))

    async def test_office365_does_not_attest_ineligible_or_unowned_chats(self):
        for metadata in (
            {'internal': True},
            {'automation_id': 'job'},
            {'parent_chat_id': 'parent'},
            {'subagent_id': 'worker'},
            {'chat_id': 'channel:group'},
            {'chat_id': 'temporary:1'},
        ):
            self.assertNotIn(self.module.HEADER, await self.headers(tool_name='search_emails', **metadata))
        self.claim.assert_not_awaited()
        self.claim.return_value = None
        self.assertNotIn(self.module.HEADER, await self.headers(tool_name='read_email'))

    async def test_signature_binds_actual_bearer_and_authenticated_owner(self):
        headers = await self.headers()
        payload, signature = headers[self.module.HEADER].split('.')
        self.assertEqual(signature, hmac.new(b'x' * 32, payload.encode(), hashlib.sha256).hexdigest())
        value = json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4)))
        self.assertEqual(value['user_id'], 'user@example.com')
        self.assertEqual(value['token_sha256'], hashlib.sha256(b'token').hexdigest())
        self.assertEqual(value['exp'] - value['iat'], 60)
        self.assertEqual(value['request_id'], 'inbound-user-message')
        self.assertEqual(value['message_id'], 'inbound-user-message')
        self.assertEqual(value['session_kind'], 'interactive')
        self.claim.assert_awaited_once_with('saved', 'owner', 'message', user_message_id=None)
        self.assertNotIn('x-artha-connector-context', headers)

    async def test_user_source_hint_is_verified_and_canonical_source_is_signed(self):
        first = await self.headers(user_message_id='inbound-user-message', message_id='assistant-1')
        second = await self.headers(user_message_id='inbound-user-message', message_id='assistant-regenerated')
        decode = lambda headers: json.loads(base64.urlsafe_b64decode(headers[self.module.HEADER].split('.')[0] + '=='))
        self.assertEqual(decode(first)['message_id'], decode(second)['message_id'])
        self.assertEqual(decode(first)['request_id'], decode(second)['request_id'])
        self.claim.assert_awaited_with(
            'saved', 'owner', 'assistant-regenerated', user_message_id='inbound-user-message'
        )
        self.claim.return_value = None
        self.assertNotIn(self.module.HEADER, await self.headers(user_message_id='missing-user-source'))

    async def test_exact_destination_only(self):
        for url in ('https://attacker.example/mcp', 'https://artha.example/mcp/', 'http://artha.example/mcp'):
            headers = await self.headers(url)
            self.assertNotIn(self.module.HEADER, headers)
            self.assertNotIn('x-artha-connector-context', headers)
        self.claim.assert_not_awaited()

    async def test_background_group_temporary_and_missing_message_are_unattested(self):
        for metadata in (
            {'internal': True},
            {'automation_id': 'job'},
            {'subagent_id': 'worker'},
            {'chat_id': 'channel:group'},
            {'chat_id': 'temporary:1'},
            {'message_id': None},
        ):
            self.assertNotIn(self.module.HEADER, await self.headers(**metadata))
        self.claim.assert_not_awaited()

    async def test_live_authority_rechecked_on_every_request(self):
        self.assertIn(self.module.HEADER, await self.headers())
        self.claim.return_value = False
        self.assertNotIn(self.module.HEADER, await self.headers())
        self.assertEqual(self.claim.await_count, 2)

    async def test_missing_key_preserves_existing_transport_and_strips_forgery(self):
        with patch.dict(os.environ, {'PERSONAL_MCP_CHEWIE_CONTEXT_KEY': ''}):
            headers = await self.headers()
        self.assertEqual(headers, {'Authorization': 'Bearer token'})

    async def test_short_key_fails_closed(self):
        with patch.dict(os.environ, {'PERSONAL_MCP_CHEWIE_CONTEXT_KEY': 'short'}):
            with self.assertRaises(self.modules['fastapi'].HTTPException):
                await self.headers()

    async def test_portfolio_tools_lock_an_owned_private_conversation(self):
        for name in self.module.PORTFOLIO_DOCUMENT_TOOLS:
            headers = await self.headers(tool_name=name)
            self.assertIn(self.module.HEADER, headers)
        self.assertEqual(self.claim.await_count, 4)

    async def test_portfolio_tools_do_not_attest_shared_or_background_conversations(self):
        for name in self.module.PORTFOLIO_DOCUMENT_TOOLS:
            self.assertNotIn(self.module.HEADER, await self.headers(tool_name=name, automation_id='job'))
            self.assertNotIn(self.module.HEADER, await self.headers(tool_name=name, chat_id='channel:group'))
        self.claim.assert_not_awaited()
        self.claim.return_value = None
        self.assertNotIn(self.module.HEADER, await self.headers(tool_name='search_portfolio_documents'))


class ChatClaimTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        source = PATH.parents[2] / 'models/chats.py'
        tree = ast.parse(source.read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'ChatTable')
        method = next(
            n for n in cls.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'claim_personal_connector_chat'
        )
        query = types.SimpleNamespace()
        query.where = lambda *_: query
        query.limit = lambda *_: query
        namespace = {'select': lambda *_: query, 'ChatMessage': object()}
        exec(compile(ast.Module(body=[method], type_ignores=[]), '<saved-chat-claim>', 'exec'), namespace)
        self.chat = types.SimpleNamespace(
            user_id='owner', share_id=None, timer_at=None, meta={}, personal_connectors_private=False
        )
        self.rows = {}
        self.session = types.SimpleNamespace(
            scalar=AsyncMock(return_value=None), get=AsyncMock(side_effect=lambda _, ident: self.rows.get(ident))
        )

        @asynccontextmanager
        async def transaction(_):
            yield self.session, self.chat

        self.table = types.SimpleNamespace(_chat_transaction=transaction)
        self.claim = lambda message, **kwargs: namespace['claim_personal_connector_chat'](
            self.table, 'saved', 'owner', message, **kwargs
        )
        self.stub = patch.dict(
            sys.modules,
            {
                'open_webui.models.shared_chats': types.SimpleNamespace(
                    SharedChat=types.SimpleNamespace(id='id', chat_id='saved')
                )
            },
        )
        self.stub.start()

    async def asyncTearDown(self):
        self.stub.stop()

    def row(self, ident, role, parent=None, owner='owner', chat='saved'):
        self.rows['saved-' + ident] = types.SimpleNamespace(role=role, parent_id=parent, user_id=owner, chat_id=chat)

    async def test_real_user_source_is_required_and_checked(self):
        self.row('assistant', 'assistant', 'source')
        self.row('source', 'user')
        self.assertEqual(await self.claim('assistant', user_message_id='source'), 'source')
        self.assertTrue(self.chat.personal_connectors_private)
        self.chat.personal_connectors_private = False
        self.assertIsNone(await self.claim('assistant', user_message_id='assistant'))
        self.assertIsNone(await self.claim('assistant', user_message_id='missing'))
        self.assertFalse(self.chat.personal_connectors_private)

    async def test_regenerated_outputs_resolve_to_one_saved_source(self):
        self.row('source', 'user')
        self.row('assistant-original', 'assistant', 'source')
        self.row('assistant-regenerated', 'assistant', 'source')
        self.assertEqual(await self.claim('assistant-original'), 'source')
        self.assertEqual(await self.claim('assistant-regenerated'), 'source')

    async def test_foreign_missing_and_cyclic_sources_fail_closed(self):
        self.row('foreign', 'user', owner='other')
        self.row('wrong-chat', 'user', chat='different')
        self.row('cycle', 'assistant', 'cycle')
        self.row('no-source', 'assistant')
        self.row('system', 'system')
        for ident in ('foreign', 'wrong-chat', 'cycle', 'no-source', 'system', 'missing'):
            self.assertIsNone(await self.claim(ident))
        self.assertFalse(self.chat.personal_connectors_private)

    async def test_live_share_guard_precedes_source_and_lock(self):
        self.row('source', 'user')
        self.chat.share_id = 'public'
        self.assertIsNone(await self.claim('source'))
        self.chat.share_id = None
        self.session.scalar.return_value = 'existing-shared-snapshot'
        self.assertIsNone(await self.claim('source'))
        self.assertFalse(self.chat.personal_connectors_private)


if __name__ == '__main__':
    unittest.main()
