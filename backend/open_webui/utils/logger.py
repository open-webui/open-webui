from datetime import timedelta
import json
from typing import Literal, Optional, TYPE_CHECKING, Protocol
import logging
import sys

from loguru import logger
from pydantic import TypeAdapter

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
        print(record["extra"])
        record["extra"].pop("auditable", None)

        extra = record["extra"].copy()
        log_level = record["level"].name

        event_user_id = extra.pop("event_user_id", None)
        source_ip = extra.pop("source_ip", None)
        object_id = extra.pop("object_id", None)
        object_type = extra.pop("object_type", None)
        user_api_key = extra.pop("user_api_key", None)
        request_uri = extra.pop("request_uri", None)
        user_agent = extra.pop("user_agent", None)
        request_info_data = extra.pop("request_info", None)
        response_info_data = extra.pop("response_info", None)

        request_info = (
            RequestInfo(**request_info_data)
            if isinstance(request_info_data, dict)
            else request_info_data
        )
        response_info = (
            ResponseInfo(**response_info_data)
            if isinstance(response_info_data, dict)
            else response_info_data
        )

        event_message = record["message"]
        if isinstance(event_message, AUDIT_EVENT):
            event = event_message
        else:
            event = AUDIT_EVENT(event_message)

        self.audit_log_table.create_log(
            log_level=log_level,
            event=event,
            event_user_id=event_user_id,
            source_ip=source_ip,
            object_id=object_id,
            object_type=object_type,
            user_api_key=user_api_key,
            request_uri=request_uri,
            user_agent=user_agent,
            request_info=request_info,
            response_info=response_info,
            extra=extra,
        )


class Identifiable(Protocol):
    id: str


class AuditLogger:
    def __init__(
        self,
        logger: "Logger",
        *,
        event_user_id: Optional[str] = None,
        user_api_key: Optional[str] = None,
    ):
        self.logger = logger.bind(auditable=True)
        self.event_user_id = event_user_id
        self.user_api_key = user_api_key

    def __call__(
        self,
        event: AUDIT_EVENT,
        *,
        level: str = "INFO",
        event_user_id: Optional[str] = None,
        source_ip: Optional[str] = None,
        object_id: Optional[str] = None,
        object_type: Optional[str] = None,
        user_api_key: Optional[str] = None,
        request_uri: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_info: Optional[RequestInfo] = None,
        response_info: Optional[ResponseInfo] = None,
        extra: Optional[dict] = None,
        **kwargs,
    ):
        if event_user_id is None:
            event_user_id = self.event_user_id
        if user_api_key is None:
            user_api_key = self.user_api_key

        log_extra = {
            "event_user_id": event_user_id,
            "source_ip": source_ip,
            "object_id": object_id,
            "object_type": object_type,
            "user_api_key": user_api_key,
            "request_uri": request_uri,
            "user_agent": user_agent,
            "request_info": (
                request_info.model_dump()
                if isinstance(request_info, RequestInfo)
                else request_info
            ),
            "response_info": (
                response_info.model_dump()
                if isinstance(response_info, ResponseInfo)
                else response_info
            ),
        }
        # making sure all values in log_extra are JSON serializable
        for key, value in log_extra.items():
            if isinstance(value, (RequestInfo, ResponseInfo)):
                log_extra[key] = value.model_dump()
            elif not isinstance(value, (str, int, float, bool, type(None), dict, list)):
                log_extra[key] = str(value)
        if extra:
            log_extra.update(extra)

        self.logger.log(
            level,
            event.value,
            **log_extra,
            **kwargs,
        )

    def write(
        self,
        action: Literal[
            AUDIT_EVENT.ENTITY_CREATED,
            AUDIT_EVENT.ENTITY_UPDATED,
            AUDIT_EVENT.ENTITY_DELETED,
        ],
        obj: Identifiable,
        *,
        object_type: Optional[str] = None,
        event_user_id: Optional[str] = None,
        **kwargs,
    ) -> None:
        if event_user_id is None:
            event_user_id = self.event_user_id

        self(
            action,
            object_id=obj.id,
            object_type=object_type,
            event_user_id=event_user_id,
            **kwargs,
        )


def start_logger():
    logger.remove()

    logger.add(
        sys.stdout,
        level=GLOBAL_LOG_LEVEL,
        format=stdout_format,
        filter=lambda record: "auditable" not in record["extra"],
    )

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
        serialize=True,
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
