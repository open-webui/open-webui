from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from enum import Enum
import re
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Dict,
    MutableMapping,
    Optional,
    cast,
)
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

from open_webui.env import AUDIT_LOG_LEVEL, MAX_BODY_LOG_SIZE
from open_webui.utils.auth import get_current_user, get_http_authorization_cred
from open_webui.models.users import UserModel


if TYPE_CHECKING:
    from loguru import Logger


@dataclass(frozen=True)
class AuditLogEntry:
    # `Metadata` audit level properties
    id: str
    user: Optional[dict[str, Any]]
    audit_level: str
    verb: str
    request_uri: str
    user_agent: Optional[str] = None
    source_ip: Optional[str] = None
    # `Request` audit level properties
    request_object: Any = None
    # `Request Response` level
    response_object: Any = None
    response_status_code: Optional[int] = None


class AuditLevel(str, Enum):
    NONE = "NONE"
    METADATA = "METADATA"
    REQUEST = "REQUEST"
    REQUEST_RESPONSE = "REQUEST_RESPONSE"


class AuditLogger:
    """
    A helper class that encapsulates audit logging functionality. It uses Loguru’s logger with an auditable binding to ensure that audit log entries are filtered correctly.

    Parameters:
    logger (Logger): An instance of Loguru’s logger.
    """

    def __init__(self, logger: "Logger"):
        self.logger = logger.bind(auditable=True)

    def write(
        self,
        audit_entry: AuditLogEntry,
        *,
        log_level: str = "INFO",
        extra: Optional[dict] = None,
    ):

        entry = asdict(audit_entry)

        if extra:
            entry["extra"] = extra

        self.logger.log(
            log_level,
            "",
            **entry,
        )


class AuditContext:
    """
    Captures and aggregates the HTTP request and response bodies during the processing of a request. It ensures that only a configurable maximum amount of data is stored to prevent excessive memory usage.

    Attributes:
    request_body (bytearray): Accumulated request payload.
    response_body (bytearray): Accumulated response payload.
    max_body_size (int): Maximum number of bytes to capture.
    metadata (Dict[str, Any]): A dictionary to store additional audit metadata (user, http verb, user agent, etc.).
    """

    def __init__(self, max_body_size: int = MAX_BODY_LOG_SIZE):
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
    """
    ASGI middleware that intercepts HTTP requests and responses to perform audit logging. It captures request/response bodies (depending on audit level), headers, HTTP methods, and user information, then logs a structured audit entry at the end of the request cycle.
    """

    AUDITED_METHODS = {"PUT", "PATCH", "DELETE", "POST"}

    def __init__(
        self,
        app: ASGI3Application,
        *,
        excluded_paths: Optional[list[str]] = None,
        max_body_size: int = MAX_BODY_LOG_SIZE,
        audit_level: AuditLevel = AuditLevel.NONE,
    ) -> None:
        self.app = app
        self.audit_logger = AuditLogger(logger)
        self.excluded_paths = excluded_paths or []
        self.max_body_size = max_body_size
        self.audit_level = audit_level

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
                if self.audit_level == AuditLevel.REQUEST_RESPONSE:
                    await self._capture_response(message, context)

                await send(message)

            original_receive = receive

            async def receive_wrapper() -> ASGIReceiveEvent:
                nonlocal original_receive
                message = await original_receive()

                if self.audit_level in (
                    AuditLevel.REQUEST,
                    AuditLevel.REQUEST_RESPONSE,
                ):
                    await self._capture_request(message, context)

                return message

            await self.app(scope, receive_wrapper, send_wrapper)

    @asynccontextmanager
    async def _audit_context(
        self, request: Request
    ) -> AsyncGenerator[AuditContext, None]:
        """
        async context manager that ensures that an audit log entry is recorded after the request is processed.
        """
        context = AuditContext()
        try:
            yield context
        finally:
            await self._log_audit_entry(request, context)

    async def _get_authenticated_user(self, request: Request) -> Optional[UserModel]:
        auth_header = request.headers.get("Authorization")

        try:
            user = get_current_user(
                request, None, get_http_authorization_cred(auth_header)
            )
            return user
        except Exception as e:
            logger.debug(f"Failed to get authenticated user: {str(e)}")

        return None

    def _should_skip_auditing(self, request: Request) -> bool:
        if (
            request.method not in {"POST", "PUT", "PATCH", "DELETE"}
            or AUDIT_LOG_LEVEL == "NONE"
        ):
            return True

        ALWAYS_LOG_ENDPOINTS = {
            "/api/v1/auths/signin",
            "/api/v1/auths/signout",
            "/api/v1/auths/signup",
        }
        path = request.url.path.lower()
        for endpoint in ALWAYS_LOG_ENDPOINTS:
            if path.startswith(endpoint):
                return False  # Do NOT skip logging for auth endpoints

        # Skip logging if the request is not authenticated
        if not request.headers.get("authorization"):
            return True

        # match either /api/<resource>/...(for the endpoint /api/chat case) or /api/v1/<resource>/...
        pattern = re.compile(
            r"^/api(?:/v1)?/(" + "|".join(self.excluded_paths) + r")\b"
        )
        if pattern.match(request.url.path):
            return True

        return False

    async def _capture_request(self, message: ASGIReceiveEvent, context: AuditContext):
        if message["type"] == "http.request":
            body = message.get("body", b"")
            context.add_request_chunk(body)

    async def _capture_response(self, message: ASGISendEvent, context: AuditContext):
        if message["type"] == "http.response.start":
            context.metadata["response_status_code"] = message["status"]

        elif message["type"] == "http.response.body":
            body = message.get("body", b"")
            context.add_response_chunk(body)

    async def _log_audit_entry(self, request: Request, context: AuditContext):
        try:
            user = await self._get_authenticated_user(request)

            user = (
                user.model_dump(include={"id", "name", "email", "role"}) if user else {}
            )

            request_body = context.request_body.decode("utf-8", errors="replace")
            response_body = context.response_body.decode("utf-8", errors="replace")

            # Redact sensitive information
            if "password" in request_body:
                request_body = re.sub(
                    r'"password":\s*"(.*?)"',
                    '"password": "********"',
                    request_body,
                )

            entry = AuditLogEntry(
                id=str(uuid.uuid4()),
                user=user,
                audit_level=self.audit_level.value,
                verb=request.method,
                request_uri=str(request.url),
                response_status_code=context.metadata.get("response_status_code", None),
                source_ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                request_object=request_body,
                response_object=response_body,
            )

            self.audit_logger.write(entry)
        except Exception as e:
            logger.error(f"Failed to log audit entry: {str(e)}")
