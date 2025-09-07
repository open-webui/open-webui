from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TaskAction(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    KillSession: _ClassVar[TaskAction]
    LockSession: _ClassVar[TaskAction]
    UnlockSession: _ClassVar[TaskAction]
    TokenPermExpired: _ClassVar[TaskAction]
    TokenPermValid: _ClassVar[TaskAction]

class RiskLevel(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    Normal: _ClassVar[RiskLevel]
    Warning: _ClassVar[RiskLevel]
    Reject: _ClassVar[RiskLevel]
    ReviewReject: _ClassVar[RiskLevel]
    ReviewAccept: _ClassVar[RiskLevel]
    ReviewCancel: _ClassVar[RiskLevel]
KillSession: TaskAction
LockSession: TaskAction
UnlockSession: TaskAction
TokenPermExpired: TaskAction
TokenPermValid: TaskAction
Normal: RiskLevel
Warning: RiskLevel
Reject: RiskLevel
ReviewReject: RiskLevel
ReviewAccept: RiskLevel
ReviewCancel: RiskLevel

class User(_message.Message):
    __slots__ = ("id", "name", "username", "role", "is_valid", "is_active")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    IS_VALID_FIELD_NUMBER: _ClassVar[int]
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    username: str
    role: str
    is_valid: bool
    is_active: bool
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., username: _Optional[str] = ..., role: _Optional[str] = ..., is_valid: bool = ..., is_active: bool = ...) -> None: ...

class Account(_message.Message):
    __slots__ = ("id", "name", "username", "secret", "secretType")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    SECRET_FIELD_NUMBER: _ClassVar[int]
    SECRETTYPE_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    username: str
    secret: str
    secretType: LabelValue
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., username: _Optional[str] = ..., secret: _Optional[str] = ..., secretType: _Optional[_Union[LabelValue, _Mapping]] = ...) -> None: ...

class LabelValue(_message.Message):
    __slots__ = ("label", "value")
    LABEL_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    label: str
    value: str
    def __init__(self, label: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...

class Asset(_message.Message):
    __slots__ = ("id", "name", "address", "org_id", "org_name", "protocols", "specific")
    class Specific(_message.Message):
        __slots__ = ("db_name", "use_ssl", "ca_cert", "client_cert", "client_key", "allow_invalid_cert", "auto_fill", "username_selector", "password_selector", "submit_selector", "script", "http_proxy", "pg_ssl_mode")
        DB_NAME_FIELD_NUMBER: _ClassVar[int]
        USE_SSL_FIELD_NUMBER: _ClassVar[int]
        CA_CERT_FIELD_NUMBER: _ClassVar[int]
        CLIENT_CERT_FIELD_NUMBER: _ClassVar[int]
        CLIENT_KEY_FIELD_NUMBER: _ClassVar[int]
        ALLOW_INVALID_CERT_FIELD_NUMBER: _ClassVar[int]
        AUTO_FILL_FIELD_NUMBER: _ClassVar[int]
        USERNAME_SELECTOR_FIELD_NUMBER: _ClassVar[int]
        PASSWORD_SELECTOR_FIELD_NUMBER: _ClassVar[int]
        SUBMIT_SELECTOR_FIELD_NUMBER: _ClassVar[int]
        SCRIPT_FIELD_NUMBER: _ClassVar[int]
        HTTP_PROXY_FIELD_NUMBER: _ClassVar[int]
        PG_SSL_MODE_FIELD_NUMBER: _ClassVar[int]
        db_name: str
        use_ssl: bool
        ca_cert: str
        client_cert: str
        client_key: str
        allow_invalid_cert: bool
        auto_fill: str
        username_selector: str
        password_selector: str
        submit_selector: str
        script: str
        http_proxy: str
        pg_ssl_mode: str
        def __init__(self, db_name: _Optional[str] = ..., use_ssl: bool = ..., ca_cert: _Optional[str] = ..., client_cert: _Optional[str] = ..., client_key: _Optional[str] = ..., allow_invalid_cert: bool = ..., auto_fill: _Optional[str] = ..., username_selector: _Optional[str] = ..., password_selector: _Optional[str] = ..., submit_selector: _Optional[str] = ..., script: _Optional[str] = ..., http_proxy: _Optional[str] = ..., pg_ssl_mode: _Optional[str] = ...) -> None: ...
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    ORG_NAME_FIELD_NUMBER: _ClassVar[int]
    PROTOCOLS_FIELD_NUMBER: _ClassVar[int]
    SPECIFIC_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    address: str
    org_id: str
    org_name: str
    protocols: _containers.RepeatedCompositeFieldContainer[Protocol]
    specific: Asset.Specific
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., address: _Optional[str] = ..., org_id: _Optional[str] = ..., org_name: _Optional[str] = ..., protocols: _Optional[_Iterable[_Union[Protocol, _Mapping]]] = ..., specific: _Optional[_Union[Asset.Specific, _Mapping]] = ...) -> None: ...

class Protocol(_message.Message):
    __slots__ = ("name", "id", "port")
    NAME_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    PORT_FIELD_NUMBER: _ClassVar[int]
    name: str
    id: int
    port: int
    def __init__(self, name: _Optional[str] = ..., id: _Optional[int] = ..., port: _Optional[int] = ...) -> None: ...

class Gateway(_message.Message):
    __slots__ = ("id", "name", "ip", "port", "protocol", "username", "password", "private_key")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    IP_FIELD_NUMBER: _ClassVar[int]
    PORT_FIELD_NUMBER: _ClassVar[int]
    PROTOCOL_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    PASSWORD_FIELD_NUMBER: _ClassVar[int]
    PRIVATE_KEY_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    ip: str
    port: int
    protocol: str
    username: str
    password: str
    private_key: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., ip: _Optional[str] = ..., port: _Optional[int] = ..., protocol: _Optional[str] = ..., username: _Optional[str] = ..., password: _Optional[str] = ..., private_key: _Optional[str] = ...) -> None: ...

class Permission(_message.Message):
    __slots__ = ("enable_connect", "enable_download", "enable_upload", "enable_copy", "enable_paste")
    ENABLE_CONNECT_FIELD_NUMBER: _ClassVar[int]
    ENABLE_DOWNLOAD_FIELD_NUMBER: _ClassVar[int]
    ENABLE_UPLOAD_FIELD_NUMBER: _ClassVar[int]
    ENABLE_COPY_FIELD_NUMBER: _ClassVar[int]
    ENABLE_PASTE_FIELD_NUMBER: _ClassVar[int]
    enable_connect: bool
    enable_download: bool
    enable_upload: bool
    enable_copy: bool
    enable_paste: bool
    def __init__(self, enable_connect: bool = ..., enable_download: bool = ..., enable_upload: bool = ..., enable_copy: bool = ..., enable_paste: bool = ...) -> None: ...

class CommandACL(_message.Message):
    __slots__ = ("id", "name", "priority", "action", "is_active", "command_groups")
    class Action(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        Reject: _ClassVar[CommandACL.Action]
        Accept: _ClassVar[CommandACL.Action]
        Review: _ClassVar[CommandACL.Action]
        Warning: _ClassVar[CommandACL.Action]
        NotifyWarning: _ClassVar[CommandACL.Action]
        Unknown: _ClassVar[CommandACL.Action]
    Reject: CommandACL.Action
    Accept: CommandACL.Action
    Review: CommandACL.Action
    Warning: CommandACL.Action
    NotifyWarning: CommandACL.Action
    Unknown: CommandACL.Action
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    ACTION_FIELD_NUMBER: _ClassVar[int]
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    COMMAND_GROUPS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    priority: int
    action: CommandACL.Action
    is_active: bool
    command_groups: _containers.RepeatedCompositeFieldContainer[CommandGroup]
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., priority: _Optional[int] = ..., action: _Optional[_Union[CommandACL.Action, str]] = ..., is_active: bool = ..., command_groups: _Optional[_Iterable[_Union[CommandGroup, _Mapping]]] = ...) -> None: ...

class CommandGroup(_message.Message):
    __slots__ = ("id", "name", "content", "Type", "pattern", "ignore_case")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    PATTERN_FIELD_NUMBER: _ClassVar[int]
    IGNORE_CASE_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    content: str
    Type: str
    pattern: str
    ignore_case: bool
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., content: _Optional[str] = ..., Type: _Optional[str] = ..., pattern: _Optional[str] = ..., ignore_case: bool = ...) -> None: ...

class ExpireInfo(_message.Message):
    __slots__ = ("expire_at",)
    EXPIRE_AT_FIELD_NUMBER: _ClassVar[int]
    expire_at: int
    def __init__(self, expire_at: _Optional[int] = ...) -> None: ...

class Session(_message.Message):
    __slots__ = ("id", "user", "asset", "account", "login_from", "remote_addr", "protocol", "date_start", "org_id", "user_id", "asset_id", "account_id", "token_id")
    class LoginFrom(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        WT: _ClassVar[Session.LoginFrom]
        ST: _ClassVar[Session.LoginFrom]
        RT: _ClassVar[Session.LoginFrom]
        DT: _ClassVar[Session.LoginFrom]
    WT: Session.LoginFrom
    ST: Session.LoginFrom
    RT: Session.LoginFrom
    DT: Session.LoginFrom
    ID_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    ASSET_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_FIELD_NUMBER: _ClassVar[int]
    LOGIN_FROM_FIELD_NUMBER: _ClassVar[int]
    REMOTE_ADDR_FIELD_NUMBER: _ClassVar[int]
    PROTOCOL_FIELD_NUMBER: _ClassVar[int]
    DATE_START_FIELD_NUMBER: _ClassVar[int]
    ORG_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    ASSET_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    TOKEN_ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    user: str
    asset: str
    account: str
    login_from: Session.LoginFrom
    remote_addr: str
    protocol: str
    date_start: int
    org_id: str
    user_id: str
    asset_id: str
    account_id: str
    token_id: str
    def __init__(self, id: _Optional[str] = ..., user: _Optional[str] = ..., asset: _Optional[str] = ..., account: _Optional[str] = ..., login_from: _Optional[_Union[Session.LoginFrom, str]] = ..., remote_addr: _Optional[str] = ..., protocol: _Optional[str] = ..., date_start: _Optional[int] = ..., org_id: _Optional[str] = ..., user_id: _Optional[str] = ..., asset_id: _Optional[str] = ..., account_id: _Optional[str] = ..., token_id: _Optional[str] = ...) -> None: ...

class TokenStatus(_message.Message):
    __slots__ = ("code", "detail", "is_expired")
    CODE_FIELD_NUMBER: _ClassVar[int]
    DETAIL_FIELD_NUMBER: _ClassVar[int]
    IS_EXPIRED_FIELD_NUMBER: _ClassVar[int]
    code: str
    detail: str
    is_expired: bool
    def __init__(self, code: _Optional[str] = ..., detail: _Optional[str] = ..., is_expired: bool = ...) -> None: ...

class TerminalTask(_message.Message):
    __slots__ = ("id", "action", "session_id", "terminated_by", "created_by", "token_status")
    ID_FIELD_NUMBER: _ClassVar[int]
    ACTION_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    TERMINATED_BY_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    TOKEN_STATUS_FIELD_NUMBER: _ClassVar[int]
    id: str
    action: TaskAction
    session_id: str
    terminated_by: str
    created_by: str
    token_status: TokenStatus
    def __init__(self, id: _Optional[str] = ..., action: _Optional[_Union[TaskAction, str]] = ..., session_id: _Optional[str] = ..., terminated_by: _Optional[str] = ..., created_by: _Optional[str] = ..., token_status: _Optional[_Union[TokenStatus, _Mapping]] = ...) -> None: ...

class TokenAuthInfo(_message.Message):
    __slots__ = ("key_id", "secrete_id", "asset", "user", "account", "permission", "expire_info", "filter_rules", "gateways", "setting", "platform", "FaceMonitorToken")
    KEY_ID_FIELD_NUMBER: _ClassVar[int]
    SECRETE_ID_FIELD_NUMBER: _ClassVar[int]
    ASSET_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_FIELD_NUMBER: _ClassVar[int]
    PERMISSION_FIELD_NUMBER: _ClassVar[int]
    EXPIRE_INFO_FIELD_NUMBER: _ClassVar[int]
    FILTER_RULES_FIELD_NUMBER: _ClassVar[int]
    GATEWAYS_FIELD_NUMBER: _ClassVar[int]
    SETTING_FIELD_NUMBER: _ClassVar[int]
    PLATFORM_FIELD_NUMBER: _ClassVar[int]
    FACEMONITORTOKEN_FIELD_NUMBER: _ClassVar[int]
    key_id: str
    secrete_id: str
    asset: Asset
    user: User
    account: Account
    permission: Permission
    expire_info: ExpireInfo
    filter_rules: _containers.RepeatedCompositeFieldContainer[CommandACL]
    gateways: _containers.RepeatedCompositeFieldContainer[Gateway]
    setting: ComponentSetting
    platform: Platform
    FaceMonitorToken: str
    def __init__(self, key_id: _Optional[str] = ..., secrete_id: _Optional[str] = ..., asset: _Optional[_Union[Asset, _Mapping]] = ..., user: _Optional[_Union[User, _Mapping]] = ..., account: _Optional[_Union[Account, _Mapping]] = ..., permission: _Optional[_Union[Permission, _Mapping]] = ..., expire_info: _Optional[_Union[ExpireInfo, _Mapping]] = ..., filter_rules: _Optional[_Iterable[_Union[CommandACL, _Mapping]]] = ..., gateways: _Optional[_Iterable[_Union[Gateway, _Mapping]]] = ..., setting: _Optional[_Union[ComponentSetting, _Mapping]] = ..., platform: _Optional[_Union[Platform, _Mapping]] = ..., FaceMonitorToken: _Optional[str] = ...) -> None: ...

class Platform(_message.Message):
    __slots__ = ("id", "name", "category", "charset", "type", "protocols")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CATEGORY_FIELD_NUMBER: _ClassVar[int]
    CHARSET_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    PROTOCOLS_FIELD_NUMBER: _ClassVar[int]
    id: int
    name: str
    category: str
    charset: str
    type: str
    protocols: _containers.RepeatedCompositeFieldContainer[PlatformProtocol]
    def __init__(self, id: _Optional[int] = ..., name: _Optional[str] = ..., category: _Optional[str] = ..., charset: _Optional[str] = ..., type: _Optional[str] = ..., protocols: _Optional[_Iterable[_Union[PlatformProtocol, _Mapping]]] = ...) -> None: ...

class PlatformProtocol(_message.Message):
    __slots__ = ("id", "name", "port", "settings")
    class SettingsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PORT_FIELD_NUMBER: _ClassVar[int]
    SETTINGS_FIELD_NUMBER: _ClassVar[int]
    id: int
    name: str
    port: int
    settings: _containers.ScalarMap[str, str]
    def __init__(self, id: _Optional[int] = ..., name: _Optional[str] = ..., port: _Optional[int] = ..., settings: _Optional[_Mapping[str, str]] = ...) -> None: ...

class ComponentSetting(_message.Message):
    __slots__ = ("max_idle_time", "max_session_time")
    MAX_IDLE_TIME_FIELD_NUMBER: _ClassVar[int]
    MAX_SESSION_TIME_FIELD_NUMBER: _ClassVar[int]
    max_idle_time: int
    max_session_time: int
    def __init__(self, max_idle_time: _Optional[int] = ..., max_session_time: _Optional[int] = ...) -> None: ...

class Forward(_message.Message):
    __slots__ = ("id", "Host", "port")
    ID_FIELD_NUMBER: _ClassVar[int]
    HOST_FIELD_NUMBER: _ClassVar[int]
    PORT_FIELD_NUMBER: _ClassVar[int]
    id: str
    Host: str
    port: int
    def __init__(self, id: _Optional[str] = ..., Host: _Optional[str] = ..., port: _Optional[int] = ...) -> None: ...

class PublicSetting(_message.Message):
    __slots__ = ("xpack_enabled", "valid_license", "gpt_base_url", "gpt_api_key", "gpt_proxy", "gpt_model", "license_content")
    XPACK_ENABLED_FIELD_NUMBER: _ClassVar[int]
    VALID_LICENSE_FIELD_NUMBER: _ClassVar[int]
    GPT_BASE_URL_FIELD_NUMBER: _ClassVar[int]
    GPT_API_KEY_FIELD_NUMBER: _ClassVar[int]
    GPT_PROXY_FIELD_NUMBER: _ClassVar[int]
    GPT_MODEL_FIELD_NUMBER: _ClassVar[int]
    LICENSE_CONTENT_FIELD_NUMBER: _ClassVar[int]
    xpack_enabled: bool
    valid_license: bool
    gpt_base_url: str
    gpt_api_key: str
    gpt_proxy: str
    gpt_model: str
    license_content: str
    def __init__(self, xpack_enabled: bool = ..., valid_license: bool = ..., gpt_base_url: _Optional[str] = ..., gpt_api_key: _Optional[str] = ..., gpt_proxy: _Optional[str] = ..., gpt_model: _Optional[str] = ..., license_content: _Optional[str] = ...) -> None: ...

class Cookie(_message.Message):
    __slots__ = ("name", "value")
    NAME_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    name: str
    value: str
    def __init__(self, name: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...

class LifecycleLogData(_message.Message):
    __slots__ = ("event", "reason", "user")
    class event_type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        AssetConnectSuccess: _ClassVar[LifecycleLogData.event_type]
        AssetConnectFinished: _ClassVar[LifecycleLogData.event_type]
        CreateShareLink: _ClassVar[LifecycleLogData.event_type]
        UserJoinSession: _ClassVar[LifecycleLogData.event_type]
        UserLeaveSession: _ClassVar[LifecycleLogData.event_type]
        AdminJoinMonitor: _ClassVar[LifecycleLogData.event_type]
        AdminExitMonitor: _ClassVar[LifecycleLogData.event_type]
        ReplayConvertStart: _ClassVar[LifecycleLogData.event_type]
        ReplayConvertSuccess: _ClassVar[LifecycleLogData.event_type]
        ReplayConvertFailure: _ClassVar[LifecycleLogData.event_type]
        ReplayUploadStart: _ClassVar[LifecycleLogData.event_type]
        ReplayUploadSuccess: _ClassVar[LifecycleLogData.event_type]
        ReplayUploadFailure: _ClassVar[LifecycleLogData.event_type]
    AssetConnectSuccess: LifecycleLogData.event_type
    AssetConnectFinished: LifecycleLogData.event_type
    CreateShareLink: LifecycleLogData.event_type
    UserJoinSession: LifecycleLogData.event_type
    UserLeaveSession: LifecycleLogData.event_type
    AdminJoinMonitor: LifecycleLogData.event_type
    AdminExitMonitor: LifecycleLogData.event_type
    ReplayConvertStart: LifecycleLogData.event_type
    ReplayConvertSuccess: LifecycleLogData.event_type
    ReplayConvertFailure: LifecycleLogData.event_type
    ReplayUploadStart: LifecycleLogData.event_type
    ReplayUploadSuccess: LifecycleLogData.event_type
    ReplayUploadFailure: LifecycleLogData.event_type
    EVENT_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    event: LifecycleLogData.event_type
    reason: str
    user: str
    def __init__(self, event: _Optional[_Union[LifecycleLogData.event_type, str]] = ..., reason: _Optional[str] = ..., user: _Optional[str] = ...) -> None: ...
