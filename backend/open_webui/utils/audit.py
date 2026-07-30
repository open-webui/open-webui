import re
import time
import uuid
from json import JSONDecodeError, dumps, loads
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Dict,
    MutableMapping,
    Optional,
    cast,
)

from asgiref.typing import (
    ASGI3Application,
    ASGIReceiveCallable,
    ASGIReceiveEvent,
    ASGISendCallable,
    ASGISendEvent,
)
from asgiref.typing import (
    Scope as ASGIScope,
)
from loguru import logger
from open_webui.env import AUDIT_LOG_LEVEL, ENABLE_AUDIT_GET_REQUESTS, ENABLE_AUDIT_LOGS_DB, MAX_BODY_LOG_SIZE
from open_webui.models.audit_logs import AuditLogCreate, AuditLogs
from open_webui.models.users import UserModel
from open_webui.utils.auth import get_current_user, get_http_authorization_cred
from starlette.requests import Request
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

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
    NONE = 'NONE'
    METADATA = 'METADATA'
    REQUEST = 'REQUEST'
    REQUEST_RESPONSE = 'REQUEST_RESPONSE'


SENSITIVE_FIELD_NAMES = {
    'api_key',
    'apikey',
    'authorization',
    'cookie',
    'password',
    'secret',
    'token',
}


def _is_sensitive_field(name: str) -> bool:
    normalized_name = name.lower().replace('-', '_')
    return normalized_name in SENSITIVE_FIELD_NAMES or normalized_name.endswith(('_api_key', '_secret', '_token'))


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: '********' if _is_sensitive_field(key) else _redact_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    return value


def _redact_body(body: str) -> str:
    if not body:
        return body

    try:
        return dumps(_redact_value(loads(body)), ensure_ascii=False)
    except (JSONDecodeError, TypeError):
        pattern = r'("(?:api[_-]?key|authorization|cookie|password|secret|token)"\s*:\s*")[^"]*(")'
        return re.sub(pattern, r'\1********\2', body, flags=re.IGNORECASE)


def _extract_request_fields(body: str) -> dict[str, Any]:
    try:
        payload = loads(body)
    except (JSONDecodeError, TypeError):
        return {}

    if not isinstance(payload, dict):
        return {}

    payload = _redact_value(payload)
    messages = payload.get('messages')
    if not isinstance(messages, list):
        messages = []

    def message_contents(role: str) -> list[Any]:
        return [
            message.get('content')
            for message in messages
            if isinstance(message, dict) and message.get('role') == role and 'content' in message
        ]

    return {
        'request_model': payload.get('model'),
        'request_extra': payload.get('extra'),
        'request_skill_ids': payload.get('skill_ids'),
        'request_tool_ids': payload.get('tool_ids'),
        'request_response_format': payload.get('response_format'),
        'request_extra_body': payload.get('extra_body'),
        'request_system_messages': message_contents('system'),
        'request_user_messages': message_contents('user'),
    }


def _extract_response_fields(body: str) -> dict[str, Any]:
    try:
        payloads = [loads(body)]
    except (JSONDecodeError, TypeError):
        payloads = []
        for line in body.splitlines():
            if not line.startswith('data:'):
                continue
            try:
                payloads.append(loads(line.removeprefix('data:').strip()))
            except (JSONDecodeError, TypeError):
                continue

    response_id = None
    response_model = None
    finish_reasons = []
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        response_id = response_id or payload.get('id')
        response_model = response_model or payload.get('model')
        choices = payload.get('choices')
        if isinstance(choices, list):
            finish_reasons.extend(
                choice.get('finish_reason')
                for choice in choices
                if isinstance(choice, dict) and choice.get('finish_reason') is not None
            )

    return {
        'response_id': response_id,
        'response_model': response_model,
        'response_finish_reasons': finish_reasons or None,
    }


def _redact_uri(uri: str) -> str:
    parts = urlsplit(uri)
    if not parts.query:
        return uri

    query = urlencode(
        [(key, '********' if _is_sensitive_field(key) else value) for key, value in parse_qsl(parts.query, keep_blank_values=True)],
        doseq=True,
    )
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))


class AuditLogger:
    """
    A helper class that encapsulates audit logging functionality. It uses Loguru’s logger with an auditable binding to ensure that audit log entries are filtered correctly.

    Parameters:
    logger (Logger): An instance of Loguru’s logger.
    """

    def __init__(self, logger: 'Logger'):
        self.logger = logger.bind(auditable=True)

    def write(
        self,
        audit_entry: AuditLogEntry,
        *,
        log_level: str = 'INFO',
        extra: Optional[dict] = None,
    ):
        entry = asdict(audit_entry)

        if extra:
            entry['extra'] = extra

        self.logger.log(
            log_level,
            '',
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
        self.request_truncated = False
        self.response_truncated = False
        self.metadata: Dict[str, Any] = {}

    def add_request_chunk(self, chunk: bytes):
        if len(self.request_body) < self.max_body_size:
            remaining = self.max_body_size - len(self.request_body)
            self.request_body.extend(chunk[:remaining])
            self.request_truncated = self.request_truncated or len(chunk) > remaining
        elif chunk:
            self.request_truncated = True

    def add_response_chunk(self, chunk: bytes):
        if len(self.response_body) < self.max_body_size:
            remaining = self.max_body_size - len(self.response_body)
            self.response_body.extend(chunk[:remaining])
            self.response_truncated = self.response_truncated or len(chunk) > remaining
        elif chunk:
            self.response_truncated = True


class AuditLoggingMiddleware:
    """
    ASGI middleware that intercepts HTTP requests and responses to perform audit logging. It captures request/response bodies (depending on audit level), headers, HTTP methods, and user information, then logs a structured audit entry at the end of the request cycle.
    """

    DEFAULT_AUDITED_METHODS = {'PUT', 'PATCH', 'DELETE', 'POST'}

    def __init__(
        self,
        app: ASGI3Application,
        *,
        excluded_paths: Optional[list[str]] = None,
        included_paths: Optional[list[str]] = None,
        exact_included_paths: Optional[list[str]] = None,
        max_body_size: int = MAX_BODY_LOG_SIZE,
        audit_level: AuditLevel = AuditLevel.NONE,
        audit_get_requests: bool = False,
    ) -> None:
        self.app = app
        self.audit_logger = AuditLogger(logger)

        def normalize_paths(paths: Optional[list[str]]) -> list[str]:
            return [path for path in (path.strip().lstrip('/') for path in paths or []) if path]

        self.excluded_paths = normalize_paths(excluded_paths)
        self.included_paths = normalize_paths(included_paths)
        self.exact_included_paths = {path.strip() for path in exact_included_paths or [] if path.strip()}
        self.max_body_size = max_body_size
        self.audited_methods = set(self.DEFAULT_AUDITED_METHODS)
        if audit_get_requests:
            self.audited_methods.add('GET')
        self.audit_level = audit_level

        # Paths are fixed for the process lifetime; compile once instead of
        # per request. None means the corresponding mode has nothing to match.
        self._included_pattern = (
            re.compile(r'^/api(?:/v1)?/(' + '|'.join(self.included_paths) + r')\b') if self.included_paths else None
        )
        self._excluded_pattern = (
            re.compile(r'^/api(?:/v1)?/(' + '|'.join(self.excluded_paths) + r')\b') if self.excluded_paths else None
        )

        if self.exact_included_paths and (self.included_paths or self.excluded_paths):
            logger.warning(
                'AUDIT_EXACT_INCLUDED_PATHS is set and takes precedence over '
                'AUDIT_INCLUDED_PATHS and AUDIT_EXCLUDED_PATHS.'
            )
        elif self.included_paths and self.excluded_paths:
            logger.warning(
                'Both AUDIT_INCLUDED_PATHS and AUDIT_EXCLUDED_PATHS are set. '
                'AUDIT_INCLUDED_PATHS (whitelist) takes precedence.'
            )

    async def __call__(
        self,
        scope: ASGIScope,
        receive: ASGIReceiveCallable,
        send: ASGISendCallable,
    ) -> None:
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)

        request = Request(scope=cast(MutableMapping, scope))

        if self._should_skip_auditing(request):
            return await self.app(scope, receive, send)

        async with self._audit_context(request) as context:

            async def send_wrapper(message: ASGISendEvent) -> None:
                if message['type'] == 'http.response.start':
                    context.metadata['response_status_code'] = message['status']
                elif self.audit_level == AuditLevel.REQUEST_RESPONSE:
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
    async def _audit_context(self, request: Request) -> AsyncGenerator[AuditContext, None]:
        """
        async context manager that ensures that an audit log entry is recorded after the request is processed.
        """
        context = AuditContext()
        try:
            yield context
        finally:
            await self._log_audit_entry(request, context)

    async def _get_authenticated_user(self, request: Request) -> Optional[UserModel]:
        # get_current_user stashes the resolved user on the scope-backed state;
        # reuse it instead of running the full auth pipeline (JWT decode, Redis
        # revocation checks, DB fetch, last-active write) a second time.
        user = getattr(request.state, 'user', None)
        if isinstance(user, UserModel):
            return user

        auth_header = request.headers.get('Authorization')

        try:
            user = await get_current_user(request, None, None, get_http_authorization_cred(auth_header))
            return user
        except Exception as e:
            logger.debug(f'Failed to get authenticated user: {str(e)}')

        return None

    ALWAYS_LOG_ENDPOINTS = (
        '/api/v1/auths/signin',
        '/api/v1/auths/signout',
        '/api/v1/auths/signup',
    )

    def _should_skip_auditing(self, request: Request) -> bool:
        if AUDIT_LOG_LEVEL == 'NONE':
            return True

        if request.method not in self.audited_methods:
            return True

        path = request.url.path

        # Exact whitelist mode takes precedence over all other path rules,
        # including the always-audited authentication endpoints.
        if self.exact_included_paths and path not in self.exact_included_paths:
            return True

        path = path.lower()
        for endpoint in self.ALWAYS_LOG_ENDPOINTS:
            if path.startswith(endpoint):
                return False  # Do NOT skip logging for auth endpoints

        # Skip logging if the request is not authenticated
        # Check both Authorization header (API keys) and token cookie (browser sessions)
        if not request.headers.get('authorization') and not request.cookies.get('token'):
            return True

        if self.exact_included_paths:
            return False

        # Whitelist mode: only log paths that match included_paths
        if self._included_pattern:
            return not self._included_pattern.match(request.url.path)

        # Blacklist mode: skip paths that match excluded_paths
        if self._excluded_pattern and self._excluded_pattern.match(request.url.path):
            return True

        return False

    async def _capture_request(self, message: ASGIReceiveEvent, context: AuditContext):
        if message['type'] == 'http.request':
            body = message.get('body', b'')
            context.add_request_chunk(body)

    async def _capture_response(self, message: ASGISendEvent, context: AuditContext):
        if message['type'] == 'http.response.body':
            body = message.get('body', b'')
            context.add_response_chunk(body)

    async def _log_audit_entry(self, request: Request, context: AuditContext):
        try:
            user = await self._get_authenticated_user(request)

            user = user.model_dump(include={'id', 'name', 'email', 'role'}) if user else {}

            captures_request = self.audit_level in (AuditLevel.REQUEST, AuditLevel.REQUEST_RESPONSE)
            captures_response = self.audit_level == AuditLevel.REQUEST_RESPONSE
            request_body = _redact_body(context.request_body.decode('utf-8', errors='replace')) if captures_request else None
            response_body = _redact_body(context.response_body.decode('utf-8', errors='replace')) if captures_response else None
            request_fields = _extract_request_fields(request_body) if request_body is not None else {}
            response_fields = _extract_response_fields(response_body) if response_body is not None else {}
            request_uri = _redact_uri(str(request.url))

            entry = AuditLogEntry(
                id=str(uuid.uuid4()),
                user=user,
                audit_level=self.audit_level.value,
                verb=request.method,
                request_uri=request_uri,
                response_status_code=context.metadata.get('response_status_code', None),
                source_ip=request.client.host if request.client else None,
                user_agent=request.headers.get('user-agent'),
                request_object=request_body,
                response_object=response_body,
            )

            self.audit_logger.write(entry)

            if ENABLE_AUDIT_LOGS_DB:
                await AuditLogs.insert(
                    AuditLogCreate(
                        id=entry.id,
                        created_at=int(time.time() * 1000),
                        user_id=user.get('id') or None,
                        user_snapshot=user or None,
                        audit_level=entry.audit_level,
                        verb=entry.verb,
                        request_path=request.url.path,
                        request_uri=entry.request_uri,
                        response_status_code=entry.response_status_code,
                        source_ip=entry.source_ip,
                        user_agent=entry.user_agent,
                        request_object=request_body,
                        **request_fields,
                        response_object=response_body,
                        **response_fields,
                        request_truncated=context.request_truncated if captures_request else None,
                        response_truncated=context.response_truncated if captures_response else None,
                    )
                )
        except Exception as e:
            logger.error(f'Failed to log audit entry: {str(e)}')
