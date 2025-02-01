import json
import logging
import sys
from typing import TYPE_CHECKING, Optional

from loguru import logger

from open_webui.models.audits import UserAuditInfo
from open_webui.env import (
    AUDIT_LOG_FILE_ROTATION_SIZE,
    AUDIT_LOGS_FILE_PATH,
    GLOBAL_LOG_LEVEL,
)
from open_webui.models.users import UserModel


if TYPE_CHECKING:
    from loguru import Logger, Message, Record


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


class AuditLogger:
    def __init__(self, logger: "Logger", user: UserModel):
        self.logger = logger.bind(auditable=True)
        self.user = user

    def write(
        self,
        api_version: str,
        open_webui_version,
        http_method: str,
        audit_level: str,
        resource: str,
        source_ip: str,
        user_agent: str,
        request_uri: str,
        *,
        user: Optional[UserModel] = None,
        log_level: str = "INFO",
        request_object: Optional[dict] = None,
        response_object: Optional[dict] = None,
        extra: Optional[dict] = None,
    ):

        user = user or self.user

        if request_object and "headers" in request_object:
            request_object["headers"].pop("Authorization", None)

        log_extra = {
            "user": user.model_dump(),
            "api_version": api_version,
            "open_webui_version": open_webui_version,
            "http_method": http_method,
            "audit_level": audit_level,
            "resource": resource,
            "source_ip": source_ip,
            "user_agent": user_agent,
            "request_uri": request_uri,
            "request_object": request_object,
            "response_object": response_object,
            "extra": extra,
        }

        if extra:
            log_extra.update(extra)

        event = self._format_event(resource, http_method)

        self.logger.log(
            log_level,
            event,
            **log_extra,
        )

    def _format_event(self, resource: str, method: str) -> str:
        return f"RESOURCE_{resource}_{method}_EVENT"


def file_format(record: "Record"):

    user = record["extra"].get("user", dict())
    user_audit_info = UserAuditInfo.model_validate(user)

    audit_data = {
        "timestamp": int(record["time"].timestamp()),
        "user": user_audit_info.model_dump(),
        "api_version": record["extra"].get("api_version"),
        "http_method": record["extra"].get("http_method"),
        "audit_level": record["extra"].get("audit_level"),
        "log_level": record["level"].name,
        "resource": record["extra"].get("resource"),
        "source_ip": record["extra"].get("source_ip"),
        "user_agent": record["extra"].get("user_agent"),
        "request_uri": record["extra"].get("request_uri"),
        "request_object": record["extra"].get("request_object"),
        "response_object": record["extra"].get("response_object"),
        "extra": record["extra"].get("extra", {}),
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
            AUDIT_LOGS_FILE_PATH,
            level=GLOBAL_LOG_LEVEL,
            rotation=AUDIT_LOG_FILE_ROTATION_SIZE,
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
