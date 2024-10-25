import json
import logging
import sys
from datetime import timedelta
from typing import Any, Optional, Protocol, TYPE_CHECKING, Union

from loguru import logger
from pydantic import TypeAdapter
from pydantic.json import pydantic_encoder

from open_webui.apps.webui.models.users import UserModel
from open_webui.apps.webui.models.audits import (
    AuditLogs,
    AuditLogsTable,
    RequestInfo,
    ResponseInfo,
)
from open_webui.constants import AUDIT_EVENT
from open_webui.env import (
    AUDIT_LOG_FILE_ROTATION_SIZE,
    AUDIT_LOG_RETENTION_PERIOD,
    AUDIT_LOGS_FILE_PATH,
    GLOBAL_LOG_LEVEL,
)

if TYPE_CHECKING:
    from loguru import Logger, Record, Message


def stdout_format(record: "Record") -> str:
    record["extra"]["extra_json"] = json.dumps(record["extra"])
    return (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level> - {extra[extra_json]}"
        "\n{exception}"
    )


class InterceptHandler(logging.Handler):
    """
    Intercepts log records from Python's standard logging module
    and redirects them to Loguru's logger.
    """

    def emit(self, record):
        """
        Called by the standard logging module for each log event.
        It transforms the standard `LogRecord` into a format compatible with Loguru
        and passes it to Loguru's logger.
        """
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


class DatabaseAuditLogHandler:
    def __init__(self, audit_logs_table: AuditLogsTable):
        self.audit_log_table = audit_logs_table

    def __call__(self, message: "Message") -> None:
        record = message.record
        # Make a copy of 'extra' instead of modifying it in place
        extra = record["extra"].copy()
        extra.pop("auditable", None)

        log_level = record["level"].name

        fields = [
            "admin_id",
            "source_ip",
            "object_id",
            "object_type",
            "admin_api_key",
            "request_uri",
            "user_agent",
            "request_info",
            "response_info",
        ]
        extracted = {field: extra.pop(field, None) for field in fields}

        for key in ["request_info", "response_info"]:
            data = extracted[key]
            if isinstance(data, dict):
                try:
                    extracted[key] = (
                        RequestInfo(**data)
                        if key == "request_info"
                        else ResponseInfo(**data)
                    )
                except Exception as e:
                    logger.exception(f"Failed to parse {key}: {e}")
                    extracted[key] = None

        event_message = record["message"]
        try:
            event = (
                AUDIT_EVENT(event_message)
                if not isinstance(event_message, AUDIT_EVENT)
                else event_message
            )
        except ValueError:
            logger.error(f"Invalid audit event: {event_message}")
            return

        self.audit_log_table.create_log(
            log_level=log_level,
            event=event,
            **extracted,
            extra=extra,
        )


class Identifiable(Protocol):
    id: str


class AuditLogger:
    def __init__(self, logger: "Logger", *, admin: Optional[UserModel] = None):
        self.logger = logger.bind(auditable=True)
        self.admin = admin

    def __call__(
        self,
        event: AUDIT_EVENT,
        *,
        level: str = "INFO",
        admin: Optional[UserModel] = None,
        source_ip: Optional[str] = None,
        object_id: Optional[str] = None,
        object_type: Optional[str] = None,
        request_uri: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_info: Optional[RequestInfo] = None,
        response_info: Optional[ResponseInfo] = None,
        extra: Optional[dict] = None,
    ):
        admin = admin or self.admin

        log_extra = {
            "admin_id": admin.id if admin else None,
            "admin_api_key": admin.api_key if admin else None,
            "source_ip": source_ip,
            "object_id": object_id,
            "object_type": object_type,
            "request_uri": request_uri,
            "user_agent": user_agent,
            "request_info": request_info,
            "response_info": response_info,
        }

        log_extra = json.loads(json.dumps(log_extra, default=pydantic_encoder))

        if extra:
            log_extra.update(extra)

        if admin:
            log_extra["admin_action"] = True

        self.logger.log(
            level,
            event.value,
            **log_extra,
        )

    def write(
        self,
        action: AUDIT_EVENT,
        obj: Union[str, Any, None] = None,
        object_type: Optional[str] = None,
        admin: Optional[UserModel] = None,
        **kwargs,
    ) -> None:
        if admin is None:
            admin = self.admin

        if isinstance(obj, str) or obj is None:
            object_id = obj
        elif hasattr(obj, "id") and isinstance(obj.id, str):
            object_id = obj.id
        else:
            raise TypeError(f"Unsupported type for obj: {type(obj)}")

        self(
            action,
            object_id=object_id,
            object_type=object_type,
            admin=admin,
            **kwargs,
        )


def file_format(record):
    audit_data = {
        "timestamp": int(record["time"].timestamp()),
        "log_level": record["level"].name,
        "event": record["message"],
        "extra": record["extra"].get("extra", {}),
        "source_ip": record["extra"].get("source_ip"),
        "object_id": record["extra"].get("object_id"),
        "object_type": record["extra"].get("object_type"),
        "admin_id": record["extra"].get("admin_id"),
        "admin_api_key": record["extra"].get("admin_api_key"),
        "request_uri": record["extra"].get("request_uri"),
        "user_agent": record["extra"].get("user_agent"),
        "request_info": record["extra"].get("request_info"),
        "response_info": record["extra"].get("response_info"),
    }

    record["extra"]["file_extra"] = json.dumps(audit_data, default=str)
    return "{extra[file_extra]}\n"


def start_logger(enable_audit_logging: bool):
    logger.remove()

    logger.add(
        sys.stdout,
        level=GLOBAL_LOG_LEVEL,
        format=stdout_format,
        filter=lambda record: "auditable" not in record["extra"],
    )

    if enable_audit_logging:
        logger.add(
            DatabaseAuditLogHandler(AuditLogs),
            level=GLOBAL_LOG_LEVEL,
            filter=lambda r: r["extra"].get("auditable") is True,
        )
        retention_period_str = AUDIT_LOG_RETENTION_PERIOD
        timedelta_adapter = TypeAdapter(timedelta)

        try:
            retention_period = timedelta_adapter.validate_python(retention_period_str)
        except Exception:
            logger.exception(f"Invalid retention period format: {retention_period_str}")
            retention_period = timedelta(days=30)

        logger.add(
            AUDIT_LOGS_FILE_PATH,
            level=GLOBAL_LOG_LEVEL,
            rotation=AUDIT_LOG_FILE_ROTATION_SIZE,
            retention=retention_period,
            compression="zip",
            format=file_format,
            filter=lambda record: record["extra"].get("auditable") is True,
        )

    logging.basicConfig(
        handlers=[InterceptHandler()], level=GLOBAL_LOG_LEVEL, force=True
    )
    for uvicorn_logger_name in ["uvicorn", "uvicorn.error"]:
        uvicorn_logger = logging.getLogger(uvicorn_logger_name)
        uvicorn_logger.setLevel(GLOBAL_LOG_LEVEL)
        uvicorn_logger.handlers = []
    for uvicorn_logger_name in ["uvicorn.access"]:
        uvicorn_logger = logging.getLogger(uvicorn_logger_name)
        uvicorn_logger.setLevel(GLOBAL_LOG_LEVEL)
        uvicorn_logger.handlers = [InterceptHandler()]

    logger.info(f"GLOBAL_LOG_LEVEL: {GLOBAL_LOG_LEVEL}")
