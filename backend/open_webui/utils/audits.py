from contextlib import asynccontextmanager
from pprint import pp as pprint
from typing import Any, AsyncGenerator, Dict, Mapping, MutableMapping, Optional, cast
import uuid

from asgiref.typing import (
    ASGI3Application,
    ASGIReceiveCallable,
    ASGIReceiveEvent,
    ASGISendCallable,
    ASGISendEvent,
    HTTPRequestEvent,
    HTTPScope,
    Scope as ASGIScope,
)
from fastapi.datastructures import Headers
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
