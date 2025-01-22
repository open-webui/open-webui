from contextlib import asynccontextmanager
from pprint import pp as pprint
from typing import Any, AsyncGenerator, Dict, MutableMapping, Optional, cast
import uuid

from asgiref.typing import (
    ASGI3Application,
    ASGIReceiveCallable,
    ASGIReceiveEvent,
    ASGISendCallable,
    ASGISendEvent,
    Scope as ASGIScope,
)
from loguru import logger
from starlette.requests import Request

from open_webui.env import AUDIT_LOG_LEVEL
from open_webui.utils.auth import get_current_user, get_http_authorization_cred
from open_webui.models.users import UserModel
from open_webui.utils.logger import AuditLogEntry, AuditLogger


class AuditContext:
    def __init__(self, max_body_size: int = 4096):
        self.request_body = bytearray()
        self.response_body = bytearray()
        self.max_body_size = max_body_size
        self.metadata: Dict[str, Any] = {}

    def add_request_chunk(self, chunk: bytes):
        if len(self.request_body) < self.max_body_size:
            self.request_body.extend(
                chunk[: self.max_body_size - len(self.request_body)]
            )

    def add_response_chunk(self, chunk: bytes):
        if len(self.response_body) < self.max_body_size:
            self.response_body.extend(
                chunk[: self.max_body_size - len(self.response_body)]
            )


class AuditLoggingMiddleware:
    AUDITED_METHODS = {"PUT", "PATCH", "DELETE", "POST"}

    def __init__(
        self,
        app: ASGI3Application,
        *,
        excluded_paths: Optional[list[str]] = None,
        max_body_size: int = 4096,
    ) -> None:
        self.app = app
        self.audit_logger = AuditLogger(logger)
        self.excluded_paths = excluded_paths or []
        self.max_body_size = max_body_size

    async def __call__(
        self,
        scope: ASGIScope,
        receive: ASGIReceiveCallable,
        send: ASGISendCallable,
    ) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        request = Request(scope=cast(MutableMapping, scope))

        if self._should_skip_auditing(request):
            return await self.app(scope, receive, send)

        async with self._audit_context(request) as context:

            async def send_wrapper(message: ASGISendEvent) -> None:
                await self._capture_response(message, context)
                await send(message)

            original_receive = receive

            async def receive_wrapper() -> ASGIReceiveEvent:
                nonlocal original_receive
                message = await original_receive()
                await self._capture_request(message, context)
                return message

            await self.app(scope, receive_wrapper, send_wrapper)

    @asynccontextmanager
    async def _audit_context(
        self, request: Request
    ) -> AsyncGenerator[AuditContext, None]:
        context = AuditContext()
        try:
            yield context
        finally:
            await self._log_audit_entry(request, context)

    async def _get_authenticated_user(self, request: Request) -> UserModel:

        auth_header = request.headers.get("Authorization")
        assert auth_header
        user = get_current_user(request, get_http_authorization_cred(auth_header))

        return user

    def _should_skip_auditing(self, request: Request) -> bool:
        return request.method not in {
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        } or not request.headers.get("authorization")

    async def _capture_request(self, message: ASGIReceiveEvent, context: AuditContext):
        if message["type"] == "http.request":
            body = message.get("body", b"")
            pprint(f"Req Body: {body}")
            context.add_request_chunk(body)

    async def _capture_response(self, message: ASGISendEvent, context: AuditContext):
        if message["type"] == "http.response.start":
            context.metadata["response_status_code"] = message["status"]

        elif message["type"] == "http.response.body":
            body = message.get("body", b"")
            pprint(f"Res Body: {body}")
            context.add_response_chunk(body)

    async def _log_audit_entry(self, request: Request, context: AuditContext):
        try:
            user = await self._get_authenticated_user(request)

            entry = AuditLogEntry(
                id=str(uuid.uuid4()),
                user=user.model_dump(include={"id", "name", "email", "role"}),
                audit_level=AUDIT_LOG_LEVEL,
                verb=request.method,
                request_uri=str(request.url),
                response_status_code=context.metadata.get("response_status_code", None),
                source_ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                request_object=context.request_body.decode("utf-8"),
                response_object=context.response_body.decode("utf-8"),
            )

            self.audit_logger.write(entry)
        except Exception as e:
            logger.error(f"Failed to log audit entry: {str(e)}")
