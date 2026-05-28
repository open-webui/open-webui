import asyncio
import os
import sqlite3
import tempfile
import time
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

TEST_DATA_DIR = tempfile.mkdtemp(prefix='open-webui-openai-web-auth-')
TEST_DB_PATH = os.path.join(TEST_DATA_DIR, 'webui.db')
os.environ.setdefault('DATA_DIR', TEST_DATA_DIR)
os.environ.setdefault('DATABASE_URL', f'sqlite:///{TEST_DB_PATH}')
os.environ.setdefault('ENABLE_DB_MIGRATIONS', 'False')
os.environ.setdefault('VECTOR_DB', 'none')

with sqlite3.connect(TEST_DB_PATH) as conn:
    conn.execute(
        'CREATE TABLE IF NOT EXISTS config ('
        'id INTEGER PRIMARY KEY, '
        'data JSON NOT NULL, '
        'version INTEGER NOT NULL DEFAULT 0, '
        'created_at DATETIME DEFAULT CURRENT_TIMESTAMP, '
        'updated_at DATETIME'
        ')'
    )

from open_webui.models.oauth_sessions import OAuthSessions
from open_webui.routers import openai


class FakeOAuthSessions:
    def __init__(self):
        self.sessions = {}
        self.created_tokens = []
        self.next_id = 0

    async def create_session(self, user_id: str, provider: str, token: dict, db=None):
        self.next_id += 1
        session_id = f'session-{self.next_id}'
        session = SimpleNamespace(
            id=session_id,
            user_id=user_id,
            provider=provider,
            token=token,
            expires_at=token.get('expires_at') or int(time.time()) + 3600,
        )
        self.sessions[session_id] = session
        self.created_tokens.append(token)
        return session

    async def get_session_by_id(self, session_id: str, db=None):
        return self.sessions.get(session_id)

    async def get_session_by_provider_and_user_id(self, provider: str, user_id: str, db=None):
        matches = [s for s in self.sessions.values() if s.provider == provider and s.user_id == user_id]
        return matches[-1] if matches else None

    async def update_session_by_id(self, session_id: str, token: dict, db=None):
        session = self.sessions.get(session_id)
        if not session:
            return None
        session.token = token
        session.expires_at = token.get('expires_at') or int(time.time()) + 3600
        self.created_tokens.append(token)
        return session

    async def delete_session_by_id(self, session_id: str, db=None):
        return self.sessions.pop(session_id, None) is not None

    async def delete_sessions_by_user_id_and_provider(self, user_id: str, provider: str, db=None):
        to_delete = [k for k, v in self.sessions.items() if v.user_id == user_id and v.provider == provider]
        for key in to_delete:
            del self.sessions[key]
        return bool(to_delete)


def run(coro):
    return asyncio.run(coro)


def test_openai_web_auth_start_returns_safe_fields(monkeypatch):
    fake_sessions = FakeOAuthSessions()
    monkeypatch.setattr(openai, 'OAuthSessions', fake_sessions)

    async def fake_start():
        return {
            'device_auth_id': 'device-secret',
            'user_code': 'USER-CODE',
            'interval': 5,
            'expires_at': int(time.time()) + 600,
        }

    monkeypatch.setattr(openai, 'start_openai_web_auth_device_flow', fake_start)

    response = run(openai.start_web_auth(user=SimpleNamespace(role='admin')))

    assert response.verification_url == openai.OPENAI_WEB_AUTH_VERIFICATION_URL
    assert response.user_code == 'USER-CODE'
    assert response.session_id == 'session-1'
    assert response.interval == 5
    assert not hasattr(response, 'device_auth_id')
    assert fake_sessions.created_tokens[0]['device_auth_id'] == 'device-secret'


def test_openai_web_auth_complete_stores_credential_without_returning_tokens(monkeypatch):
    async def scenario():
        fake_sessions = FakeOAuthSessions()
        monkeypatch.setattr(openai, 'OAuthSessions', fake_sessions)
        device = await fake_sessions.create_session(
            user_id=openai.OPENAI_WEB_AUTH_STORAGE_USER_ID,
            provider=openai.OPENAI_WEB_AUTH_DEVICE_SESSION_PROVIDER,
            token={
                'device_auth_id': 'device-secret',
                'user_code': 'USER-CODE',
                'expires_at': int(time.time()) + 600,
            },
        )

        async def fake_complete(device_auth_id: str, user_code: str):
            assert device_auth_id == 'device-secret'
            assert user_code == 'USER-CODE'
            return {
                'access_token': 'access-secret',
                'refresh_token': 'refresh-secret',
                'expires_at': int(time.time()) + 3600,
                'account_id': 'acct_123',
            }

        monkeypatch.setattr(openai, 'complete_openai_web_auth_device_flow', fake_complete)

        response = await openai.complete_web_auth(
            openai.OpenAIWebAuthCompleteForm(session_id=device.id),
            request=None,
            user=SimpleNamespace(role='admin'),
        )

        payload = response.model_dump()
        assert payload == {
            'credential_type': 'web_auth',
            'connected': True,
            'has_credential': True,
            'status': 'connected',
            'expires_at': payload['expires_at'],
        }
        assert 'access_token' not in payload
        assert 'refresh_token' not in payload
        assert 'account_id' not in payload
        credential = await fake_sessions.get_session_by_provider_and_user_id(
            openai.OPENAI_WEB_AUTH_CREDENTIAL_PROVIDER,
            openai.OPENAI_WEB_AUTH_STORAGE_USER_ID,
        )
        assert credential.token['access_token'] == 'access-secret'
        assert credential.token['account_id'] == 'acct_123'
        assert await fake_sessions.get_session_by_id(device.id) is None

    run(scenario())


def test_openai_web_auth_status_and_disconnect_are_redacted(monkeypatch):
    async def scenario():
        fake_sessions = FakeOAuthSessions()
        monkeypatch.setattr(openai, 'OAuthSessions', fake_sessions)
        await fake_sessions.create_session(
            user_id=openai.OPENAI_WEB_AUTH_STORAGE_USER_ID,
            provider=openai.OPENAI_WEB_AUTH_CREDENTIAL_PROVIDER,
            token={
                'access_token': 'access-secret',
                'refresh_token': 'refresh-secret',
                'expires_at': int(time.time()) + 3600,
                'account_id': 'acct_123',
            },
        )

        status_response = await openai.get_web_auth_status(user=SimpleNamespace(role='admin'))
        assert 'access-secret' not in str(status_response.model_dump())
        assert 'refresh-secret' not in str(status_response.model_dump())
        assert 'acct_123' not in str(status_response.model_dump())

        disconnect_response = await openai.disconnect_web_auth(request=None, user=SimpleNamespace(role='admin'))
        assert disconnect_response.model_dump() == {
            'credential_type': 'none',
            'connected': False,
            'has_credential': False,
            'status': 'not_configured',
            'expires_at': None,
        }

    run(scenario())


def test_openai_web_auth_complete_and_disconnect_invalidate_model_caches(monkeypatch):
    async def scenario():
        fake_sessions = FakeOAuthSessions()
        monkeypatch.setattr(openai, 'OAuthSessions', fake_sessions)
        invalidations = []

        async def fake_invalidate(request=None, user=None):
            invalidations.append((request, user))

        async def fake_complete(device_auth_id: str, user_code: str):
            return {
                'access_token': 'access-secret',
                'refresh_token': 'refresh-secret',
                'expires_at': int(time.time()) + 3600,
            }

        monkeypatch.setattr(openai, 'invalidate_openai_models_cache', fake_invalidate)
        monkeypatch.setattr(openai, 'complete_openai_web_auth_device_flow', fake_complete)

        device = await fake_sessions.create_session(
            user_id=openai.OPENAI_WEB_AUTH_STORAGE_USER_ID,
            provider=openai.OPENAI_WEB_AUTH_DEVICE_SESSION_PROVIDER,
            token={
                'device_auth_id': 'device-secret',
                'user_code': 'USER-CODE',
                'expires_at': int(time.time()) + 600,
            },
        )
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(OPENAI_MODELS={'old': {}})))
        user = SimpleNamespace(id='admin', role='admin')

        await openai.complete_web_auth(openai.OpenAIWebAuthCompleteForm(session_id=device.id), request=request, user=user)
        await openai.disconnect_web_auth(request=request, user=user)

        assert invalidations == [(request, user), (request, user)]

    run(scenario())


def test_invalidate_openai_models_cache_clears_user_and_app_state(monkeypatch):
    async def scenario():
        deleted_keys = []

        async def fake_delete(cache_key: str):
            deleted_keys.append(cache_key)

        monkeypatch.setattr(openai.get_all_models.cache, 'delete', fake_delete)
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(OPENAI_MODELS={'stale': {}})))

        await openai.invalidate_openai_models_cache(request, SimpleNamespace(id='admin'))

        assert deleted_keys == ['openai_all_models', 'openai_all_models_admin']
        assert request.app.state.OPENAI_MODELS == {}

    run(scenario())


def test_openai_config_update_invalidates_model_caches(monkeypatch):
    async def scenario():
        invalidations = []

        async def fake_invalidate(request=None, user=None):
            invalidations.append((request, user))

        monkeypatch.setattr(openai, 'invalidate_openai_models_cache', fake_invalidate)
        request = SimpleNamespace(
            app=SimpleNamespace(
                state=SimpleNamespace(
                    config=SimpleNamespace(
                        ENABLE_OPENAI_API=True,
                        OPENAI_API_BASE_URLS=['https://stale.example/v1'],
                        OPENAI_API_KEYS=['stale'],
                        OPENAI_API_CONFIGS={},
                    )
                )
            )
        )
        user = SimpleNamespace(id='admin', role='admin')
        form = openai.OpenAIConfigForm(
            ENABLE_OPENAI_API=True,
            OPENAI_API_BASE_URLS=['https://api.openai.com/v1'],
            OPENAI_API_KEYS=[''],
            OPENAI_API_CONFIGS={'0': {'auth_type': 'openai_web_auth'}, '9': {'enable': True}},
        )

        response = await openai.update_config(request, form, user=user)

        assert invalidations == [(request, user)]
        assert response['OPENAI_API_CONFIGS'] == {'0': {'auth_type': 'openai_web_auth'}}

    run(scenario())


def test_openai_web_auth_upstream_start_pending_failure_and_invalid_responses(monkeypatch):
    async def success_json(url: str, payload: dict):
        return 200, {'device_auth_id': 'device-secret', 'user_code': 'CODE', 'interval': '2', 'expires_in': '30'}

    monkeypatch.setattr(openai, '_post_openai_web_auth_json', success_json)
    started = run(openai.start_openai_web_auth_device_flow())
    assert started['interval'] == 2
    assert started['expires_at'] > int(time.time())

    async def failing_json(url: str, payload: dict):
        return 500, {'access_token': 'must-not-leak'}

    monkeypatch.setattr(openai, '_post_openai_web_auth_json', failing_json)
    with pytest.raises(HTTPException) as failure:
        run(openai.start_openai_web_auth_device_flow())
    assert failure.value.status_code == 502
    assert 'must-not-leak' not in failure.value.detail

    async def invalid_json(url: str, payload: dict):
        return 200, {'device_auth_id': 'device-secret', 'user_code': 'CODE', 'interval': 'not-int'}

    monkeypatch.setattr(openai, '_post_openai_web_auth_json', invalid_json)
    with pytest.raises(HTTPException) as invalid:
        run(openai.start_openai_web_auth_device_flow())
    assert invalid.value.status_code == 502
    assert 'invalid interval' in invalid.value.detail


def test_openai_web_auth_complete_pending_failure_and_invalid_responses(monkeypatch):
    async def pending_json(url: str, payload: dict):
        return 403, {}

    monkeypatch.setattr(openai, '_post_openai_web_auth_json', pending_json)
    with pytest.raises(HTTPException) as pending:
        run(openai.complete_openai_web_auth_device_flow('device', 'CODE'))
    assert pending.value.status_code == 409

    async def invalid_device_json(url: str, payload: dict):
        return 200, {'authorization_code': 'auth-code'}

    monkeypatch.setattr(openai, '_post_openai_web_auth_json', invalid_device_json)
    with pytest.raises(HTTPException) as invalid_device:
        run(openai.complete_openai_web_auth_device_flow('device', 'CODE'))
    assert invalid_device.value.status_code == 502

    async def valid_device_json(url: str, payload: dict):
        return 200, {'authorization_code': 'auth-code', 'code_verifier': 'verifier'}

    async def token_failure_form(url: str, payload: dict):
        return 500, {'refresh_token': 'must-not-leak'}

    monkeypatch.setattr(openai, '_post_openai_web_auth_json', valid_device_json)
    monkeypatch.setattr(openai, '_post_openai_web_auth_form', token_failure_form)
    with pytest.raises(HTTPException) as token_failure:
        run(openai.complete_openai_web_auth_device_flow('device', 'CODE'))
    assert token_failure.value.status_code == 502
    assert 'must-not-leak' not in token_failure.value.detail

    async def invalid_token_form(url: str, payload: dict):
        return 200, {'access_token': 'access-secret', 'refresh_token': 'refresh-secret', 'expires_in': 'bad'}

    monkeypatch.setattr(openai, '_post_openai_web_auth_form', invalid_token_form)
    with pytest.raises(HTTPException) as invalid_token:
        run(openai.complete_openai_web_auth_device_flow('device', 'CODE'))
    assert invalid_token.value.status_code == 502
    assert 'access-secret' not in invalid_token.value.detail


def test_openai_web_auth_complete_rejects_expired_sessions(monkeypatch):
    async def scenario():
        fake_sessions = FakeOAuthSessions()
        monkeypatch.setattr(openai, 'OAuthSessions', fake_sessions)
        device = await fake_sessions.create_session(
            user_id=openai.OPENAI_WEB_AUTH_STORAGE_USER_ID,
            provider=openai.OPENAI_WEB_AUTH_DEVICE_SESSION_PROVIDER,
            token={'device_auth_id': 'device', 'user_code': 'CODE', 'expires_at': int(time.time()) - 1},
        )

        with pytest.raises(HTTPException) as expired:
            await openai.complete_web_auth(openai.OpenAIWebAuthCompleteForm(session_id=device.id), request=None)
        assert expired.value.status_code == 409
        assert await fake_sessions.get_session_by_id(device.id) is None

    run(scenario())


def test_openai_web_auth_runtime_refresh_and_codex_headers(monkeypatch):
    async def scenario():
        fake_sessions = FakeOAuthSessions()
        monkeypatch.setattr(openai, 'OAuthSessions', fake_sessions)
        session = await fake_sessions.create_session(
            user_id=openai.OPENAI_WEB_AUTH_STORAGE_USER_ID,
            provider=openai.OPENAI_WEB_AUTH_CREDENTIAL_PROVIDER,
            token={
                'access_token': 'old-access',
                'refresh_token': 'refresh-secret',
                'expires_at': int(time.time()) - 1,
                'account_id': 'acct_123',
            },
        )

        async def fake_refresh(token: dict):
            assert token['refresh_token'] == 'refresh-secret'
            return {
                **token,
                'access_token': 'new-access',
                'expires_at': int(time.time()) + 3600,
            }

        monkeypatch.setattr(openai, 'refresh_openai_web_auth_credential', fake_refresh)
        request = SimpleNamespace(cookies={}, state=SimpleNamespace())

        headers, cookies = await openai.get_headers_and_cookies(
            request,
            openai.OPENAI_CODEX_API_ENDPOINT,
            key='',
            config={'auth_type': openai.OPENAI_CODEX_WEB_AUTH_TYPE},
            metadata={'chat_id': 'chat-1'},
            user=SimpleNamespace(id='admin'),
        )

        assert headers['Authorization'] == 'Bearer new-access'
        assert headers['ChatGPT-Account-Id'] == 'acct_123'
        assert headers['originator'] == 'open-webui'
        assert headers['User-Agent'] == 'Open WebUI'
        assert headers['session_id'] == 'chat-1'
        assert cookies == {}
        assert fake_sessions.sessions[session.id].token['access_token'] == 'new-access'

    run(scenario())


def test_openai_web_auth_runtime_header_resolution(monkeypatch):
    async def scenario():
        fake_sessions = FakeOAuthSessions()
        monkeypatch.setattr(openai, 'OAuthSessions', fake_sessions)
        await fake_sessions.create_session(
            user_id=openai.OPENAI_WEB_AUTH_STORAGE_USER_ID,
            provider=openai.OPENAI_WEB_AUTH_CREDENTIAL_PROVIDER,
            token={
                'access_token': 'access-secret',
                'refresh_token': 'refresh-secret',
                'expires_at': int(time.time()) + 3600,
                'account_id': 'acct_456',
            },
        )
        request = SimpleNamespace(cookies={}, state=SimpleNamespace())

        headers, cookies = await openai.get_headers_and_cookies(
            request,
            openai.OPENAI_CODEX_API_ENDPOINT,
            key='',
            config={'auth_type': openai.OPENAI_CODEX_WEB_AUTH_TYPE},
            user=SimpleNamespace(id='admin'),
        )

        assert headers['Authorization'] == 'Bearer access-secret'
        assert headers['ChatGPT-Account-Id'] == 'acct_456'
        assert cookies == {}

    run(scenario())


def test_openai_api_key_header_behavior_remains_unchanged():
    async def scenario():
        request = SimpleNamespace(cookies={}, state=SimpleNamespace())

        headers, cookies = await openai.get_headers_and_cookies(
            request,
            'https://api.openai.com/v1',
            key='sk-api-key',
            config={'auth_type': 'bearer'},
            user=SimpleNamespace(id='admin'),
        )

        assert headers['Authorization'] == 'Bearer sk-api-key'
        assert cookies == {}

    run(scenario())


def test_empty_native_openai_bearer_models_route_returns_empty_without_upstream_call():
    async def scenario():
        request = SimpleNamespace(
            app=SimpleNamespace(
                state=SimpleNamespace(
                    config=SimpleNamespace(
                        ENABLE_OPENAI_API=True,
                        OPENAI_API_BASE_URLS=['https://api.openai.com/v1'],
                        OPENAI_API_KEYS=[''],
                        OPENAI_API_CONFIGS={'0': {'enable': True, 'auth_type': 'bearer'}},
                    )
                )
            )
        )

        response = await openai.get_models(request, url_idx=0, user=SimpleNamespace(id='admin', role='admin'))

        assert response == {'data': []}

    run(scenario())


def test_empty_native_openai_bearer_is_skipped_during_aggregate_model_fetch(monkeypatch):
    async def scenario():
        requested = []

        async def fake_models_request(request=None, url=None, key=None, user=None, config=None):
            requested.append((url, key, config))
            return {'data': [{'id': 'gpt-test'}]}

        async def fake_get_token():
            return 'connected-token'

        monkeypatch.setattr(openai, 'get_models_request', fake_models_request)
        monkeypatch.setattr(openai, 'get_openai_web_auth_access_token', fake_get_token)
        request = SimpleNamespace(
            app=SimpleNamespace(
                state=SimpleNamespace(
                    config=SimpleNamespace(
                        ENABLE_OPENAI_API=True,
                        OPENAI_API_BASE_URLS=['https://api.openai.com/v1', openai.OPENAI_CODEX_API_ENDPOINT],
                        OPENAI_API_KEYS=['', ''],
                        OPENAI_API_CONFIGS={
                            '0': {'enable': True, 'auth_type': 'bearer'},
                            '1': {'enable': True, 'auth_type': openai.OPENAI_CODEX_WEB_AUTH_TYPE},
                        },
                    )
                )
            )
        )

        responses = await openai.get_all_models_responses(request, user=SimpleNamespace(id='admin', role='admin'))

        assert responses[0] is None
        assert requested == []
        assert [model['id'] for model in responses[1]['data']] == openai.OPENAI_CODEX_WEB_AUTH_MODEL_IDS
        assert responses[1]['data'][0]['urlIdx'] == 1

    run(scenario())


def test_codex_web_auth_models_are_hidden_without_connected_credential(monkeypatch):
    async def scenario():
        async def fail_models_request(*args, **kwargs):
            raise AssertionError('Codex account auth must not call /v1/models')

        async def fake_get_token():
            return None

        monkeypatch.setattr(openai, 'get_models_request', fail_models_request)
        monkeypatch.setattr(openai, 'get_openai_web_auth_access_token', fake_get_token)
        request = SimpleNamespace(
            app=SimpleNamespace(
                state=SimpleNamespace(
                    config=SimpleNamespace(
                        ENABLE_OPENAI_API=True,
                        OPENAI_API_BASE_URLS=[openai.OPENAI_CODEX_API_ENDPOINT],
                        OPENAI_API_KEYS=[''],
                        OPENAI_API_CONFIGS={'0': {'enable': True, 'auth_type': openai.OPENAI_CODEX_WEB_AUTH_TYPE}},
                    )
                )
            )
        )

        response = await openai.get_models(request, url_idx=0, user=SimpleNamespace(id='admin', role='admin'))

        assert response == {'data': []}

    run(scenario())


def test_codex_web_auth_models_route_returns_static_list_with_connected_credential(monkeypatch):
    async def scenario():
        async def fail_models_request(*args, **kwargs):
            raise AssertionError('Codex account auth must not call /v1/models')

        async def fake_get_token():
            return 'connected-token'

        monkeypatch.setattr(openai, 'get_models_request', fail_models_request)
        monkeypatch.setattr(openai, 'get_openai_web_auth_access_token', fake_get_token)
        request = SimpleNamespace(
            app=SimpleNamespace(
                state=SimpleNamespace(
                    config=SimpleNamespace(
                        ENABLE_OPENAI_API=True,
                        OPENAI_API_BASE_URLS=[openai.OPENAI_CODEX_API_ENDPOINT],
                        OPENAI_API_KEYS=[''],
                        OPENAI_API_CONFIGS={'0': {'enable': True, 'auth_type': openai.OPENAI_CODEX_WEB_AUTH_TYPE}},
                    )
                )
            )
        )

        response = await openai.get_models(request, url_idx=0, user=SimpleNamespace(id='admin', role='admin'))

        assert [model['id'] for model in response['data']] == openai.OPENAI_CODEX_WEB_AUTH_MODEL_IDS
        assert response['data'][0]['urlIdx'] == 0

    run(scenario())


def test_codex_web_auth_aggregate_model_fetch_is_hidden_without_connected_credential(monkeypatch):
    async def scenario():
        requested = []

        async def fake_models_request(request=None, url=None, key=None, user=None, config=None):
            requested.append((url, key, config))
            return {'data': [{'id': 'gpt-test'}]}

        async def fake_get_token():
            return None

        monkeypatch.setattr(openai, 'get_models_request', fake_models_request)
        monkeypatch.setattr(openai, 'get_openai_web_auth_access_token', fake_get_token)
        request = SimpleNamespace(
            app=SimpleNamespace(
                state=SimpleNamespace(
                    config=SimpleNamespace(
                        ENABLE_OPENAI_API=True,
                        OPENAI_API_BASE_URLS=['https://api.openai.com/v1', openai.OPENAI_CODEX_API_ENDPOINT],
                        OPENAI_API_KEYS=['', ''],
                        OPENAI_API_CONFIGS={
                            '0': {'enable': True, 'auth_type': 'bearer'},
                            '1': {'enable': True, 'auth_type': openai.OPENAI_CODEX_WEB_AUTH_TYPE},
                        },
                    )
                )
            )
        )

        responses = await openai.get_all_models_responses(request, user=SimpleNamespace(id='admin', role='admin'))

        assert responses == [None, None]
        assert requested == []

    run(scenario())


def test_codex_web_auth_request_rewrites_to_responses_endpoint():
    payload = {
        'model': 'gpt-5.5',
        'messages': [{'role': 'user', 'content': 'hello'}],
        'max_tokens': 10,
    }

    request_url, converted, is_responses = openai.prepare_openai_codex_web_auth_request(payload, False)

    assert request_url == openai.OPENAI_CODEX_API_ENDPOINT
    assert is_responses is True
    assert converted['model'] == 'gpt-5.5'
    assert converted['instructions'] == 'You are ChatGPT, a helpful assistant.'
    assert converted['store'] is False
    assert converted['stream'] is True
    assert converted['input'][0]['role'] == 'user'
    assert converted['max_output_tokens'] == 10


def test_codex_web_auth_sse_response_parser_uses_last_json_payload():
    parsed = openai.parse_openai_codex_sse_response(
        'event: response.created\n'
        'data: {"type":"response.created"}\n\n'
        'event: response.completed\n'
        'data: {"id":"resp_1","output":[{"type":"message","content":[{"type":"output_text","text":"ok"}]}]}\n\n'
        'data: [DONE]\n'
    )

    assert parsed['id'] == 'resp_1'
    assert parsed['output'][0]['content'][0]['text'] == 'ok'


def test_codex_web_auth_sse_delta_converter_outputs_chat_chunks():
    converted = openai.convert_openai_codex_sse_payload(
        {
            'type': 'response.output_text.delta',
            'response_id': 'resp_1',
            'delta': 'hello',
            'model': 'gpt-5.5',
        }
    )

    assert converted == (
        b'data: {"id": "resp_1", "object": "chat.completion.chunk", "model": "gpt-5.5", '
        b'"choices": [{"index": 0, "delta": {"content": "hello"}, "finish_reason": null}]}\n\n'
    )
    assert openai.convert_openai_codex_sse_payload({'type': 'response.completed'}) == b'data: [DONE]\n\n'
def test_codex_web_auth_sse_failure_converter_preserves_error_signal():
    converted = openai.convert_openai_codex_sse_payload(
        {
            'type': 'response.failed',
            'status_details': {'message': 'permission denied', 'code': 'permission_denied'},
        }
    )

    assert converted is not None
    assert b'permission denied' in converted
    assert b'data: [DONE]' in converted


def test_codex_web_auth_non_2xx_sse_is_forwarded_as_json_error(monkeypatch):
    async def scenario():
        async def fake_headers_and_cookies(*args, **kwargs):
            return {}, {}

        async def fake_check_model_access(*args, **kwargs):
            return None

        class FakeResponse:
            status = 502
            headers = {'Content-Type': 'text/event-stream'}

            async def text(self):
                return (
                    'data: {"type":"response.failed","status_details":{"message":"upstream denied","code":"denied"}}\n\n'
                    'data: [DONE]\n'
                )

        class FakeSession:
            async def request(self, *args, **kwargs):
                return FakeResponse()

        async def fake_get_session():
            return FakeSession()

        async def fake_cleanup_response(*args, **kwargs):
            return None

        async def fake_get_model_by_id(*args, **kwargs):
            return None

        monkeypatch.setattr(openai.Models, 'get_model_by_id', staticmethod(fake_get_model_by_id))
        monkeypatch.setattr(openai, 'check_model_access', fake_check_model_access)
        monkeypatch.setattr(openai, 'get_headers_and_cookies', fake_headers_and_cookies)
        monkeypatch.setattr(openai, 'get_session', fake_get_session)
        monkeypatch.setattr(openai, 'cleanup_response', fake_cleanup_response)

        request = SimpleNamespace(
            state=SimpleNamespace(bypass_filter=False),
            app=SimpleNamespace(
                state=SimpleNamespace(
                    OPENAI_MODELS={'gpt-5.5': {'urlIdx': 0}},
                    config=SimpleNamespace(
                        OPENAI_API_BASE_URLS=[openai.OPENAI_CODEX_API_ENDPOINT],
                        OPENAI_API_KEYS=[''],
                        OPENAI_API_CONFIGS={'0': {'auth_type': openai.OPENAI_CODEX_WEB_AUTH_TYPE}},
                    ),
                )
            ),
        )

        response = await openai.generate_chat_completion(
            request,
            {'model': 'gpt-5.5', 'messages': [{'role': 'user', 'content': 'hello'}], 'stream': True},
            user=SimpleNamespace(id='admin', role='admin'),
        )

        assert response.status_code == 502
        assert b'upstream denied' in response.body

    run(scenario())


def test_oauth_sessions_encrypts_persisted_web_auth_tokens():
    token = {
        'access_token': 'access-secret',
        'refresh_token': 'refresh-secret',
        'expires_at': int(time.time()) + 3600,
    }

    encrypted = OAuthSessions._encrypt_token(token)

    assert 'access-secret' not in encrypted
    assert 'refresh-secret' not in encrypted
    assert OAuthSessions._decrypt_token(encrypted) == token


def test_openai_web_auth_routes_require_admin_dependency(monkeypatch):
    app = FastAPI()
    app.include_router(openai.router, prefix='/openai')
    client = TestClient(app)

    response = client.get('/openai/web-auth/status')

    assert response.status_code in (401, 403)
