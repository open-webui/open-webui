"""OBS-04 proof of concept: audit event schema v1, validated against sample events.

Self-contained spec for docs/observability/Canchat-v2-OBS-04-Audit-Event-Schema.md; OBS-41 moves
it into observability/audit.py. Regenerate docs/observability/obs04-audit-event-v1.schema.json with
OBS04_WRITE_SCHEMA=1 pytest backend/open_webui/test/util/test_audit_event_schema_poc.py
"""

import base64
import hashlib
import hmac
import json
import os
import sys
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Literal, Optional, Union

import pytest
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    IPvAnyAddress,
    TypeAdapter,
    ValidationError,
    create_model,
    field_validator,
    model_validator,
)

SCHEMA_VERSION = "1.0"
MAX_EVENT_BYTES = 16384
MAX_IDS = 100
MAX_KEYS = 200
SCHEMA_PATH = (
    Path(__file__).resolve().parents[4]
    / "docs"
    / "observability"
    / "obs04-audit-event-v1.schema.json"
)
SCHEMA_ID = "https://canchat.ssc-spc.gc.ca/schemas/audit-event/v1.json"

# --- Bounded value types: no field accepts free text --------------------------

UUID_RE = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
Uuid = Annotated[str, Field(pattern=rf"^{UUID_RE}$")]
ModelId = Annotated[str, Field(pattern=r"^[A-Za-z0-9._:/-]{1,128}$")]
McpServerId = Annotated[
    str, Field(pattern=rf"^(?:{UUID_RE}|[a-z0-9][a-z0-9_-]{{0,63}})$")
]
Label = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9_.-]{0,63}$")]
ConfigKey = Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{0,63}$")]
PermissionKey = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_.]{0,63}$")]
CorrelationId = Annotated[str, Field(pattern=r"^[A-Za-z0-9._-]{8,64}$")]
Pseudonym = Annotated[str, Field(pattern=r"^ps1:[a-z0-9-]{1,32}:[A-Za-z0-9_-]{22}$")]
Count = Annotated[int, Field(ge=0, le=2**53 - 1)]
EpochSeconds = Annotated[int, Field(ge=0, le=2**40)]


class Outcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"
    ERROR = "error"
    CANCELLED = "cancelled"


class ActorType(str, Enum):
    USER = "user"
    ANONYMOUS = "anonymous"


class AuthMethod(str, Enum):
    PASSWORD = "password"
    LDAP = "ldap"
    OAUTH = "oauth"
    TRUSTED_HEADER = "trusted_header"
    API_KEY = "api_key"
    SESSION = "session"
    REFRESH_TOKEN = "refresh_token"


class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"
    PENDING = "pending"
    ANALYST = "analyst"
    GLOBAL_ANALYST = "global_analyst"


class RouteGuard(str, Enum):
    ADMIN = "admin"  # get_admin_user
    METRICS = "metrics"  # get_metrics_user


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class ChangeSource(str, Enum):
    MANUAL = "manual"
    OAUTH_SYNC = "oauth_sync"


class Initiator(str, Enum):
    SELF = "self"
    ADMIN = "admin"


class LoginFailureReason(str, Enum):
    INVALID_CREDENTIALS = "invalid_credentials"
    INVALID_TRUSTED_HEADER = "invalid_trusted_header"
    LDAP_ERROR = "ldap_error"
    RATE_LIMITED = "rate_limited"
    INTERNAL_ERROR = "internal_error"


class RefreshFailureReason(str, Enum):
    MISSING_REFRESH_TOKEN = "missing_refresh_token"
    INVALID_REFRESH_TOKEN = "invalid_refresh_token"
    SESSION_CONFLICT = "session_conflict"


class AccessDeniedReason(str, Enum):
    NO_ACCESS = "no_access"
    MODEL_NOT_FOUND = "model_not_found"


class UserField(str, Enum):
    NAME = "name"
    EMAIL = "email"
    PROFILE_IMAGE_URL = "profile_image_url"
    PASSWORD = "password"


class MimeGroup(str, Enum):
    PDF = "pdf"
    IMAGE = "image"
    OFFICE = "office"
    TEXT = "text"
    AUDIO = "audio"
    VIDEO = "video"
    ARCHIVE = "archive"
    OTHER = "other"


class SizeBucket(str, Enum):
    LT_1MB = "lt_1mb"
    MB_1_10 = "1mb_10mb"
    MB_10_100 = "10mb_100mb"
    GTE_100MB = "gte_100mb"


class DeleteScope(str, Enum):
    OWN = "own"
    ALL_USERS = "all_users"


class McpServerType(str, Enum):
    BUILT_IN = "built_in"
    USER_CREATED = "user_created"


class McpTransport(str, Enum):
    STDIO = "stdio"
    HTTP = "http"


class McpServerField(str, Enum):
    NAME = "name"
    DESCRIPTION = "description"
    COMMAND = "command"
    ARGS = "args"
    ENV = "env"
    TRANSPORT = "transport"
    URL = "url"
    PORT = "port"
    IS_ACTIVE = "is_active"
    CAPABILITIES = "capabilities"
    TOOLS = "tools"
    ACCESS_CONTROL = "access_control"


class Provider(str, Enum):
    OPENAI = "openai"
    OLLAMA = "ollama"
    ARENA = "arena"
    FUNCTION = "function"
    CREWAI = "crewai"
    OTHER = "other"


class ChatPath(str, Enum):
    HTTP_BACKGROUND = "http_background"
    HTTP_STREAM = "http_stream"
    HTTP_JSON = "http_json"
    CREWAI = "crewai"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# --- Envelope parts ----------------------------------------------------------


class Actor(_Strict):
    type: ActorType
    id: Optional[Uuid] = None
    role: Optional[Role] = None
    auth_method: Optional[AuthMethod] = None
    subject_pseudonym: Optional[Pseudonym] = None

    @model_validator(mode="after")
    def _identity(self):
        if self.type is ActorType.USER and self.id is None:
            raise ValueError("user actor requires id")
        if self.type is ActorType.ANONYMOUS and (self.id or self.role):
            raise ValueError("anonymous actor has no id or role")
        return self


class Correlation(_Strict):
    request_id: Optional[CorrelationId] = None
    operation_id: Optional[CorrelationId] = None
    trace_id: Optional[Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")]] = None
    span_id: Optional[Annotated[str, Field(pattern=r"^[0-9a-f]{16}$")]] = None
    session_id: Optional[Uuid] = None


class Client(_Strict):
    address: IPvAnyAddress


class Source(_Strict):
    service: Label
    version: Annotated[str, Field(pattern=r"^[0-9A-Za-z.+-]{1,32}$")]
    environment: Label


# --- Per-action details ------------------------------------------------------


class LoginFailureDetails(_Strict):
    reason: LoginFailureReason


class RefreshFailureDetails(_Strict):
    reason: RefreshFailureReason


class RoleDetails(_Strict):
    role: Role


class PasswordChangeDetails(_Strict):
    initiated_by: Initiator


class UserUpdateDetails(_Strict):
    changed_fields: Annotated[list[UserField], Field(min_length=1, max_length=4)]


class RoleChangeDetails(_Strict):
    from_role: Role
    to_role: Role
    source: ChangeSource


class OAuthLinkDetails(_Strict):
    oauth_provider: Label


class GroupChangeDetails(_Strict):
    source: ChangeSource
    member_count: Count
    member_ids_added: Annotated[list[Uuid], Field(max_length=MAX_IDS)] = []
    member_ids_removed: Annotated[list[Uuid], Field(max_length=MAX_IDS)] = []
    ids_truncated: bool = False
    permissions_changed: bool = False


class GroupDeleteDetails(_Strict):
    member_count: Count


class PermissionKeysDetails(_Strict):
    changed_keys: Annotated[
        list[PermissionKey], Field(min_length=1, max_length=MAX_KEYS)
    ]


class ConfigDetails(_Strict):
    section: Label
    keys: Annotated[list[ConfigKey], Field(min_length=1, max_length=MAX_KEYS)]


class AccessDeniedDetails(_Strict):
    reason: AccessDeniedReason


class RouteDeniedDetails(_Strict):
    guard: RouteGuard
    method: HttpMethod
    # Route template (request.scope["route"].path), never the concrete path.
    route: Annotated[str, Field(pattern=r"^/[A-Za-z0-9_{}/.-]{0,199}$")]


class FileUploadDetails(_Strict):
    mime_group: MimeGroup
    size_bucket: SizeBucket
    knowledge_id: Optional[Uuid] = None


class BulkDeleteDetails(_Strict):
    scope: DeleteScope
    count: Count


class KnowledgeFilesDetails(_Strict):
    file_ids: Annotated[list[Uuid], Field(min_length=1, max_length=MAX_IDS)]
    file_count: Count
    ids_truncated: bool = False


class KnowledgeResetDetails(_Strict):
    file_count: Count


class McpServerChangeDetails(_Strict):
    server_type: McpServerType
    transport: McpTransport
    changed_fields: Annotated[list[McpServerField], Field(max_length=12)] = []


class McpServerDetails(_Strict):
    server_type: McpServerType


class ExportDetails(_Strict):
    row_count: Count
    file_size_bytes: Count
    date_range_start: EpochSeconds
    date_range_end: EpochSeconds


class ChatMessageDetails(_Strict):
    chat_id: Uuid
    model: ModelId
    provider: Provider
    path: ChatPath
    # None means the provider did not report usage; never a measured zero.
    prompt_tokens: Optional[Count] = None
    completion_tokens: Optional[Count] = None
    total_tokens: Optional[Count] = None
    has_files: bool
    web_search: bool
    has_knowledge: bool
    has_tools: bool
    mcp_tool: Optional[Label] = None


class ChatShareDetails(_Strict):
    share_id: Optional[Uuid] = None


# --- Action catalogue --------------------------------------------------------


class FailMode(str, Enum):
    CLOSED = "closed"  # blocks under every policy
    OPEN = "open"  # blocks only under block_all
    NEVER_BLOCK = "never_block"  # refusals, logout and post-response chat records


class AuditFailPolicy(str, Enum):
    BLOCK_PRIVILEGED = "block_privileged"
    BLOCK_ALL = "block_all"


@dataclass(frozen=True)
class ActionSpec:
    category: str
    target: Optional[str]
    details: Optional[type[BaseModel]]
    fail_mode: FailMode
    outcomes: frozenset = frozenset({Outcome.SUCCESS})
    actors: frozenset = frozenset({ActorType.USER})
    target_optional: bool = False


_C, _O, _N = FailMode.CLOSED, FailMode.OPEN, FailMode.NEVER_BLOCK
_ANON = frozenset({ActorType.ANONYMOUS})
_ANY = frozenset({ActorType.USER, ActorType.ANONYMOUS})

CATALOGUE: dict[str, ActionSpec] = {
    # auth
    "login.success": ActionSpec("auth", "user", None, _O),
    "login.failure": ActionSpec(
        "auth",
        "user",
        LoginFailureDetails,
        _N,
        outcomes=frozenset({Outcome.FAILURE}),
        actors=_ANON,
        target_optional=True,
    ),
    "logout": ActionSpec("auth", None, None, _N),
    "token.refresh.failure": ActionSpec(
        "auth",
        None,
        RefreshFailureDetails,
        _N,
        outcomes=frozenset({Outcome.FAILURE}),
        actors=_ANY,
    ),
    "signup": ActionSpec("auth", "user", RoleDetails, _C),
    "password.change": ActionSpec("auth", "user", PasswordChangeDetails, _C),
    "api_key.create": ActionSpec("auth", "user", None, _C),
    "api_key.delete": ActionSpec("auth", "user", None, _C),
    # admin
    "user.create": ActionSpec("admin", "user", RoleDetails, _C),
    "user.update": ActionSpec("admin", "user", UserUpdateDetails, _C),
    "user.role_change": ActionSpec("admin", "user", RoleChangeDetails, _C),
    "user.delete": ActionSpec("admin", "user", None, _C),
    "user.oauth_link": ActionSpec("admin", "user", OAuthLinkDetails, _C),
    "group.create": ActionSpec("admin", "group", GroupChangeDetails, _C),
    "group.update": ActionSpec("admin", "group", GroupChangeDetails, _C),
    "group.delete": ActionSpec("admin", "group", GroupDeleteDetails, _C),
    "permissions.default_update": ActionSpec(
        "admin", "permissions", PermissionKeysDetails, _C
    ),
    "config.update": ActionSpec("admin", "config", ConfigDetails, _C),
    "config.import": ActionSpec("admin", "config", ConfigDetails, _C),
    "domain.create": ActionSpec("admin", "domain", None, _C),
    "domain.update": ActionSpec("admin", "domain", None, _C),
    "domain.delete": ActionSpec("admin", "domain", None, _C),
    # access
    "model.denied": ActionSpec(
        "access",
        "model",
        AccessDeniedDetails,
        _N,
        outcomes=frozenset({Outcome.DENIED}),
    ),
    "admin_route.denied": ActionSpec(
        "access",
        None,
        RouteDeniedDetails,
        _N,
        outcomes=frozenset({Outcome.DENIED}),
    ),
    # resource
    "file.upload": ActionSpec("resource", "file", FileUploadDetails, _C),
    "file.update": ActionSpec("resource", "file", None, _C),
    "file.delete": ActionSpec("resource", "file", None, _C),
    "file.delete_all": ActionSpec("resource", None, BulkDeleteDetails, _C),
    "knowledge.create": ActionSpec("resource", "knowledge", None, _C),
    "knowledge.update": ActionSpec("resource", "knowledge", None, _C),
    "knowledge.delete": ActionSpec("resource", "knowledge", None, _C),
    "knowledge.delete_all": ActionSpec("resource", None, BulkDeleteDetails, _C),
    "knowledge.file_add": ActionSpec(
        "resource", "knowledge", KnowledgeFilesDetails, _C
    ),
    "knowledge.file_remove": ActionSpec(
        "resource", "knowledge", KnowledgeFilesDetails, _C
    ),
    "knowledge.reset": ActionSpec("resource", "knowledge", KnowledgeResetDetails, _C),
    # mcp
    "mcp_server.create": ActionSpec("mcp", "mcp_server", McpServerChangeDetails, _C),
    "mcp_server.update": ActionSpec("mcp", "mcp_server", McpServerChangeDetails, _C),
    "mcp_server.delete": ActionSpec("mcp", "mcp_server", McpServerDetails, _C),
    "mcp_server.start": ActionSpec("mcp", "mcp_server", McpServerDetails, _C),
    "mcp_server.stop": ActionSpec("mcp", "mcp_server", McpServerDetails, _C),
    "mcp_server.restart": ActionSpec("mcp", "mcp_server", McpServerDetails, _C),
    "mcp.config_update": ActionSpec("mcp", "config", ConfigDetails, _C),
    # export
    "metrics.export": ActionSpec("export", "export", ExportDetails, _C),
    # chat
    "message": ActionSpec(
        "chat",
        "message",
        ChatMessageDetails,
        # Written after the reply is sent; a pre-call circuit breaker is deferred.
        _N,
        outcomes=frozenset({Outcome.SUCCESS, Outcome.ERROR, Outcome.CANCELLED}),
    ),
    "chat.share": ActionSpec("chat", "chat", ChatShareDetails, _C),
    "chat.unshare": ActionSpec("chat", "chat", ChatShareDetails, _C),
}

CATEGORIES = ("auth", "admin", "access", "resource", "mcp", "export", "chat")
CLIENT_CATEGORIES = {"auth", "access"}
AUTH_METHOD_ACTIONS = {"login.success", "login.failure", "signup"}

TARGET_IDS: dict[str, Any] = {
    "user": Uuid,
    "group": Uuid,
    "domain": Uuid,
    "file": Uuid,
    "knowledge": Uuid,
    "chat": Uuid,
    "message": Uuid,
    "export": Uuid,
    "model": ModelId,
    "mcp_server": McpServerId,
    "config": None,
    "permissions": None,
}


def _target_model(target_type: str) -> type[BaseModel]:
    fields: dict[str, Any] = {"type": (Literal[target_type], ...)}
    if TARGET_IDS[target_type] is not None:
        fields["id"] = (TARGET_IDS[target_type], ...)
    return create_model(f"Target_{target_type}", __base__=_Strict, **fields)


TARGETS = {t: _target_model(t) for t in TARGET_IDS}


class _EventBase(_Strict):
    event_id: uuid.UUID
    schema_version: Literal["1.0"]
    time: datetime
    outcome: Outcome
    actor: Actor
    correlation: Correlation = Field(default_factory=Correlation)
    client: Optional[Client] = None
    source: Source

    @field_validator("time")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != timedelta(0):
            raise ValueError("time must be timezone-aware UTC")
        return value

    @model_validator(mode="after")
    def _action_rules(self):
        action = getattr(self, "action")
        spec = CATALOGUE[action]
        if self.outcome not in spec.outcomes:
            raise ValueError(f"outcome {self.outcome.value} not allowed for {action}")
        if self.actor.type not in spec.actors:
            raise ValueError(
                f"actor type {self.actor.type.value} not allowed for {action}"
            )
        if (self.actor.subject_pseudonym is not None) != (action == "login.failure"):
            raise ValueError(
                "subject_pseudonym is required for, and only for, login.failure"
            )
        if (self.actor.auth_method is not None) != (action in AUTH_METHOD_ACTIONS):
            raise ValueError("auth_method is required for, and only for, login/signup")
        if self.client is not None and spec.category not in CLIENT_CATEGORIES:
            raise ValueError("client is only recorded for auth and access events")
        if len(self.model_dump_json().encode()) > MAX_EVENT_BYTES:
            raise ValueError(f"event exceeds {MAX_EVENT_BYTES} bytes")
        return self


def _event_model(action: str, spec: ActionSpec) -> type[BaseModel]:
    fields: dict[str, Any] = {
        "category": (Literal[spec.category], ...),
        "action": (Literal[action], ...),
    }
    if spec.target is not None:
        target = TARGETS[spec.target]
        fields["target"] = (
            (Optional[target], None) if spec.target_optional else (target, ...)
        )
    if spec.details is not None:
        fields["details"] = (spec.details, ...)
    name = "AuditEvent_" + action.replace(".", "_")
    return create_model(name, __base__=_EventBase, **fields)


EVENT_MODELS = {
    action: _event_model(action, spec) for action, spec in CATALOGUE.items()
}
AuditEventV1 = TypeAdapter(
    Annotated[Union[tuple(EVENT_MODELS.values())], Field(discriminator="action")]
)


def json_schema() -> dict:
    schema = AuditEventV1.json_schema()
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": SCHEMA_ID,
        "title": f"CANChat audit event v{SCHEMA_VERSION}",
        **schema,
    }


# --- Failure policy and pseudonymization --------------------------------------


def audit_failure_blocks(action: str, policy: AuditFailPolicy) -> bool:
    mode = CATALOGUE[action].fail_mode
    if mode is FailMode.CLOSED:
        return True
    if mode is FailMode.NEVER_BLOCK:
        return False
    return policy is AuditFailPolicy.BLOCK_ALL


def pseudonymize(identifier: str, key: bytes, key_id: str) -> str:
    if len(key) < 32:
        raise ValueError("pseudonym key must be at least 256 bits")
    normalized = unicodedata.normalize("NFKC", identifier).strip().casefold()
    digest = hmac.new(key, normalized.encode("utf-8"), hashlib.sha256).digest()[:16]
    return f"ps1:{key_id}:{base64.urlsafe_b64encode(digest).rstrip(b'=').decode()}"


# --- Sample events -----------------------------------------------------------

KEY_2026 = bytes(range(32))
KEY_2027 = bytes(range(32, 64))
USER_ID = "3f2b8a1e-6c4d-4e8f-9a0b-1c2d3e4f5a6b"
OTHER_ID = "7d9e0f1a-2b3c-4d5e-8f6a-7b8c9d0e1f2a"
CHAT_ID = "0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d"


def _uuid() -> str:
    return str(uuid.uuid4())


def _base(action: str, **overrides) -> dict:
    spec = CATALOGUE[action]
    event = {
        "event_id": _uuid(),
        "schema_version": SCHEMA_VERSION,
        "time": "2026-10-08T14:03:12.481Z",
        "category": spec.category,
        "action": action,
        "outcome": sorted(o.value for o in spec.outcomes)[0],
        "actor": {"type": "user", "id": USER_ID, "role": "admin"},
        "correlation": {
            "request_id": "b6f1d2c3e4a5",
            "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
            "span_id": "00f067aa0ba902b7",
        },
        "source": {
            "service": "canchat-backend",
            "version": "2.4.1",
            "environment": "prod",
        },
    }
    if spec.target is not None and TARGET_IDS[spec.target] in (Uuid, McpServerId):
        event["target"] = {"type": spec.target, "id": OTHER_ID}
    elif spec.target is not None and TARGET_IDS[spec.target] is None:
        event["target"] = {"type": spec.target}
    event.update(overrides)
    return event


_CONFIG = {"section": "retrieval", "keys": ["RAG_TOP_K", "CHUNK_SIZE"]}
_MCP = {
    "server_type": "user_created",
    "transport": "http",
    "changed_fields": ["url", "env"],
}

SAMPLES: dict[str, dict] = {
    "login.success": _base(
        "login.success",
        actor={
            "type": "user",
            "id": USER_ID,
            "role": "user",
            "auth_method": "password",
        },
        target={"type": "user", "id": USER_ID},
        client={"address": "10.20.30.40"},
    ),
    "login.failure": _base(
        "login.failure",
        actor={
            "type": "anonymous",
            "auth_method": "ldap",
            "subject_pseudonym": pseudonymize(
                "Jane.Doe@ssc-spc.gc.ca", KEY_2026, "k2026a"
            ),
        },
        target={"type": "user", "id": USER_ID},
        details={"reason": "invalid_credentials"},
        client={"address": "2001:db8::1"},
    ),
    "logout": _base("logout", correlation={"session_id": _uuid()}),
    "token.refresh.failure": _base(
        "token.refresh.failure",
        actor={"type": "anonymous"},
        details={"reason": "invalid_refresh_token"},
    ),
    "signup": _base(
        "signup",
        actor={
            "type": "user",
            "id": USER_ID,
            "role": "pending",
            "auth_method": "oauth",
        },
        target={"type": "user", "id": USER_ID},
        details={"role": "pending"},
    ),
    "password.change": _base("password.change", details={"initiated_by": "admin"}),
    "api_key.create": _base("api_key.create", target={"type": "user", "id": USER_ID}),
    "api_key.delete": _base("api_key.delete", target={"type": "user", "id": USER_ID}),
    "user.create": _base("user.create", details={"role": "user"}),
    "user.update": _base(
        "user.update", details={"changed_fields": ["email", "password"]}
    ),
    "user.role_change": _base(
        "user.role_change",
        details={"from_role": "pending", "to_role": "user", "source": "manual"},
    ),
    "user.delete": _base("user.delete"),
    "user.oauth_link": _base(
        "user.oauth_link", details={"oauth_provider": "microsoft"}
    ),
    "group.create": _base(
        "group.create",
        details={"source": "manual", "member_count": 1, "member_ids_added": [USER_ID]},
    ),
    "group.update": _base(
        "group.update",
        details={
            "source": "oauth_sync",
            "member_count": 140,
            "member_ids_added": [_uuid() for _ in range(MAX_IDS)],
            "ids_truncated": True,
            "permissions_changed": True,
        },
    ),
    "group.delete": _base("group.delete", details={"member_count": 12}),
    "permissions.default_update": _base(
        "permissions.default_update",
        details={"changed_keys": ["chat.file_upload", "workspace.knowledge"]},
    ),
    "config.update": _base("config.update", details=_CONFIG),
    "config.import": _base(
        "config.import",
        details={"section": "configs", "keys": [f"KEY_{i}" for i in range(MAX_KEYS)]},
    ),
    "domain.create": _base("domain.create"),
    "domain.update": _base("domain.update"),
    "domain.delete": _base("domain.delete"),
    "model.denied": _base(
        "model.denied",
        actor={"type": "user", "id": USER_ID, "role": "user"},
        target={"type": "model", "id": "azure/gpt-4o-mini"},
        details={"reason": "no_access"},
        client={"address": "10.20.30.40"},
    ),
    "admin_route.denied": _base(
        "admin_route.denied",
        actor={"type": "user", "id": USER_ID, "role": "analyst"},
        details={
            "guard": "admin",
            "method": "POST",
            "route": "/api/v1/users/{user_id}/update",
        },
        client={"address": "10.20.30.40"},
    ),
    "file.upload": _base(
        "file.upload",
        details={
            "mime_group": "pdf",
            "size_bucket": "1mb_10mb",
            "knowledge_id": _uuid(),
        },
    ),
    "file.update": _base("file.update"),
    "file.delete": _base("file.delete"),
    "file.delete_all": _base(
        "file.delete_all", details={"scope": "all_users", "count": 42}
    ),
    "knowledge.create": _base("knowledge.create"),
    "knowledge.update": _base("knowledge.update"),
    "knowledge.delete": _base("knowledge.delete"),
    "knowledge.delete_all": _base(
        "knowledge.delete_all", details={"scope": "all_users", "count": 3}
    ),
    "knowledge.file_add": _base(
        "knowledge.file_add", details={"file_ids": [_uuid()], "file_count": 1}
    ),
    "knowledge.file_remove": _base(
        "knowledge.file_remove", details={"file_ids": [_uuid()], "file_count": 1}
    ),
    "knowledge.reset": _base("knowledge.reset", details={"file_count": 7}),
    "mcp_server.create": _base("mcp_server.create", details=_MCP),
    "mcp_server.update": _base("mcp_server.update", details=_MCP),
    "mcp_server.delete": _base(
        "mcp_server.delete", details={"server_type": "user_created"}
    ),
    "mcp_server.start": _base(
        "mcp_server.start", details={"server_type": "user_created"}
    ),
    "mcp_server.stop": _base(
        "mcp_server.stop", details={"server_type": "user_created"}
    ),
    "mcp_server.restart": _base(
        "mcp_server.restart",
        target={"type": "mcp_server", "id": "news"},
        details={"server_type": "built_in"},
    ),
    "mcp.config_update": _base(
        "mcp.config_update", details={"section": "mcp", "keys": ["MCP_SERVER_URLS"]}
    ),
    "metrics.export": _base(
        "metrics.export",
        details={
            "row_count": 1200,
            "file_size_bytes": 88412,
            "date_range_start": 1788220800,
            "date_range_end": 1790812800,
        },
    ),
    "message": _base(
        "message",
        actor={"type": "user", "id": USER_ID, "role": "user"},
        correlation={"operation_id": "op-3c1f9a2e7b", "request_id": "b6f1d2c3e4a5"},
        details={
            "chat_id": CHAT_ID,
            "model": "azure/gpt-4o-mini",
            "provider": "openai",
            "path": "http_background",
            "prompt_tokens": 812,
            "completion_tokens": 240,
            "total_tokens": 1052,
            "has_files": True,
            "web_search": False,
            "has_knowledge": True,
            "has_tools": False,
        },
    ),
    "chat.share": _base(
        "chat.share",
        actor={"type": "user", "id": USER_ID, "role": "user"},
        target={"type": "chat", "id": CHAT_ID},
        details={"share_id": _uuid()},
    ),
    "chat.unshare": _base(
        "chat.unshare",
        actor={"type": "user", "id": USER_ID, "role": "user"},
        target={"type": "chat", "id": CHAT_ID},
        details={},
    ),
}

FORBIDDEN_KEYS = {
    "email",
    "user_email",
    "name",
    "user_name",
    "first_name",
    "last_name",
    "username",
    "display_name",
    "password",
    "new_password",
    "password_hash",
    "token",
    "access_token",
    "refresh_token",
    "id_token",
    "api_key",
    "secret",
    "client_secret",
    "authorization",
    "cookie",
    "prompt",
    "response",
    "content",
    "messages",
    "text",
    "query",
    "title",
    "filename",
    "file_name",
    "description",
    "env",
    "args",
    "command",
    "url",
    "value",
    "old_value",
    "new_value",
    "user_agent",
    "user_domain",
    "email_domain",
}


def _validate(event: dict):
    return AuditEventV1.validate_python(event)


def _with(action: str, path: tuple[str, ...], value: Any) -> dict:
    event = json.loads(json.dumps(SAMPLES[action]))
    node = event
    for key in path[:-1]:
        node = node.setdefault(key, {})
    node[path[-1]] = value
    return event


# --- Tests -------------------------------------------------------------------


def test_every_action_and_category_has_a_sample():
    assert set(SAMPLES) == set(CATALOGUE)
    assert {spec.category for spec in CATALOGUE.values()} == set(CATEGORIES)


@pytest.mark.parametrize("action", sorted(CATALOGUE))
def test_sample_event_validates_and_round_trips(action):
    event = _validate(SAMPLES[action])
    assert event.action == action
    dumped = json.loads(event.model_dump_json(exclude_none=True))
    assert dumped["time"].endswith("Z")
    assert _validate(dumped) == event


def test_schema_declares_no_forbidden_property():
    found: set[str] = set()

    def walk(node):
        if isinstance(node, dict):
            found.update(node.get("properties", {}).keys())
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(json_schema())
    assert found and not (found & FORBIDDEN_KEYS)


@pytest.mark.parametrize("key", sorted(FORBIDDEN_KEYS))
@pytest.mark.parametrize(
    "where", [(), ("details",), ("target",), ("actor",), ("correlation",)]
)
def test_forbidden_fields_rejected(key, where):
    with pytest.raises(ValidationError):
        _validate(_with("user.update", (*where, key), "jane.doe@ssc-spc.gc.ca"))


@pytest.mark.parametrize(
    "action, path, value",
    [
        ("user.delete", ("target", "id"), "jane.doe@ssc-spc.gc.ca"),
        ("user.delete", ("target", "id"), "Jane Doe"),
        ("user.delete", ("actor", "id"), "jane.doe"),
        ("model.denied", ("target", "id"), "summarize my medical file"),
        ("model.denied", ("target", "id"), "jane@ssc-spc.gc.ca"),
        ("config.update", ("details", "keys"), ["OPENAI_API_KEY=sk-123"]),
        ("config.update", ("details", "section"), "Retrieval settings"),
        ("message", ("details", "mcp_tool"), "Jane's SharePoint"),
        ("message", ("correlation", "request_id"), "<script>alert(1)</script>"),
        ("login.failure", ("actor", "subject_pseudonym"), "jane.doe@ssc-spc.gc.ca"),
        ("admin_route.denied", ("details", "route"), "/api/v1/search?q=my secret"),
        ("admin_route.denied", ("details", "route"), "users/{user_id}"),
    ],
)
def test_free_text_and_identifiers_rejected(action, path, value):
    with pytest.raises(ValidationError):
        _validate(_with(action, path, value))


@pytest.mark.parametrize(
    "action, path, value",
    [
        ("user.delete", ("action",), "user.purge"),
        ("user.delete", ("category",), "auth"),
        ("user.delete", ("schema_version",), "2.0"),
        ("user.delete", ("target", "type"), "group"),
        ("user.delete", ("time",), "2026-10-08T10:03:12"),
        ("user.delete", ("time",), "2026-10-08T10:03:12-04:00"),
        ("user.delete", ("outcome",), "failure"),
        ("user.delete", ("actor",), {"type": "anonymous"}),
        ("user.delete", ("client",), {"address": "10.0.0.1"}),
        ("user.delete", ("actor", "auth_method"), "password"),
        ("login.success", ("actor", "auth_method"), None),
        ("login.failure", ("actor", "subject_pseudonym"), None),
        (
            "login.failure",
            ("actor",),
            {"type": "user", "id": USER_ID, "auth_method": "password"},
        ),
        ("model.denied", ("outcome",), "success"),
        ("message", ("details", "prompt_tokens"), -1),
        ("knowledge.file_add", ("details", "file_ids"), []),
        ("group.update", ("details", "member_ids_removed"), [OTHER_ID] * (MAX_IDS + 1)),
        ("config.update", ("details", "keys"), ["K"] * (MAX_KEYS + 1)),
    ],
)
def test_envelope_and_action_rules(action, path, value):
    with pytest.raises(ValidationError):
        _validate(_with(action, path, value))


def test_unknown_token_usage_is_not_zero():
    event = _validate(
        _with(
            "message",
            ("details",),
            {**SAMPLES["message"]["details"], "prompt_tokens": None},
        )
    )
    assert event.details.prompt_tokens is None


def test_largest_valid_events_fit_and_size_limit_is_enforced(monkeypatch):
    largest = [
        _with(
            "group.update",
            ("details", "member_ids_removed"),
            [_uuid() for _ in range(MAX_IDS)],
        ),
        _with("config.import", ("details", "keys"), ["A" + "B" * 63] * MAX_KEYS),
    ]
    for event in largest:
        _validate(event)
    # Field bounds keep valid events under the limit; the byte check is a backstop.
    monkeypatch.setattr(sys.modules[__name__], "MAX_EVENT_BYTES", 4096)
    for event in largest:
        with pytest.raises(ValidationError, match="exceeds"):
            _validate(event)


def test_pseudonym_is_stable_normalized_and_rotates():
    p1 = pseudonymize("Jane.Doe@ssc-spc.gc.ca", KEY_2026, "k2026a")
    assert p1 == pseudonymize("  jane.doe@SSC-SPC.GC.CA ", KEY_2026, "k2026a")
    assert p1 != pseudonymize("john.doe@ssc-spc.gc.ca", KEY_2026, "k2026a")
    p2 = pseudonymize("Jane.Doe@ssc-spc.gc.ca", KEY_2027, "k2027a")
    assert p1.split(":")[2] != p2.split(":")[2]
    assert p1.startswith("ps1:k2026a:") and "jane" not in p1.lower()
    with pytest.raises(ValueError):
        pseudonymize("jane", b"short", "k")


EXPECTED_BLOCKING = {
    # action: (block_privileged, block_all)
    "login.success": (False, True),
    "message": (False, False),
    "login.failure": (False, False),
    "admin_route.denied": (False, False),
    "token.refresh.failure": (False, False),
    "logout": (False, False),
    "model.denied": (False, False),
}


@pytest.mark.parametrize("action", sorted(CATALOGUE))
def test_fail_policy(action):
    expected = EXPECTED_BLOCKING.get(action, (True, True))
    actual = (
        audit_failure_blocks(action, AuditFailPolicy.BLOCK_PRIVILEGED),
        audit_failure_blocks(action, AuditFailPolicy.BLOCK_ALL),
    )
    assert actual == expected


def test_checked_in_json_schema_is_current():
    generated = json_schema()
    if os.environ.get("OBS04_WRITE_SCHEMA") == "1":
        SCHEMA_PATH.write_text(json.dumps(generated, indent=2, sort_keys=True) + "\n")
    assert json.loads(SCHEMA_PATH.read_text()) == generated
