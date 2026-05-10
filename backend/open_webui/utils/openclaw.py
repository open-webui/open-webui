import asyncio
import base64
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator, Optional

import aiohttp
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import HTTPException, Request, status
from starlette.responses import StreamingResponse

from open_webui.env import DATA_DIR
from open_webui.models.chats import Chats

log = logging.getLogger(__name__)

OPENCLAW_MODEL_PREFIX = 'openclaw:'
OPENCLAW_PROTOCOL_VERSION = 4
OPENCLAW_DEFAULT_SCOPES = ['operator.read', 'operator.write', 'operator.approvals']


class OpenClawGatewayError(Exception):
    pass


@dataclass
class OpenClawDeviceIdentity:
    device_id: str
    public_key: str
    private_key_pem: str


def is_openclaw_model_id(model_id: str | None) -> bool:
    return bool(model_id and model_id.startswith(OPENCLAW_MODEL_PREFIX))


def agent_id_from_model_id(model_id: str) -> str:
    return model_id.removeprefix(OPENCLAW_MODEL_PREFIX)


def model_id_from_agent_id(agent_id: str) -> str:
    return f'{OPENCLAW_MODEL_PREFIX}{agent_id}'


def normalize_gateway_url(raw_url: str) -> str:
    if raw_url.startswith('http://'):
        return f'ws://{raw_url[len("http://") :]}'
    if raw_url.startswith('https://'):
        return f'wss://{raw_url[len("https://") :]}'
    return raw_url


def base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode('ascii').rstrip('=')


def load_or_create_device_identity(path: str) -> OpenClawDeviceIdentity:
    device_path = Path(path)
    if device_path.exists():
        data = json.loads(device_path.read_text())
        return OpenClawDeviceIdentity(
            device_id=data['device_id'],
            public_key=data['public_key'],
            private_key_pem=data['private_key_pem'],
        )

    # Gateway 的设备配对是“设备身份”维度，不是单纯 token 维度。
    # 这里把本地 backend 伪装成一个稳定设备，后续重启后仍能复用同一份配对授权。
    device_path.parent.mkdir(parents=True, exist_ok=True)
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode('ascii')
    public_key_raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    identity = OpenClawDeviceIdentity(
        device_id=uuid.uuid4().hex,
        public_key=base64url_encode(public_key_raw),
        private_key_pem=private_key_pem,
    )
    device_path.write_text(json.dumps(identity.__dict__, indent=2))
    try:
        os.chmod(device_path, 0o600)
    except OSError:
        pass
    return identity


def build_device_auth_payload_v3(
    *,
    device_id: str,
    client_id: str,
    client_mode: str,
    role: str,
    scopes: list[str],
    signed_at_ms: int,
    token: str,
    nonce: str,
    platform: str,
    device_family: str,
) -> str:
    return '|'.join(
        [
            'v3',
            device_id,
            client_id,
            client_mode,
            role,
            ','.join(scopes),
            str(signed_at_ms),
            token or '',
            nonce,
            (platform or '').strip().lower(),
            (device_family or '').strip().lower(),
        ]
    )


def sign_payload(private_key_pem: str, payload: str) -> str:
    private_key = serialization.load_pem_private_key(private_key_pem.encode('ascii'), password=None)
    return base64url_encode(private_key.sign(payload.encode('utf-8')))


def get_openclaw_config(request: Request) -> dict[str, Any]:
    config = request.app.state.config
    device_path = getattr(config, 'OPENCLAW_GATEWAY_DEVICE_PATH', '') or str(
        Path(DATA_DIR) / 'openclaw_gateway_device.json'
    )
    return {
        'enabled': bool(getattr(config, 'ENABLE_OPENCLAW_GATEWAY', False)),
        'url': getattr(config, 'OPENCLAW_GATEWAY_URL', ''),
        'token': getattr(config, 'OPENCLAW_GATEWAY_TOKEN', ''),
        'client_id': getattr(config, 'OPENCLAW_GATEWAY_CLIENT_ID', 'gateway-client'),
        'client_mode': getattr(config, 'OPENCLAW_GATEWAY_CLIENT_MODE', 'backend'),
        'device_path': device_path,
        'allowed_agent_ids': getattr(config, 'OPENCLAW_ALLOWED_AGENT_IDS', []) or [],
    }


class OpenClawGatewayClient:
    def __init__(self, request: Request):
        self.request = request
        self.config = get_openclaw_config(request)
        self.url = normalize_gateway_url(self.config['url'])
        self.token = self.config['token']

    def ensure_configured(self) -> None:
        if not self.config['enabled']:
            raise OpenClawGatewayError('OpenClaw Gateway is disabled')
        if not self.url:
            raise OpenClawGatewayError('OpenClaw Gateway URL is not configured')
        if not self.token:
            raise OpenClawGatewayError('OpenClaw Gateway token is not configured')

    async def _connect(self) -> tuple[aiohttp.ClientSession, aiohttp.ClientWebSocketResponse]:
        self.ensure_configured()
        timeout = aiohttp.ClientTimeout(total=120)
        session = aiohttp.ClientSession(timeout=timeout, trust_env=True)
        try:
            ws = await session.ws_connect(self.url, heartbeat=20)
            first = await self._recv_json(ws, timeout_seconds=10)
            challenge = first.get('payload') if isinstance(first.get('payload'), dict) else {}
            nonce = str(challenge.get('nonce') or '')
            signed_at_ms = int(time.time() * 1000)
            identity = load_or_create_device_identity(self.config['device_path'])
            scopes = OPENCLAW_DEFAULT_SCOPES
            # OpenClaw Gateway v4 连接不是“带 token 直连”而是 challenge + 设备签名双重校验。
            # token 负责声明是谁，device signature 负责声明“这台被批准过的设备就是我”。
            signature_payload = build_device_auth_payload_v3(
                device_id=identity.device_id,
                client_id=self.config['client_id'],
                client_mode=self.config['client_mode'],
                role='operator',
                scopes=scopes,
                signed_at_ms=signed_at_ms,
                token=self.token,
                nonce=nonce,
                platform='python',
                device_family='OpenWebUI',
            )

            await ws.send_json(
                {
                    'type': 'req',
                    'id': self._request_id('connect'),
                    'method': 'connect',
                    'params': {
                        'client': {
                            'id': self.config['client_id'],
                            'mode': self.config['client_mode'],
                            'platform': 'python',
                            'version': '0.1.0',
                            'deviceFamily': 'OpenWebUI',
                        },
                        'role': 'operator',
                        'scopes': scopes,
                        'caps': [],
                        'commands': [],
                        'permissions': {},
                        'auth': {'token': self.token},
                        'locale': 'en-US',
                        'userAgent': 'openwebui-openclaw/0.1.0',
                        'minProtocol': OPENCLAW_PROTOCOL_VERSION,
                        'maxProtocol': OPENCLAW_PROTOCOL_VERSION,
                        'device': {
                            'id': identity.device_id,
                            'publicKey': identity.public_key,
                            'signature': sign_payload(identity.private_key_pem, signature_payload),
                            'signedAt': signed_at_ms,
                            'nonce': nonce,
                        },
                    },
                }
            )
            response = await self._recv_json(ws, timeout_seconds=10)
            if not response.get('ok'):
                raise OpenClawGatewayError(self._error_message(response, 'OpenClaw Gateway connect failed'))
            return session, ws
        except Exception:
            await session.close()
            raise

    async def _recv_json(
        self, ws: aiohttp.ClientWebSocketResponse, timeout_seconds: Optional[int] = None
    ) -> dict[str, Any]:
        msg = await asyncio.wait_for(ws.receive(), timeout=timeout_seconds or 120)
        if msg.type == aiohttp.WSMsgType.TEXT:
            return json.loads(msg.data)
        if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSE):
            raise OpenClawGatewayError('OpenClaw Gateway closed the WebSocket')
        if msg.type == aiohttp.WSMsgType.ERROR:
            raise OpenClawGatewayError(f'OpenClaw Gateway WebSocket error: {ws.exception()}')
        raise OpenClawGatewayError(f'Unexpected OpenClaw Gateway WebSocket message type: {msg.type}')

    async def _rpc(
        self,
        ws: aiohttp.ClientWebSocketResponse,
        method: str,
        params: Optional[dict[str, Any]] = None,
        timeout_seconds: int = 60,
    ) -> dict[str, Any]:
        request_id = self._request_id(method.replace('.', '_'))
        await ws.send_json({'type': 'req', 'id': request_id, 'method': method, 'params': params or {}})

        deadline = time.monotonic() + timeout_seconds
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise OpenClawGatewayError(f'Timed out waiting for OpenClaw RPC {method}')
            response = await self._recv_json(ws, timeout_seconds=max(1, int(remaining)))
            if response.get('id') == request_id:
                if not response.get('ok'):
                    raise OpenClawGatewayError(self._error_message(response, f'OpenClaw RPC {method} failed'))
                return response.get('payload') or {}

    def _request_id(self, prefix: str) -> str:
        return f'{prefix}_{uuid.uuid4().hex}'

    def _error_message(self, response: dict[str, Any], fallback: str) -> str:
        error = response.get('error') if isinstance(response, dict) else None
        if isinstance(error, dict):
            return str(error.get('message') or error.get('code') or fallback)
        if error:
            return str(error)
        return fallback

    async def list_agents(self) -> list[dict[str, Any]]:
        session, ws = await self._connect()
        try:
            payload = await self._rpc(ws, 'agents.list', timeout_seconds=30)
            agents = payload.get('agents') if isinstance(payload.get('agents'), list) else []
            allowed = set(self.config['allowed_agent_ids'])
            if allowed:
                agents = [agent for agent in agents if agent.get('id') in allowed]
            return agents
        finally:
            await ws.close()
            await session.close()

    async def create_session(self, agent_id: str) -> dict[str, Any]:
        session, ws = await self._connect()
        try:
            return await self._rpc(ws, 'sessions.create', {'agentId': agent_id}, timeout_seconds=30)
        finally:
            await ws.close()
            await session.close()


async def fetch_openclaw_models(request: Request) -> list[dict[str, Any]]:
    if not get_openclaw_config(request)['enabled']:
        return []

    try:
        agents = await OpenClawGatewayClient(request).list_agents()
    except Exception as e:
        log.warning(f'Failed to fetch OpenClaw agents: {e}')
        return []

    models = []
    for agent in agents:
        agent_id = agent.get('id')
        if not agent_id:
            continue
        model = agent.get('model') if isinstance(agent.get('model'), dict) else {}
        # 把 OpenClaw Agent 包装成 OpenWebUI 可识别的 model 结构，
        # 这样前端现有“选模型”链路可以最小代价切换成“选 Agent”。
        models.append(
            {
                'id': model_id_from_agent_id(agent_id),
                'name': agent.get('name') or agent_id,
                'object': 'model',
                'created': int(time.time()),
                'owned_by': 'openclaw',
                'connection_type': 'external',
                'openclaw': {
                    'agent_id': agent_id,
                    'workspace': agent.get('workspace'),
                    'runtime': agent.get('agentRuntime'),
                    'model': model,
                },
                'info': {
                    'id': model_id_from_agent_id(agent_id),
                    'name': agent.get('name') or agent_id,
                    'meta': {
                        'description': f'Agent · {agent_id}',
                        'tags': [{'name': 'Agent'}],
                        'capabilities': {
                            'vision': False,
                            'file_upload': False,
                            'web_search': False,
                            'code_interpreter': False,
                            'citations': False,
                        },
                    },
                },
                'tags': [{'name': 'Agent'}],
                'actions': [],
                'filters': [],
            }
        )
    return models


async def _get_or_create_openclaw_session_key(
    request: Request,
    agent_id: str,
    model_id: str,
    metadata: dict[str, Any],
) -> str:
    chat_id = metadata.get('chat_id')
    user_id = metadata.get('user_id')

    if chat_id and not str(chat_id).startswith('local:'):
        chat = await Chats.get_chat_by_id(chat_id)
        if chat and chat.user_id == user_id:
            sessions = (chat.meta or {}).get('openclaw_sessions') or {}
            existing = sessions.get(model_id) or sessions.get(agent_id)
            if isinstance(existing, dict) and existing.get('key'):
                return existing['key']

    payload = await OpenClawGatewayClient(request).create_session(agent_id)
    key = payload.get('key')
    if not key:
        raise OpenClawGatewayError('OpenClaw sessions.create did not return payload.key')

    if chat_id and not str(chat_id).startswith('local:'):
        chat = await Chats.get_chat_by_id(chat_id)
        if chat and chat.user_id == user_id:
            meta = chat.meta or {}
            sessions = meta.get('openclaw_sessions') or {}
            # 这里把 OpenClaw 返回的 session key 固化到当前 chat 的 meta 中。
            # 隔离粒度是“当前 OpenWebUI chat + 当前 agent/model”，避免不同会话串用上下文。
            sessions[model_id] = {
                'agent_id': agent_id,
                'key': key,
                'session_id': payload.get('sessionId'),
                'updated_at': int(time.time()),
            }
            await Chats.update_chat_meta_by_id(chat_id, {**meta, 'openclaw_sessions': sessions})

    return key


def _message_text(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get('role') != 'user':
            continue
        content = message.get('content', '')
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get('text') or item.get('content')
                    if text:
                        parts.append(str(text))
            return '\n'.join(parts)
    return ''


def _sse(data: dict[str, Any]) -> str:
    return f'data: {json.dumps(data, ensure_ascii=False)}\n\n'


def _openai_chunk(model_id: str, content: str = '', finish_reason: Optional[str] = None) -> dict[str, Any]:
    delta = {'content': content} if content else {}
    return {
        'id': f'chatcmpl-openclaw-{uuid.uuid4().hex}',
        'object': 'chat.completion.chunk',
        'created': int(time.time()),
        'model': model_id,
        'choices': [
            {
                'index': 0,
                'delta': delta,
                'finish_reason': finish_reason,
            }
        ],
    }


async def generate_openclaw_chat_completion(request: Request, form_data: dict, user: Any) -> StreamingResponse:
    model_id = form_data.get('model')
    agent_id = agent_id_from_model_id(model_id)
    metadata = form_data.get('metadata') or {}
    message = _message_text(form_data.get('messages') or [])
    if not message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Missing user message for OpenClaw Agent')

    async def event_generator() -> AsyncIterator[str]:
        session: Optional[aiohttp.ClientSession] = None
        ws: Optional[aiohttp.ClientWebSocketResponse] = None
        try:
            session_key = await _get_or_create_openclaw_session_key(request, agent_id, model_id, metadata)
            client = OpenClawGatewayClient(request)
            session, ws = await client._connect()
            await client._rpc(ws, 'sessions.subscribe', {'key': session_key}, timeout_seconds=30)
            await client._rpc(ws, 'sessions.send', {'key': session_key, 'message': message}, timeout_seconds=30)

            final_text = ''
            while True:
                event = await client._recv_json(ws, timeout_seconds=120)
                event_name = event.get('event')
                payload = event.get('payload') if isinstance(event.get('payload'), dict) else {}
                if payload.get('sessionKey') and payload.get('sessionKey') != session_key:
                    continue

                # OpenWebUI 前端消费的是 OpenAI 风格 SSE；
                # 这里把 OpenClaw 的 agent/chat/session 事件流翻译成兼容 chunk。
                if event_name == 'agent' and payload.get('stream') == 'assistant':
                    delta = (payload.get('data') or {}).get('delta')
                    if delta:
                        final_text = (payload.get('data') or {}).get('text') or f'{final_text}{delta}'
                        yield _sse(_openai_chunk(model_id, delta))
                elif event_name == 'chat':
                    if payload.get('state') == 'final':
                        content = payload.get('message', {}).get('content', [])
                        if isinstance(content, list) and content:
                            final_text = content[0].get('text') or final_text
                        yield _sse(_openai_chunk(model_id, '', finish_reason='stop'))
                        yield 'data: [DONE]\n\n'
                        break
                elif event_name == 'session.message':
                    message_payload = payload.get('message') or {}
                    if message_payload.get('role') == 'assistant':
                        usage = message_payload.get('usage') or {}
                        if usage:
                            yield _sse({'usage': usage})
                elif event_name == 'sessions.changed' and payload.get('status') in {'done', 'error'}:
                    if payload.get('status') == 'error':
                        raise OpenClawGatewayError(str(payload.get('error') or 'OpenClaw run failed'))
        except Exception as e:
            log.exception(f'OpenClaw chat completion failed: {e}')
            yield _sse({'error': {'message': str(e)}})
            yield 'data: [DONE]\n\n'
        finally:
            if ws is not None:
                await ws.close()
            if session is not None:
                await session.close()

    return StreamingResponse(event_generator(), media_type='text/event-stream')
