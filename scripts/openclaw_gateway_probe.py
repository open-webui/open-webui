#!/usr/bin/env python3
"""Probe an OpenClaw Gateway WebSocket connection.

This script is intentionally standalone. It verifies the real Gateway protocol
shape before the OpenWebUI chat flow is modified.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Any

import aiohttp
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


DEFAULT_GATEWAY_URL = "ws://127.0.0.1:18789"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_DEVICE_PATH = ".openclaw_probe_device.json"


class ProbeError(RuntimeError):
    pass


@dataclass
class RpcResult:
    id: str
    payload: dict[str, Any]


@dataclass
class DeviceIdentity:
    device_id: str
    public_key: str
    private_key_pem: str


def base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def print_json(label: str, value: Any) -> None:
    print(f"\n## {label}")
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def make_request_id(prefix: str = "owui_probe") -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def normalize_gateway_url(raw_url: str) -> str:
    if raw_url.startswith("http://"):
        return f"ws://{raw_url[len('http://') :]}"
    if raw_url.startswith("https://"):
        return f"wss://{raw_url[len('https://') :]}"
    return raw_url


def load_or_create_device_identity(path: str) -> DeviceIdentity:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        if (
            data.get("version") == 1
            and isinstance(data.get("device_id"), str)
            and isinstance(data.get("public_key"), str)
            and isinstance(data.get("private_key_pem"), str)
        ):
            return DeviceIdentity(
                device_id=data["device_id"],
                public_key=data["public_key"],
                private_key_pem=data["private_key_pem"],
            )

    # 探针脚本也要复用稳定 device identity，否则每次运行都会被 Gateway 视为新设备，
    # 需要重复走 pairing 审批，无法真实验证后续后端接入流程。
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    raw_public_key = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")

    identity = DeviceIdentity(
        device_id=hashlib.sha256(raw_public_key).hexdigest(),
        public_key=base64url_encode(raw_public_key),
        private_key_pem=private_key_pem,
    )

    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            {
                "version": 1,
                "device_id": identity.device_id,
                "public_key": identity.public_key,
                "private_key_pem": identity.private_key_pem,
                "created_at_ms": int(time.time() * 1000),
            },
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")
    os.chmod(path, 0o600)
    return identity


def normalize_metadata(value: str | None) -> str:
    return (value or "").strip().lower()


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
    return "|".join(
        [
            "v3",
            device_id,
            client_id,
            client_mode,
            role,
            ",".join(scopes),
            str(signed_at_ms),
            token or "",
            nonce,
            normalize_metadata(platform),
            normalize_metadata(device_family),
        ]
    )


def sign_payload(private_key_pem: str, payload: str) -> str:
    private_key = serialization.load_pem_private_key(private_key_pem.encode("ascii"), password=None)
    signature = private_key.sign(payload.encode("utf-8"))
    return base64url_encode(signature)


class OpenClawGatewayProbe:
    def __init__(
        self,
        url: str,
        token: str,
        role: str,
        scopes: list[str],
        client_id: str,
        client_mode: str,
        client_platform: str,
        device_family: str,
        device_path: str,
        protocol: int,
        timeout_seconds: int,
        verbose: bool,
    ):
        self.url = normalize_gateway_url(url)
        self.token = token
        self.role = role
        self.scopes = scopes
        self.client_id = client_id
        self.client_mode = client_mode
        self.client_platform = client_platform
        self.device_family = device_family
        self.device_path = device_path
        self.protocol = protocol
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self.verbose = verbose
        self.session: aiohttp.ClientSession | None = None
        self.ws: aiohttp.ClientWebSocketResponse | None = None

    async def __aenter__(self) -> "OpenClawGatewayProbe":
        self.session = aiohttp.ClientSession(timeout=self.timeout, trust_env=True)
        try:
            self.ws = await self.session.ws_connect(self.url, heartbeat=20)
            print(f"Connected to {self.url}")
            return self
        except Exception:
            await self.session.close()
            self.session = None
            raise

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.ws is not None:
            await self.ws.close()
        if self.session is not None:
            await self.session.close()

    async def recv_json(self, timeout_seconds: int | None = None) -> dict[str, Any]:
        if self.ws is None:
            raise ProbeError("WebSocket is not connected")

        msg = await asyncio.wait_for(
            self.ws.receive(),
            timeout=timeout_seconds or self.timeout.total or DEFAULT_TIMEOUT_SECONDS,
        )
        if msg.type == aiohttp.WSMsgType.TEXT:
            try:
                payload = json.loads(msg.data)
            except json.JSONDecodeError as exc:
                raise ProbeError(f"Gateway returned non-JSON text: {msg.data}") from exc
            if self.verbose:
                print_json("recv", payload)
            return payload
        if msg.type == aiohttp.WSMsgType.ERROR:
            raise ProbeError(f"WebSocket error: {self.ws.exception()}")
        if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSE):
            raise ProbeError("WebSocket closed by Gateway")
        raise ProbeError(f"Unexpected WebSocket message type: {msg.type}")

    async def send_json(self, payload: dict[str, Any]) -> None:
        if self.ws is None:
            raise ProbeError("WebSocket is not connected")
        if self.verbose:
            print_json("send", redact_secrets(payload))
        await self.ws.send_json(payload)

    async def connect_control_plane(self) -> dict[str, Any]:
        first = await self.recv_json(timeout_seconds=10)
        first_type = first.get("type") or first.get("event") or first.get("method")

        if first_type and "challenge" not in str(first_type).lower():
            print_json("first gateway message", first)

        challenge_payload = first.get("payload") if isinstance(first.get("payload"), dict) else {}
        nonce = str(challenge_payload.get("nonce") or "")
        signed_at_ms = int(time.time() * 1000)
        device = load_or_create_device_identity(self.device_path)
        # 这里严格按 Gateway v4 的 challenge/签名协议组装 connect 请求，
        # 目的是先把协议摸清，再把同一套握手逻辑搬进 OpenWebUI 后端。
        signature_payload = build_device_auth_payload_v3(
            device_id=device.device_id,
            client_id=self.client_id,
            client_mode=self.client_mode,
            role=self.role,
            scopes=self.scopes,
            signed_at_ms=signed_at_ms,
            token=self.token,
            nonce=nonce,
            platform=self.client_platform,
            device_family=self.device_family,
        )

        connect_payload = {
            "type": "req",
            "id": make_request_id("connect"),
            "method": "connect",
            "params": {
                "minProtocol": self.protocol,
                "maxProtocol": self.protocol,
                "client": {
                    "id": self.client_id,
                    "version": "0.1.0",
                    "platform": self.client_platform,
                    "mode": self.client_mode,
                    "deviceFamily": self.device_family,
                },
                "role": self.role,
                "scopes": self.scopes,
                "caps": [],
                "commands": [],
                "permissions": {},
                "auth": {"token": self.token},
                "locale": "en-US",
                "userAgent": "openwebui-openclaw-probe/0.1.0",
                "device": {
                    "id": device.device_id,
                    "publicKey": device.public_key,
                    "signature": sign_payload(device.private_key_pem, signature_payload),
                    "signedAt": signed_at_ms,
                    "nonce": nonce,
                },
            },
        }

        await self.send_json(connect_payload)
        response = await self.recv_json(timeout_seconds=10)
        print_json("connect response", redact_secrets(response))

        if is_error(response):
            raise ProbeError("Gateway connect returned an error")
        return response

    async def rpc(self, method: str, params: dict[str, Any] | None = None) -> RpcResult:
        request_id = make_request_id(method.replace(".", "_"))
        payload = {
            "type": "req",
            "id": request_id,
            "method": method,
            "params": params or {},
        }
        await self.send_json(payload)

        deadline = time.monotonic() + (self.timeout.total or DEFAULT_TIMEOUT_SECONDS)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ProbeError(f"Timed out waiting for RPC response to {method}")

            response = await self.recv_json(timeout_seconds=int(max(1, remaining)))
            response_id = response.get("id") or response.get("requestId") or response.get("request_id")
            if response_id == request_id:
                print_json(f"{method} response", redact_secrets(response))
                if is_error(response):
                    raise ProbeError(f"RPC {method} returned an error")
                return RpcResult(id=request_id, payload=response)

            print_json("event while waiting for rpc", redact_secrets(response))

    async def drain_events(self, seconds: int) -> None:
        if seconds <= 0:
            return

        print(f"\nListening for events for {seconds}s ...")
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            remaining = int(max(1, deadline - time.monotonic()))
            try:
                event = await self.recv_json(timeout_seconds=remaining)
            except asyncio.TimeoutError:
                break
            print_json("event", redact_secrets(event))


def is_error(payload: dict[str, Any]) -> bool:
    if payload.get("type") in {"error", "rpc.error"}:
        return True
    if payload.get("ok") is False:
        return True
    if payload.get("error"):
        return True
    return False


def redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            normalized_key = key.lower()
            if (
                "token" in normalized_key
                or normalized_key in {"authorization", "password", "secret", "apikey", "api_key"}
            ):
                redacted[key] = "***REDACTED***"
            else:
                redacted[key] = redact_secrets(item)
        return redacted
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    return value


def pick_agent_id(agents_response: dict[str, Any], explicit_agent_id: str | None) -> str | None:
    if explicit_agent_id:
        return explicit_agent_id

    candidates = []
    for key in ("agents", "data", "result", "items"):
        value = agents_response.get(key)
        if isinstance(value, list):
            candidates = value
            break
        if isinstance(value, dict):
            for nested_key in ("agents", "data", "items"):
                nested = value.get(nested_key)
                if isinstance(nested, list):
                    candidates = nested
                    break
            if candidates:
                break

    payload = agents_response.get("payload")
    if not candidates and isinstance(payload, dict):
        for key in ("agents", "data", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                candidates = value
                break

    for item in candidates:
        if isinstance(item, dict):
            agent_id = item.get("id") or item.get("agent_id") or item.get("name")
            if agent_id:
                return str(agent_id)
        elif isinstance(item, str):
            return item
    return None


def pick_session_key(session_response: dict[str, Any], explicit_session_key: str | None) -> str | None:
    if explicit_session_key:
        return explicit_session_key

    containers = []
    payload = session_response.get("payload")
    if isinstance(payload, dict):
        containers.append(payload)
    containers.append(session_response)

    for container in containers:
        for key_name in ("key", "sessionKey", "session_key"):
            value = container.get(key_name)
            if isinstance(value, str) and value:
                return value

        session = container.get("session")
        if isinstance(session, dict):
            for key_name in ("key", "sessionKey", "session_key"):
                value = session.get(key_name)
                if isinstance(value, str) and value:
                    return value

    if isinstance(payload, dict):
        value = payload.get("sessionId")
        if isinstance(value, str) and value:
            return value

    return None


async def run_probe(args: argparse.Namespace) -> int:
    token = args.token or os.getenv("OPENCLAW_GATEWAY_TOKEN")
    if not token:
        print(
            "Missing Gateway token. Set OPENCLAW_GATEWAY_TOKEN or pass --token.",
            file=sys.stderr,
        )
        return 2

    async with OpenClawGatewayProbe(
        url=args.url,
        token=token,
        role=args.role,
        scopes=args.scope,
        client_id=args.client_id,
        client_mode=args.client_mode,
        client_platform=args.client_platform,
        device_family=args.device_family,
        device_path=args.device_path,
        protocol=args.protocol,
        timeout_seconds=args.timeout,
        verbose=args.verbose,
    ) as gateway:
        await gateway.connect_control_plane()
        agents = await gateway.rpc("agents.list")
        agent_id = pick_agent_id(agents.payload, args.agent_id)

        if not agent_id:
            print("\nNo agent_id could be inferred from agents.list. Pass --agent-id to continue.")
            return 0

        print(f"\nUsing agent_id={agent_id}")

        session_key = args.session_key

        if args.skip_session_create:
            print("\nSkipping sessions.create by request.")
        else:
            try:
                create_result = await gateway.rpc("sessions.create", {"agentId": agent_id})
                session_key = pick_session_key(create_result.payload, args.session_key)
            except ProbeError as exc:
                print(f"\nsessions.create failed: {exc}")
                print("Continuing only if --session-key supplied an existing OpenClaw session key.")

        if not session_key:
            print("\nNo OpenClaw session key is available. sessions.create did not return a key.")
            print("Pass --session-key with an existing key to continue, or inspect the sessions.create response above.")
            return 0

        print(f"\nUsing openclaw_session_key={session_key}")

        for subscribe_method in ("sessions.subscribe", "sessions.messages.subscribe"):
            try:
                await gateway.rpc(
                    subscribe_method,
                    {"key": session_key},
                )
                break
            except ProbeError as exc:
                print(f"\n{subscribe_method} failed: {exc}")

        if args.message:
            send_params = {
                "key": session_key,
                "message": args.message,
            }
            try:
                await gateway.rpc("sessions.send", send_params)
            except ProbeError as exc:
                print(f"\nsessions.send failed: {exc}")

        await gateway.drain_events(args.listen_seconds)

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        default=os.getenv("OPENCLAW_GATEWAY_URL", DEFAULT_GATEWAY_URL),
        help=f"Gateway WebSocket URL. Default: env OPENCLAW_GATEWAY_URL or {DEFAULT_GATEWAY_URL}",
    )
    parser.add_argument("--token", default=None, help="Gateway token. Prefer env OPENCLAW_GATEWAY_TOKEN.")
    parser.add_argument("--role", default="operator", help="Gateway role to request. Default: operator")
    parser.add_argument(
        "--client-id",
        default="gateway-client",
        help="Gateway client id. Default: gateway-client",
    )
    parser.add_argument(
        "--client-mode",
        default="backend",
        help="Gateway client mode. Default: backend",
    )
    parser.add_argument("--client-platform", default="python", help="Client platform metadata. Default: python")
    parser.add_argument(
        "--device-family",
        default="OpenWebUI",
        help="Client device family metadata. Default: OpenWebUI",
    )
    parser.add_argument(
        "--device-path",
        default=DEFAULT_DEVICE_PATH,
        help=f"Path for probe device identity. Default: {DEFAULT_DEVICE_PATH}",
    )
    parser.add_argument("--protocol", type=int, default=4, help="Gateway protocol version. Default: 4")
    parser.add_argument(
        "--scope",
        action="append",
        default=["operator.read", "operator.write", "operator.approvals"],
        help="Gateway scope. Can be passed multiple times.",
    )
    parser.add_argument("--agent-id", default=None, help="Agent id to use. Defaults to first from agents.list.")
    parser.add_argument(
        "--session-key",
        default=None,
        help="Existing OpenClaw session key. By default the probe uses the key returned by sessions.create.",
    )
    parser.add_argument("--message", default="Hello from OpenWebUI OpenClaw Gateway probe.", help="Test message.")
    parser.add_argument("--listen-seconds", type=int, default=20, help="Seconds to print session events.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS, help="Total client timeout seconds.")
    parser.add_argument("--skip-session-create", action="store_true", help="Skip sessions.create before send.")
    parser.add_argument("--verbose", action="store_true", help="Print raw sent and received frames.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return asyncio.run(run_probe(args))
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"\nProbe failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
