import common_pb2 as _common_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class JoinFaceMonitorRequest(_message.Message):
    __slots__ = ("face_monitor_token", "session_id")
    FACE_MONITOR_TOKEN_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    face_monitor_token: str
    session_id: str
    def __init__(self, face_monitor_token: _Optional[str] = ..., session_id: _Optional[str] = ...) -> None: ...

class JoinFaceMonitorResponse(_message.Message):
    __slots__ = ("status",)
    STATUS_FIELD_NUMBER: _ClassVar[int]
    status: Status
    def __init__(self, status: _Optional[_Union[Status, _Mapping]] = ...) -> None: ...

class FaceMonitorCallbackRequest(_message.Message):
    __slots__ = ("token", "success", "error_message", "is_finished", "action", "face_codes")
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    IS_FINISHED_FIELD_NUMBER: _ClassVar[int]
    ACTION_FIELD_NUMBER: _ClassVar[int]
    FACE_CODES_FIELD_NUMBER: _ClassVar[int]
    token: str
    success: bool
    error_message: str
    is_finished: bool
    action: str
    face_codes: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, token: _Optional[str] = ..., success: bool = ..., error_message: _Optional[str] = ..., is_finished: bool = ..., action: _Optional[str] = ..., face_codes: _Optional[_Iterable[str]] = ...) -> None: ...

class FaceMonitorCallbackResponse(_message.Message):
    __slots__ = ("status",)
    STATUS_FIELD_NUMBER: _ClassVar[int]
    status: Status
    def __init__(self, status: _Optional[_Union[Status, _Mapping]] = ...) -> None: ...

class FaceRecognitionCallbackRequest(_message.Message):
    __slots__ = ("token", "success", "error_message", "face_code")
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    FACE_CODE_FIELD_NUMBER: _ClassVar[int]
    token: str
    success: bool
    error_message: str
    face_code: str
    def __init__(self, token: _Optional[str] = ..., success: bool = ..., error_message: _Optional[str] = ..., face_code: _Optional[str] = ...) -> None: ...

class FaceRecognitionCallbackResponse(_message.Message):
    __slots__ = ("status",)
    STATUS_FIELD_NUMBER: _ClassVar[int]
    status: Status
    def __init__(self, status: _Optional[_Union[Status, _Mapping]] = ...) -> None: ...

class AssetLoginTicketRequest(_message.Message):
    __slots__ = ("user_id", "asset_id", "account_username")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    ASSET_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_USERNAME_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    asset_id: str
    account_username: str
    def __init__(self, user_id: _Optional[str] = ..., asset_id: _Optional[str] = ..., account_username: _Optional[str] = ...) -> None: ...

class AssetLoginTicketResponse(_message.Message):
    __slots__ = ("status", "ticket_info", "need_confirm", "ticket_id")
    STATUS_FIELD_NUMBER: _ClassVar[int]
    TICKET_INFO_FIELD_NUMBER: _ClassVar[int]
    NEED_CONFIRM_FIELD_NUMBER: _ClassVar[int]
    TICKET_ID_FIELD_NUMBER: _ClassVar[int]
    status: Status
    ticket_info: TicketInfo
    need_confirm: bool
    ticket_id: str
    def __init__(self, status: _Optional[_Union[Status, _Mapping]] = ..., ticket_info: _Optional[_Union[TicketInfo, _Mapping]] = ..., need_confirm: bool = ..., ticket_id: _Optional[str] = ...) -> None: ...

class Status(_message.Message):
    __slots__ = ("ok", "err")
    OK_FIELD_NUMBER: _ClassVar[int]
    ERR_FIELD_NUMBER: _ClassVar[int]
    ok: bool
    err: str
    def __init__(self, ok: bool = ..., err: _Optional[str] = ...) -> None: ...

class TokenRequest(_message.Message):
    __slots__ = ("token",)
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    token: str
    def __init__(self, token: _Optional[str] = ...) -> None: ...

class TokenResponse(_message.Message):
    __slots__ = ("status", "data")
    STATUS_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    status: Status
    data: _common_pb2.TokenAuthInfo
    def __init__(self, status: _Optional[_Union[Status, _Mapping]] = ..., data: _Optional[_Union[_common_pb2.TokenAuthInfo, _Mapping]] = ...) -> None: ...

class SessionCreateRequest(_message.Message):
    __slots__ = ("data",)
    DATA_FIELD_NUMBER: _ClassVar[int]
    data: _common_pb2.Session
    def __init__(self, data: _Optional[_Union[_common_pb2.Session, _Mapping]] = ...) -> None: ...

class SessionCreateResponse(_message.Message):
    __slots__ = ("status", "data")
    STATUS_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    status: Status
    data: _common_pb2.Session
    def __init__(self, status: _Optional[_Union[Status, _Mapping]] = ..., data: _Optional[_Union[_common_pb2.Session, _Mapping]] = ...) -> None: ...

class SessionFinishRequest(_message.Message):
    __slots__ = ("id", "success", "date_end", "err")
    ID_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    DATE_END_FIELD_NUMBER: _ClassVar[int]
    ERR_FIELD_NUMBER: _ClassVar[int]
    id: str
    success: bool
    date_end: int
    err: str
    def __init__(self, id: _Optional[str] = ..., success: bool = ..., date_end: _Optional[int] = ..., err: _Optional[str] = ...) -> None: ...

class SessionFinishResp(_message.Message):
    __slots__ = ("status",)
    STATUS_FIELD_NUMBER: _ClassVar[int]
    status: Status
    def __init__(self, status: _Optional[_Union[Status, _Mapping]] = ...) -> None: ...

class ReplayRequest(_message.Message):
    __slots__ = ("session_id", "replay_file_path")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    REPLAY_FILE_PATH_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    replay_file_path: str
    def __init__(self, session_id: _Optional[str] = ..., replay_file_path: _Optional[str] = ...) -> None: ...

class ReplayResponse(_message.Message):
    __slots__ = ("status",)
    STATUS_FIELD_NUMBER: _ClassVar[int]
    status: Status
    def __init__(self, status: _Optional[_Union[Status, _Mapping]] = ...) -> None: ...

class CommandRequest(_message.Message):
    __slots__ = ("sid", "org_id", "input", "output", "user", "asset", "account", "timestamp", "risk_level", "cmd_acl_id", "cmd_group_id")
    SID_FIELD_NUMBER: _ClassVar[int]
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    INPUT_FIELD_NUMBER: _ClassVar[int]
    OUTPUT_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    ASSET_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    RISK_LEVEL_FIELD_NUMBER: _ClassVar[int]
    CMD_ACL_ID_FIELD_NUMBER: _ClassVar[int]
    CMD_GROUP_ID_FIELD_NUMBER: _ClassVar[int]
    sid: str
    org_id: str
    input: str
    output: str
    user: str
    asset: str
    account: str
    timestamp: int
    risk_level: _common_pb2.RiskLevel
    cmd_acl_id: str
    cmd_group_id: str
    def __init__(self, sid: _Optional[str] = ..., org_id: _Optional[str] = ..., input: _Optional[str] = ..., output: _Optional[str] = ..., user: _Optional[str] = ..., asset: _Optional[str] = ..., account: _Optional[str] = ..., timestamp: _Optional[int] = ..., risk_level: _Optional[_Union[_common_pb2.RiskLevel, str]] = ..., cmd_acl_id: _Optional[str] = ..., cmd_group_id: _Optional[str] = ...) -> None: ...

class CommandResponse(_message.Message):
    __slots__ = ("status",)
    STATUS_FIELD_NUMBER: _ClassVar[int]
    status: Status
    def __init__(self, status: _Optional[_Union[Status, _Mapping]] = ...) -> None: ...

class FinishedTaskRequest(_message.Message):
    __slots__ = ("task_id",)
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    def __init__(self, task_id: _Optional[str] = ...) -> None: ...

class TaskResponse(_message.Message):
    __slots__ = ("task",)
    TASK_FIELD_NUMBER: _ClassVar[int]
    task: _common_pb2.TerminalTask
    def __init__(self, task: _Optional[_Union[_common_pb2.TerminalTask, _Mapping]] = ...) -> None: ...

class RemainReplayRequest(_message.Message):
    __slots__ = ("replay_dir",)
    REPLAY_DIR_FIELD_NUMBER: _ClassVar[int]
    replay_dir: str
    def __init__(self, replay_dir: _Optional[str] = ...) -> None: ...

class RemainReplayResponse(_message.Message):
    __slots__ = ("status", "success_files", "failure_files", "failure_errs")
    STATUS_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FILES_FIELD_NUMBER: _ClassVar[int]
    FAILURE_FILES_FIELD_NUMBER: _ClassVar[int]
    FAILURE_ERRS_FIELD_NUMBER: _ClassVar[int]
    status: Status
    success_files: _containers.RepeatedScalarFieldContainer[str]
    failure_files: _containers.RepeatedScalarFieldContainer[str]
    failure_errs: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, status: _Optional[_Union[Status, _Mapping]] = ..., success_files: _Optional[_Iterable[str]] = ..., failure_files: _Optional[_Iterable[str]] = ..., failure_errs: _Optional[_Iterable[str]] = ...) -> None: ...

class StatusResponse(_message.Message):
    __slots__ = ("status",)
    STATUS_FIELD_NUMBER: _ClassVar[int]
    status: Status
    def __init__(self, status: _Optional[_Union[Status, _Mapping]] = ...) -> None: ...

class CommandConfirmRequest(_message.Message):
    __slots__ = ("session_id", "cmd_acl_id", "cmd")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    CMD_ACL_ID_FIELD_NUMBER: _ClassVar[int]
    CMD_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    cmd_acl_id: str
    cmd: str
    def __init__(self, session_id: _Optional[str] = ..., cmd_acl_id: _Optional[str] = ..., cmd: _Optional[str] = ...) -> None: ...

class ReqInfo(_message.Message):
    __slots__ = ("method", "url")
    METHOD_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    method: str
    url: str
    def __init__(self, method: _Optional[str] = ..., url: _Optional[str] = ...) -> None: ...

class CommandConfirmResponse(_message.Message):
    __slots__ = ("status", "info")
    STATUS_FIELD_NUMBER: _ClassVar[int]
    INFO_FIELD_NUMBER: _ClassVar[int]
    status: Status
    info: TicketInfo
    def __init__(self, status: _Optional[_Union[Status, _Mapping]] = ..., info: _Optional[_Union[TicketInfo, _Mapping]] = ...) -> None: ...

class TicketInfo(_message.Message):
    __slots__ = ("check_req", "cancel_req", "ticket_detail_url", "reviewers")
    CHECK_REQ_FIELD_NUMBER: _ClassVar[int]
    CANCEL_REQ_FIELD_NUMBER: _ClassVar[int]
    TICKET_DETAIL_URL_FIELD_NUMBER: _ClassVar[int]
    REVIEWERS_FIELD_NUMBER: _ClassVar[int]
    check_req: ReqInfo
    cancel_req: ReqInfo
    ticket_detail_url: str
    reviewers: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, check_req: _Optional[_Union[ReqInfo, _Mapping]] = ..., cancel_req: _Optional[_Union[ReqInfo, _Mapping]] = ..., ticket_detail_url: _Optional[str] = ..., reviewers: _Optional[_Iterable[str]] = ...) -> None: ...

class TicketRequest(_message.Message):
    __slots__ = ("req",)
    REQ_FIELD_NUMBER: _ClassVar[int]
    req: ReqInfo
    def __init__(self, req: _Optional[_Union[ReqInfo, _Mapping]] = ...) -> None: ...

class TicketStateResponse(_message.Message):
    __slots__ = ("Data", "status")
    DATA_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    Data: TicketState
    status: Status
    def __init__(self, Data: _Optional[_Union[TicketState, _Mapping]] = ..., status: _Optional[_Union[Status, _Mapping]] = ...) -> None: ...

class TicketState(_message.Message):
    __slots__ = ("state", "processor")
    class State(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        Open: _ClassVar[TicketState.State]
        Approved: _ClassVar[TicketState.State]
        Rejected: _ClassVar[TicketState.State]
        Closed: _ClassVar[TicketState.State]
    Open: TicketState.State
    Approved: TicketState.State
    Rejected: TicketState.State
    Closed: TicketState.State
    STATE_FIELD_NUMBER: _ClassVar[int]
    PROCESSOR_FIELD_NUMBER: _ClassVar[int]
    state: TicketState.State
    processor: str
    def __init__(self, state: _Optional[_Union[TicketState.State, str]] = ..., processor: _Optional[str] = ...) -> None: ...

class ForwardRequest(_message.Message):
    __slots__ = ("host", "port", "gateways")
    HOST_FIELD_NUMBER: _ClassVar[int]
    PORT_FIELD_NUMBER: _ClassVar[int]
    GATEWAYS_FIELD_NUMBER: _ClassVar[int]
    host: str
    port: int
    gateways: _containers.RepeatedCompositeFieldContainer[_common_pb2.Gateway]
    def __init__(self, host: _Optional[str] = ..., port: _Optional[int] = ..., gateways: _Optional[_Iterable[_Union[_common_pb2.Gateway, _Mapping]]] = ...) -> None: ...

class ForwardDeleteRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class ForwardResponse(_message.Message):
    __slots__ = ("status", "id", "host", "port")
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    HOST_FIELD_NUMBER: _ClassVar[int]
    PORT_FIELD_NUMBER: _ClassVar[int]
    status: Status
    id: str
    host: str
    port: int
    def __init__(self, status: _Optional[_Union[Status, _Mapping]] = ..., id: _Optional[str] = ..., host: _Optional[str] = ..., port: _Optional[int] = ...) -> None: ...

class PublicSettingResponse(_message.Message):
    __slots__ = ("status", "data")
    STATUS_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    status: Status
    data: _common_pb2.PublicSetting
    def __init__(self, status: _Optional[_Union[Status, _Mapping]] = ..., data: _Optional[_Union[_common_pb2.PublicSetting, _Mapping]] = ...) -> None: ...

class Empty(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ListenPortResponse(_message.Message):
    __slots__ = ("status", "ports")
    STATUS_FIELD_NUMBER: _ClassVar[int]
    PORTS_FIELD_NUMBER: _ClassVar[int]
    status: Status
    ports: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, status: _Optional[_Union[Status, _Mapping]] = ..., ports: _Optional[_Iterable[int]] = ...) -> None: ...

class PortInfoRequest(_message.Message):
    __slots__ = ("port",)
    PORT_FIELD_NUMBER: _ClassVar[int]
    port: int
    def __init__(self, port: _Optional[int] = ...) -> None: ...

class PortInfoResponse(_message.Message):
    __slots__ = ("status", "data")
    STATUS_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    status: Status
    data: PortInfo
    def __init__(self, status: _Optional[_Union[Status, _Mapping]] = ..., data: _Optional[_Union[PortInfo, _Mapping]] = ...) -> None: ...

class PortInfo(_message.Message):
    __slots__ = ("asset", "gateways")
    ASSET_FIELD_NUMBER: _ClassVar[int]
    GATEWAYS_FIELD_NUMBER: _ClassVar[int]
    asset: _common_pb2.Asset
    gateways: _containers.RepeatedCompositeFieldContainer[_common_pb2.Gateway]
    def __init__(self, asset: _Optional[_Union[_common_pb2.Asset, _Mapping]] = ..., gateways: _Optional[_Iterable[_Union[_common_pb2.Gateway, _Mapping]]] = ...) -> None: ...

class PortFailure(_message.Message):
    __slots__ = ("port", "reason")
    PORT_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    port: int
    reason: str
    def __init__(self, port: _Optional[int] = ..., reason: _Optional[str] = ...) -> None: ...

class PortFailureRequest(_message.Message):
    __slots__ = ("data",)
    DATA_FIELD_NUMBER: _ClassVar[int]
    data: _containers.RepeatedCompositeFieldContainer[PortFailure]
    def __init__(self, data: _Optional[_Iterable[_Union[PortFailure, _Mapping]]] = ...) -> None: ...

class CookiesRequest(_message.Message):
    __slots__ = ("cookies",)
    COOKIES_FIELD_NUMBER: _ClassVar[int]
    cookies: _containers.RepeatedCompositeFieldContainer[_common_pb2.Cookie]
    def __init__(self, cookies: _Optional[_Iterable[_Union[_common_pb2.Cookie, _Mapping]]] = ...) -> None: ...

class UserResponse(_message.Message):
    __slots__ = ("status", "data")
    STATUS_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    status: Status
    data: _common_pb2.User
    def __init__(self, status: _Optional[_Union[Status, _Mapping]] = ..., data: _Optional[_Union[_common_pb2.User, _Mapping]] = ...) -> None: ...

class SessionLifecycleLogRequest(_message.Message):
    __slots__ = ("session_id", "event", "reason", "user")
    class EventType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        AssetConnectSuccess: _ClassVar[SessionLifecycleLogRequest.EventType]
        AssetConnectFinished: _ClassVar[SessionLifecycleLogRequest.EventType]
        CreateShareLink: _ClassVar[SessionLifecycleLogRequest.EventType]
        UserJoinSession: _ClassVar[SessionLifecycleLogRequest.EventType]
        UserLeaveSession: _ClassVar[SessionLifecycleLogRequest.EventType]
        AdminJoinMonitor: _ClassVar[SessionLifecycleLogRequest.EventType]
        AdminExitMonitor: _ClassVar[SessionLifecycleLogRequest.EventType]
        ReplayConvertStart: _ClassVar[SessionLifecycleLogRequest.EventType]
        ReplayConvertSuccess: _ClassVar[SessionLifecycleLogRequest.EventType]
        ReplayConvertFailure: _ClassVar[SessionLifecycleLogRequest.EventType]
        ReplayUploadStart: _ClassVar[SessionLifecycleLogRequest.EventType]
        ReplayUploadSuccess: _ClassVar[SessionLifecycleLogRequest.EventType]
        ReplayUploadFailure: _ClassVar[SessionLifecycleLogRequest.EventType]
    AssetConnectSuccess: SessionLifecycleLogRequest.EventType
    AssetConnectFinished: SessionLifecycleLogRequest.EventType
    CreateShareLink: SessionLifecycleLogRequest.EventType
    UserJoinSession: SessionLifecycleLogRequest.EventType
    UserLeaveSession: SessionLifecycleLogRequest.EventType
    AdminJoinMonitor: SessionLifecycleLogRequest.EventType
    AdminExitMonitor: SessionLifecycleLogRequest.EventType
    ReplayConvertStart: SessionLifecycleLogRequest.EventType
    ReplayConvertSuccess: SessionLifecycleLogRequest.EventType
    ReplayConvertFailure: SessionLifecycleLogRequest.EventType
    ReplayUploadStart: SessionLifecycleLogRequest.EventType
    ReplayUploadSuccess: SessionLifecycleLogRequest.EventType
    ReplayUploadFailure: SessionLifecycleLogRequest.EventType
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    EVENT_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    event: SessionLifecycleLogRequest.EventType
    reason: str
    user: str
    def __init__(self, session_id: _Optional[str] = ..., event: _Optional[_Union[SessionLifecycleLogRequest.EventType, str]] = ..., reason: _Optional[str] = ..., user: _Optional[str] = ...) -> None: ...
